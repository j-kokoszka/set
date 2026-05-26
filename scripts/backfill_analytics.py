import os
import json
import boto3
from decimal import Decimal
from datetime import datetime
from typing import Dict, List

# Setup
TABLE_NAME = os.getenv("DYNAMODB_TABLE", "set-app-table-prod")
AWS_REGION = os.getenv("AWS_REGION", "eu-central-1")
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(TABLE_NAME)

# Load exercises for muscle lookup
with open("backend/data/exercises.json", "r") as f:
    EXERCISES = json.load(f)
    EXERCISE_MAP = {ex["name"]: ex["primaryMuscles"] for ex in EXERCISES}

def get_muscles(name: str) -> List[str]:
    return EXERCISE_MAP.get(name, [])

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def backfill():
    print(f"Starting backfill for table: {TABLE_NAME}")
    
    # 1. Scan all workouts
    workouts = []
    scan_kwargs = {
        "FilterExpression": boto3.dynamodb.conditions.Attr("type").eq("WORKOUT")
    }
    
    done = False
    start_key = None
    while not done:
        if start_key:
            scan_kwargs["ExclusiveStartKey"] = start_key
        response = table.scan(**scan_kwargs)
        workouts.extend(response.get("Items", []))
        start_key = response.get("LastEvaluatedKey")
        done = start_key is None
    
    print(f"Found {len(workouts)} workouts.")
    
    # 2. Aggregate by user and period
    # user_period_aggregates[user_id][period] = { ... }
    aggregates = {}
    
    for w in workouts:
        user_id = w["pk"].replace("USER#", "")
        # Date format in SK: WORKOUT#YYYY-MM-DD
        try:
            date_str = w["sk"].split("#")[1]
            period = date_str[:7] # YYYY-MM
        except:
            print(f"Skipping malformed workout: {w['pk']} / {w['sk']}")
            continue
            
        if user_id not in aggregates:
            aggregates[user_id] = {}
        if period not in aggregates[user_id]:
            aggregates[user_id][period] = {
                "total_volume": Decimal("0"),
                "workout_count": 0,
                "muscles": {},
                "muscle_sets": {}
            }
            
        agg = aggregates[user_id][period]
        agg["workout_count"] += 1
        
        exercises = w.get("exercises", [])
        for ex in exercises:
            ex_name = ex.get("exercise_name")
            muscles = get_muscles(ex_name)
            sets = ex.get("sets", [])
            completed_sets = [s for s in sets if s.get("completed")]
            
            ex_volume = sum(Decimal(str(s.get("weight", 0))) * Decimal(str(s.get("reps", 0))) for s in completed_sets)
            ex_sets_count = len(completed_sets)
            
            agg["total_volume"] += ex_volume
            
            for m in muscles:
                agg["muscles"][m] = agg["muscles"].get(m, Decimal("0")) + ex_volume
                agg["muscle_sets"][m] = agg["muscle_sets"].get(m, 0) + ex_sets_count
                
    # 3. Update database
    print("Updating VOLUME_AGGREGATE records...")
    for user_id, periods in aggregates.items():
        for period, data in periods.items():
            print(f"  Updating {user_id} for {period}...")
            item = {
                "pk": f"USER#{user_id}",
                "sk": f"VOL#{period}",
                "type": "VOLUME_AGGREGATE",
                "user_id": user_id,
                "period": period,
                "total_volume": data["total_volume"],
                "workout_count": data["workout_count"],
                "muscles": data["muscles"],
                "muscle_sets": data["muscle_sets"]
            }
            table.put_item(Item=item)
            
    print("Backfill completed successfully.")

if __name__ == "__main__":
    backfill()
