import json
import os
import boto3
import structlog
from typing import List, Dict
import time
import sys

# Ensure sys.path includes the current directory and backend directory
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "backend"))

from database import db
from models import GlobalExercise

logger = structlog.get_logger()

# Configuration
EXERCISES_FILE = "backend/data/exercises.json"
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BEDROCK_REGION = "us-east-1" # Bedrock Nova is available in us-east-1

bedrock_client = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)

def translate_exercises(exercises: List[Dict], batch_size: int = 20) -> List[Dict]:
    """
    Translates exercise names to Polish in batches using Bedrock Nova Micro.
    """
    translated_exercises = []
    
    for i in range(0, len(exercises), batch_size):
        batch = exercises[i:i + batch_size]
        names = [ex['name'] for ex in batch]
        
        prompt = f"""
        Translate the following exercise names from English to Polish. 
        Return ONLY a JSON array of strings in the same order.
        
        Names:
        {json.dumps(names)}
        
        JSON Output:
        """
        
        try:
            logger.info("Translating batch", start=i, end=min(i + batch_size, len(exercises)))
            
            response = bedrock_client.invoke_model(
                modelId="eu.amazon.nova-micro-v1:0",
                body=json.dumps({
                    "inferenceConfig": { "max_new_tokens": 1000 },
                    "messages": [
                        { "role": "user", "content": [{ "text": prompt }] }
                    ]
                })
            )
            
            response_body = json.loads(response.get("body").read())
            llm_text = response_body["output"]["message"]["content"][0]["text"]
            
            if "```json" in llm_text:
                llm_text = llm_text.split("```json")[1].split("```")[0].strip()
            elif "```" in llm_text:
                llm_text = llm_text.split("```")[1].split("```")[0].strip()
            
            polish_names = json.loads(llm_text)
            
            for j, ex in enumerate(batch):
                ex['translations'] = {'pl': polish_names[j]}
                translated_exercises.append(ex)
                
        except Exception as e:
            logger.error("Batch translation failed", error=str(e), batch=names)
            # Fallback to English if translation fails
            for ex in batch:
                ex['translations'] = {'pl': ex['name']}
                translated_exercises.append(ex)
                
        # Simple rate limiting/politeness
        time.sleep(0.5)
        
    return translated_exercises

def migrate():
    if not os.path.exists(EXERCISES_FILE):
        logger.error("Exercises file not found", path=EXERCISES_FILE)
        return

    with open(EXERCISES_FILE, "r") as f:
        exercises = json.load(f)

    logger.info("Starting migration", count=len(exercises))
    
    # Filter only essential exercises for the first run or handle all
    # For this task, we will handle all but maybe in smaller batches to Dynamo
    
    translated = translate_exercises(exercises)
    
    count = 0
    from database import to_dynamo_item
    
    with db.table.batch_writer() as batch:
        for ex_data in translated:
            try:
                # Map JSON structure to GlobalExercise model
                ex = GlobalExercise(
                    id=ex_data.get('id', ex_data['name'].replace(' ', '_')),
                    name=ex_data['name'],
                    translations=ex_data.get('translations', {}),
                    force=ex_data.get('force'),
                    level=ex_data.get('level', 'beginner'),
                    mechanic=ex_data.get('mechanic'),
                    equipment=ex_data.get('equipment'),
                    primaryMuscles=ex_data.get('primaryMuscles', []),
                    secondaryMuscles=ex_data.get('secondaryMuscles', []),
                    instructions=ex_data.get('instructions', []),
                    category=ex_data.get('category', 'strength')
                )
                
                ex_item = to_dynamo_item(ex.model_dump())
                item = {
                    'pk': "CATALOG#EXERCISES",
                    'sk': f"EXERCISE#{ex.id}",
                    'type': 'GLOBAL_EXERCISE',
                    **ex_item
                }
                
                batch.put_item(Item=item)
                count += 1
                if count % 100 == 0:
                    logger.info("Migrated exercises", count=count)
            except Exception as e:
                logger.error("Failed to migrate exercise", error=str(e), name=ex_data.get('name'))

    logger.info("Migration complete", total=count)

if __name__ == "__main__":
    # Ensure sys.path includes the current directory to find backend
    import sys
    sys.path.append(os.getcwd())
    migrate()
