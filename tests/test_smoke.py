def test_app_starts(client):
    resp = client.get("/")
    assert resp.status_code in (200, 404)  # 404 ok until routes wired
