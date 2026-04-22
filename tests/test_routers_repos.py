import pytest


def test_list_repos_empty(client):
    resp = client.get("/api/repos")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_repo_bad_url(client, monkeypatch):
    import app.github as gh
    async def bad_clone(*a, **kw):
        raise RuntimeError("not found")
    monkeypatch.setattr(gh, "clone_repo", bad_clone)
    resp = client.post("/api/repos", json={
        "name": "test", "github_url": "https://github.com/bad/repo"
    })
    assert resp.status_code == 422


def test_create_and_delete_repo(client, monkeypatch):
    import app.github as gh
    async def fake_clone(*a, **kw): return "/tmp/fake"
    monkeypatch.setattr(gh, "clone_repo", fake_clone)
    resp = client.post("/api/repos", json={
        "name": "myrepo", "github_url": "https://github.com/u/r"
    })
    assert resp.status_code == 201
    repo_id = resp.json()["id"]
    resp2 = client.delete(f"/api/repos/{repo_id}")
    assert resp2.status_code == 204
    assert client.get("/api/repos").json() == []