import boto3
import uuid
import time
from decimal import Decimal

# CONFIGURATION
TABLE_NAME = 'set-workouts'
EXTERNAL_ID = 'kuba.kokoszka@gmail.com' # The identifier currently in PK
INTERNAL_ID = str(uuid.uuid4())        # The new stable internal ID

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

def migrate():
    print(f"Migrating {EXTERNAL_ID} to new internal ID {INTERNAL_ID}...")
    
    # 1. Create Identity Mapping
    mapping_pk = f"IDENTITY#{EXTERNAL_ID}"
    table.put_item(Item={
        'pk': mapping_pk,
        'sk': 'METADATA',
        'type': 'IDENTITY_MAPPING',
        'external_id': EXTERNAL_ID,
        'internal_id': INTERNAL_ID,
        'created_at': Decimal(str(time.time()))
    })
    
    # 2. Create Profile
    table.put_item(Item={
        'pk': f"USER#{INTERNAL_ID}",
        'sk': 'PROFILE',
        'type': 'USER_PROFILE',
        'primary_identity': EXTERNAL_ID,
        'internal_id': INTERNAL_ID,
        'created_at': Decimal(str(time.time()))
    })
    
    # 3. Migrate all data
    response = table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key('pk').eq(f"USER#{EXTERNAL_ID}")
    )
    items = response.get('Items', [])
    print(f"Found {len(items)} items to migrate.")
    
    for item in items:
        old_sk = item['sk']
        new_item = item.copy()
        new_item['pk'] = f"USER#{INTERNAL_ID}"
        if 'user_id' in new_item:
            new_item['user_id'] = INTERNAL_ID
        
        table.put_item(Item=new_item)
        print(f"  Migrated {old_sk}")
        
    print("Migration complete. PLEASE NOTE THE INTERNAL ID:", INTERNAL_ID)

if __name__ == "__main__":
    migrate()
