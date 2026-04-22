from pydantic import BaseModel, model_validator
from typing import Optional
from datetime import datetime
from croniter import croniter, CroniterBadCronError


def _validate_cron_expression(expr: str) -> None:
    """Validate a cron expression field-by-field.

    Valid ranges: minute=0-59, hour=0-23, day=1-31, month=1-12, dow=0-6.
    Raises ValueError naming the bad field if any field is invalid.
    """
    parts = expr.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression: expected 5 fields, got {len(parts)}")
    minute, hour, day, month, dow = parts
    try:
        croniter(expr, datetime.now())
    except (CroniterBadCronError, KeyError, ValueError):
        # Validate each field individually to name the bad field
        for i, (val, field, lo, hi) in enumerate(
            [(minute, "minute", 0, 59),
             (hour, "hour", 0, 23),
             (day, "day of month", 1, 31),
             (month, "month", 1, 12),
             (dow, "day of week", 0, 6)]
        ):
            if val == "*":
                continue
            if "/" in val:
                base = val.split("/")[0]
                if base != "*":
                    try:
                        v = int(base)
                        if v < lo or v > hi:
                            raise ValueError
                    except ValueError:
                        raise ValueError(f"'{val}' is not a valid {field} value (must be {lo}-{hi})")
                continue
            try:
                v = int(val)
                if v < lo or v > hi:
                    raise ValueError
            except ValueError:
                raise ValueError(f"'{val}' is not a valid {field} value (must be {lo}-{hi})")
        raise ValueError(f"{expr!r} is not a valid cron expression")


class EnvVarIn(BaseModel):
    key: str
    value: str


class RepoCreate(BaseModel):
    name: str
    github_url: str
    github_token: Optional[str] = None
    auto_pull: bool = False


class RepoOut(BaseModel):
    id: int
    name: str
    github_url: str
    auto_pull: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class JobCreate(BaseModel):
    repo_id: int
    name: str
    entrypoint: str
    python_version: str = "3.12"
    run_mode: str = "forever"
    cron_expression: Optional[str] = None
    extra_args: Optional[str] = None
    restart_on_crash: bool = True
    auto_pull: bool = False
    notification_url: Optional[str] = None
    notify_on_stderr: bool = False
    env_vars: list[EnvVarIn] = []

    @model_validator(mode="after")
    def cron_requires_expression(self) -> "JobCreate":
        if self.run_mode == "cron" and not self.cron_expression:
            raise ValueError("cron_expression is required when run_mode is 'cron'")
        if self.cron_expression:
            _validate_cron_expression(self.cron_expression)
        return self


class JobUpdate(BaseModel):
    repo_id: int
    name: str
    entrypoint: str
    python_version: str = "3.12"
    run_mode: str = "forever"
    cron_expression: Optional[str] = None
    extra_args: Optional[str] = None
    restart_on_crash: bool = True
    auto_pull: bool = False
    notification_url: Optional[str] = None
    notify_on_stderr: bool = False
    env_vars: list[EnvVarIn] = []

    @model_validator(mode="after")
    def cron_requires_expression(self) -> "JobUpdate":
        if self.run_mode == "cron" and not self.cron_expression:
            raise ValueError("cron_expression is required when run_mode is 'cron'")
        if self.cron_expression:
            _validate_cron_expression(self.cron_expression)
        return self


class JobOut(BaseModel):
    id: int
    repo_id: int
    name: str
    entrypoint: str
    python_version: str
    run_mode: str
    cron_expression: Optional[str]
    extra_args: Optional[str]
    restart_on_crash: bool
    auto_pull: bool
    status: str
    notification_url: Optional[str]
    notify_on_stderr: bool
    created_at: datetime
    env_vars: list[EnvVarIn] = []
    model_config = {"from_attributes": True}


class SettingsOut(BaseModel):
    default_python_version: str
    default_notification_url: Optional[str]
    log_retention_days: int
    model_config = {"from_attributes": True}
