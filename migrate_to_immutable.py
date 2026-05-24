import boto3
import uuid
import time
import argparse
import sys
from decimal import Decimal

def migrate(external_id, table_name):
    """
    Migrates user data to the stable immutable internal ID system.
    Handles pagination and uses transactions for safety.
    """
    print(f"Starting migration for: {external_id}")
    
    dynamodb = boto3.resource('dynamodb')
    client = dynamodb.meta.client
    table = dynamodb.Table(table_name)
    
    internal_id = str(uuid.uuid4())
    now = Decimal(str(time.time()))
    
    try:
        # 1. Check if mapping already exists
        response = table.get_item(Key={'pk': f"IDENTITY#{external_id}", 'sk': 'METADATA'})
        if 'Item' in response:
            print(f"  [SKIP] Mapping already exists: {response['Item']['internal_id']}")
            return response['Item']['internal_id']

        # 2. Create internal profile and identity mapping atomically
        print(f"  Creating new identity mapping -> {internal_id}")
        client.transact_write_items(
            TransactItems=[
                {
                    'Put': {
                        'TableName': table_name,
                        'Item': {
                            'pk': {'S': f"IDENTITY#{external_id}"},
                            'sk': {'S': 'METADATA'},
                            'type': {'S': 'IDENTITY_MAPPING'},
                            'external_id': {'S': external_id},
                            'internal_id': {'S': internal_id},
                            'created_at': {'N': str(now)}
                        },
                        'ConditionExpression': 'attribute_not_exists(pk)'
                    }
                },
                {
                    'Put': {
                        'TableName': table_name,
                        'Item': {
                            'pk': {'S': f"USER#{internal_id}"},
                            'sk': {'S': 'PROFILE'},
                            'type': {'S': 'USER_PROFILE'},
                            'primary_identity': {'S': external_id},
                            'internal_id': {'S': internal_id},
                            'created_at': {'N': str(now)}
                        }
                    }
                }
            ]
        )

        # 3. Migrate all data items (with pagination)
        print(f"  Scanning for items under old identity: USER#{external_id}...")
        paginator = client.get_paginator('query')
        page_iterator = paginator.paginate(
            TableName=table_name,
            KeyConditionExpression='pk = :pk',
            ExpressionAttributeValues={':pk': {'S': f"USER#{external_id}"}}
        )

        migrate_count = 0
        for page in page_iterator:
            for item in page.get('Items', []):
                # Update PK and user_id attribute
                new_item = item.copy()
                new_item['pk'] = {'S': f"USER#{internal_id}"}
                if 'user_id' in new_item:
                    new_item['user_id'] = {'S': internal_id}
                
                # Write to new partition
                client.put_item(TableName=table_name, Item=new_item)
                migrate_count += 1
        
        print(f"  [SUCCESS] Migrated {migrate_count} items.")
        print(f"  PERMANENT INTERNAL ID: {internal_id}")
        return internal_id

    except client.exceptions.TransactionCanceledException:
        print("  [ERROR] Transaction failed. Mapping might have been created by another process.")
        sys.exit(1)
    except Exception as e:
        print(f"  [ERROR] Migration failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate user data to immutable UUID identity.")
    parser.add_argument("--email", required=True, help="The user email (external ID) to migrate.")
    parser.add_argument("--table", default="set-workouts", help="DynamoDB table name.")
    
    args = parser.parse_args()
    migrate(args.email, args.table)
