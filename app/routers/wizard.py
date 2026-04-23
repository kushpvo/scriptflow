import os
from fastapi import APIRouter, Form, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Annotated
from app.database import get_db
from app.models import Repo, Job, EnvVar
from app import github, uv_manager
from app.routers.jobs import process_manager
from app.scheduler import add_cron_job, remove_cron_job
from app.routers.jobs import process_manager as _process_manager
from app.uv_manager import venv_python

router = APIRouter(prefix="/api/wizard", tags=["wizard"])


@router.post("/clone", response_class=HTMLResponse)
async def wizard_clone(
    github_url: Annotated[str, Form()],
    github_token: Annotated[str, Form()] = "",
    repo_name: Annotated[str, Form()] = "",
    db: Session = Depends(get_db),
):
    token = github_token.strip() or None
    repo = db.query(Repo).filter_by(github_url=github_url).first()
    if not repo:
        repo = Repo(name=repo_name or github_url.split("/")[-1],
                    github_url=github_url, github_token=token)
        db.add(repo)
        db.commit()
        db.refresh(repo)
    elif token and token != repo.github_token:
        repo.github_token = token
        db.commit()
    try:
        await github.clone_repo(repo.id, github_url, token or repo.github_token)
    except RuntimeError as e:
        return HTMLResponse(f'<option disabled>Error: {e}</option>', status_code=200)
    files = github.scan_py_files(repo.id)
    options = "\n".join(f'<option value="{f}">{f}</option>' for f in files)
    return HTMLResponse(f'<input type="hidden" name="repo_id" value="{repo.id}">{options}')


@router.post("/deploy")
async def wizard_deploy(
    request: Request,
    db: Session = Depends(get_db),
):
    form = await request.form()
    repo_id = int(form.get("repo_id", 0))
    entrypoint = form.get("entrypoint", "")
    python_version = form.get("python_version", "3.12")
    run_mode = form.get("run_mode", "forever")
    cron_expression = form.get("cron_expression") or None
    extra_args = form.get("extra_args") or None
    restart_on_crash = "restart_on_crash" in form
    auto_pull = "auto_pull" in form
    notification_url = form.get("notification_url") or None
    notify_on_stderr = "notify_on_stderr" in form
    job_name = form.get("job_name") or entrypoint.replace("/", "_").replace(".py", "")

    keys = form.getlist("env_key")
    values = form.getlist("env_value")
    env_pairs = [(k.strip(), v) for k, v in zip(keys, values) if k.strip()]

    repo = db.get(Repo, repo_id)
    if not repo:
        return RedirectResponse("/jobs/new?error=repo_not_found", status_code=302)

    job = Job(
        repo_id=repo_id, name=job_name, entrypoint=entrypoint,
        python_version=python_version, run_mode=run_mode,
        cron_expression=cron_expression, extra_args=extra_args,
        restart_on_crash=restart_on_crash, auto_pull=auto_pull,
        notification_url=notification_url, notify_on_stderr=notify_on_stderr,
        status="idle",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    for key, value in env_pairs:
        db.add(EnvVar(job_id=job.id, key=key, value=value))
    db.commit()
    db.refresh(job)

    try:
        await uv_manager.create_venv(job.id, python_version)
        await uv_manager.install_requirements(job.id, repo_id)
    except RuntimeError as e:
        job.status = "install_failed"
        db.commit()
        return RedirectResponse(f"/?error=install_failed&job={job.id}", status_code=302)

    data_dir = os.environ.get("DATA_DIR", "/data")
    cmd = [str(venv_python(job.id)),
           os.path.join(data_dir, "repos", str(repo_id), entrypoint)]
    if extra_args:
        cmd += extra_args.split()
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}
    env.update({k: v for k, v in env_pairs})

    if run_mode == "forever":
        await process_manager.start(job.id, cmd, env, restart_on_crash,
                                    notification_url, notify_on_stderr)
        job.status = "running"
    else:
        add_cron_job(job.id, cron_expression, cmd, env, notification_url)
        job.status = "idle"
    db.commit()
    return RedirectResponse("/", status_code=302)


@router.post("/update/{job_id}")
async def wizard_update(
    job_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    form = await request.form()
    entrypoint = form.get("entrypoint", "")
    python_version = form.get("python_version", "3.12")
    run_mode = form.get("run_mode", "forever")
    cron_expression = form.get("cron_expression") or None
    extra_args = form.get("extra_args") or None
    restart_on_crash = "restart_on_crash" in form
    auto_pull = "auto_pull" in form
    notification_url = form.get("notification_url") or None
    notify_on_stderr = "notify_on_stderr" in form
    job_name = form.get("job_name") or entrypoint.replace("/", "_").replace(".py", "")

    keys = form.getlist("env_key")
    values = form.getlist("env_value")
    env_pairs = [(k.strip(), v) for k, v in zip(keys, values) if k.strip()]

    job = db.get(Job, job_id)
    if not job:
        return RedirectResponse("/?error=job_not_found", status_code=302)

    old_run_mode = job.run_mode
    job.name = job_name
    job.entrypoint = entrypoint
    job.python_version = python_version
    job.run_mode = run_mode
    job.cron_expression = cron_expression
    job.extra_args = extra_args
    job.restart_on_crash = restart_on_crash
    job.auto_pull = auto_pull
    job.notification_url = notification_url
    job.notify_on_stderr = notify_on_stderr

    db.query(EnvVar).filter(EnvVar.job_id == job_id).delete()
    for key, value in env_pairs:
        db.add(EnvVar(job_id=job_id, key=key, value=value))
    db.commit()
    db.refresh(job)

    # Rebuild venv and reinstall requirements
    try:
        await uv_manager.create_venv(job_id, python_version, fresh=True)
        await uv_manager.install_requirements(job_id, job.repo_id)
    except RuntimeError as e:
        job.status = "install_failed"
        db.commit()
        return RedirectResponse(f"/?error=install_failed&job={job_id}", status_code=302)

    data_dir = os.environ.get("DATA_DIR", "/data")
    cmd = [str(venv_python(job_id)),
           os.path.join(data_dir, "repos", str(job.repo_id), entrypoint)]
    if extra_args:
        cmd += extra_args.split()
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}
    env.update({k: v for k, v in env_pairs})

    # Stop old scheduler/process
    if old_run_mode == "cron":
        remove_cron_job(job_id)
    else:
        await _process_manager.stop(job_id)

    # Start under new mode
    if run_mode == "forever":
        await _process_manager.start(job_id, cmd, env, restart_on_crash,
                                     notification_url, notify_on_stderr)
        job.status = "running"
    else:
        add_cron_job(job_id, cron_expression, cmd, env, notification_url)
        job.status = "idle"
    db.commit()
    return RedirectResponse("/", status_code=302)
