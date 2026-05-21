from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_routine_lifecycle():
    # 1. Create a routine
    routine_payload = {
        "name": "Push Day",
        "exercises": [
            {
                "exercise_name": "Bench Press",
                "sets": [{"reps": 10, "weight": 60}]
            }
        ]
    }
    headers = {"Authorization": "Bearer mock_testuser"}
    resp = client.post("/routines", json=routine_payload, headers=headers)
    assert resp.status_code == 200
    routine = resp.json()
    assert routine["name"] == "Push Day"
    assert routine["id"] is not None
    routine_id = routine["id"]

    # 2. List routines
    resp = client.get("/routines", headers=headers)
    assert resp.status_code == 200
    routines = resp.json()
    assert len(routines) >= 1
    assert any(p["id"] == routine_id for p in routines)

    # 3. Update routine
    routine["name"] = "Push Day v2"
    resp = client.put(f"/routines/{routine_id}", json=routine, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Push Day v2"

    # 4. Delete routine
    resp = client.delete(f"/routines/{routine_id}", headers=headers)
    assert resp.status_code == 200
    
    # 5. Verify deletion
    resp = client.get("/routines", headers=headers)
    assert not any(p["id"] == routine_id for p in resp.json())

