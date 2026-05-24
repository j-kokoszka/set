from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mangum import Mangum
from typing import List, Dict, Optional
from models import Workout, WorkoutRoutine, Feedback, CustomExercise, Schedule, PlannedWorkout, PersonalRecord, VolumeAggregate
from database import db
from auth import get_current_user
import uuid
import json
import os
import boto3
import httpx
from datetime import date, timedelta
from contextlib import asynccontextmanager
import structlog
import logging
import sys
import anyio

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

# Configuration
AWS_REGION = os.getenv("SET_AWS_REGION", os.getenv("AWS_REGION", "us-east-1"))
GITHUB_REPO_OWNER = os.getenv("GITHUB_REPO_OWNER", "j-kokoszka")
GITHUB_REPO_NAME = os.getenv("GITHUB_REPO_NAME", "set")

# Initialize OpenTelemetry
OTEL_ENABLED = bool(os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"))

if OTEL_ENABLED:
    try:
        from opentelemetry import trace, metrics, _logs as logs
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
        from opentelemetry.sdk._logs.export import SimpleLogRecordProcessor
        from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
        from opentelemetry.instrumentation.logging import LoggingInstrumentor
        from opentelemetry.instrumentation.botocore import BotocoreInstrumentor
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource

        resource = Resource(attributes={
            SERVICE_NAME: os.getenv("OTEL_SERVICE_NAME", "set-backend")
        })
        
        # 1. Tracing Setup
        tracer_provider = TracerProvider(resource=resource)
        tracer_processor = SimpleSpanProcessor(OTLPSpanExporter())
        tracer_provider.add_span_processor(tracer_processor)
        trace.set_tracer_provider(tracer_provider)
        
        # 2. Metrics Setup
        metric_reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(),
            export_interval_millis=1000 # Short interval for Lambda responsiveness
        )
        meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
        metrics.set_meter_provider(meter_provider)

        # 3. Logging Setup
        logger_provider = LoggerProvider(resource=resource)
        # Using SimpleLogRecordProcessor for Lambda to ensure logs are sent immediately
        log_exporter = OTLPLogExporter()
        logger_provider.add_log_record_processor(SimpleLogRecordProcessor(log_exporter))
        logs.set_logger_provider(logger_provider)

        # Connect standard logging to OTel with dynamic level
        current_level = getattr(logging, log_level, logging.INFO)
        otel_handler = LoggingHandler(level=current_level, logger_provider=logger_provider)
        logging.getLogger().addHandler(otel_handler)
        
        # 4. Instrumentations
        BotocoreInstrumentor().instrument()
        LoggingInstrumentor().instrument(set_logging_format=True)
        
        logger.info("opentelemetry_initialized")
    except Exception as e:
        logger.error("opentelemetry_initialization_failed", error=str(e))
        OTEL_ENABLED = False

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

# Instrument FastAPI
if OTEL_ENABLED:
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app)
    except Exception as e:
        logger.error("fastapi_instrumentation_failed", error=str(e))

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
EXTERNAL_EXERCISES_FILE = os.path.join(os.path.dirname(__file__), "data", "external_exercises.json")

def load_exercises(file_path):
    if not os.path.exists(file_path):
        logger.warning("exercises_file_missing", path=file_path)
        return []
    try:
        with open(file_path, "r") as f:
            raw_exercises = json.load(f)
            processed = []
            for ex in raw_exercises:
                if not isinstance(ex, dict): continue
                ex["primaryMuscles"] = ex.get("primaryMuscles") or []
                if not isinstance(ex["primaryMuscles"], list):
                    ex["primaryMuscles"] = [str(ex["primaryMuscles"])]
                processed.append(ex)
            return processed
    except Exception as e:
        logger.error("failed_to_load_exercises", file=file_path, error=str(e))
        return []

# Global exercises cache
global_exercises_cache: List[Dict] = []

async def get_global_exercises():
    global global_exercises_cache
    if not global_exercises_cache:
        try:
            logger.info("loading_global_exercises_from_db")
            items = db.get_global_exercises()
            global_exercises_cache = items
        except Exception as e:
            logger.error("failed_to_load_global_exercises", error=str(e))
            # Fallback to file if DB fails and file exists
            if not global_exercises_cache:
                global_exercises_cache = load_exercises(EXERCISES_FILE)
    return global_exercises_cache

def calculate_1rm(weight: float, reps: int) -> float:
    """Calculates estimated 1RM using the Brzycki formula."""
    if reps <= 0:
        return 0.0
    if reps == 1:
        return weight
    return weight * (36 / (37 - reps))

async def get_exercise_muscles(exercise_name: str) -> List[str]:
    """Helper to find muscle groups for an exercise."""
    # Ensure cache is loaded
    all_global = await get_global_exercises()
    for ex in all_global:
        if ex.get("name") == exercise_name:
            return ex.get("primaryMuscles", [])
    # Check external cache
    for ex in external_exercises_cache:
        if ex.get("name") == exercise_name:
            return ex.get("primaryMuscles", [])
    return []

async def update_user_analytics(user_id: str, workout: Workout, multiplier: int = 1):
    """Updates PRs and volume aggregates for a user."""
    logger.info("Updating user analytics", user_id=user_id, workout_id=workout.id, multiplier=multiplier)
    
    # 1. Update Monthly Volume Aggregate
    try:
        workout_date = date.fromisoformat(workout.date[:10])
        period = workout_date.strftime("%Y-%m")
        
        # Fetch current aggregates to find the right one
        aggregates = db.get_volume_aggregates(user_id)
        current_agg_data = next((a for a in aggregates if a['period'] == period), None)
        
        from models import VolumeAggregate
        if not current_agg_data:
            current_agg = VolumeAggregate(
                total_volume=0.0,
                muscles={},
                workout_count=0,
                period=period,
                user_id=user_id
            )
        else:
            current_agg = VolumeAggregate(**current_agg_data)
        
        workout_total_volume = 0.0
        muscle_volumes = {}
        
        for ex_record in workout.exercises:
            muscles = await get_exercise_muscles(ex_record.exercise_name)
            ex_volume = sum(s.weight * s.reps for s in ex_record.sets if s.completed)
            workout_total_volume += ex_volume
            
            for muscle in muscles:
                muscle_volumes[muscle] = muscle_volumes.get(muscle, 0.0) + ex_volume

        # Apply multiplier
        current_agg.total_volume += workout_total_volume * multiplier
        current_agg.workout_count += 1 * multiplier
        
        for muscle, vol in muscle_volumes.items():
            current_agg.muscles[muscle] = current_agg.muscles.get(muscle, 0.0) + vol * multiplier
            
        db.save_volume_aggregate(current_agg)
    except Exception as e:
        logger.error("Failed to update volume analytics", error=str(e), user_id=user_id)

    # 2. Update PRs (Only for additions/updates, not for deletions as we don't easily know the "next best" PR)
    if multiplier > 0:
        try:
            from models import PersonalRecord
            current_prs = {pr['exercise_name']: PersonalRecord(**pr) for pr in db.get_personal_records(user_id)}
            
            for ex_record in workout.exercises:
                ex_name = ex_record.exercise_name
                best_set_1rm = 0.0
                max_weight = 0.0
                max_volume_set = 0.0
                
                for s in ex_record.sets:
                    if not s.completed: continue
                    one_rm = calculate_1rm(s.weight, s.reps)
                    if one_rm > best_set_1rm: best_set_1rm = one_rm
                    if s.weight > max_weight: max_weight = s.weight
                    if s.weight * s.reps > max_volume_set: max_volume_set = s.weight * s.reps
                
                if best_set_1rm == 0: continue # No completed sets for this exercise

                existing_pr = current_prs.get(ex_name)
                is_new_pr = False
                
                if not existing_pr:
                    existing_pr = PersonalRecord(
                        exercise_name=ex_name,
                        estimated_1rm=best_set_1rm,
                        max_weight=max_weight,
                        max_volume_set=max_volume_set,
                        date_achieved=workout.date,
                        user_id=user_id
                    )
                    is_new_pr = True
                else:
                    if best_set_1rm > existing_pr.estimated_1rm:
                        existing_pr.estimated_1rm = best_set_1rm
                        existing_pr.date_achieved = workout.date
                        is_new_pr = True
                    if max_weight > existing_pr.max_weight:
                        existing_pr.max_weight = max_weight
                        is_new_pr = True
                    if max_volume_set > existing_pr.max_volume_set:
                        existing_pr.max_volume_set = max_volume_set
                        is_new_pr = True
                
                if is_new_pr:
                    db.save_personal_record(existing_pr)
        except Exception as e:
            logger.error("Failed to update PR analytics", error=str(e), user_id=user_id)

external_exercises_cache = load_exercises(EXTERNAL_EXERCISES_FILE)

# Persistent AWS clients
http_client = httpx.AsyncClient(timeout=10.0)
bedrock_client = boto3.client("bedrock-runtime", region_name=AWS_REGION)

def get_localized_name(ex: Dict, lang: str = "en") -> str:
    translations = ex.get("translations") or {}
    return translations.get(lang) or ex.get("name", "Unknown")

@app.get("/exercises")
async def list_exercises(request: Request):
    lang = request.headers.get("Accept-Language", "en").split(",")[0].split("-")[0]
    exercises = await get_global_exercises()
    
    # Simple localization for the list
    localized = []
    for ex in exercises:
        localized.append({
            **ex,
            "display_name": get_localized_name(ex, lang)
        })
    return localized

@app.get("/exercises/search")
async def search_exercises(q: str, request: Request, _user_id: str = Depends(get_current_user)):
    """
    Search the extended/external database for additional exercises.
    """
    lang = request.headers.get("Accept-Language", "en").split(",")[0].split("-")[0]
    logger.info("searching_exercises", query=q, lang=lang)
    try:
        query = q.lower().strip()
        results = []
        
        # Search in global exercises
        all_global = await get_global_exercises()
        for ex in all_global:
            name = ex.get("name", "").lower()
            trans_name = get_localized_name(ex, lang).lower()
            if query in name or query in trans_name:
                results.append({
                    "id": ex.get("id"),
                    "name": ex.get("name"),
                    "display_name": get_localized_name(ex, lang),
                    "category": (ex.get("category") or "strength").lower(),
                    "primaryMuscles": ex.get("primaryMuscles", []),
                    "is_external": False
                })
                if len(results) >= 50: break

        # Also search in external cache if results are low
        if len(results) < 10:
            for ex in external_exercises_cache:
                if query in ex.get("name", "").lower():
                    # Check if already in results
                    if any(r["name"] == ex["name"] for r in results): continue
                    
                    results.append({
                        "id": f"ext-{ex.get('id') or ex.get('name')}",
                        "name": ex.get("name"),
                        "display_name": ex.get("name"), # External might not have translations yet
                        "category": (ex.get("category") or "strength").lower(),
                        "primaryMuscles": ex.get("primaryMuscles", []),
                        "is_external": True
                    })
                    if len(results) >= 50: break
        
        return results
    except Exception as e:
        logger.error("search_failed", error=str(e))
        raise HTTPException(status_code=502, detail="Error searching exercises")

@app.get("/exercises/custom")
def list_custom_exercises(user_id: str = Depends(get_current_user)):
    try:
        return db.get_custom_exercises(user_id)
    except Exception as e:
        logger.error("failed_to_list_custom_exercises", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Failed to fetch custom exercises")

@app.post("/exercises/custom", response_model=CustomExercise)
def create_custom_exercise(exercise: CustomExercise, user_id: str = Depends(get_current_user)):
    exercise.user_id = user_id
    if not exercise.id:
        exercise.id = f"custom-{str(uuid.uuid4())}"
    
    logger.info("creating_custom_exercise", user_id=user_id, name=exercise.name)
    try:
        db.save_custom_exercise(exercise)
        return exercise
    except Exception as e:
        logger.error("failed_to_create_custom_exercise", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Failed to save custom exercise")

@app.delete("/exercises/custom/{ex_id}")
def delete_custom_exercise(ex_id: str, user_id: str = Depends(get_current_user)):
    logger.info("deleting_custom_exercise", user_id=user_id, ex_id=ex_id)
    try:
        db.delete_custom_exercise(user_id, ex_id)
        return {"status": "success"}
    except Exception as e:
        logger.error("failed_to_delete_custom_exercise", error=str(e), user_id=user_id, ex_id=ex_id)
        raise HTTPException(status_code=500, detail="Failed to delete custom exercise")

@app.post("/exercises/custom/suggest", response_model=CustomExercise)
async def suggest_custom_exercise(exercise: CustomExercise, user_id: str = Depends(get_current_user)):
    """
    Use Bedrock to suggest details for a custom exercise based on its name.
    """
    logger.info("suggesting_custom_exercise", user_id=user_id, name=exercise.name)
    try:
        
        prompt = f"""
        Provide technical details for the following physical exercise: "{exercise.name}"
        Return ONLY a JSON object with these keys:
        - "force": "pull", "push", or "static"
        - "level": "beginner", "intermediate", or "expert"
        - "mechanic": "compound" or "isolation"
        - "equipment": e.g., "barbell", "dumbbell", "machine", "body only"
        - "primaryMuscles": array of strings (e.g. ["chest"])
        - "secondaryMuscles": array of strings
        - "instructions": array of short strings (numbered steps)
        - "category": "strength", "stretching", or "cardio"

        Exercise Name: {exercise.name}
        JSON Output:
        """
        
        # Region-agnostic cross-region inference profile
        inference_profile_id = "eu.amazon.nova-micro-v1:0"
        
        # Run synchronous boto3 call in a thread to avoid blocking the event loop
        def invoke_bedrock():
            return bedrock_client.invoke_model(
                modelId=inference_profile_id,
                body=json.dumps({
                    "inferenceConfig": { "max_new_tokens": 1000 },
                    "messages": [
                        { "role": "user", "content": [{ "text": prompt }] }
                    ]
                })
            )
            
        response = await anyio.to_thread.run_sync(invoke_bedrock)
        
        response_body = json.loads(response.get("body").read())
        llm_text = response_body["output"]["message"]["content"][0]["text"]
        
        if "```json" in llm_text:
            llm_text = llm_text.split("```json")[1].split("```")[0].strip()
        elif "```" in llm_text:
            llm_text = llm_text.split("```")[1].split("```")[0].strip()
            
        suggested_data = json.loads(llm_text)
        
        # Merge AI data with current exercise (keeping name)
        exercise.force = suggested_data.get("force")
        exercise.level = suggested_data.get("level", "beginner")
        exercise.mechanic = suggested_data.get("mechanic")
        exercise.equipment = suggested_data.get("equipment")
        exercise.primaryMuscles = suggested_data.get("primaryMuscles") or []
        exercise.secondaryMuscles = suggested_data.get("secondaryMuscles") or []
        exercise.instructions = suggested_data.get("instructions") or []
        exercise.category = suggested_data.get("category", "strength")
        
        return exercise
        
    except Exception as e:
        logger.error("suggestion_failed", error=str(e), name=exercise.name)
        # Return what we have if AI fails
        return exercise

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
async def create_workout(workout: Workout, user_id: str = Depends(get_current_user)):
    workout.user_id = user_id
    if not workout.id:
        workout.id = str(uuid.uuid4())
    
    logger.info("Creating workout", user_id=user_id, workout_id=workout.id)
    try:
        db.save_workout(workout)
        await update_user_analytics(user_id, workout, multiplier=1)
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
async def delete_workout(workout_id: str, date: str, user_id: str = Depends(get_current_user)):
    logger.info("Deleting workout", user_id=user_id, workout_id=workout_id, date=date)
    try:
        old_workout_data = db.delete_workout(user_id, workout_id, date)
        if not old_workout_data:
            raise HTTPException(status_code=404, detail="Workout not found")
        
        old_workout = Workout(**old_workout_data)
        await update_user_analytics(user_id, old_workout, multiplier=-1)
        return {"message": "Workout deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete workout", error=str(e), user_id=user_id, workout_id=workout_id)
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/workouts/{workout_id}", response_model=Workout)
async def update_workout(workout_id: str, workout: Workout, old_date: str, user_id: str = Depends(get_current_user)):
    workout.user_id = user_id
    if workout.id != workout_id:
        raise HTTPException(status_code=400, detail="Workout ID mismatch")
    
    logger.info("Updating workout", user_id=user_id, workout_id=workout_id)
    try:
        old_workout_data = db.update_workout(workout, old_date)
        if old_workout_data:
            old_workout = Workout(**old_workout_data)
            await update_user_analytics(user_id, old_workout, multiplier=-1)
        
        await update_user_analytics(user_id, workout, multiplier=1)
        return workout
    except Exception as e:
        logger.error("Failed to update workout", error=str(e), user_id=user_id, workout_id=workout_id)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/routines", response_model=WorkoutRoutine)
def create_routine(routine: WorkoutRoutine, user_id: str = Depends(get_current_user)):
    routine.user_id = user_id
    if not routine.id:
        routine.id = str(uuid.uuid4())
    
    logger.info("Creating workout routine", user_id=user_id, routine_id=routine.id)
    try:
        db.save_routine(routine)
        return routine
    except Exception as e:
        logger.error("Failed to create workout routine", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/routines")
def list_routines(user_id: str = Depends(get_current_user)):
    logger.info("Listing workout routines", user_id=user_id)
    try:
        return db.get_routines(user_id)
    except Exception as e:
        logger.error("Failed to list workout routines", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/routines/{routine_id}")
def delete_routine(routine_id: str, user_id: str = Depends(get_current_user)):
    logger.info("Deleting workout routine", user_id=user_id, routine_id=routine_id)
    try:
        success = db.delete_routine(user_id, routine_id)
        if not success:
            raise HTTPException(status_code=404, detail="Routine not found")
        return {"message": "Workout routine deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete workout routine", error=str(e), user_id=user_id, routine_id=routine_id)
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/routines/{routine_id}", response_model=WorkoutRoutine)
def update_routine(routine_id: str, routine: WorkoutRoutine, user_id: str = Depends(get_current_user)):
    routine.user_id = user_id
    if routine.id != routine_id:
        raise HTTPException(status_code=400, detail="Routine ID mismatch")
    
    logger.info("Updating workout routine", user_id=user_id, routine_id=routine_id)
    try:
        db.save_routine(routine)
        return routine
    except Exception as e:
        logger.error("Failed to update workout routine", error=str(e), user_id=user_id, routine_id=routine_id)
        raise HTTPException(status_code=500, detail=str(e))

# --- Workout Planning & Progression ---

def apply_progression(user_id: str, routine: WorkoutRoutine, history_cache: Optional[Dict[str, List[dict]]] = None) -> WorkoutRoutine:
    """
    Analyzes user history and applies progression increments to a routine.
    """
    new_routine = routine.model_copy(deep=True)
    for ex in new_routine.exercises:
        if ex.progression and ex.progression.enabled:
            history = None
            if history_cache is not None:
                if ex.exercise_name in history_cache:
                    history = history_cache[ex.exercise_name]
                else:
                    history = db.get_exercise_history(user_id, ex.exercise_name)
                    history_cache[ex.exercise_name] = history
            else:
                history = db.get_exercise_history(user_id, ex.exercise_name)
                
            if history:
                # Sort by date descending (sk format: EXERCISE#<name>#<date>)
                history.sort(key=lambda x: x['sk'].split('#')[-1], reverse=True)
                last_record = history[0]
                
                # Check progression condition
                success = False
                if ex.progression.condition == "all_completed":
                    success = all(s.get('completed', False) for s in last_record.get('sets', []))
                elif ex.progression.condition == "last_set_completed":
                    sets = last_record.get('sets', [])
                    if sets:
                        success = sets[-1].get('completed', False)
                
                if success:
                    logger.info("Applying progression", exercise=ex.exercise_name, user_id=user_id)
                    for s in ex.sets:
                        if s.weight is not None:
                            s.weight += ex.progression.increment_weight
                        if s.reps is not None:
                            s.reps += ex.progression.increment_reps
    return new_routine

@app.post("/schedules", response_model=Schedule)
def create_schedule(schedule: Schedule, user_id: str = Depends(get_current_user)):
    schedule.id = str(uuid.uuid4())
    schedule.user_id = user_id
    
    # Fetch routine name for convenience
    routine = db.get_routine_by_id(user_id, schedule.routine_id)
    if routine:
        schedule.routine_name = routine.get('name')
    
    logger.info("Creating schedule", user_id=user_id, schedule_id=schedule.id)
    try:
        db.save_schedule(schedule)
        return schedule
    except Exception as e:
        logger.error("Failed to create schedule", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/schedules", response_model=List[Schedule])
def list_schedules(user_id: str = Depends(get_current_user)):
    logger.info("Listing schedules", user_id=user_id)
    try:
        return db.get_schedules(user_id)
    except Exception as e:
        logger.error("Failed to list schedules", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/schedules/{schedule_id}")
def delete_schedule(schedule_id: str, user_id: str = Depends(get_current_user)):
    logger.info("Deleting schedule", user_id=user_id, schedule_id=schedule_id)
    try:
        db.delete_schedule(user_id, schedule_id)
        return {"message": "Schedule deleted successfully"}
    except Exception as e:
        logger.error("Failed to delete schedule", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/plan/upcoming", response_model=List[PlannedWorkout])
def get_upcoming_plan(days: int = 14, user_id: str = Depends(get_current_user)):
    """
    Returns a list of planned workouts for the next N days, with progression applied.
    """
    logger.info("Fetching upcoming plan", user_id=user_id, days=days)
    try:
        schedules = db.get_schedules(user_id)
        routines_cache = {}
        history_cache = {} # N+1 problem mitigation
        
        upcoming = []
        today = date.today()
        
        for i in range(days + 1):
            current_date = today + timedelta(days=i)
            iso_date = current_date.isoformat()
            dow = current_date.weekday()
            
            for s in schedules:
                match = False
                if s.get('schedule_type') == 'recurring' and s.get('day_of_week') == dow:
                    match = True
                elif s.get('schedule_type') == 'specific_date' and s.get('specific_date') == iso_date:
                    match = True
                
                if match:
                    routine_id = s.get('routine_id')
                    if routine_id not in routines_cache:
                        r_data = db.get_routine_by_id(user_id, routine_id)
                        if r_data:
                            routines_cache[routine_id] = WorkoutRoutine(**r_data)
                    
                    if routine_id in routines_cache:
                        # Apply progression engine with cache
                        progressed_routine = apply_progression(user_id, routines_cache[routine_id], history_cache)
                        upcoming.append(PlannedWorkout(
                            date=iso_date,
                            routine=progressed_routine,
                            is_recurring=(s.get('schedule_type') == 'recurring'),
                            schedule_id=s.get('id')
                        ))
        
        # Sort by date
        upcoming.sort(key=lambda x: x.date)
        return upcoming
        
    except Exception as e:
        logger.error("Failed to fetch upcoming plan", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/prs", response_model=List[PersonalRecord])
def get_personal_records(user_id: str = Depends(get_current_user)):
    try:
        return db.get_personal_records(user_id)
    except Exception as e:
        logger.error("Failed to fetch PRs", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Failed to fetch personal records")

@app.get("/analytics/volume", response_model=List[VolumeAggregate])
def get_volume_analytics(user_id: str = Depends(get_current_user)):
    try:
        aggregates = db.get_volume_aggregates(user_id)
        # Sort by period
        aggregates.sort(key=lambda x: x['period'])
        return aggregates
    except Exception as e:
        logger.error("Failed to fetch volume analytics", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Failed to fetch volume analytics")

def get_github_pat():
    secret_id = os.getenv("GITHUB_PAT_SECRET_ID")
    if not secret_id:
        return os.getenv("GITHUB_PAT")
    
    try:
        client = boto3.client("secretsmanager", region_name=AWS_REGION)
        response = client.get_secret_value(SecretId=secret_id)
        return response.get("SecretString")
    except Exception as e:
        logger.error("Failed to retrieve GITHUB_PAT from Secrets Manager", error=str(e))
        return None

@app.post("/feedback")
async def submit_feedback(feedback: Feedback, user_id: str = Depends(get_current_user)):
    logger.info("Received feedback", user_id=user_id)
    
    # 1. Call Bedrock to parse feedback
    try:
        prompt = f"""
        Analyze the following user feedback for a workout tracking app and return a JSON object.
        The JSON object must have the following keys:
        - "title": A concise summary of the feedback.
        - "body": A formatted Markdown description, categorizing it as a Bug or Feature Request and extracting relevant details.
        - "labels": An array of labels (e.g., ["bug"], ["enhancement"], ["ui"]).

        User Feedback:
        {feedback.text}

        JSON Output:
        """
        
        # Region-agnostic cross-region inference profile
        inference_profile_id = "eu.amazon.nova-micro-v1:0"
        
        def invoke_bedrock():
            return bedrock_client.invoke_model(
                modelId=inference_profile_id,
                body=json.dumps({
                    "inferenceConfig": { "max_new_tokens": 500 },
                    "messages": [
                        { "role": "user", "content": [{ "text": prompt }] }
                    ]
                })
            )
            
        response = await anyio.to_thread.run_sync(invoke_bedrock)
        response_body = json.loads(response.get("body").read())
        llm_text = response_body["output"]["message"]["content"][0]["text"]
        
        if "```json" in llm_text:
            llm_text = llm_text.split("```json")[1].split("```")[0].strip()
        elif "```" in llm_text:
            llm_text = llm_text.split("```")[1].split("```")[0].strip()
            
        parsed_feedback = json.loads(llm_text)
        
    except Exception as e:
        logger.error("Failed to parse feedback with Bedrock", error=str(e))
        parsed_feedback = {
            "title": "User Feedback",
            "body": feedback.text,
            "labels": ["feedback"]
        }

    # 2. Call GitHub API to create issue
    github_pat = get_github_pat()
    if not github_pat:
        logger.error("GITHUB_PAT not set")
        raise HTTPException(status_code=500, detail="GitHub integration not configured")
        
    url = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/issues"
    
    headers = {
        "Authorization": f"token {github_pat}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    issue_data = {
        "title": parsed_feedback.get("title", "User Feedback"),
        "body": f"{parsed_feedback.get('body', feedback.text)}\n\n---\nSubmitted by: {user_id}",
        "labels": parsed_feedback.get("labels", [])
    }
    
    async with httpx.AsyncClient() as client:
        gh_response = await client.post(url, headers=headers, json=issue_data)
        
        if gh_response.status_code != 201:
            logger.error("Failed to create GitHub issue", status=gh_response.status_code, response=gh_response.text)
            raise HTTPException(status_code=502, detail="Failed to submit feedback to GitHub")
        
        return {"message": "Feedback submitted successfully", "issue_url": gh_response.json().get("html_url")}

# Mangum handler for AWS Lambda
handler = Mangum(app)
