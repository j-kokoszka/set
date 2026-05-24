import pytest
from backend.main import calculate_1rm
from backend.models import Workout, ExerciseRecord, ExerciseSet

def test_calculate_1rm():
    # 100kg for 1 rep = 100kg
    assert calculate_1rm(100.0, 1) == 100.0
    # 100kg for 10 reps (Brzycki: 100 * (36 / (37 - 10)) = 100 * (36/27) = 133.33)
    assert round(calculate_1rm(100.0, 10), 2) == 133.33
    # 0 reps = 0.0
    assert calculate_1rm(100.0, 0) == 0.0

@pytest.mark.asyncio
async def test_update_user_analytics_logic(mocker):
    # Mock db and exercises
    mock_db = mocker.patch("backend.main.db")
    mocker.patch("backend.main.get_exercise_muscles", return_value=["chest"])
    mocker.patch("backend.main.db.get_volume_aggregates", return_value=[])
    mocker.patch("backend.main.db.get_personal_records", return_value=[])
    
    from backend.main import update_user_analytics
    
    workout = Workout(
        id="test-w",
        name="Test Workout",
        date="2026-05-24T12:00:00",
        user_id="user-1",
        exercises=[
            ExerciseRecord(
                exercise_name="Bench Press",
                sets=[
                    ExerciseSet(reps=10, weight=100.0, completed=True)
                ]
            )
        ]
    )
    
    await update_user_analytics("user-1", workout, multiplier=1)
    
    # Verify save_volume_aggregate was called
    assert mock_db.save_volume_aggregate.called
    agg = mock_db.save_volume_aggregate.call_args[0][0]
    assert agg.total_volume == 1000.0 # 100 * 10
    assert agg.muscles["chest"] == 1000.0
    assert agg.period == "2026-05"
    
    # Verify save_personal_record was called
    assert mock_db.save_personal_record.called
    pr = mock_db.save_personal_record.call_args[0][0]
    assert pr.exercise_name == "Bench Press"
    assert round(pr.estimated_1rm, 2) == 133.33
    assert pr.max_weight == 100.0
