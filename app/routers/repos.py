import os
import shutil
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Repo
from app.schemas import RepoCreate, RepoOut
from app import github

router = APIRouter(prefix="/api/repos", tags=["repos"])


@router.get("", response_model=list[RepoOut])
def list_repos(db: Session = Depends(get_db)):
    return db.query(Repo).all()


@router.post("", response_model=RepoOut, status_code=201)
async def create_repo(payload: RepoCreate, db: Session = Depends(get_db)):
    repo = Repo(**payload.model_dump())
    db.add(repo)
    db.commit()
    db.refresh(repo)
    try:
        await github.clone_repo(repo.id, repo.github_url, repo.github_token)
    except RuntimeError as e:
        db.delete(repo)
        db.commit()
        raise HTTPException(status_code=422, detail=str(e))
    return repo


@router.delete("/{repo_id}", status_code=204)
def delete_repo(repo_id: int, db: Session = Depends(get_db)):
    repo = db.get(Repo, repo_id)
    if not repo:
        raise HTTPException(404, "Repo not found")
    data_dir = os.environ.get("DATA_DIR", "/data")
    job_ids = [job.id for job in repo.jobs]
    db.delete(repo)
    db.commit()
    shutil.rmtree(os.path.join(data_dir, "repos", str(repo_id)), ignore_errors=True)
    for job_id in job_ids:
        shutil.rmtree(os.path.join(data_dir, "venvs", str(job_id)), ignore_errors=True)
        shutil.rmtree(os.path.join(data_dir, "logs", str(job_id)), ignore_errors=True)


@router.post("/{repo_id}/pull")
async def pull_repo(repo_id: int, db: Session = Depends(get_db)):
    repo = db.get(Repo, repo_id)
    if not repo:
        raise HTTPException(404, "Repo not found")
    try:
        result = await github.pull_repo(repo.id, repo.github_url, repo.github_token)
    except RuntimeError as e:
        raise HTTPException(422, str(e))
    return {"result": result}


@router.get("/{repo_id}/scan")
def scan_repo(repo_id: int, db: Session = Depends(get_db)):
    repo = db.get(Repo, repo_id)
    if not repo:
        raise HTTPException(404, "Repo not found")
    files = github.scan_py_files(repo_id)
    return {"files": files}