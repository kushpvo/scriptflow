from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Job, Repo, AppSettings
from app.routers.jobs import process_manager

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    jobs = db.query(Job).all()
    for job in jobs:
        if job.run_mode == "forever":
            job.status = process_manager.get_status(job.id)
    return templates.TemplateResponse(request, "dashboard.html", {"jobs": jobs})


@router.get("/jobs/new", response_class=HTMLResponse)
def new_job_wizard(request: Request, db: Session = Depends(get_db)):
    repos = db.query(Repo).all()
    return templates.TemplateResponse(request, "wizard.html", {"repos": repos})


@router.get("/wizard/edit/{job_id}", response_class=HTMLResponse)
def edit_job_wizard(request: Request, job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    repos = db.query(Repo).all()
    return templates.TemplateResponse(request, "wizard.html", {
        "repos": repos,
        "job": job,
        "edit_mode": True,
    })


@router.get("/jobs/{job_id}/logs", response_class=HTMLResponse)
def log_viewer(job_id: int, request: Request, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    return templates.TemplateResponse(request, "log_viewer.html", {"job": job})


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, db: Session = Depends(get_db)):
    s = db.get(AppSettings, 1)
    return templates.TemplateResponse(request, "settings.html", {"settings": s})
