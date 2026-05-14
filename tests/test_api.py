import requests
import uuid
import time

def test_workout_lifecycle():
    base_url = "http://localhost:8000"
    user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    
    # 1. Health check
    print("Checking health...")
    resp = requests.get(f"{base_url}/health")
    assert resp.status_code == 200
    
    # 2. Create workout
    print("Creating workout...")
    workout_payload = {
        "name": "Test Leg Day",
        "user_id": user_id,
        "exercises": [
            {
                "exercise_name": "Squats",
                "sets": [
                    {"reps": 10, "weight": 100.5},
                    {"reps": 8, "weight": 110.0}
                ],
                "notes": "Feeling strong"
            }
        ]
    }
    
    resp = requests.post(f"{base_url}/workouts", json=workout_payload)
    if resp.status_code != 200:
        print(f"FAILED: {resp.text}")
    assert resp.status_code == 200
    workout_id = resp.json()["id"]
    
    # 3. List workouts
    print("Listing workouts...")
    time.sleep(1) # Allow for DynamoDB consistency if needed (though local is usually fast)
    resp = requests.get(f"{base_url}/workouts?user_id={user_id}")
    assert resp.status_code == 200
    workouts = resp.json()
    assert len(workouts) >= 1
    assert any(w["name"] == "Test Leg Day" for w in workouts)
    
    # 4. Check exercise history
    print("Checking exercise history...")
    resp = requests.get(f"{base_url}/exercises/Squats/history?user_id={user_id}")
    assert resp.status_code == 200
    history = resp.json()
    assert len(history) >= 1
    assert history[0]["sets"][0]["weight"] == 100.5
    
    print("\n✅ API Lifecycle Test Passed!")

if __name__ == "__main__":
    try:
        test_workout_lifecycle()
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
