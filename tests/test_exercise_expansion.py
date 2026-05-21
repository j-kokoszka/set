import pytest
from fastapi.testclient import TestClient
from backend.main import app
import uuid
from unittest.mock import patch, MagicMock

client = TestClient(app)

def test_custom_exercise_lifecycle():
    user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    headers = {"Authorization": f"Bearer mock_{user_id}"}
    
    # 1. Create custom exercise
    payload = {
        "name": "Custom Deadlift",
        "category": "strength",
        "primaryMuscles": ["back"]
    }
    resp = client.post("/exercises/custom", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Custom Deadlift"
    assert data["id"].startswith("custom-")
    ex_id = data["id"]
    
    # 2. List custom exercises
    resp = client.get("/exercises/custom", headers=headers)
    assert resp.status_code == 200
    exercises = resp.json()
    assert any(ex["id"] == ex_id for ex in exercises)
    
    # 3. Delete custom exercise
    resp = client.delete(f"/exercises/custom/{ex_id}", headers=headers)
    assert resp.status_code == 200
    
    # 4. Verify deletion
    resp = client.get("/exercises/custom", headers=headers)
    assert resp.status_code == 200
    exercises = resp.json()
    assert not any(ex["id"] == ex_id for ex in exercises)

def test_external_search_mock():
    # Use a simpler approach by patching httpx.AsyncClient
    # Since we use TestClient (sync), we can just mock the response directly
    # and use a side_effect that returns a completed future or just mock the async method.
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "suggestions": [
                {
                    "value": "External Row",
                    "data": {
                        "id": 12345,
                        "name": "External Row",
                        "category": "Back"
                    }
                }
            ]
        }
        
        # Mock the __aenter__ and __aexit__ for context manager
        # But actually httpx.AsyncClient usage in main.py is:
        # async with httpx.AsyncClient(timeout=5.0) as client:
        #     response = await client.get(url)
        
        # A simpler way to test async code with TestClient is to mock the internal logic
        # OR just make the test function async and use anyio/asyncio.
        
        # Let's try to make it non-async in the test since TestClient is sync.
        from unittest.mock import AsyncMock
        mock_get.return_value = mock_resp
        
        resp = client.get("/exercises/search?q=row")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "External Row"
        assert data[0]["is_external"] is True
        assert data[0]["id"] == "wger-12345"
