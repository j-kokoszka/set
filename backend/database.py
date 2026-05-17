import boto3
import os
import json
from decimal import Decimal
from botocore.exceptions import ClientError
from typing import List, Optional
from models import Workout, WorkoutPlan
import structlog

logger = structlog.get_logger()

def to_dynamo_item(obj):
    """
    Recursively convert Python types to DynamoDB-compatible formats.
    - Floats are converted to Decimals.
    - Dictionaries are filtered to remove None values.
    - Lists are processed recursively.
    """
    if isinstance(obj, list):
        return [to_dynamo_item(i) for i in obj]
    if isinstance(obj, dict):
        return {k: to_dynamo_item(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, float):
        return Decimal(str(obj))
    return obj

def from_dynamo_item(item):
    """
    Recursively convert DynamoDB items back to standard Python types.
    - Decimals are converted to floats or ints.
    """
    if isinstance(item, list):
        return [from_dynamo_item(i) for i in item]
    if isinstance(item, dict):
        return {k: from_dynamo_item(v) for k, v in item.items()}
    if isinstance(item, Decimal):
        if item % 1 == 0:
            return int(item)
        return float(item)
    return item

class Database:
    def __init__(self):
        self.table_name = os.getenv("DYNAMODB_TABLE", "set-workouts")
        endpoint_url = os.getenv("DYNAMODB_ENDPOINT_URL")
        
        if endpoint_url:
            self.db = boto3.resource(
                'dynamodb', 
                endpoint_url=endpoint_url, 
                region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
                aws_access_key_id="local",
                aws_secret_access_key="local"
            )
        else:
            self.db = boto3.resource('dynamodb', region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
        
        self.table = self.db.Table(self.table_name)

    def create_table_if_not_exists(self):
        try:
            self.db.create_table(
                TableName=self.table_name,
                KeySchema=[
                    {'AttributeName': 'pk', 'KeyType': 'HASH'},
                    {'AttributeName': 'sk', 'KeyType': 'RANGE'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'pk', 'AttributeType': 'S'},
                    {'AttributeName': 'sk', 'AttributeType': 'S'}
                ],
                ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
            )
            logger.info("Table created", table_name=self.table_name)
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceInUseException':
                raise

    def save_workout(self, workout: Workout):
        try:
            workout_data = to_dynamo_item(workout.model_dump())
            item = {
                'pk': f"USER#{workout.user_id}",
                'sk': f"WORKOUT#{workout.date}#{workout.id}",
                'type': 'WORKOUT',
                **workout_data
            }
            logger.info("Saving workout", user_id=workout.user_id, workout_id=workout.id, date=workout.date)
            self.table.put_item(Item=item)
            
            # Save individual exercise records
            for ex in workout.exercises:
                ex_data = to_dynamo_item(ex.model_dump())
                self.table.put_item(
                    Item={
                        'pk': f"USER#{workout.user_id}",
                        'sk': f"EXERCISE#{ex.exercise_name}#{workout.date}",
                        'type': 'EXERCISE_RECORD',
                        'workout_id': workout.id,
                        **ex_data
                    }
                )
            logger.info("Workout saved successfully", workout_id=workout.id)
        except Exception as e:
            logger.error("Error saving to DynamoDB", error=str(e), user_id=workout.user_id, workout_id=workout.id)
            raise e

    def get_workouts(self, user_id: str) -> List[dict]:
        try:
            response = self.table.query(
                KeyConditionExpression="pk = :pk AND begins_with(sk, :sk)",
                ExpressionAttributeValues={
                    ':pk': f"USER#{user_id}",
                    ':sk': "WORKOUT#"
                }
            )
            return from_dynamo_item(response.get('Items', []))
        except Exception as e:
            logger.error("Error querying workouts", error=str(e), user_id=user_id)
            raise e

    def get_exercise_history(self, user_id: str, exercise_name: str) -> List[dict]:
        try:
            response = self.table.query(
                KeyConditionExpression="pk = :pk AND begins_with(sk, :sk)",
                ExpressionAttributeValues={
                    ':pk': f"USER#{user_id}",
                    ':sk': f"EXERCISE#{exercise_name}#"
                }
            )
            return from_dynamo_item(response.get('Items', []))
        except Exception as e:
            logger.error("Error querying exercise history", error=str(e), user_id=user_id, exercise=exercise_name)
            raise e

    def delete_workout(self, user_id: str, workout_id: str, date: str):
        try:
            pk = f"USER#{user_id}"
            sk = f"WORKOUT#{date}#{workout_id}"
            
            response = self.table.get_item(Key={'pk': pk, 'sk': sk})
            workout = response.get('Item')
            
            if not workout:
                logger.warning("Workout not found for deletion", user_id=user_id, workout_id=workout_id)
                return False

            with self.table.batch_writer() as batch:
                batch.delete_item(Key={'pk': pk, 'sk': sk})
                for ex in workout.get('exercises', []):
                    ex_name = ex.get('exercise_name')
                    if ex_name:
                        ex_sk = f"EXERCISE#{ex_name}#{date}"
                        batch.delete_item(Key={'pk': pk, 'sk': ex_sk})
            
            logger.info("Workout deleted successfully", workout_id=workout_id)
            return True
        except Exception as e:
            logger.error("Error deleting from DynamoDB", error=str(e), user_id=user_id, workout_id=workout_id)
            raise e

    def update_workout(self, workout: Workout, old_date: str):
        try:
            logger.info("Updating workout", user_id=workout.user_id, workout_id=workout.id, old_date=old_date, new_date=workout.date)
            # Delete old record
            self.delete_workout(workout.user_id, workout.id, old_date)
            # Save new record
            self.save_workout(workout)
            return True
        except Exception as e:
            logger.error("Error updating in DynamoDB", error=str(e), user_id=workout.user_id, workout_id=workout.id)
            raise e

    def save_plan(self, plan: WorkoutPlan):
        try:
            plan_data = to_dynamo_item(plan.model_dump())
            item = {
                'pk': f"USER#{plan.user_id}",
                'sk': f"PLAN#{plan.id}",
                'type': 'PLAN',
                **plan_data
            }
            logger.info("Saving workout plan", user_id=plan.user_id, plan_id=plan.id)
            self.table.put_item(Item=item)
            logger.info("Workout plan saved successfully", plan_id=plan.id)
        except Exception as e:
            logger.error("Error saving plan to DynamoDB", error=str(e), user_id=plan.user_id, plan_id=plan.id)
            raise e

    def get_plans(self, user_id: str) -> List[dict]:
        try:
            response = self.table.query(
                KeyConditionExpression="pk = :pk AND begins_with(sk, :sk)",
                ExpressionAttributeValues={
                    ':pk': f"USER#{user_id}",
                    ':sk': "PLAN#"
                }
            )
            return from_dynamo_item(response.get('Items', []))
        except Exception as e:
            logger.error("Error querying plans", error=str(e), user_id=user_id)
            raise e

    def delete_plan(self, user_id: str, plan_id: str):
        try:
            pk = f"USER#{user_id}"
            sk = f"PLAN#{plan_id}"
            
            # Check if plan exists
            response = self.table.get_item(Key={'pk': pk, 'sk': sk})
            if 'Item' not in response:
                logger.warning("Plan not found for deletion", user_id=user_id, plan_id=plan_id)
                return False

            self.table.delete_item(Key={'pk': pk, 'sk': sk})
            logger.info("Workout plan deleted successfully", plan_id=plan_id)
            return True
        except Exception as e:
            logger.error("Error deleting plan from DynamoDB", error=str(e), user_id=user_id, plan_id=plan_id)
            raise e

db = Database()
