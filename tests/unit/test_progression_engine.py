import pytest
from backend.main import apply_progression
from backend.models import WorkoutRoutine, RoutineExercise, RoutineExerciseSet, ProgressionConfig
from unittest.mock import MagicMock, patch

@pytest.fixture
def sample_routine():
    return WorkoutRoutine(
        id="routine-123",
        name="Test Routine",
        exercises=[
            RoutineExercise(
                exercise_name="Bench Press",
                sets=[RoutineExerciseSet(reps=10, weight=60, unit="kg")],
                progression=ProgressionConfig(
                    enabled=True,
                    increment_weight=2.5,
                    condition="all_completed"
                )
            )
        ]
    )

def test_progression_applies_when_all_completed(sample_routine):
    mock_history = [
        {
            'sk': 'EXERCISE#Bench Press#2026-05-20',
            'sets': [{'completed': True}, {'completed': True}]
        }
    ]
    
    with patch('backend.main.db.get_exercise_history', return_value=mock_history):
        progressed = apply_progression("user-1", sample_routine)
        assert progressed.exercises[0].sets[0].weight == 62.5

def test_progression_skips_when_not_completed(sample_routine):
    mock_history = [
        {
            'sk': 'EXERCISE#Bench Press#2026-05-20',
            'sets': [{'completed': True}, {'completed': False}]
        }
    ]
    
    with patch('backend.main.db.get_exercise_history', return_value=mock_history):
        progressed = apply_progression("user-1", sample_routine)
        assert progressed.exercises[0].sets[0].weight == 60.0

def test_progression_with_cache(sample_routine):
    mock_history = [
        {
            'sk': 'EXERCISE#Bench Press#2026-05-20',
            'sets': [{'completed': True}]
        }
    ]
    
    cache = {}
    with patch('backend.main.db.get_exercise_history', return_value=mock_history) as mock_get:
        # First call updates cache
        apply_progression("user-1", sample_routine, cache)
        assert "Bench Press" in cache
        
        # Second call uses cache
        apply_progression("user-1", sample_routine, cache)
        assert mock_get.call_count == 1
