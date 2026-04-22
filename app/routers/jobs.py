import os
import shutil
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Job, EnvVar, Repo
from app.schemas import JobCreate, JobOut, JobUpdate
from app import uv_manager, github
from app.process_manager import ProcessManager
from app.scheduler import add_cron_job, remove_cron_job
from app.log_utils import write_log_line

process_manager = ProcessManager()

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _build_cmd(job: Job) -> list[str]:
    python = uv_manager.venv_python(job.id)
    entrypoint = os.path.join(os.environ.get("DATA_DIR", "/data"), "repos", str(job.repo_id), job.entrypoint)
    cmd = [str(python), entrypoint]
    if job.extra_args:
        cmd += job.extra_args.split()
    return cmd


def _build_env(job: Job) -> dict:
    base = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}
    base.update({ev.key: ev.value for ev in job.env_vars})
    return base


@router.get("", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db)):
    jobs = db.query(Job).all()
    for job in jobs:
        job.status = process_manager.get_status(job.id) if job.run_mode == "forever" else job.status
    return jobs


@router.post("", response_model=JobOut, status_code=201)
async def create_job(payload: JobCreate, db: Session = Depends(get_db)):
    repo = db.get(Repo, payload.repo_id)
    if not repo:
        raise HTTPException(404, "Repo not found")
    env_vars_data = payload.env_vars
    job_data = payload.model_dump(exclude={"env_vars"})
    job = Job(**job_data)
    db.add(job)
    db.commit()
    db.refresh(job)
    for ev in env_vars_data:
        db.add(EnvVar(job_id=job.id, key=ev.key, value=ev.value))
    db.commit()
    db.refresh(job)
    try:
        await uv_manager.create_venv(job.id, job.python_version)
        await uv_manager.install_requirements(job.id, job.repo_id)
    except RuntimeError as e:
        job.status = "install_failed"
        db.commit()
        raise HTTPException(422, f"Setup failed: {e}")
    return job


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.delete("/{job_id}", status_code=204)
async def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.run_mode == "forever":
        await process_manager.stop(job_id)
    else:
        remove_cron_job(job_id)
    data_dir = os.environ.get("DATA_DIR", "/data")
    for subdir in ("venvs", "logs"):
        path = os.path.join(data_dir, subdir, str(job_id))
        if os.path.exists(path):
            shutil.rmtree(path, ignore_errors=True)
    db.delete(job)
    db.commit()


@router.post("/{job_id}/start", status_code=204)
async def start_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.run_mode == "cron":
        add_cron_job(job_id, job.cron_expression, _build_cmd(job),
                     _build_env(job), job.notification_url)
        job.status = "idle"
        db.commit()
        return
    if job.auto_pull:
        write_log_line(job_id, "stdout", "--- Pulling latest code ---")
        await github.pull_repo(job.repo_id, job.repo.github_url, job.repo.github_token)
        write_log_line(job_id, "stdout", "--- Installing requirements ---")
        await uv_manager.create_venv(job_id, job.python_version, fresh=True)
        await uv_manager.install_requirements(job_id, job.repo_id)
    await process_manager.start(
        job_id, _build_cmd(job), _build_env(job),
        job.restart_on_crash, job.notification_url, job.notify_on_stderr,
    )
    job.status = "running"
    db.commit()


@router.post("/{job_id}/stop", status_code=204)
async def stop_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.run_mode == "cron":
        remove_cron_job(job_id)
        job.status = "idle"
    else:
        await process_manager.stop(job_id)
        job.status = "stopped"
    db.commit()


@router.put("/{job_id}", response_model=JobOut)
def update_job(job_id: int, payload: JobUpdate, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    old_run_mode = job.run_mode
    old_cron_expression = job.cron_expression
    env_vars_data = payload.env_vars
    job_data = payload.model_dump(exclude={"env_vars"})
    for key, value in job_data.items():
        setattr(job, key, value)
    db.query(EnvVar).filter(EnvVar.job_id == job_id).delete()
    for ev in env_vars_data:
        db.add(EnvVar(job_id=job.id, key=ev.key, value=ev.value))
    db.commit()
    db.refresh(job)
    if old_run_mode == "cron":
        remove_cron_job(job_id)
    if job.run_mode == "cron":
        add_cron_job(job_id, job.cron_expression, _build_cmd(job),
                     _build_env(job), job.notification_url)
    return job


@router.post("/{job_id}/restart", status_code=204)
async def restart_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.run_mode == "forever":
        await process_manager.restart(
            job_id, _build_cmd(job), _build_env(job),
            job.restart_on_crash, job.notification_url, job.notify_on_stderr,
        )
        job.status = "running"
        db.commit()
    else:
        raise HTTPException(422, "restart not supported for cron jobs")


@router.post("/{job_id}/sync", status_code=204)
async def sync_job(job_id: int, db: Session = Depends(get_db)):
    """Pull latest code, reinstall requirements, restart job."""
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    write_log_line(job_id, "stdout", "=== Sync started ===")

    write_log_line(job_id, "stdout", "--- Pulling latest code ---")
    try:
        result = await github.pull_repo(job.repo_id, job.repo.github_url, job.repo.github_token)
        write_log_line(job_id, "stdout", f"Pull: {result}")
    except RuntimeError as e:
        write_log_line(job_id, "stderr", f"Pull failed: {e}")
        raise HTTPException(422, f"Pull failed: {e}")

    write_log_line(job_id, "stdout", "--- Installing requirements ---")
    try:
        await uv_manager.create_venv(job_id, job.python_version, fresh=True)
        result = await uv_manager.install_requirements(job_id, job.repo_id)
        write_log_line(job_id, "stdout", result if result else "No requirements.txt found")
    except RuntimeError as e:
        write_log_line(job_id, "stderr", f"Install failed: {e}")
        raise HTTPException(422, f"Install failed: {e}")

    write_log_line(job_id, "stdout", "--- Restarting job ---")
    if job.run_mode == "forever":
        await process_manager.restart(
            job_id, _build_cmd(job), _build_env(job),
            job.restart_on_crash, job.notification_url, job.notify_on_stderr,
        )
        job.status = "running"
    else:
        job.status = "idle"
    db.commit()
    write_log_line(job_id, "stdout", "=== Sync complete ===")
