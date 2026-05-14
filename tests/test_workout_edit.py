import pytest
from fastapi.testclient import TestClient
from backend.main import app
import uuid

client = TestClient(app)

def test_workout_edit_lifecycle():
    user_id = f"edit_test_user_{uuid.uuid4().hex[:8]}"
    headers = {"Authorization": f"Bearer mock_{user_id}"}
    
    # 1. Create a workout
    workout_payload = {
        "name": "Original Workout",
        "exercises": [
            {
                "exercise_name": "Bench Press",
                "sets": [{"reps": 10, "weight": 60, "unit": "kg"}]
            }
        ]
    }
    resp = client.post("/workouts", json=workout_payload, headers=headers)
    assert resp.status_code == 200
    created = resp.json()
    workout_id = created["id"]
    original_date = created["date"]
    
    # 2. Update the workout
    updated_payload = {
        "id": workout_id,
        "name": "Updated Workout",
        "date": original_date,
        "exercises": [
            {
                "exercise_name": "Bench Press",
                "sets": [
                    {"reps": 10, "weight": 60, "unit": "kg"},
                    {"reps": 8, "weight": 65, "unit": "kg"}
                ]
            },
            {
                "exercise_name": "Push Ups",
                "sets": [{"reps": 20, "weight": 0, "unit": "kg"}]
            }
        ]
    }
    
    resp = client.put(f"/workouts/{workout_id}?old_date={original_date}", json=updated_payload, headers=headers)
    assert resp.status_code == 200
    
    # 3. Verify changes in workout list
    resp = client.get("/workouts", headers=headers)
    workouts = resp.json()
    updated_workout = next(w for w in workouts if w["id"] == workout_id)
    assert updated_workout["name"] == "Updated Workout"
    assert len(updated_workout["exercises"]) == 2
    
    # 4. Verify exercise history reflects changes
    # Bench Press should have 2 sets now
    resp = client.get("/exercises/Bench%20Press/history", headers=headers)
    history = resp.json()
    assert len(history) == 1
    assert len(history[0]["sets"]) == 2
    
    # Push Ups should now exist
    resp = client.get("/exercises/Push%20Ups/history", headers=headers)
    assert len(resp.json()) == 1
    
    # 5. Delete the workout
    resp = client.delete(f"/workouts/{workout_id}?date={original_date}", headers=headers)
    assert resp.status_code == 200
    
    # 6. Verify everything is gone
    resp = client.get("/workouts", headers=headers)
    assert not any(w["id"] == workout_id for w in resp.json())
    
    resp = client.get("/exercises/Bench%20Press/history", headers=headers)
    assert len(resp.json()) == 0
    
    print("\n✅ Workout Edit/Delete Lifecycle Test Passed!")
