import os
import json
import urllib.parse
from decimal import Decimal

import boto3

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ.get("TABLE_NAME", "ImageRecords")
table = dynamodb.Table(TABLE_NAME)


def json_safe(obj):
    if isinstance(obj, list):
        return [json_safe(i) for i in obj]
    if isinstance(obj, dict):
        return {k: json_safe(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    return obj


def build_response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(json_safe(body)),
    }


def lambda_handler(event, context):
    print("Event:", json.dumps(event))

    http_method = event.get("httpMethod")
    path = event.get("path", "")

    if http_method != "GET":
        return build_response(405, {"message": "Method not allowed"})

    if path != "/images":
        return build_response(400, {"message": f"Unsupported route: {http_method} {path}"})

    params = event.get("queryStringParameters") or {}
    raw_image_id = params.get("imageId")

    if raw_image_id:
        image_id = urllib.parse.unquote(raw_image_id)
        resp = table.get_item(Key={"imageId": image_id})
        item = resp.get("Item")
        if not item:
            return build_response(404, {"message": "Image not found"})
        return build_response(200, item)

    resp = table.scan(Limit=50)
    items = resp.get("Items", [])
    return build_response(200, {"items": items})
