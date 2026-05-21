from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_delete_nonexistent_routine():
    headers = {"Authorization": "Bearer mock_testuser"}
    # Delete a non-existent UUID-like routine ID
    resp = client.delete("/routines/00000000-0000-0000-0000-000000000000", headers=headers)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Routine not found"

def test_delete_routine_unauthorized():
    # No auth header
    resp = client.delete("/routines/some-id")
    assert resp.status_code == 401

