import pytest
from pydantic import ValidationError
from models import Workout, ExerciseRecord, ExerciseSet, WorkoutRoutine, RoutineExercise, RoutineExerciseSet

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

def test_exercise_set_difficulty():
    s = ExerciseSet(reps=10, weight=60.0, difficulty="hard", completed=True)
    assert s.difficulty == "hard"
    assert s.completed is True

def test_exercise_set_defaults():
    s = ExerciseSet(reps=10, weight=60.0)
    assert s.difficulty is None
    assert s.completed is False

def test_workout_routine_defaults():
    plan = WorkoutRoutine(
        name="Strength Routine",
        exercises=[
            RoutineExercise(
                exercise_name="Squat",
                sets=[RoutineExerciseSet()]
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

from models import CustomExercise

def test_custom_exercise_full_schema():
    ex = CustomExercise(
        name="Plank",
        force="static",
        level="intermediate",
        mechanic="isolation",
        equipment="body only",
        primaryMuscles=["abdominals"],
        secondaryMuscles=["shoulders"],
        instructions=["Hold position for 60 seconds"],
        category="strength"
    )
    assert ex.name == "Plank"
    assert ex.force == "static"
    assert len(ex.primaryMuscles) == 1
    assert ex.level == "intermediate"

def test_custom_exercise_defaults():
    ex = CustomExercise(name="Default Ex")
    assert ex.level == "beginner"
    assert ex.category == "strength"
    assert ex.primaryMuscles == []
    assert ex.instructions == []
