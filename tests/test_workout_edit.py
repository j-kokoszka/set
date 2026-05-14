import requests
import uuid
import time

def test_workout_edit():
    base_url = "http://localhost:8000"
    user_id = "test_user_edit"
    
    # 1. Create workout
    print("Creating workout...")
    workout_payload = {
        "name": "Original Workout",
        "user_id": user_id,
        "date": "2023-10-01T10:00:00",
        "exercises": [
            {
                "exercise_name": "Squats",
                "sets": [{"reps": 10, "weight": 100}]
            }
        ]
    }
    
    resp = requests.post(f"{base_url}/workouts", json=workout_payload)
    assert resp.status_code == 200
    created_workout = resp.json()
    workout_id = created_workout["id"]
    original_date = created_workout["date"]
    
    # 2. Verify it exists
    print("Verifying workout exists...")
    resp = requests.get(f"{base_url}/workouts?user_id={user_id}")
    workouts = resp.json()
    assert any(w["id"] == workout_id for w in workouts)
    
    # 3. Edit workout
    print("Editing workout...")
    updated_payload = created_workout.copy()
    updated_payload["name"] = "Updated Workout"
    updated_payload["exercises"].append({
        "exercise_name": "Bench Press",
        "sets": [{"reps": 10, "weight": 60}]
    })
    
    resp = requests.put(f"{base_url}/workouts/{workout_id}?old_date={original_date}", json=updated_payload)
    assert resp.status_code == 200
    
    # 4. Verify updates
    print("Verifying updates...")
    resp = requests.get(f"{base_url}/workouts?user_id={user_id}")
    workouts = resp.json()
    updated_workout = next(w for w in workouts if w["id"] == workout_id)
    assert updated_workout["name"] == "Updated Workout"
    assert len(updated_workout["exercises"]) == 2
    
    # 5. Verify exercise records
    print("Verifying exercise records...")
    resp = requests.get(f"{base_url}/exercises/Bench Press/history?user_id={user_id}")
    history = resp.json()
    assert len(history) == 1
    assert history[0]["workout_id"] == workout_id

    print("\n✅ Workout Edit Test Passed!")

if __name__ == "__main__":
    try:
        test_workout_edit()
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()
