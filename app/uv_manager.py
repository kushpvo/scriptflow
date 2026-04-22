import asyncio
import os
import shutil
from pathlib import Path


def _data_dir() -> str:
    return os.environ.get("DATA_DIR", "/data")


def _venv_path(job_id: int) -> Path:
    return Path(_data_dir()) / "venvs" / str(job_id)


async def create_venv(job_id: int, python_version: str = "3.12", fresh: bool = False) -> Path:
    venv_path = _venv_path(job_id)
    if fresh and venv_path.exists():
        shutil.rmtree(venv_path)
    if not fresh and venv_python(job_id).exists():
        return venv_path
    venv_path.parent.mkdir(parents=True, exist_ok=True)
    proc = await asyncio.create_subprocess_exec(
        "uv", "venv", str(venv_path), "--python", python_version,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(stderr.decode().strip())
    return venv_path


def venv_python(job_id: int) -> Path:
    return _venv_path(job_id) / "bin" / "python"


async def install_requirements(job_id: int, repo_id: int) -> str | None:
    req_path = Path(_data_dir()) / "repos" / str(repo_id) / "requirements.txt"
    if not req_path.exists():
        return None
    venv_path = _venv_path(job_id)
    proc = await asyncio.create_subprocess_exec(
        "uv", "pip", "install", "--python", str(venv_python(job_id)), "-r", str(req_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(stderr.decode().strip())
    return stdout.decode()