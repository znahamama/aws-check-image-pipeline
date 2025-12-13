import os
import json
import urllib.parse
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")

TABLE_NAME = os.environ.get("TABLE_NAME", "ImageRecords")
table = dynamodb.Table(TABLE_NAME)

URL_TTL_SECONDS = int(os.environ.get("URL_TTL_SECONDS", "300"))

UPLOAD_BUCKET = os.environ.get("UPLOAD_BUCKET", "ziad-image-ingest-88")
UPLOAD_PREFIX = os.environ.get("UPLOAD_PREFIX", "uploads/")
UPLOAD_URL_TTL_SECONDS = int(os.environ.get("UPLOAD_URL_TTL_SECONDS", "300"))


def _json_safe(obj):
    if isinstance(obj, list):
        return [_json_safe(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    return obj


def build_response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        },
        "body": json.dumps(_json_safe(body)),
    }


def _presigned_download_url(bucket, key):
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=URL_TTL_SECONDS,
    )


def lambda_handler(event, context):
    print("Event:", json.dumps(event))

    method = event.get("httpMethod")
    path = event.get("path", "")

    if method == "GET" and path == "/images":
        resp = table.scan(Limit=50)
        items = resp.get("Items", [])

        summaries = []
        for i in items:
            summaries.append(
                {
                    "imageId": i.get("imageId"),
                    "objectKey": i.get("objectKey"),
                    "bucket": i.get("bucket"),
                    "processedAt": i.get("processedAt"),
                    "contentType": i.get("contentType"),
                    "sizeBytes": i.get("sizeBytes"),
                    "sha256": i.get("sha256"),
                    "ocrStatus": i.get("ocrStatus"),
                    "ocrLineCount": i.get("ocrLineCount"),
                    "ocrAvgConfidencePct": i.get("ocrAvgConfidencePct"),
                }
            )

        return build_response(200, {"items": summaries})

    if method == "GET" and path.startswith("/images/"):
        path_params = event.get("pathParameters") or {}
        raw_id = path_params.get("imageId")  

        if not raw_id:
            return build_response(400, {"message": "imageId path parameter is required"})

        image_id = urllib.parse.unquote(raw_id)

        resp = table.get_item(Key={"imageId": image_id})
        item = resp.get("Item")
        if not item:
            return build_response(404, {"message": "Image not found"})

        bucket = item.get("bucket")
        key = item.get("objectKey")

        if bucket and key:
            try:
                item["downloadUrl"] = _presigned_download_url(bucket, key)
                item["urlExpiresInSeconds"] = URL_TTL_SECONDS
            except ClientError as e:
                print("presign download failed:", str(e))

        return build_response(200, item)

    if method == "POST" and path == "/uploads":
        body_raw = event.get("body") or "{}"
        try:
            body = json.loads(body_raw)
        except Exception:
            body = {}

        filename = (body.get("filename") or "upload.bin").strip()
        content_type = (body.get("contentType") or "application/octet-stream").strip()

        filename = filename.replace("/", "_")
        ext = ""
        if "." in filename:
            ext = "." + filename.split(".")[-1][:10]

        import uuid
        object_key = f"{UPLOAD_PREFIX}{uuid.uuid4().hex}{ext}"

        try:
            upload_url = s3.generate_presigned_url(
                "put_object",
                Params={"Bucket": UPLOAD_BUCKET, "Key": object_key, "ContentType": content_type},
                ExpiresIn=UPLOAD_URL_TTL_SECONDS,
            )
        except ClientError as e:
            print("presign upload failed:", str(e))
            return build_response(500, {"message": "Failed to create upload URL"})

        image_id = f"{UPLOAD_BUCKET}:{object_key}"

        return build_response(
            200,
            {
                "uploadUrl": upload_url,
                "bucket": UPLOAD_BUCKET,
                "objectKey": object_key,
                "imageId": image_id,
                "requiredHeaders": {"Content-Type": content_type},
                "expiresInSeconds": UPLOAD_URL_TTL_SECONDS,
            },
        )

    return build_response(400, {"message": f"Unsupported route: {method} {path}"})
