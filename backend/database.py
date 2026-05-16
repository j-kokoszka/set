import boto3
import os
import json
from decimal import Decimal
from botocore.exceptions import ClientError
from typing import List, Optional
from models import Workout
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

class Database:
    def __init__(self):
        self.table_name = os.getenv("DYNAMODB_TABLE", "set-workouts")
        # For local development, you can set DYNAMODB_ENDPOINT_URL
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
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceInUseException':
                raise

    def save_workout(self, workout: Workout):
        try:
            # Save workout summary
            workout_data = to_dynamo_item(workout.dict())
            item = {
                'pk': f"USER#{workout.user_id}",
                'sk': f"WORKOUT#{workout.date}#{workout.id}",
                'type': 'WORKOUT',
                **workout_data
            }
            self.table.put_item(Item=item)
            
            # Save individual exercise records for history lookup
            for ex in workout.exercises:
                ex_data = to_dynamo_item(ex.dict())
                self.table.put_item(
                    Item={
                        'pk': f"USER#{workout.user_id}",
                        'sk': f"EXERCISE#{ex.exercise_name}#{workout.date}",
                        'type': 'EXERCISE_RECORD',
                        'workout_id': workout.id,
                        **ex_data
                    }
                )
        except Exception as e:
            logger.error("Error saving to DynamoDB", error=str(e), user_id=workout.user_id, workout_id=workout.id)
            raise e

    def get_workouts(self, user_id: str) -> List[dict]:
        response = self.table.query(
            KeyConditionExpression="pk = :pk AND begins_with(sk, :sk)",
            ExpressionAttributeValues={
                ':pk': f"USER#{user_id}",
                ':sk': "WORKOUT#"
            }
        )
        return response.get('Items', [])

    def get_exercise_history(self, user_id: str, exercise_name: str) -> List[dict]:
        response = self.table.query(
            KeyConditionExpression="pk = :pk AND begins_with(sk, :sk)",
            ExpressionAttributeValues={
                ':pk': f"USER#{user_id}",
                ':sk': f"EXERCISE#{exercise_name}#"
            }
        )
        return response.get('Items', [])

    def delete_workout(self, user_id: str, workout_id: str, date: str):
        try:
            pk = f"USER#{user_id}"
            sk = f"WORKOUT#{date}#{workout_id}"
            
            # Get the workout first to find all associated exercises
            response = self.table.get_item(Key={'pk': pk, 'sk': sk})
            workout = response.get('Item')
            
            if not workout:
                return False

            with self.table.batch_writer() as batch:
                # Delete the workout summary
                batch.delete_item(Key={'pk': pk, 'sk': sk})
                
                # Delete each exercise record
                for ex in workout.get('exercises', []):
                    ex_name = ex.get('exercise_name')
                    if ex_name:
                        ex_sk = f"EXERCISE#{ex_name}#{date}"
                        batch.delete_item(Key={'pk': pk, 'sk': ex_sk})
            
            return True
        except Exception as e:
            logger.error("Error deleting from DynamoDB", error=str(e), user_id=user_id, workout_id=workout_id, date=date)
            raise e

    def update_workout(self, workout: Workout, old_date: str):
        try:
            # Delete old record
            self.delete_workout(workout.user_id, workout.id, old_date)
            # Save new record
            self.save_workout(workout)
            return True
        except Exception as e:
            logger.error("Error updating in DynamoDB", error=str(e), user_id=workout.user_id, workout_id=workout.id)
            raise e

db = Database()
