import pytest
from pydantic import ValidationError
from models import Workout, ExerciseRecord, ExerciseSet, WorkoutPlan, PlanExercise, PlanExerciseSet

def test_workout_valid():
    workout = Workout(
        name="Morning Session",
        exercises=[
            ExerciseRecord(
                exercise_name="Bench Press",
                sets=[ExerciseSet(reps=10, weight=60.0)]
            )
        ],
        user_id="user123"
    )
    assert workout.name == "Morning Session"
    assert len(workout.exercises) == 1
    assert workout.date is not None

def test_workout_missing_name():
    with pytest.raises(ValidationError):
        Workout(exercises=[])

def test_exercise_set_invalid_types():
    with pytest.raises(ValidationError):
        ExerciseSet(reps="ten", weight=60.0)
    
    with pytest.raises(ValidationError):
        ExerciseSet(reps=10, weight="heavy")

def test_workout_plan_defaults():
    plan = WorkoutPlan(
        name="Strength Plan",
        exercises=[
            PlanExercise(
                exercise_name="Squat",
                sets=[PlanExerciseSet()]
            )
        ]
    )
    assert plan.exercises[0].sets[0].unit == "kg"
    assert plan.exercises[0].sets[0].reps is None

def test_workout_date_generation():
    workout = Workout(
        name="Test Workout",
        exercises=[]
    )
    assert isinstance(workout.date, str)
    # Should be ISO format
    from datetime import datetime
    datetime.fromisoformat(workout.date)
