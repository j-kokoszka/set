import pytest
from fastapi.testclient import TestClient
from backend.main import app
import uuid

client = TestClient(app)

def test_workout_lifecycle():
    user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    headers = {"Authorization": f"Bearer mock_{user_id}"}
    
    # 1. Health check
    resp = client.get("/health")
    assert resp.status_code == 200
    
    # 2. Create workout
    workout_payload = {
        "name": "Test Leg Day",
        "exercises": [
            {
                "exercise_name": "Squats",
                "sets": [
                    {"reps": 10, "weight": 100.5, "unit": "kg"},
                    {"reps": 8, "weight": 110.0, "unit": "kg"}
                ],
                "notes": "Feeling strong"
            }
        ]
    }
    
    resp = client.post("/workouts", json=workout_payload, headers=headers)
    assert resp.status_code == 200
    workout_data = resp.json()
    workout_id = workout_data["id"]
    
    # 3. List workouts
    resp = client.get("/workouts", headers=headers)
    assert resp.status_code == 200
    workouts = resp.json()
    assert len(workouts) >= 1
    assert any(w["name"] == "Test Leg Day" for w in workouts)
    
    # 4. Check exercise history
    resp = client.get("/exercises/Squats/history", headers=headers)
    assert resp.status_code == 200
    history = resp.json()
    assert len(history) >= 1
    assert history[0]["sets"][0]["weight"] == 100.5
    
    print("\n✅ API Lifecycle Test Passed!")
