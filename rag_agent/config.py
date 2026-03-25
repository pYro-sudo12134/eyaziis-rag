import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    opensearch_host: str = os.getenv('OPENSEARCH_HOST', 'localhost')
    opensearch_port: int = int(os.getenv('OPENSEARCH_PORT', '9200'))
    opensearch_index: str = os.getenv('OPENSEARCH_INDEX', 'rag_documents')
    
    confidence: float = float(os.getenv('CONFIDENCE', 0.5))
    ollama_host: str = os.getenv('OLLAMA_HOST', 'localhost')
    ollama_port: int = int(os.getenv('OLLAMA_PORT', '11434'))
    embedding_model: str = os.getenv('EMBEDDING_MODEL', 'nomic-embed-text')
    llm_model: str = os.getenv('LLM_MODEL', 'llama3.2')
    
    top_k: int = int(os.getenv('TOP_K', '5'))
    knn_weight: float = float(os.getenv('KNN_WEIGHT', 0.6))
    chunk_size: int = int(os.getenv('CHUNK_SIZE', '512'))
    chunk_overlap: int = int(os.getenv('CHUNK_OVERLAP', '50'))
    
    s3_endpoint_url: str = os.getenv('S3_ENDPOINT_URL', 'http://localhost:4566')
    s3_bucket_name: str = os.getenv('S3_BUCKET_NAME', 'rag-documents')
    s3_results_prefix: str = os.getenv('S3_RESULTS_PREFIX', 'results/')
    s3_uploads_prefix: str = os.getenv('S3_UPLOADS_PREFIX', 'uploads/')
    s3_access_key: str = os.getenv('AWS_ACCESS_KEY_ID', 'test')
    s3_secret_key: str = os.getenv('AWS_SECRET_ACCESS_KEY', 'test')
    s3_region: str = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    
    @property
    def opensearch_url(self) -> str:
        return f"http://{self.opensearch_host}:{self.opensearch_port}"
    
    @property
    def ollama_url(self) -> str:
        return f"http://{self.ollama_host}:{self.ollama_port}"
    
    def validate(self) -> bool:
        """Проверяет доступность сервисов"""
        import requests
        try:
            r = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if r.status_code != 200:
                return False
            return True
        except:
            return False
    
    def get_s3_config(self) -> dict:
        """Возвращает конфигурацию для S3 клиента"""
        return {
            'endpoint_url': self.s3_endpoint_url,
            'bucket_name': self.s3_bucket_name,
            'results_prefix': self.s3_results_prefix,
            'uploads_prefix': self.s3_uploads_prefix,
            'aws_access_key_id': self.s3_access_key,
            'aws_secret_access_key': self.s3_secret_key,
            'region_name': self.s3_region
        }


config = Config()