from fastapi.testclient import TestClient
from backend.main import app, external_exercises_cache
import uuid
import json
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

def test_external_search_local_cache():
    user_id = "test_user"
    headers = {"Authorization": f"Bearer mock_{user_id}"}
    
    # Inject a mock exercise into the cache
    test_ex = {
        "id": "test-123",
        "name": "Cached Row Machine",
        "category": "strength",
        "primaryMuscles": ["back"]
    }
    external_exercises_cache.append(test_ex)
    
    try:
        resp = client.get("/exercises/search?q=Cached%20Row", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert any(ex["name"] == "Cached Row Machine" for ex in data)
        assert data[0]["is_external"] is True
    finally:
        # Clean up
        external_exercises_cache.remove(test_ex)

def test_external_search_unauthorized():
    resp = client.get("/exercises/search?q=row")
    assert resp.status_code == 401 

def test_external_search_error_502():
    user_id = "test_user"
    headers = {"Authorization": f"Bearer mock_{user_id}"}
    
    # Force an exception by patching the loop or cache access
    # Since main.py already loaded the cache, we patch it there
    with patch("backend.main.external_exercises_cache", [None]):
        resp = client.get("/exercises/search?q=row", headers=headers)
        assert resp.status_code == 502
        assert "Error communicating with external database" in resp.json()["detail"]

def test_suggest_custom_exercise_mock():
    user_id = "test_user"
    headers = {"Authorization": f"Bearer mock_{user_id}"}
    
    # Patch the global bedrock_client
    with patch("backend.main.bedrock_client") as mock_bedrock:
        mock_response = MagicMock()
        mock_response.get.return_value.read.return_value = json.dumps({
            "output": {
                "message": {
                    "content": [
                        {
                            "text": json.dumps({
                                "force": "pull",
                                "level": "intermediate",
                                "mechanic": "compound",
                                "equipment": "cable",
                                "primaryMuscles": ["lats"],
                                "secondaryMuscles": ["biceps"],
                                "instructions": ["Step 1", "Step 2"],
                                "category": "strength"
                            })
                        }
                    ]
                }
            }
        }).encode("utf-8")
        
        mock_bedrock.invoke_model.return_value = mock_response
        
        payload = {"name": "Lat Pulldown"}
        resp = client.post("/exercises/custom/suggest", json=payload, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["force"] == "pull"
        assert data["level"] == "intermediate"
        assert "lats" in data["primaryMuscles"]
        assert len(data["instructions"]) == 2
