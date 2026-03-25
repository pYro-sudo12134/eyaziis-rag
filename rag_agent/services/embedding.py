import requests
from typing import List
from ..config import config

class EmbeddingService:
    def __init__(self):
        self.url = f"{config.ollama_url}/api/embeddings"
        self.model = config.embedding_model
    
    def embed(self, text: str) -> List[float]:
        """Получить эмбеддинг для текста"""
        response = requests.post(
            self.url,
            json={
                "model": self.model,
                "prompt": text
            }
        )
        response.raise_for_status()
        return response.json()["embedding"]
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Эмбеддинги для списка текстов"""
        return [self.embed(text) for text in texts]