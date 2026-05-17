from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_delete_nonexistent_plan():
    headers = {"Authorization": "Bearer mock_testuser"}
    # Delete a non-existent UUID-like plan ID
    resp = client.delete("/plans/00000000-0000-0000-0000-000000000000", headers=headers)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Plan not found"

def test_delete_plan_unauthorized():
    # No auth header
    resp = client.delete("/plans/some-id")
    assert resp.status_code == 401

