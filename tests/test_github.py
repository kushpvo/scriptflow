import os
import subprocess
import pytest
from app.github import clone_repo, pull_repo, scan_py_files, _inject_token


@pytest.fixture
def local_bare_repo(tmp_path):
    """Create a local git repo to clone from — no network needed."""
    bare = tmp_path / "bare"
    bare.mkdir()
    subprocess.run(["git", "init", "--bare", str(bare)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(bare), "symbolic-ref", "HEAD", "refs/heads/main"], check=True, capture_output=True)
    # Create a working copy, add files, push to bare
    work = tmp_path / "work"
    subprocess.run(["git", "clone", str(bare), str(work)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(work), "config", "user.email", "test@test.com"], check=True)
    subprocess.run(["git", "-C", str(work), "config", "user.name", "Test"], check=True)
    (work / "main.py").write_text("print('hello')")
    (work / "scripts").mkdir()
    (work / "scripts" / "worker.py").write_text("pass")
    (work / "__pycache__").mkdir()
    (work / "__pycache__" / "cached.py").write_text("pass")
    subprocess.run(["git", "-C", str(work), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(work), "commit", "-m", "init"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(work), "push", "origin", "HEAD:main"], check=True, capture_output=True)
    return str(bare)


def test_inject_token_inserts_correctly():
    url = "https://github.com/user/repo"
    result = _inject_token(url, "mytoken")
    assert result == "https://mytoken@github.com/user/repo"


def test_inject_token_no_token():
    url = "https://github.com/user/repo"
    assert _inject_token(url, None) == url


@pytest.mark.asyncio
async def test_clone_repo(tmp_data_dir, local_bare_repo):
    dest = await clone_repo(99, local_bare_repo, None)
    assert os.path.exists(dest)
    assert os.path.exists(os.path.join(dest, "main.py"))


@pytest.mark.asyncio
async def test_clone_repo_bad_url(tmp_data_dir):
    with pytest.raises(RuntimeError):
        await clone_repo(100, "/nonexistent/path", None)


@pytest.mark.asyncio
async def test_pull_repo(tmp_data_dir, local_bare_repo):
    await clone_repo(101, local_bare_repo, None)
    result = await pull_repo(101, local_bare_repo, None)
    assert result == "Already up to date."  # up to date


@pytest.mark.asyncio
async def test_scan_py_files(tmp_data_dir, local_bare_repo):
    await clone_repo(102, local_bare_repo, None)
    files = scan_py_files(102)
    # __pycache__ should be excluded
    assert "__pycache__/cached.py" not in files
    assert "main.py" in files
    assert "scripts/worker.py" in files


def test_scan_py_files_nonexistent_repo():
    assert scan_py_files(9999) == []