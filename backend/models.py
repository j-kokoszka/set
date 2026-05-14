from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ExerciseSet(BaseModel):
    reps: int
    weight: float
    unit: str = "kg"  # "kg" or "lbs"

class ExerciseRecord(BaseModel):
    exercise_name: str
    sets: List[ExerciseSet]
    notes: Optional[str] = None

class Workout(BaseModel):
    id: Optional[str] = None
    name: str
    date: str = Field(default_factory=lambda: datetime.now().isoformat())
    exercises: List[ExerciseRecord]
    user_id: Optional[str] = None
