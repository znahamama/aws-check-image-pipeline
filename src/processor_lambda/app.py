import os
import json
import hashlib
from datetime import datetime

import boto3

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
textract = boto3.client("textract")

TABLE_NAME = os.environ.get("TABLE_NAME", "ImageRecords")
table = dynamodb.Table(TABLE_NAME)


def lambda_handler(event, context):
    print("Received event:", json.dumps(event))

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Processor Lambda placeholder"})
    }
