import boto3
import os
import json
import uuid
import time
from decimal import Decimal
from botocore.exceptions import ClientError
from typing import List, Optional, Dict
from models import Workout, WorkoutRoutine, CustomExercise, Schedule, GlobalExercise, PersonalRecord, VolumeAggregate
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
                return None

            with self.table.batch_writer() as batch:
                batch.delete_item(Key={'pk': pk, 'sk': sk})
                for ex in workout.get('exercises', []):
                    ex_name = ex.get('exercise_name')
                    if ex_name:
                        ex_sk = f"EXERCISE#{ex_name}#{date}"
                        batch.delete_item(Key={'pk': pk, 'sk': ex_sk})
            
            logger.info("Workout deleted successfully", workout_id=workout_id)
            return from_dynamo_item(workout)
        except Exception as e:
            logger.error("Error deleting from DynamoDB", error=str(e), user_id=user_id, workout_id=workout_id)
            raise e

    def update_workout(self, workout: Workout, old_date: str):
        try:
            logger.info("Updating workout", user_id=workout.user_id, workout_id=workout.id, old_date=old_date, new_date=workout.date)
            # Delete old record
            old_workout = self.delete_workout(workout.user_id, workout.id, old_date)
            # Save new record
            self.save_workout(workout)
            return old_workout
        except Exception as e:
            logger.error("Error updating in DynamoDB", error=str(e), user_id=workout.user_id, workout_id=workout.id)
            raise e

    def save_routine(self, routine: WorkoutRoutine):
        try:
            routine_data = to_dynamo_item(routine.model_dump())
            item = {
                'pk': f"USER#{routine.user_id}",
                'sk': f"PLAN#{routine.id}",
                'type': 'PLAN',
                **routine_data
            }
            logger.info("Saving workout routine", user_id=routine.user_id, routine_id=routine.id)
            self.table.put_item(Item=item)
            logger.info("Workout routine saved successfully", routine_id=routine.id)
        except Exception as e:
            logger.error("Error saving routine to DynamoDB", error=str(e), user_id=routine.user_id, routine_id=routine.id)
            raise e

    def get_routines(self, user_id: str) -> List[dict]:
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
            logger.error("Error querying routines", error=str(e), user_id=user_id)
            raise e

    def delete_routine(self, user_id: str, routine_id: str):
        try:
            pk = f"USER#{user_id}"
            sk = f"PLAN#{routine_id}"
            
            # Check if routine exists
            response = self.table.get_item(Key={'pk': pk, 'sk': sk})
            if 'Item' not in response:
                logger.warning("Routine not found for deletion", user_id=user_id, routine_id=routine_id)
                return False

            self.table.delete_item(Key={'pk': pk, 'sk': sk})
            logger.info("Workout routine deleted successfully", routine_id=routine_id)
            return True
        except Exception as e:
            logger.error("Error deleting routine from DynamoDB", error=str(e), user_id=user_id, routine_id=routine_id)
            raise e

    def save_custom_exercise(self, exercise: CustomExercise):
        try:
            ex_data = to_dynamo_item(exercise.model_dump())
            item = {
                'pk': f"USER#{exercise.user_id}",
                'sk': f"CUSTOMEX#{exercise.id}",
                'type': 'CUSTOM_EXERCISE',
                **ex_data
            }
            logger.info("Saving custom exercise", user_id=exercise.user_id, ex_id=exercise.id)
            self.table.put_item(Item=item)
            return True
        except Exception as e:
            logger.error("Error saving custom exercise", error=str(e), user_id=exercise.user_id)
            raise e

    def get_custom_exercises(self, user_id: str) -> List[dict]:
        try:
            response = self.table.query(
                KeyConditionExpression="pk = :pk AND begins_with(sk, :sk)",
                ExpressionAttributeValues={
                    ':pk': f"USER#{user_id}",
                    ':sk': "CUSTOMEX#"
                }
            )
            return from_dynamo_item(response.get('Items', []))
        except Exception as e:
            logger.error("Error querying custom exercises", error=str(e), user_id=user_id)
            raise e

    def delete_custom_exercise(self, user_id: str, ex_id: str):
        try:
            self.table.delete_item(Key={
                'pk': f"USER#{user_id}",
                'sk': f"CUSTOMEX#{ex_id}"
            })
            return True
        except Exception as e:
            logger.error("Error deleting custom exercise", error=str(e), user_id=user_id, ex_id=ex_id)
            raise e

    def save_schedule(self, schedule: Schedule):
        try:
            schedule_data = to_dynamo_item(schedule.model_dump())
            item = {
                'pk': f"USER#{schedule.user_id}",
                'sk': f"SCHEDULE#{schedule.id}",
                'type': 'SCHEDULE',
                **schedule_data
            }
            logger.info("Saving schedule", user_id=schedule.user_id, schedule_id=schedule.id)
            self.table.put_item(Item=item)
            return True
        except Exception as e:
            logger.error("Error saving schedule to DynamoDB", error=str(e), user_id=schedule.user_id)
            raise e

    def get_schedules(self, user_id: str) -> List[dict]:
        try:
            response = self.table.query(
                KeyConditionExpression="pk = :pk AND begins_with(sk, :sk)",
                ExpressionAttributeValues={
                    ':pk': f"USER#{user_id}",
                    ':sk': "SCHEDULE#"
                }
            )
            return from_dynamo_item(response.get('Items', []))
        except Exception as e:
            logger.error("Error querying schedules", error=str(e), user_id=user_id)
            raise e

    def delete_schedule(self, user_id: str, schedule_id: str):
        try:
            self.table.delete_item(Key={
                'pk': f"USER#{user_id}",
                'sk': f"SCHEDULE#{schedule_id}"
            })
            return True
        except Exception as e:
            logger.error("Error deleting schedule from DynamoDB", error=str(e), user_id=user_id, schedule_id=schedule_id)
            raise e

    def get_routine_by_id(self, user_id: str, routine_id: str) -> Optional[dict]:
        try:
            response = self.table.get_item(Key={
                'pk': f"USER#{user_id}",
                'sk': f"PLAN#{routine_id}"
            })
            return from_dynamo_item(response.get('Item'))
        except Exception as e:
            logger.error("Error fetching routine by id", error=str(e), user_id=user_id, routine_id=routine_id)
            raise e

    def save_global_exercise(self, exercise: GlobalExercise):
        try:
            ex_data = to_dynamo_item(exercise.model_dump())
            item = {
                'pk': "CATALOG#EXERCISES",
                'sk': f"EXERCISE#{exercise.id}",
                'type': 'GLOBAL_EXERCISE',
                **ex_data
            }
            logger.info("Saving global exercise", ex_id=exercise.id, name=exercise.name)
            self.table.put_item(Item=item)
            return True
        except Exception as e:
            logger.error("Error saving global exercise", error=str(e), ex_id=exercise.id)
            raise e

    def get_global_exercises(self) -> List[dict]:
        try:
            items = []
            scan_kwargs = {
                'KeyConditionExpression': "pk = :pk AND begins_with(sk, :sk)",
                'ExpressionAttributeValues': {
                    ':pk': "CATALOG#EXERCISES",
                    ':sk': "EXERCISE#"
                }
            }
            
            done = False
            start_key = None
            while not done:
                if start_key:
                    scan_kwargs['ExclusiveStartKey'] = start_key
                response = self.table.query(**scan_kwargs)
                items.extend(response.get('Items', []))
                start_key = response.get('LastEvaluatedKey')
                done = start_key is None
                
            return from_dynamo_item(items)
        except Exception as e:
            logger.error("Error querying global exercises", error=str(e))
            raise e

    def get_personal_records(self, user_id: str) -> List[dict]:
        try:
            items = []
            query_kwargs = {
                'KeyConditionExpression': "pk = :pk AND begins_with(sk, :sk)",
                'ExpressionAttributeValues': {
                    ':pk': f"USER#{user_id}",
                    ':sk': "PR#"
                }
            }
            
            done = False
            start_key = None
            while not done:
                if start_key:
                    query_kwargs['ExclusiveStartKey'] = start_key
                response = self.table.query(**query_kwargs)
                items.extend(response.get('Items', []))
                start_key = response.get('LastEvaluatedKey')
                done = start_key is None
                
            return from_dynamo_item(items)
        except Exception as e:
            logger.error("Error querying PRs", error=str(e), user_id=user_id)
            raise e

    def save_personal_record(self, pr: PersonalRecord):
        try:
            pr_data = to_dynamo_item(pr.model_dump())
            item = {
                'pk': f"USER#{pr.user_id}",
                'sk': f"PR#{pr.exercise_name}",
                'type': 'PERSONAL_RECORD',
                **pr_data
            }
            self.table.put_item(Item=item)
            return True
        except Exception as e:
            logger.error("Error saving PR", error=str(e), user_id=pr.user_id, exercise=pr.exercise_name)
            raise e

    def get_volume_aggregates(self, user_id: str) -> List[dict]:
        try:
            items = []
            query_kwargs = {
                'KeyConditionExpression': "pk = :pk AND begins_with(sk, :sk)",
                'ExpressionAttributeValues': {
                    ':pk': f"USER#{user_id}",
                    ':sk': "VOL#"
                }
            }
            
            done = False
            start_key = None
            while not done:
                if start_key:
                    query_kwargs['ExclusiveStartKey'] = start_key
                response = self.table.query(**query_kwargs)
                items.extend(response.get('Items', []))
                start_key = response.get('LastEvaluatedKey')
                done = start_key is None
                
            return from_dynamo_item(items)
        except Exception as e:
            logger.error("Error querying volume aggregates", error=str(e), user_id=user_id)
            raise e

    def save_volume_aggregate(self, aggregate: VolumeAggregate):
        try:
            agg_data = to_dynamo_item(aggregate.model_dump())
            item = {
                'pk': f"USER#{aggregate.user_id}",
                'sk': f"VOL#{aggregate.period}",
                'type': 'VOLUME_AGGREGATE',
                **agg_data
            }
            self.table.put_item(Item=item)
            return True
        except Exception as e:
            logger.error("Error saving volume aggregate", error=str(e), user_id=aggregate.user_id, period=aggregate.period)
            raise e

    def update_volume_aggregate_atomic(self, user_id: str, period: str, total_volume_delta: float, workout_count_delta: int, muscle_volumes: Dict[str, float]):
        """
        Atomically updates volume aggregates using ADD action to prevent race conditions.
        """
        try:
            pk = f"USER#{user_id}"
            sk = f"VOL#{period}"
            
            # Use ADD to atomically increment values
            # Note: ADD creates the attribute if it doesn't exist (initializes to 0)
            update_expr = "ADD total_volume :tv, workout_count :wc"
            attr_values = {
                ':tv': Decimal(str(total_volume_delta)),
                ':wc': workout_count_delta,
                ':type': 'VOLUME_AGGREGATE',
                ':period': period,
                ':user_id': user_id
            }
            
            # SET type, period, and user_id if they don't exist
            # Note: ADD cannot be used for strings, so we use SET with if_not_exists
            set_expr_parts = [
                "period = if_not_exists(period, :period)",
                "user_id = if_not_exists(user_id, :user_id)",
                "#t = if_not_exists(#t, :type)"
            ]
            
            # Add muscle volume updates
            # DynamoDB 'ADD' works on Number types in a Map too? No, ADD is only for top-level attributes or sets.
            # For maps, we have to use SET muscles.#m = if_not_exists(muscles.#m, :zero) + :delta
            # This is complex for a dynamic list of muscles.
            # Alternative: Since we only have a few muscles, we can build the SET expression dynamically.
            
            attr_names = {"#t": "type", "#muscles": "muscles"}
            for i, (muscle, delta) in enumerate(muscle_volumes.items()):
                m_key = f"#m{i}"
                v_key = f":v{i}"
                zero_key = f":z{i}"
                attr_names[m_key] = muscle
                attr_values[v_key] = Decimal(str(delta))
                attr_values[zero_key] = Decimal("0")
                set_expr_parts.append(f"#muscles.{m_key} = if_not_exists(#muscles.{m_key}, {zero_key}) + {v_key}")

            # Ensure 'muscles' map exists
            set_expr_parts.insert(0, "#muscles = if_not_exists(#muscles, :empty_map)")
            attr_values[':empty_map'] = {}

            full_expr = f"{update_expr} SET {', '.join(set_expr_parts)}"
            
            self.table.update_item(
                Key={'pk': pk, 'sk': sk},
                UpdateExpression=full_expr,
                ExpressionAttributeNames=attr_names,
                ExpressionAttributeValues=attr_values
            )
            return True
        except Exception as e:
            logger.error("Error atomically updating volume aggregate", error=str(e), user_id=user_id, period=period)
            raise e

    def get_or_create_internal_user_id(self, external_id: str) -> str:
        """
        Maps an external identifier (e.g. email, Cognito sub) to a stable internal UUID.
        Uses a transaction and conditional check to handle concurrent requests safely.
        """
        try:
            # 1. Try to find existing mapping
            pk = f"IDENTITY#{external_id}"
            sk = "METADATA"
            
            response = self.table.get_item(Key={'pk': pk, 'sk': sk})
            item = response.get('Item')
            
            if item:
                return item['internal_id']
            
            # 2. Create new mapping if not found
            internal_id = str(uuid.uuid4())
            logger.info("Creating new user identity mapping", external_id=external_id, internal_id=internal_id)
            
            now = Decimal(str(time.time()))
            
            # Use a transaction to ensure atomicity and prevent race conditions
            self.db.meta.client.transact_write_items(
                TransactItems=[
                    {
                        'Put': {
                            'TableName': self.table_name,
                            'Item': to_dynamo_item({
                                'pk': pk,
                                'sk': sk,
                                'type': 'IDENTITY_MAPPING',
                                'external_id': external_id,
                                'internal_id': internal_id,
                                'created_at': now
                            }),
                            # Condition ensures we don't overwrite if another request beat us to it
                            'ConditionExpression': 'attribute_not_exists(pk)'
                        }
                    },
                    {
                        'Put': {
                            'TableName': self.table_name,
                            'Item': to_dynamo_item({
                                'pk': f"USER#{internal_id}",
                                'sk': "PROFILE",
                                'type': 'USER_PROFILE',
                                'primary_identity': external_id,
                                'internal_id': internal_id,
                                'created_at': now
                            })
                        }
                    }
                ]
            )
            
            return internal_id
            
        except self.db.meta.client.exceptions.TransactionCanceledException as e:
            # Check if it failed because the condition was not met (mapping already exists)
            for reason in e.response.get('CancellationReasons', []):
                if reason.get('Code') == 'ConditionalCheckFailed':
                    # Another process created the mapping, just fetch it
                    logger.info("Concurrency handled: mapping already exists", external_id=external_id)
                    return self.get_or_create_internal_user_id(external_id)
            raise e
        except Exception as e:
            logger.error("Error in identity mapping logic", error=str(e), external_id=external_id)
            raise e

db = Database()
