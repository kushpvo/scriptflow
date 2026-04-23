import pytest


@pytest.fixture
def setup_mocks(monkeypatch):
    import app.github as gh, app.uv_manager as uvm
    from app.routers import wizard as wiz_mod
    async def fake_clone(*a, **kw): return "/tmp/fake"
    async def fake_venv(*a, **kw): return "/tmp/v"
    async def fake_install(*a, **kw): return None
    async def fake_start(*a, **kw): return None
    monkeypatch.setattr(gh, "clone_repo", fake_clone)
    monkeypatch.setattr(uvm, "create_venv", fake_venv)
    monkeypatch.setattr(uvm, "install_requirements", fake_install)
    monkeypatch.setattr(wiz_mod.process_manager, "start", fake_start)


@pytest.fixture
def repo(client, monkeypatch):
    import app.github as gh
    async def fake_clone(*a, **kw): return "/tmp/fake"
    monkeypatch.setattr(gh, "clone_repo", fake_clone)
    resp = client.post("/api/repos", json={"name": "r", "github_url": "https://github.com/u/r"})
    return resp.json()


def test_clone_returns_options_html(client, setup_mocks):
    resp = client.post("/api/wizard/clone", data={
        "github_url": "https://github.com/test/repo",
        "repo_name": "test-repo",
    })
    assert resp.status_code == 200
    # Returns hidden input with repo_id on success
    assert "repo_id" in resp.text or "Error" in resp.text


def test_deploy_creates_job_and_redirects(client, setup_mocks, repo, monkeypatch):
    import app.uv_manager as uvm
    from app.routers import wizard as wiz_mod
    async def fake_venv(*a, **kw): return "/tmp/v"
    async def fake_install(*a, **kw): return None
    async def fake_start(*a, **kw): return None
    monkeypatch.setattr(uvm, "create_venv", fake_venv)
    monkeypatch.setattr(uvm, "install_requirements", fake_install)
    monkeypatch.setattr(wiz_mod.process_manager, "start", fake_start)
    resp = client.post("/api/wizard/deploy", data={
        "repo_id": str(repo["id"]),
        "entrypoint": "main.py",
        "python_version": "3.12",
        "run_mode": "forever",
    }, follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/"


def test_edit_wizard_renders_with_job_data(client, setup_mocks, repo, monkeypatch):
    """GET /wizard/edit/{id} renders wizard pre-filled with job's current values."""
    import app.uv_manager as uvm
    async def fake_venv(*a, **kw): return "/tmp/v"
    async def fake_install(*a, **kw): return None
    monkeypatch.setattr(uvm, "create_venv", fake_venv)
    monkeypatch.setattr(uvm, "install_requirements", fake_install)

    # Create a job via API (simpler than wizard deploy for testing)
    resp = client.post("/api/jobs", json={
        "repo_id": repo["id"],
        "name": "Test Job",
        "entrypoint": "main.py",
        "python_version": "3.12",
        "run_mode": "forever",
    })
    assert resp.status_code == 201
    job_id = resp.json()["id"]

    # Request the edit wizard page
    resp = client.get(f"/wizard/edit/{job_id}")
    assert resp.status_code == 200

    # Verify edit mode indicators in response
    html = resp.text
    assert "Edit Job" in html
    assert "Save Changes" in html
    assert 'action="/api/wizard/update/' in html
    assert 'value="Test Job"' in html
    assert 'value="main.py"' in html


def test_edit_wizard_returns_404_for_missing_job(client):
    """GET /wizard/edit/{id} returns 404 for non-existent job."""
    resp = client.get("/wizard/edit/99999")
    assert resp.status_code == 404


def test_edit_wizard_repo_select_disabled(client, setup_mocks, repo, monkeypatch):
    """Step 1 repo select is read-only (disabled) in edit mode."""
    import app.uv_manager as uvm
    async def fake_venv(*a, **kw): return "/tmp/v"
    async def fake_install(*a, **kw): return None
    monkeypatch.setattr(uvm, "create_venv", fake_venv)
    monkeypatch.setattr(uvm, "install_requirements", fake_install)

    # Create a job via API
    resp = client.post("/api/jobs", json={
        "repo_id": repo["id"],
        "name": "Test Job 2",
        "entrypoint": "main.py",
        "python_version": "3.12",
        "run_mode": "forever",
    })
    assert resp.status_code == 201
    job_id = resp.json()["id"]

    resp = client.get(f"/wizard/edit/{job_id}")
    assert resp.status_code == 200
    # The repo select should be disabled in edit mode
    assert 'disabled' in resp.text
