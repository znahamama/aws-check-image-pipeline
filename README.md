# AWS Serverless Image Ingestion & OCR Pipeline

## Overview
This project implements a secure, serverless image ingestion pipeline on AWS. Clients upload images using short-lived presigned URLs, images are processed asynchronously, OCR text is extracted, and structured metadata is exposed through a REST API.

The design mirrors real-world document and check-image processing systems used in fraud detection and financial platforms, with a focus on security, scalability, and auditability.

---

## Architecture

### High-Level Architecture Diagram

<img width="2720" height="867" alt="AWS_Arch" src="https://github.com/user-attachments/assets/270f8b7c-b5a5-4c76-9b98-d3044152ebac" />

### Data Flow
1. Client requests an upload URL from the API
2. API generates a **presigned S3 PUT URL** (returned by the POST /uploads endpoint)
3. Client uploads the image directly to S3
4. S3 `ObjectCreated` event triggers the processor Lambda
5. Processor Lambda:
   - Computes SHA-256 hash
   - Extracts OCR text using Amazon Rekognition
   - Stores metadata and OCR results in DynamoDB
6. Client retrieves metadata or full OCR results via the API
7. API generates **presigned S3 GET URLs** for secure downloads

Client → API Gateway → Lambda → Presigned S3 PUT
S3 → Processor Lambda → Rekognition OCR → DynamoDB
Client → API Gateway → Lambda → Presigned S3 GET


---

## Security Model

This project is designed with a **private-by-default** security model:

- S3 bucket is **private** with public access fully blocked
- No objects are publicly accessible
- Uploads use **short-lived presigned PUT URLs** (default 5 minutes)
- Downloads use **short-lived presigned GET URLs**
- Lambda functions run with **least-privilege IAM roles**
- No long-lived credentials are exposed to clients
- Metadata is retained independently of object lifecycle for audit and traceability

---

## API Endpoints

### `POST /uploads`
Generates a presigned S3 URL for secure image upload.

**Request Body**
```json
{
  "filename": "example.png",
  "contentType": "image/png"
}
```

## Response
```json
{
  "uploadUrl": "...",
  "bucket": "...",
  "objectKey": "...",
  "imageId": "...",
  "expiresInSeconds": 300
}
```

<img width="1100" alt="POST /uploads response" src="https://github.com/user-attachments/assets/d33b721e-5b46-421a-b541-883277acceb8" />


---

### `GET /images`
Returns a list of processed images with metadata only (no OCR text).


<img width="900" alt="SGET /images response" src="https://github.com/user-attachments/assets/73e56915-19c1-436a-9097-9c1d5a26f306" />


---

### `GET /images/{imageId}`
Returns full details for a single image, including:

- OCR text

- OCR confidence and line count

- Secure, time-limited download URL


<img width="1100" alt="GET /images/{imageId} response" src="https://github.com/user-attachments/assets/ce931670-9b75-4060-8484-c256bdb34c38" />


---

## Image Upload Example (CLI)
This PUT request uploads the image directly to Amazon S3 using a short-lived presigned URL, bypassing API Gateway and Lambda for improved scalability and security.

<img width="700" alt="curl PUT upload success" src="https://github.com/user-attachments/assets/f45b4b23-1dfa-4780-871f-1cf6f25749ea" />

---

## Processing & OCR

Images are processed asynchronously when uploaded to S3.

Processing includes:

- SHA-256 hashing

- OCR extraction using Amazon Rekognition

- Structured metadata persistence in DynamoDB

<img width="900" alt="CloudWatch logs showing OCR processing" src="https://github.com/user-attachments/assets/7cde8c1a-4f48-4357-ba0d-ab2df29cdbb9" />


---

## Data Model (DynamoDB)

Each processed image record includes:

- `imageId (partition key)`

- `bucket`

- `objectKey`

- `sha256`

- `sizeBytes`

- `contentType`

- `processedAt`

- `ocrStatus`

- `ocrText (optional)`

- `ocrLineCount (optional)`

- `ocrAvgConfidencePct (optional)`

<img width="900" alt="DynamoDB item with OCR fields" src="https://github.com/user-attachments/assets/f221f84d-8680-4403-b6b7-1b7209170526" />

---

## AWS Services Used

- <img width="25" height="25" alt="image" src="https://github.com/user-attachments/assets/12a24986-5c75-4613-a3b7-204b61d62cdf" /> AWS Lambda
  
- <img width="25" height="25" alt="image" src="https://github.com/user-attachments/assets/a546d82c-5dfe-4666-a422-47e51e683fe7" /> Amazon S3

- <img width="25" height="25" alt="image" src="https://github.com/user-attachments/assets/b6d90d53-d85b-4d2b-a240-c7bc779280d8" /> Amazon DynamoDB

- <img width="25" height="25" alt="image" src="https://github.com/user-attachments/assets/971605ef-03ec-4885-9894-c4868479e957" /> Amazon Rekognition

- <img width="25" height="25" alt="image" src="https://github.com/user-attachments/assets/67edad83-010e-4f5b-b916-97d6bc45bcf7" /> Amazon API Gateway

- <img width="25" height="25" alt="image" src="https://github.com/user-attachments/assets/8c05e48a-88c9-4b86-a96d-ea1e297b10f6" /> AWS IAM

- <img width="25" height="25" alt="image" src="https://github.com/user-attachments/assets/7c207ed5-f6c1-4f09-8453-c7ee67b361e2" /> Amazon CloudWatch

---

## Design Decisions
- **Asynchronous processing:** S3 events decouple ingestion from OCR for scalability and fault isolation

- **Metadata vs object separation:** DynamoDB stores audit-friendly records independent of object lifecycle

- **Presigned URLs over public access:** Eliminates the need for public buckets

- **Incremental enrichment:** Pipeline supports future analysis without breaking existing consumers

---

## Future Improvements

- Pagination for `/images`

- MIME-type and file-size validation

- Soft-delete support

- Infrastructure as Code (Terraform or CloudFormation)

---

## Why This Project

This project demonstrates hands-on experience with:

- Event-driven serverless architectures

- Secure data ingestion patterns

- OCR pipelines and document processing

- AWS best practices for IAM and storage security

