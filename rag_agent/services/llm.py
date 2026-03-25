import requests
import json
import time
from typing import Optional, Dict, Any, Generator
from ..config import config

class LLMService:
    def __init__(self):
        self.url = f"{config.ollama_url}/api/generate"
        self.model = config.llm_model
        self._ensure_model()
    
    def _ensure_model(self):
        """Проверяет, что модель загружена"""
        try:
            tags_url = f"{config.ollama_url}/api/tags"
            response = requests.get(tags_url)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m.get('name', '').split(':')[0] for m in models]
                if self.model.split(':')[0] not in model_names:
                    print(f"Model {self.model} not found, pulling...")
                    pull_url = f"{config.ollama_url}/api/pull"
                    requests.post(pull_url, json={"name": self.model})
                    time.sleep(2)
                    print(f"Model {self.model} pulled")
        except Exception as e:
            print(f"Could not check model: {e}")
    
    def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        stream: bool = False,
        temperature: float = 0.7,
        num_predict: int = 512
    ) -> str:
        """Генерация ответа"""
        
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        else:
            full_prompt = prompt
        
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "system": system_prompt,
            "stream": stream,
            "temperature": temperature,
            "options": {
                "num_predict": num_predict,
                "top_k": 50,
                "top_p": 0.95
            }
        }
        
        try:
            response = requests.post(self.url, json=payload, timeout=120)
            response.raise_for_status()
            
            if stream:
                return self._stream_response(response)
            else:
                result = response.json()
                return result.get("response", "")
        except requests.exceptions.RequestException as e:
            print(f"Error generating response: {e}")
            return "Извините, произошла ошибка при генерации ответа."
    
    def _stream_response(self, response) -> Generator[str, None, None]:
        """Обработка стриминга"""
        for line in response.iter_lines():
            if line:
                yield line.decode('utf-8')
    
    def generate_json(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        """Генерирует и парсит JSON ответ от LLM"""
        
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        full_prompt += "\n\nВерни только JSON без пояснений и дополнительного текста."
        
        response = self.generate(
            prompt=full_prompt,
            temperature=temperature,
            num_predict=1024
        )
        
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end != 0:
                return json.loads(response[start:end])
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"Response: {response}")
        
        return {
            "name": "Предложение",
            "children": [{"name": "Не удалось разобрать"}]
        }

    def get_syntax_tree(self, text: str) -> Dict[str, Any]:
        """Возвращает синтаксическое дерево зависимостей"""
        
        prompt = f"""Построй синтаксическое дерево зависимостей для предложения: "{text}"

    ВАЖНО: Дерево должно показывать иерархию связей между словами.
    Корень дерева — главное слово (обычно сказуемое или глагол).

    Формат JSON:
    {{
        "word": "главное_слово",
        "role": "сказуемое",
        "children": [
            {{
                "word": "зависимое_слово_1",
                "role": "подлежащее",
                "children": []
            }},
            {{
                "word": "зависимое_слово_2",
                "role": "дополнение",
                "children": []
            }}
        ]
    }}

    Пример 1: "Мама мыла раму"
    {{
        "word": "мыла",
        "role": "сказуемое",
        "children": [
            {{"word": "Мама", "role": "подлежащее", "children": []}},
            {{"word": "раму", "role": "дополнение", "children": []}}
        ]
    }}

    Пример 2: "Как твои дела?"
    {{
        "word": "дела",
        "role": "подлежащее",
        "children": [
            {{"word": "твои", "role": "определение", "children": []}},
            {{"word": "как", "role": "обстоятельство", "children": []}}
        ]
    }}

    Пример 3: "У меня сегодня дела просто превосходно"
    {{
        "word": "превосходно",
        "role": "сказуемое",
        "children": [
            {{"word": "дела", "role": "подлежащее", "children": []}},
            {{"word": "у меня", "role": "обстоятельство", "children": []}},
            {{"word": "сегодня", "role": "обстоятельство", "children": []}},
            {{"word": "просто", "role": "частица", "children": []}}
        ]
    }}

    Верни только JSON."""

        result = self.generate_json(prompt, temperature=0.1)
        
        if not result or 'word' not in result:
            return {
                "word": text,
                "role": "предложение",
                "children": []
            }
        
        return result
    
    def semantic_analysis(self, text: str) -> Dict[str, Any]:
        """
        Выполняет семантический анализ текста: выделяет семантические роли
        и семантические отношения между словами.
        """
        prompt = f"""Выполни полный семантико-синтаксический анализ предложения: "{text}"

Верни JSON со следующей структурой:

{{
    "syntax_tree": {{
        "word": "главное_слово",
        "role": "сказуемое",
        "children": [
            {{
                "word": "зависимое_слово_1",
                "role": "подлежащее",
                "children": []
            }}
        ]
    }},
    "semantic_roles": [
        {{
            "predicate": "глагол/действие",
            "agent": "кто/что совершает действие",
            "patient": "на кого/что направлено действие",
            "instrument": "чем совершается действие (если есть)",
            "location": "где происходит действие (если есть)",
            "temporal": "когда происходит действие (если есть)",
            "manner": "как происходит действие (если есть)",
            "cause": "причина (если есть)"
        }}
    ],
    "semantic_relations": [
        {{
            "type": "hypernym|hyponym|synonym|antonym|cause_effect|part_whole",
            "word1": "первое_слово",
            "word2": "второе_слово",
            "explanation": "пояснение связи"
        }}
    ],
    "summary": {{
        "predicate_center": "центральный предикат предложения",
        "participants": ["участник1", "участник2"],
        "circumstances": ["обстоятельство1", "обстоятельство2"],
        "complexity": "простое|сложное|сложносочиненное|сложноподчиненное",
        "type": "повествовательное|вопросительное|побудительное"
    }}
}}

ВАЖНО:
1. Если какая-то информация отсутствует, ставь null.
2. semantic_relations — список отношений между значимыми словами.
3. Все значения должны быть строками на русском языке.
4. Верни ТОЛЬКО JSON без пояснений."""

        result = self.generate_json(prompt, temperature=0.1)
        
        if not result or 'syntax_tree' not in result:
            syntax_tree = self.get_syntax_tree(text)
            return {
                "syntax_tree": syntax_tree,
                "semantic_roles": [],
                "semantic_relations": [],
                "summary": {
                    "predicate_center": None,
                    "participants": [],
                    "circumstances": [],
                    "complexity": "не определено",
                    "type": "не определено"
                }
            }
        
        return result