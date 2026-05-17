from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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
    try:
        db.create_table_if_not_exists()
    except Exception as e:
        logger.warning("Startup table creation skipped/failed", error=str(e))
    yield

app = FastAPI(
    title="set API", 
    lifespan=lifespan,
    root_path="/api"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Check logs for details."},
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
    
    logger.info("Creating workout", user_id=user_id, workout_id=workout.id)
    try:
        db.save_workout(workout)
        return workout
    except Exception as e:
        logger.error("Failed to create workout", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/workouts")
def list_workouts(user_id: str = Depends(get_current_user)):
    logger.info("Listing workouts", user_id=user_id)
    try:
        return db.get_workouts(user_id)
    except Exception as e:
        logger.error("Failed to list workouts", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/exercises/{exercise_name}/history")
def get_exercise_history(exercise_name: str, user_id: str = Depends(get_current_user)):
    logger.info("Getting exercise history", user_id=user_id, exercise=exercise_name)
    try:
        return db.get_exercise_history(user_id, exercise_name)
    except Exception as e:
        logger.error("Failed to get exercise history", error=str(e), user_id=user_id, exercise=exercise_name)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/workouts/{workout_id}")
def delete_workout(workout_id: str, date: str, user_id: str = Depends(get_current_user)):
    logger.info("Deleting workout", user_id=user_id, workout_id=workout_id, date=date)
    try:
        success = db.delete_workout(user_id, workout_id, date)
        if not success:
            raise HTTPException(status_code=404, detail="Workout not found")
        return {"message": "Workout deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete workout", error=str(e), user_id=user_id, workout_id=workout_id)
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/workouts/{workout_id}", response_model=Workout)
def update_workout(workout_id: str, workout: Workout, old_date: str, user_id: str = Depends(get_current_user)):
    workout.user_id = user_id
    if workout.id != workout_id:
        raise HTTPException(status_code=400, detail="Workout ID mismatch")
    
    logger.info("Updating workout", user_id=user_id, workout_id=workout_id)
    try:
        db.update_workout(workout, old_date)
        return workout
    except Exception as e:
        logger.error("Failed to update workout", error=str(e), user_id=user_id, workout_id=workout_id)
        raise HTTPException(status_code=500, detail=str(e))

# Mangum handler for AWS Lambda
handler = Mangum(app)
