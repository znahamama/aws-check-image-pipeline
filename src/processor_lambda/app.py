import os
import json
import hashlib
from datetime import datetime
from urllib.parse import unquote_plus

import boto3
from botocore.exceptions import ClientError

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

REGION = os.environ.get("AWS_REGION", "us-east-1")
rekognition = boto3.client("rekognition", region_name=REGION)

TABLE_NAME = os.environ.get("TABLE_NAME", "ImageRecords")
table = dynamodb.Table(TABLE_NAME)

ENABLE_OCR = os.environ.get("ENABLE_OCR", "0") in ("1", "true", "True", "yes", "YES")
OCR_MAX_LINES = int(os.environ.get("OCR_MAX_LINES", "50"))
OCR_MAX_BYTES = int(os.environ.get("OCR_MAX_BYTES", str(5 * 1024 * 1024)))


def lambda_handler(event, context):
    print("Received event:", json.dumps(event))

    records = event.get("Records", [])
    if not records:
        return {"statusCode": 400, "body": json.dumps({"message": "No records"})}

    for record in records:
        if record.get("eventSource") != "aws:s3":
            continue

        bucket = record["s3"]["bucket"]["name"]
        raw_key = record["s3"]["object"]["key"]
        key = unquote_plus(raw_key)

        print(f"Processing object s3://{bucket}/{key}")

        try:
            obj = s3.get_object(Bucket=bucket, Key=key)
            body = obj["Body"].read()
        except ClientError as e:
            print("S3 get_object ClientError:", str(e))
            continue

        size_bytes = obj.get("ContentLength", len(body))
        content_type = obj.get("ContentType", "unknown")

        sha256_hash = hashlib.sha256(body).hexdigest()

        ocr_status = "SKIPPED"
        ocr_text = ""
        ocr_avg_conf = None
        ocr_line_count = 0

        if ENABLE_OCR:
            if size_bytes > OCR_MAX_BYTES:
                ocr_status = "SKIPPED_TOO_LARGE"
            else:
                try:
                    resp = rekognition.detect_text(Image={"Bytes": body})

                    lines = []
                    confs = []

                    for d in resp.get("TextDetections", []):
                        if d.get("Type") == "LINE" and d.get("DetectedText"):
                            lines.append(d["DetectedText"])
                            if "Confidence" in d:
                                confs.append(float(d["Confidence"]))

                    lines = lines[:OCR_MAX_LINES]
                    ocr_text = "\n".join(lines)
                    ocr_line_count = len(lines)
                    ocr_avg_conf = (sum(confs) / len(confs)) if confs else None
                    ocr_status = "SUCCESS"

                except ClientError as e:
                    print("Rekognition ClientError:", str(e))
                    ocr_status = "FAILED"
                except Exception as e:
                    print("OCR failed:", str(e))
                    ocr_status = "FAILED"

        item = {
            "imageId": f"{bucket}:{key}",
            "bucket": bucket,
            "objectKey": key,
            "sha256": sha256_hash,
            "sizeBytes": int(size_bytes),
            "contentType": content_type,
            "processedAt": datetime.utcnow().isoformat() + "Z",
            "ocrStatus": ocr_status,
        }

        if ocr_text:
            item["ocrText"] = ocr_text
            item["ocrLineCount"] = int(ocr_line_count)
        if ocr_avg_conf is not None:
            item["ocrAvgConfidencePct"] = int(round(ocr_avg_conf))

        table.put_item(Item=item)
        print("Stored item in DynamoDB:", item)

    return {"statusCode": 200, "body": json.dumps({"message": "Processed"})}
