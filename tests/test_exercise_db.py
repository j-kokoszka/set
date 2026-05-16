import pytest
from fastapi.testclient import TestClient
from backend.main import app
import uuid
import os

client = TestClient(app)

def test_list_exercises():
    resp = client.get("/exercises")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # Check if a known exercise is present (e.g., Bench Press or 3/4 Sit-Up)
    assert any(ex["name"] == "3/4 Sit-Up" for ex in data)
    assert any("id" in ex for ex in data)

def test_workout_with_exercise_id():
    user_id = f"id_test_user_{uuid.uuid4().hex[:8]}"
    headers = {"Authorization": f"Bearer mock_{user_id}"}
    
    # 1. Create a workout with a standard exercise ID
    workout_payload = {
        "name": "Standard Workout",
        "exercises": [
            {
                "exercise_id": "Bench_Press",
                "exercise_name": "Bench Press",
                "sets": [{"reps": 10, "weight": 60, "unit": "kg"}]
            },
            {
                "exercise_name": "Custom Move",
                "sets": [{"reps": 15, "weight": 0, "unit": "kg"}]
            }
        ]
    }
    resp = client.post("/workouts", json=workout_payload, headers=headers)
    assert resp.status_code == 200
    created = resp.json()
    
    # Verify exercise_id is preserved
    assert created["exercises"][0]["exercise_id"] == "Bench_Press"
    assert created["exercises"][0]["exercise_name"] == "Bench Press"
    assert "exercise_id" not in created["exercises"][1] or created["exercises"][1]["exercise_id"] is None
    
    # 2. Verify retrieval
    resp = client.get("/workouts", headers=headers)
    workouts = resp.json()
    assert workouts[0]["exercises"][0]["exercise_id"] == "Bench_Press"
    
    print("\n✅ Exercise ID Persistence Test Passed!")
