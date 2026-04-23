import asyncio
import os
import re
from pathlib import Path
from urllib.parse import quote


def _data_dir() -> str:
    return os.environ.get("DATA_DIR", "/data")


def _inject_token(url: str, token: str | None) -> str:
    if not token:
        return url
    return re.sub(r"https://", f"https://x-access-token:{quote(token, safe='')}@", url, count=1)


async def clone_repo(repo_id: int, github_url: str, token: str | None) -> str:
    dest = os.path.join(_data_dir(), "repos", str(repo_id))
    if os.path.exists(dest):
        return dest
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    url = _inject_token(github_url, token)
    proc = await asyncio.create_subprocess_exec(
        "git", "clone", url, dest,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(stderr.decode().strip())
    return dest


async def pull_repo(repo_id: int, github_url: str, token: str | None) -> str:
    dest = os.path.join(_data_dir(), "repos", str(repo_id))
    if not os.path.exists(dest):
        await clone_repo(repo_id, github_url, token)
        return "cloned"
    url = _inject_token(github_url, token)
    proc = await asyncio.create_subprocess_exec(
        "git", "-C", dest, "pull", url,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(stderr.decode().strip())
    return stdout.decode().strip()


EXCLUDE_DIRS = {"__pycache__", ".venv", "venv", ".git", "node_modules"}


def scan_py_files(repo_id: int) -> list[str]:
    root = Path(os.path.join(_data_dir(), "repos", str(repo_id)))
    results = []
    for path in root.rglob("*.py"):
        parts = set(path.relative_to(root).parts[:-1])
        if parts & EXCLUDE_DIRS:
            continue
        results.append(str(path.relative_to(root)))
    return sorted(results)