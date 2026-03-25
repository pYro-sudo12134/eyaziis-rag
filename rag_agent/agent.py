from typing import List, Dict
from .config import config
from .services.llm import LLMService
from .services.vector_store import VectorStore
from .utils.chunking import chunk_text
from .models.schemas import Query, Answer, SearchResult

class RAGAgent:
    """Основной класс RAG-агента"""
    
    def __init__(self):
        self.confidence = config.confidence
        self.knn_weight = config.knn_weight
        self.llm = LLMService()
        self.vector_store = VectorStore()
        self.system_prompt = """Ты русскоязычный ассистент. 

КРИТИЧЕСКИ ВАЖНЫЕ ПРАВИЛА:
1. Отвечай ТОЛЬКО на основе предоставленного контекста.
2. НЕ выдумывай фильмы, даты, имена или факты, которых нет в контексте.
3. Если в контексте нет ответа на вопрос — скажи: "В загруженных документах нет информации по этому вопросу."
4. НЕ используй свои собственные знания — ТОЛЬКО контекст.
5. ВСЕГДА отвечай на русском языке.
6. Если перечисляешь фильмы — бери их ТОЛЬКО из контекста.

Контекст может содержать только те документы, которые загрузил пользователь.
Если контекст пустой или нерелевантный — сообщи об этом честно."""
    
    def answer(self, query: Query, include_syntax: bool = True) -> Answer:
        """Основной метод получения ответа"""
        
        search_results = self.vector_store.hybrid_search(
            query=query.text,
            top_k=query.top_k or config.top_k,
            knn_weight=self.knn_weight
        )
        
        context = self._build_context(search_results)
        
        prompt = self._build_prompt(query.text, context)
        
        response_text = self.llm.generate(
            prompt=prompt,
            system_prompt=self.system_prompt,
            temperature=0.7
        )
        
        syntax_tree = None
        if include_syntax or query.session_id:
            syntax_tree = self.llm.get_syntax_tree(query.text)
        
        return Answer(
            text=response_text,
            sources=[
                SearchResult(
                    text=r['text'],
                    score=r['score'],
                    metadata=r['metadata']
                ) for r in search_results
            ],
            syntax_tree=syntax_tree
        )
    
    def _build_context(self, results: List[Dict]) -> str:
        """Собирает контекст из результатов поиска"""
        if not results:
            return "Контекст не найден."
                
        filtered_results = [r for r in results if r['score'] > self.confidence]
        
        if not filtered_results:
            return "Нет релевантных документов для ответа на вопрос."
        
        context_parts = []
        for i, result in enumerate(filtered_results, 1):
            context_parts.append(f"[{i}] {result['text']}")
        
        return "\n\n".join(context_parts)
    
    def _build_prompt(self, question: str, context: str) -> str:
        """Собирает промпт для LLM"""
        return f"""Контекст:
{context}

Вопрос: {question}

Ответ:"""
    
    def add_document(self, text: str, metadata: Dict = None, chunk_strategy: str = "semantic"):
        """Добавляет документ в векторную базу"""
        chunks = chunk_text(text, strategy=chunk_strategy)
        
        documents = []
        for i, chunk in enumerate(chunks):
            doc_metadata = metadata.copy() if metadata else {}
            doc_metadata['chunk_index'] = i
            doc_metadata['total_chunks'] = len(chunks)
            
            documents.append({
                'text': chunk,
                'metadata': doc_metadata
            })
        
        ids = self.vector_store.index_documents(documents)
        return {
            'document_ids': ids,
            'chunks_count': len(chunks),
            'strategy': chunk_strategy
        }
    
    def get_syntax(self, text: str) -> Dict:
        """Отдельный метод для синтаксического разбора"""
        return self.llm.get_syntax_tree(text)
    
    def search(self, query: str, top_k: int = None) -> List[Dict]:
        """Простой поиск без генерации"""
        return self.vector_store.search_similar(query, top_k)
    
    def hybrid_search(self, query: str, top_k: int = None) -> List[Dict]:
        """Гибридный поиск"""
        return self.vector_store.hybrid_search(query, top_k)
    
    def get_stats(self) -> Dict:
        """Статистика агента"""
        return {
            'vector_store': self.vector_store.get_stats(),
            'config': {
                'embedding_model': config.embedding_model,
                'llm_model': config.llm_model,
                'top_k': config.top_k
            }
        }
    
    def semantic_analysis(self, text: str) -> Dict:
        """
        Выполняет полный семантико-синтаксический анализ текста.
        Возвращает синтаксическое дерево, семантические роли и отношения.
        """
        return self.llm.semantic_analysis(text)
    
    def get_semantic_roles(self, text: str) -> List[Dict]:
        """
        Возвращает только семантические роли из текста.
        """
        result = self.llm.semantic_analysis(text)
        return result.get("semantic_roles", [])
    
    def get_semantic_relations(self, text: str) -> List[Dict]:
        """
        Возвращает семантические отношения между словами.
        """
        result = self.llm.semantic_analysis(text)
        return result.get("semantic_relations", [])