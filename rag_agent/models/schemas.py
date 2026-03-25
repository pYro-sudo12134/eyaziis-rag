from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class Document(BaseModel):
    """Документ для индексации"""
    text: str
    metadata: Dict[str, Any] = {}
    id: Optional[str] = None

class SearchResult(BaseModel):
    """Результат поиска"""
    text: str
    score: float
    metadata: Dict[str, Any] = {}

class Query(BaseModel):
    """Пользовательский запрос"""
    text: str
    session_id: Optional[str] = None
    top_k: Optional[int] = None

class Answer(BaseModel):
    """Ответ агента"""
    text: str
    sources: List[SearchResult] = []
    syntax_tree: Optional[Dict] = None
    thinking: Optional[str] = None  # для отладки