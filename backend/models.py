from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ExerciseSet(BaseModel):
    reps: int
    weight: float
    unit: str = "kg"  # "kg" or "lbs"

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

class PlanExerciseSet(BaseModel):
    reps: Optional[int] = None
    weight: Optional[float] = None
    unit: str = "kg"

class PlanExercise(BaseModel):
    exercise_id: Optional[str] = None
    exercise_name: str
    sets: List[PlanExerciseSet]

class WorkoutPlan(BaseModel):
    id: Optional[str] = None
    name: str
    exercises: List[PlanExercise]
    user_id: Optional[str] = None

class Feedback(BaseModel):
    text: str
