import os
import pytest
from datetime import date
from app.log_utils import write_log_line


@pytest.fixture
def repo_and_job(client, monkeypatch):
    import app.github as gh
    import app.uv_manager as uvm
    async def fake_clone(*a, **kw): return "/tmp/f"
    async def fake_venv(*a, **kw): return "/tmp/v"
    async def fake_install(*a, **kw): return None
    monkeypatch.setattr(gh, "clone_repo", fake_clone)
    monkeypatch.setattr(uvm, "create_venv", fake_venv)
    monkeypatch.setattr(uvm, "install_requirements", fake_install)
    resp = client.post("/api/repos", json={"name": "r", "github_url": "https://github.com/u/r"})
    repo = resp.json()
    resp = client.post("/api/jobs", json={
        "repo_id": repo["id"], "name": "j", "entrypoint": "main.py",
        "python_version": "3.12", "run_mode": "forever",
    })
    return {"repo": repo, "job": resp.json()}


def test_get_log_dates(client, repo_and_job, tmp_data_dir):
    job_id = repo_and_job["job"]["id"]
    write_log_line(job_id, "stdout", "hello")
    resp = client.get(f"/api/jobs/{job_id}/logs/dates")
    assert resp.status_code == 200
    assert isinstance(resp.json()["dates"], list)


def test_get_log_content(client, repo_and_job, tmp_data_dir):
    job_id = repo_and_job["job"]["id"]
    write_log_line(job_id, "stdout", "hello world")
    today = date.today().isoformat()
    resp = client.get(f"/api/jobs/{job_id}/logs?date={today}")
    assert resp.status_code == 200
    assert "hello world" in resp.text


def test_get_log_invalid_date(client, repo_and_job):
    job_id = repo_and_job["job"]["id"]
    resp = client.get(f"/api/jobs/{job_id}/logs?date=not-a-date")
    assert resp.status_code == 400


def test_stream_logs_sse_content_type(client, repo_and_job, tmp_data_dir, db):
    job_id = repo_and_job["job"]["id"]
    write_log_line(job_id, "stdout", "hello")
    # Directly invoke the router function to check it returns a StreamingResponse
    # with the correct media_type, without hitting the async streaming body
    from app.routers.logs import stream_logs
    from fastapi.responses import StreamingResponse
    import asyncio

    result = asyncio.run(stream_logs(job_id, db))
    assert isinstance(result, StreamingResponse)
    assert result.media_type == "text/event-stream"
