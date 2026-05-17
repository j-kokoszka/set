from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mangum import Mangum
from typing import List
from models import Workout, WorkoutPlan
from database import db
from auth import get_current_user
import uuid
import json
import os
from contextlib import asynccontextmanager
import structlog
import logging
import sys

# Configure structured logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=getattr(logging, log_level, logging.INFO),
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

# Middleware for request/response logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.debug("Request received", method=request.method, url=str(request.url))
    response = await call_next(request)
    if response.status_code >= 500:
        logger.error("Request failed", status=response.status_code, url=str(request.url))
    elif response.status_code >= 400:
        logger.warning("Request client error", status=response.status_code, url=str(request.url))
    return response

# Load exercises data
EXERCISES_FILE = os.path.join(os.path.dirname(__file__), "data", "exercises.json")
exercises_cache = []
if os.path.exists(EXERCISES_FILE):
    try:
        with open(EXERCISES_FILE, "r") as f:
            raw_exercises = json.load(f)
            # Ensure each exercise has primaryMuscles as an array to prevent frontend crashes
            exercises_cache = []
            for ex in raw_exercises:
                if not isinstance(ex, dict): continue
                ex["primaryMuscles"] = ex.get("primaryMuscles") or []
                if not isinstance(ex["primaryMuscles"], list):
                    ex["primaryMuscles"] = [str(ex["primaryMuscles"])]
                exercises_cache.append(ex)
    except Exception as e:
        logger.error("failed_to_load_exercises", error=str(e))
else:
    logger.warning("exercises_file_missing", path=EXERCISES_FILE)

@app.get("/exercises")
def list_exercises():
    return exercises_cache

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

@app.post("/plans", response_model=WorkoutPlan)
def create_plan(plan: WorkoutPlan, user_id: str = Depends(get_current_user)):
    plan.user_id = user_id
    if not plan.id:
        plan.id = str(uuid.uuid4())
    
    logger.info("Creating workout plan", user_id=user_id, plan_id=plan.id)
    try:
        db.save_plan(plan)
        return plan
    except Exception as e:
        logger.error("Failed to create workout plan", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/plans")
def list_plans(user_id: str = Depends(get_current_user)):
    logger.info("Listing workout plans", user_id=user_id)
    try:
        return db.get_plans(user_id)
    except Exception as e:
        logger.error("Failed to list workout plans", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/plans/{plan_id}")
def delete_plan(plan_id: str, user_id: str = Depends(get_current_user)):
    logger.info("Deleting workout plan", user_id=user_id, plan_id=plan_id)
    try:
        success = db.delete_plan(user_id, plan_id)
        if not success:
            raise HTTPException(status_code=404, detail="Plan not found")
        return {"message": "Workout plan deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete workout plan", error=str(e), user_id=user_id, plan_id=plan_id)
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/plans/{plan_id}", response_model=WorkoutPlan)
def update_plan(plan_id: str, plan: WorkoutPlan, user_id: str = Depends(get_current_user)):
    plan.user_id = user_id
    if plan.id != plan_id:
        raise HTTPException(status_code=400, detail="Plan ID mismatch")
    
    logger.info("Updating workout plan", user_id=user_id, plan_id=plan_id)
    try:
        db.save_plan(plan)
        return plan
    except Exception as e:
        logger.error("Failed to update workout plan", error=str(e), user_id=user_id, plan_id=plan_id)
        raise HTTPException(status_code=500, detail=str(e))

# Mangum handler for AWS Lambda
handler = Mangum(app)
