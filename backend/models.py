from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Literal, Dict
from datetime import datetime

class ExerciseSet(BaseModel):
    reps: int
    weight: float
    unit: str = "kg"  # "kg" or "lbs"
    difficulty: Optional[Literal["easy", "moderate", "hard", "pass"]] = None
    completed: bool = False

class ExerciseRecord(BaseModel):
    exercise_id: Optional[str] = None
    exercise_name: str
    sets: List[ExerciseSet]
    notes: Optional[str] = None

class Workout(BaseModel):
    id: Optional[str] = None
    name: str
    date: str = Field(default_factory=lambda: datetime.now().isoformat())
    exercises: List[ExerciseRecord]
    user_id: Optional[str] = None

class RoutineExerciseSet(BaseModel):
    reps: Optional[int] = None
    weight: Optional[float] = None
    unit: str = "kg"

class ProgressionConfig(BaseModel):
    enabled: bool = False
    increment_weight: float = 2.5
    increment_reps: int = 0
    condition: Literal["all_completed", "last_set_completed"] = "all_completed"

class RoutineExercise(BaseModel):
    exercise_id: Optional[str] = None
    exercise_name: str
    sets: List[RoutineExerciseSet]
    progression: Optional[ProgressionConfig] = None

class WorkoutRoutine(BaseModel):
    id: Optional[str] = None
    name: str
    exercises: List[RoutineExercise]
    user_id: Optional[str] = None

class Feedback(BaseModel):
    text: str = Field(..., max_length=1000)

class CustomExercise(BaseModel):
    id: Optional[str] = None
    name: str
    translations: Dict[str, str] = {} # e.g. {"pl": "Pompki"}
    force: Optional[str] = None
    level: str = "beginner"
    mechanic: Optional[str] = None
    equipment: Optional[str] = None
    primaryMuscles: List[str] = []
    secondaryMuscles: List[str] = []
    instructions: List[str] = []
    category: str = "strength"
    user_id: Optional[str] = None

class GlobalExercise(BaseModel):
    id: str
    name: str
    translations: Dict[str, str] = {}
    force: Optional[str] = None
    level: str = "beginner"
    mechanic: Optional[str] = None
    equipment: Optional[str] = None
    primaryMuscles: List[str] = []
    secondaryMuscles: List[str] = []
    instructions: List[str] = []
    category: str = "strength"

class Schedule(BaseModel):
    id: Optional[str] = None
    routine_id: str
    routine_name: Optional[str] = None
    schedule_type: Literal["recurring", "specific_date"]
    day_of_week: Optional[int] = None  # 0-6 (Monday-Sunday) for recurring
    specific_date: Optional[str] = None  # YYYY-MM-DD for specific_date
    user_id: Optional[str] = None

    @model_validator(mode='after')
    def validate_schedule_fields(self) -> 'Schedule':
        if self.schedule_type == 'recurring' and self.day_of_week is None:
            raise ValueError("day_of_week is required for recurring schedules")
        if self.schedule_type == 'specific_date' and self.specific_date is None:
            raise ValueError("specific_date is required for one-off schedules")
        return self

class PlannedWorkout(BaseModel):
    date: str
    routine: WorkoutRoutine
    is_recurring: bool
    schedule_id: Optional[str] = None

class PersonalRecord(BaseModel):
    exercise_name: str
    estimated_1rm: float
    max_weight: float
    max_volume_set: float
    date_achieved: str
    user_id: Optional[str] = None

class VolumeAggregate(BaseModel):
    total_volume: float
    muscles: Dict[str, float]
    workout_count: int
    period: str  # YYYY-MM
    user_id: Optional[str] = None
