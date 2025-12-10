import os
import json
import boto3

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ.get("TABLE_NAME", "ImageRecords")
table = dynamodb.Table(TABLE_NAME)


def lambda_handler(event, context):
    http_method = event.get("httpMethod")
    path = event.get("path")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "API Lambda placeholder",
            "method": http_method,
            "path": path
        })
    }
