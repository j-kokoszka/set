from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from typing import List
from models import Workout, ExerciseRecord
from database import db
from auth import get_current_user
import uuid
from contextlib import asynccontextmanager
import structlog
import logging
import sys

# Configure structured logging
logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=logging.INFO,
)

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.stdlib.filter_by_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create table if running locally or first time
    try:
        db.create_table_if_not_exists()
    except Exception:
        # Ignore if table already exists or in production with pre-provisioned table
        pass
    yield

app = FastAPI(
    title="set API", 
    lifespan=lifespan,
    root_path="/api",
    redirect_slashes=False
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev, allow all. Refine for production.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the 'set' workout tracker API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/workouts", response_model=Workout)
def create_workout(workout: Workout, user_id: str = Depends(get_current_user)):
    workout.user_id = user_id
    if not workout.id:
        workout.id = str(uuid.uuid4())
    try:
        db.save_workout(workout)
        return workout
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/workouts", response_model=List[dict])
def list_workouts(user_id: str = Depends(get_current_user)):
    try:
        return db.get_workouts(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/exercises/{exercise_name}/history")
def get_exercise_history(exercise_name: str, user_id: str = Depends(get_current_user)):
    try:
        return db.get_exercise_history(user_id, exercise_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/workouts/{workout_id}")
def delete_workout(workout_id: str, date: str, user_id: str = Depends(get_current_user)):
    try:
        success = db.delete_workout(user_id, workout_id, date)
        if not success:
            raise HTTPException(status_code=404, detail="Workout not found")
        return {"message": "Workout deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/workouts/{workout_id}", response_model=Workout)
def update_workout(workout_id: str, workout: Workout, old_date: str, user_id: str = Depends(get_current_user)):
    workout.user_id = user_id
    if workout.id != workout_id:
        raise HTTPException(status_code=400, detail="Workout ID mismatch")
    try:
        db.update_workout(workout, old_date)
        return workout
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mangum handler for AWS Lambda
handler = Mangum(app)
