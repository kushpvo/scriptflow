import os
from datetime import datetime, date, timedelta
from pathlib import Path


def _data_dir() -> str:
    return os.environ.get("DATA_DIR", "/data")


def _log_path(job_id: int, log_date: date) -> str:
    return os.path.join(_data_dir(), "logs", str(job_id), f"{log_date.isoformat()}.log")


def write_log_line(job_id: int, stream: str, message: str) -> None:
    log_date = datetime.now().date()
    path = _log_path(job_id, log_date)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"{ts} [{stream}] {message}\n")


def read_log_file(job_id: int, log_date: date, stream_filter: str = "both") -> list[str]:
    path = _log_path(job_id, log_date)
    if not os.path.exists(path):
        return []
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if stream_filter == "both":
                lines.append(line.rstrip())
            elif f"[{stream_filter}]" in line:
                lines.append(line.rstrip())
    return lines


def list_log_dates(job_id: int) -> list[str]:
    log_dir = os.path.join(_data_dir(), "logs", str(job_id))
    if not os.path.exists(log_dir):
        return []
    dates = sorted(
        f.stem for f in Path(log_dir).glob("*.log")
    )
    return dates


def rotate_logs(retention_days: int = 30) -> int:
    cutoff = datetime.now().date() - timedelta(days=retention_days)
    logs_root = os.path.join(_data_dir(), "logs")
    deleted = 0
    if not os.path.exists(logs_root):
        return 0
    for job_dir in Path(logs_root).iterdir():
        for log_file in job_dir.glob("*.log"):
            try:
                file_date = date.fromisoformat(log_file.stem)
                if file_date < cutoff:
                    log_file.unlink()
                    deleted += 1
            except ValueError:
                pass
    return deleted