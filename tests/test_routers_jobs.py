import pytest


@pytest.fixture
def repo(client, monkeypatch):
    import app.github as gh
    async def fake_clone(*a, **kw): return "/tmp/fake"
    monkeypatch.setattr(gh, "clone_repo", fake_clone)
    resp = client.post("/api/repos", json={"name": "r", "github_url": "https://github.com/u/r"})
    return resp.json()


def test_create_job(client, repo, monkeypatch):
    import app.uv_manager as uvm
    async def fake_venv(*a, **kw): return "/tmp/v"
    async def fake_install(*a, **kw): return None
    monkeypatch.setattr(uvm, "create_venv", fake_venv)
    monkeypatch.setattr(uvm, "install_requirements", fake_install)
    resp = client.post("/api/jobs", json={
        "repo_id": repo["id"], "name": "myjob",
        "entrypoint": "main.py", "python_version": "3.12",
        "run_mode": "forever",
    })
    assert resp.status_code == 201
    assert resp.json()["name"] == "myjob"


def test_list_jobs(client, repo, monkeypatch):
    import app.uv_manager as uvm
    async def fake_venv(*a, **kw): return "/tmp/v"
    async def fake_install(*a, **kw): return None
    monkeypatch.setattr(uvm, "create_venv", fake_venv)
    monkeypatch.setattr(uvm, "install_requirements", fake_install)
    client.post("/api/jobs", json={
        "repo_id": repo["id"], "name": "j2",
        "entrypoint": "main.py", "python_version": "3.12", "run_mode": "cron",
        "cron_expression": "0 9 * * *",
    })
    resp = client.get("/api/jobs")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_update_job(client, repo, monkeypatch):
    import app.uv_manager as uvm
    async def fake_venv(*a, **kw): return "/tmp/v"
    async def fake_install(*a, **kw): return None
    monkeypatch.setattr(uvm, "create_venv", fake_venv)
    monkeypatch.setattr(uvm, "install_requirements", fake_install)
    create_resp = client.post("/api/jobs", json={
        "repo_id": repo["id"], "name": "updateme",
        "entrypoint": "main.py", "python_version": "3.12",
        "run_mode": "forever",
    })
    job_id = create_resp.json()["id"]
    resp = client.put(f"/api/jobs/{job_id}", json={
        "repo_id": repo["id"], "name": "updated",
        "entrypoint": "main.py", "python_version": "3.12",
        "run_mode": "forever",
    })
    assert resp.status_code == 200
    assert resp.json()["name"] == "updated"


def test_update_job_invalid_cron(client, repo, monkeypatch):
    import app.uv_manager as uvm
    async def fake_venv(*a, **kw): return "/tmp/v"
    async def fake_install(*a, **kw): return None
    monkeypatch.setattr(uvm, "create_venv", fake_venv)
    monkeypatch.setattr(uvm, "install_requirements", fake_install)
    create_resp = client.post("/api/jobs", json={
        "repo_id": repo["id"], "name": "badcron",
        "entrypoint": "main.py", "python_version": "3.12",
        "run_mode": "forever",
    })
    job_id = create_resp.json()["id"]
    resp = client.put(f"/api/jobs/{job_id}", json={
        "repo_id": repo["id"], "name": "badcron",
        "entrypoint": "main.py", "python_version": "3.12",
        "run_mode": "cron",
        "cron_expression": "invalid",
    })
    assert resp.status_code == 422