from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import date as _date
import asyncio
from app.database import get_db
from app.models import Job
from app.log_utils import read_log_file, list_log_dates

router = APIRouter(prefix="/api/jobs", tags=["logs"])


@router.get("/{job_id}/logs/dates")
def get_log_dates(job_id: int, db: Session = Depends(get_db)):
    if not db.get(Job, job_id):
        raise HTTPException(404, "Job not found")
    return {"dates": list_log_dates(job_id)}


@router.get("/{job_id}/logs")
def get_log(
    job_id: int,
    date: str = Query(default=None),
    stream: str = Query(default="both"),
    db: Session = Depends(get_db),
):
    if not db.get(Job, job_id):
        raise HTTPException(404, "Job not found")
    if date is None:
        date = _date.today().isoformat()
    try:
        parsed_date = _date.fromisoformat(date)
    except ValueError:
        raise HTTPException(400, "Invalid date format, use YYYY-MM-DD")
    lines = read_log_file(job_id, parsed_date, stream_filter=stream)
    return {"lines": lines}


@router.get("/{job_id}/logs/stream")
async def stream_logs(job_id: int, db: Session = Depends(get_db)):
    if not db.get(Job, job_id):
        raise HTTPException(404, "Job not found")

    async def event_generator():
        sent = 0
        while True:
            lines = read_log_file(job_id, _date.today())
            for line in lines[sent:]:
                yield f"data: {line}\n\n"
            sent = len(lines)
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")