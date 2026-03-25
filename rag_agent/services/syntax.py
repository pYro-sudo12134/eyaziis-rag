from typing import Dict
from .llm import LLMService

class SyntaxService:
    """Сервис синтаксического разбора через LLM"""
    
    def __init__(self):
        self.llm = LLMService()
    
    def parse_to_tree(self, text: str) -> Dict:
        """Возвращает синтаксическое дерево для визуализации"""
        return self.llm.get_syntax_tree(text)