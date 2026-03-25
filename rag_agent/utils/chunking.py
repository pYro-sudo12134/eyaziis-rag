import re
from typing import List
from ..config import config

class ChunkingStrategy:
    """Стратегии разделения текста на чанки"""
    
    @staticmethod
    def by_sentences(text: str, max_chunk_size: int = None) -> List[str]:
        """Разбиваем по предложениям"""
        if max_chunk_size is None:
            max_chunk_size = config.chunk_size
        
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_len = len(sentence)
            
            if current_length + sentence_len <= max_chunk_size:
                current_chunk.append(sentence)
                current_length += sentence_len
            else:
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_length = sentence_len
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    @staticmethod
    def by_paragraphs(text: str) -> List[str]:
        """Разбиваем по абзацам"""
        paragraphs = text.split('\n\n')
        return [p.strip() for p in paragraphs if p.strip()]
    
    @staticmethod
    def semantic_chunking(text: str, max_chunk_size: int = None) -> List[str]:
        """Семантический чанкинг с перекрытием"""
        if max_chunk_size is None:
            max_chunk_size = config.chunk_size
        
        overlap = config.chunk_overlap
        
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = min(start + max_chunk_size, text_len)
            
            if end < text_len:
                last_period = text.rfind('.', start, end)
                if last_period != -1 and last_period > start:
                    end = last_period + 1
            
            chunks.append(text[start:end].strip())
            start = end - overlap if end < text_len else end
        
        return chunks

def chunk_text(text: str, strategy: str = "semantic") -> List[str]:
    """Унифицированный интерфейс для чанкинга"""
    strategies = {
        "sentences": ChunkingStrategy.by_sentences,
        "paragraphs": ChunkingStrategy.by_paragraphs,
        "semantic": ChunkingStrategy.semantic_chunking
    }
    
    chunker = strategies.get(strategy, ChunkingStrategy.semantic_chunking)
    return chunker(text)