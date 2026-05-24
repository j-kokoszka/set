import sys
import os
import json
from datetime import date
from typing import List, Dict

# Ensure sys.path includes backend for imports
sys.path.append(os.path.join(os.getcwd(), "backend"))

from database import db, from_dynamo_item
from models import Workout, VolumeAggregate, PersonalRecord
import structlog

logger = structlog.get_logger()

def load_exercise_muscles():
    mapping = {}
    paths = ["backend/data/exercises.json", "backend/data/external_exercises.json"]
    for path in paths:
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
                for ex in data:
                    mapping[ex['name']] = ex.get('primaryMuscles', [])
    return mapping

def calculate_1rm(weight: float, reps: int) -> float:
    if reps <= 0: return 0.0
    if reps == 1: return weight
    return weight * (36 / (37 - reps))

def backfill():
    logger.info("Starting backfill of analytics data")
    
    # Scan the whole table for type='WORKOUT'
    try:
        response = db.table.scan(
            FilterExpression="#t = :t", 
            ExpressionAttributeNames={"#t": "type"}, 
            ExpressionAttributeValues={":t": "WORKOUT"}
        )
    except Exception as e:
        logger.error("Scan failed", error=str(e))
        return

    workouts_raw = response.get('Items', [])
    
    while 'LastEvaluatedKey' in response:
        response = db.table.scan(
            FilterExpression="#t = :t", 
            ExpressionAttributeNames={"#t": "type"}, 
            ExpressionAttributeValues={":t": "WORKOUT"},
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        workouts_raw.extend(response.get('Items', []))

    logger.info("Found workouts", count=len(workouts_raw))
    
    muscle_mapping = load_exercise_muscles()
    
    # Group by user
    user_workouts = {}
    for w_raw in workouts_raw:
        w_data = from_dynamo_item(w_raw)
        user_id = w_data.get('user_id')
        if not user_id: continue
        
        if user_id not in user_workouts:
            user_workouts[user_id] = []
        user_workouts[user_id].append(Workout(**w_data))

    for user_id, workouts in user_workouts.items():
        logger.info("Processing user", user_id=user_id, workout_count=len(workouts))
        
        # Sort workouts by date
        workouts.sort(key=lambda x: x.date)
        
        prs = {} # exercise_name -> PR object
        volume_aggs = {} # period -> Agg object
        
        for w in workouts:
            try:
                workout_date = date.fromisoformat(w.date[:10])
            except ValueError:
                logger.warning("Invalid date format", date=w.date, workout_id=w.id)
                continue
                
            period = workout_date.strftime("%Y-%m")
            
            if period not in volume_aggs:
                volume_aggs[period] = VolumeAggregate(
                    total_volume=0.0,
                    muscles={},
                    workout_count=0,
                    period=period,
                    user_id=user_id
                )
            
            agg = volume_aggs[period]
            agg.workout_count += 1
            
            for ex_record in w.exercises:
                ex_name = ex_record.exercise_name
                muscles = muscle_mapping.get(ex_name, [])
                
                ex_volume = 0.0
                best_1rm_val = 0.0
                max_w = 0.0
                max_vol_set = 0.0
                
                for s in ex_record.sets:
                    if not s.completed: continue
                    vol = s.weight * s.reps
                    ex_volume += vol
                    
                    one_rm = calculate_1rm(s.weight, s.reps)
                    if one_rm > best_1rm_val: best_1rm_val = one_rm
                    if s.weight > max_w: max_w = s.weight
                    if vol > max_vol_set: max_vol_set = vol

                agg.total_volume += ex_volume
                for m in muscles:
                    agg.muscles[m] = agg.muscles.get(m, 0.0) + ex_volume
                
                if best_1rm_val > 0:
                    if ex_name not in prs:
                        prs[ex_name] = PersonalRecord(
                            exercise_name=ex_name,
                            estimated_1rm=best_1rm_val,
                            max_weight=max_w,
                            max_volume_set=max_vol_set,
                            date_achieved=w.date,
                            user_id=user_id
                        )
                    else:
                        pr = prs[ex_name]
                        if best_1rm_val > pr.estimated_1rm:
                            pr.estimated_1rm = best_1rm_val
                            pr.date_achieved = w.date
                        if max_w > pr.max_weight: pr.max_weight = max_w
                        if max_vol_set > pr.max_volume_set: pr.max_volume_set = max_vol_set

        # Save all back to DB
        for pr in prs.values():
            db.save_personal_record(pr)
        for agg in volume_aggs.values():
            db.save_volume_aggregate(agg)

    logger.info("Backfill complete")

if __name__ == "__main__":
    backfill()
