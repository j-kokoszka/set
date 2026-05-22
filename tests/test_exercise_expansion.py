from fastapi.testclient import TestClient
from backend.main import app, external_exercises_cache
import uuid

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
