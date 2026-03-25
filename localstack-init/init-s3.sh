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

awslocal s3api put-object --bucket rag-documents --key results/
awslocal s3api put-object --bucket rag-documents --key uploads/
awslocal s3api put-object --bucket rag-documents --key results/history/