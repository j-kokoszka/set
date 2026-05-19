from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mangum import Mangum
from typing import List
from models import Workout, WorkoutPlan, Feedback
from database import db
from auth import get_current_user
import uuid
import json
import os
import boto3
import httpx
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

# Configuration
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
GITHUB_REPO_OWNER = os.getenv("GITHUB_REPO_OWNER", "j-kokoszka")
GITHUB_REPO_NAME = os.getenv("GITHUB_REPO_NAME", "set")

# Global HTTP client for connection pooling
http_client: httpx.AsyncClient = httpx.AsyncClient()

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        db.create_table_if_not_exists()
    except Exception as e:
        logger.warning("Startup table creation skipped/failed", error=str(e))
    yield
    await http_client.aclose()

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
        bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)
        
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
        
        response = bedrock.invoke_model(
            modelId="amazon.nova-micro-v1:0",
            body=json.dumps({
                "inferenceConfig": {
                    "max_new_tokens": 500,
                },
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"text": prompt}
                        ]
                    }
                ]
            })
        )
        
        response_body = json.loads(response.get("body").read())
        llm_text = response_body["output"]["message"]["content"][0]["text"]
        
        # Extract JSON from llm_text
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
    
    gh_response = await http_client.post(url, headers=headers, json=issue_data)
        
    if gh_response.status_code != 201:
        logger.error("Failed to create GitHub issue", status=gh_response.status_code, response=gh_response.text)
        raise HTTPException(status_code=500, detail="Failed to submit feedback to GitHub")
        
    return {"message": "Feedback submitted successfully", "issue_url": gh_response.json().get("html_url")}

# Mangum handler for AWS Lambda
handler = Mangum(app)
