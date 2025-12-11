import os
import json
import hashlib
from datetime import datetime
from urllib.parse import unquote_plus

import boto3

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

TABLE_NAME = os.environ.get("TABLE_NAME", "ImageRecords")
table = dynamodb.Table(TABLE_NAME)


def lambda_handler(event, context):
    print("Received event:", json.dumps(event))

    records = event.get("Records", [])
    if not records:
        print("No records in event")
        return {"statusCode": 400, "body": json.dumps({"message": "No records"})}

    for record in records:
        if record.get("eventSource") != "aws:s3":
            print("Skipping non-S3 event")
            continue

        bucket = record["s3"]["bucket"]["name"]
        raw_key = record["s3"]["object"]["key"]
        key = unquote_plus(raw_key)
        print(f"Processing object s3://{bucket}/{key}")

        obj = s3.get_object(Bucket=bucket, Key=key)
        body = obj["Body"].read()

        size_bytes = obj.get("ContentLength", len(body))
        content_type = obj.get("ContentType", "unknown")

        sha256_hash = hashlib.sha256(body).hexdigest()

        item = {
            "imageId": f"{bucket}:{key}",
            "bucket": bucket,
            "objectKey": key,
            "sha256": sha256_hash,
            "sizeBytes": size_bytes,
            "contentType": content_type,
            "processedAt": datetime.utcnow().isoformat() + "Z",
        }

        table.put_item(Item=item)
        print("Stored item in DynamoDB:", item)

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Processed records", "count": len(records)})
    }
