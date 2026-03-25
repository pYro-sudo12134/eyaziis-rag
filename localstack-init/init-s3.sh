#!/bin/bash

awslocal s3 mb s3://rag-documents

awslocal s3api put-bucket-cors --bucket rag-documents --cors-configuration '{
  "CORSRules": [
    {
      "AllowedOrigins": ["*"],
      "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
      "AllowedHeaders": ["*"]
    }
  ]
}'

echo "S3 bucket 'rag-documents' created successfully"