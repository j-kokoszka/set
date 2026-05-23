from pydantic import BaseModel, Field
from typing import List, Optional, Literal
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

class RoutineExercise(BaseModel):
    exercise_id: Optional[str] = None
    exercise_name: str
    sets: List[RoutineExerciseSet]

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
    force: Optional[str] = None
    level: str = "beginner"
    mechanic: Optional[str] = None
    equipment: Optional[str] = None
    primaryMuscles: List[str] = []
    secondaryMuscles: List[str] = []
    instructions: List[str] = []
    category: str = "strength"
    user_id: Optional[str] = None
