from opensearchpy import OpenSearch, RequestsHttpConnection
from typing import List, Dict, Any
import uuid
from ..config import config
from .embedding import EmbeddingService

class VectorStore:
    def __init__(self):
        self.client = OpenSearch(
            hosts=[{'host': config.opensearch_host, 'port': config.opensearch_port}],
            http_compress=True,
            use_ssl=False,
            verify_certs=False,
            connection_class=RequestsHttpConnection
        )
        self.index_name = config.opensearch_index
        self.embedding_service = EmbeddingService()
        
        self._ensure_index()
    
    def _ensure_index(self):
        """Создает индекс с поддержкой векторов если его нет"""
        if not self.client.indices.exists(index=self.index_name):
            index_body = {
                'settings': {
                    'index': {
                        'knn': True,
                        'knn.algo_param.ef_search': 512
                    }
                },
                'mappings': {
                    'properties': {
                        'text': {'type': 'text'},
                        'embedding': {
                            'type': 'knn_vector',
                            'dimension': 768,
                            'method': {
                                'name': 'hnsw',
                                'space_type': 'cosinesimil',
                                'engine': 'nmslib',
                                'parameters': {
                                    'ef_construction': 512,
                                    'm': 16
                                }
                            }
                        },
                        'metadata': {'type': 'object'}
                    }
                }
            }
            self.client.indices.create(index=self.index_name, body=index_body)
            print(f"Created index: {self.index_name}")
    
    def index_document(self, text: str, metadata: Dict[str, Any] = None, doc_id: str = None):
        """Индексирует один документ"""
        if doc_id is None:
            doc_id = str(uuid.uuid4())
        
        embedding = self.embedding_service.embed(text)
        
        document = {
            'text': text,
            'embedding': embedding,
            'metadata': metadata or {}
        }
        
        response = self.client.index(
            index=self.index_name,
            id=doc_id,
            body=document,
            refresh=True
        )
        return response['_id']
    
    def index_documents(self, documents: List[Dict[str, Any]]):
        """Индексирует несколько документов"""
        ids = []
        for doc in documents:
            doc_id = self.index_document(
                text=doc['text'],
                metadata=doc.get('metadata'),
                doc_id=doc.get('id')
            )
            ids.append(doc_id)
        return ids
    
    def search_similar(
        self, 
        query: str, 
        top_k: int = None,
        filters: Dict = None
    ) -> List[Dict]:
        """Поиск похожих документов по тексту"""
        if top_k is None:
            top_k = config.top_k
        
        query_embedding = self.embedding_service.embed(query)
        
        search_body = {
            'size': top_k,
            'query': {
                'knn': {
                    'embedding': {
                        'vector': query_embedding,
                        'k': top_k
                    }
                }
            }
        }
        
        if filters:
            search_body['query']['knn']['embedding']['filter'] = {
                'bool': {
                    'must': [
                        {'term': {k: v}} for k, v in filters.items()
                    ]
                }
            }
        
        response = self.client.search(
            index=self.index_name,
            body=search_body
        )
        
        results = []
        for hit in response['hits']['hits']:
            results.append({
                'text': hit['_source']['text'],
                'score': hit['_score'],
                'metadata': hit['_source'].get('metadata', {}),
                'id': hit['_id']
            })
        
        return results
    
    def hybrid_search(
        self, 
        query: str, 
        top_k: int = None,
        knn_weight: float = 0.5
    ) -> List[Dict]:
        """Гибридный поиск: векторный + текстовый (BM25)"""
        if top_k is None:
            top_k = config.top_k
        
        query_embedding = self.embedding_service.embed(query)
        
        search_body = {
            'size': top_k,
            'min_score': 0.5,
            'query': {
                'bool': {
                    'should': [
                        {
                            'knn': {
                                'embedding': {
                                    'vector': query_embedding,
                                    'k': top_k,
                                    'boost': knn_weight
                                }
                            }
                        },
                        {
                            'match': {
                                'text': {
                                    'query': query,
                                    'fuzziness' : 'AUTO',
                                    'boost': 1 - knn_weight
                                }
                            }
                        }
                    ]
                }
            }
        }
        
        response = self.client.search(
            index=self.index_name,
            body=search_body
        )
        
        results = []
        for hit in response['hits']['hits']:
            results.append({
                'text': hit['_source']['text'],
                'score': hit['_score'],
                'metadata': hit['_source'].get('metadata', {})
            })
        
        return results
    
    def delete_document(self, doc_id: str):
        """Удаляет документ"""
        self.client.delete(
            index=self.index_name,
            id=doc_id,
            refresh=True
        )
    
    def get_stats(self) -> Dict:
        """Статистика по индексу"""
        try:
            stats = self.client.indices.stats(index=self.index_name)
            return {
                'doc_count': stats['indices'][self.index_name]['primaries']['docs']['count'],
                'size_bytes': stats['indices'][self.index_name]['primaries']['store']['size_in_bytes']
            }
        except:
            return {'doc_count': 0, 'size_bytes': 0}