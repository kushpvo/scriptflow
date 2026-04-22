from fastapi import APIRouter, Depends, Form
from fastapi.responses import RedirectResponse
from typing import Annotated
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import AppSettings
from app.schemas import SettingsOut

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _get_or_create_settings(db: Session) -> AppSettings:
    s = db.get(AppSettings, 1)
    if not s:
        s = AppSettings(id=1)
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


@router.get("", response_model=SettingsOut)
def get_settings(db: Session = Depends(get_db)):
    return _get_or_create_settings(db)


@router.post("", response_class=RedirectResponse)
def update_settings(
    default_python_version: Annotated[str, Form()],
    log_retention_days: Annotated[int, Form()],
    default_notification_url: Annotated[str, Form()] = "",
    db: Session = Depends(get_db),
):
    s = _get_or_create_settings(db)
    s.default_python_version = default_python_version
    s.log_retention_days = log_retention_days
    s.default_notification_url = default_notification_url or None
    db.commit()
    return RedirectResponse("/settings", status_code=302)