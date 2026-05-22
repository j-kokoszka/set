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
    user_id = "test_user"
    headers = {"Authorization": f"Bearer mock_{user_id}"}
    
    # Mocking httpx.Response explicitly
    with patch("backend.main.http_client.get") as mock_get:
        # Create a real-looking mock response
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
        
        async def mock_async_get(*args, **kwargs):
            return mock_resp
            
        mock_get.side_effect = mock_async_get
        
        resp = client.get("/exercises/search?q=row", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data is not None
        assert len(data) == 1
        assert data[0]["name"] == "External Row"
        assert data[0]["is_external"] is True
        assert data[0]["id"] == "wger-12345"

def test_external_search_unauthorized():
    resp = client.get("/exercises/search?q=row")
    assert resp.status_code == 401 
