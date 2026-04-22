from datetime import datetime

from croniter import croniter
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/validate", tags=["validate"])


@router.get("/cron")
def validate_cron(expression: str = Query(...)):
    """Validate a cron expression. Replace + with spaces before parsing."""
    expr = expression.replace("+", " ")
    try:
        croniter(expr)
        return JSONResponse({"valid": True, "error": None})
    except Exception as e:
        return JSONResponse({"valid": False, "error": str(e)})


@router.get("/cron/nextrun")
def cron_nextrun(expression: str = Query(...)):
    """Get next run datetime for a cron expression. Replace + with spaces before parsing."""
    expr = expression.replace("+", " ")
    try:
        it = croniter(expr, datetime.now())
        next_run = it.get_next(datetime)
        return {"nextrun": next_run.isoformat()}
    except Exception:
        return {"nextrun": None}