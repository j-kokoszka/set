from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_plan_lifecycle():
    # 1. Create a plan
    plan_payload = {
        "name": "Push Day",
        "exercises": [
            {
                "exercise_name": "Bench Press",
                "sets": [{"reps": 10, "weight": 60}]
            }
        ]
    }
    headers = {"Authorization": "Bearer mock_testuser"}
    resp = client.post("/plans", json=plan_payload, headers=headers)
    assert resp.status_code == 200
    plan = resp.json()
    assert plan["name"] == "Push Day"
    assert plan["id"] is not None
    plan_id = plan["id"]

    # 2. List plans
    resp = client.get("/plans", headers=headers)
    assert resp.status_code == 200
    plans = resp.json()
    assert len(plans) >= 1
    assert any(p["id"] == plan_id for p in plans)

    # 3. Update plan
    plan["name"] = "Push Day v2"
    resp = client.put(f"/plans/{plan_id}", json=plan, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Push Day v2"

    # 4. Delete plan
    resp = client.delete(f"/plans/{plan_id}", headers=headers)
    assert resp.status_code == 200
    
    # 5. Verify deletion
    resp = client.get("/plans", headers=headers)
    assert not any(p["id"] == plan_id for p in resp.json())

