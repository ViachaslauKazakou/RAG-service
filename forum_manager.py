import hashlib
from typing import List, Dict, Optional, Union
import json
import re
from app.utils.logger_utils import timer, setup_logger
from app.ai_manager.rag_langchain import AdvancedRAG
from ollama import chat
from ollama import ChatResponse

# Настройка логирования - ИСПРАВЛЕННАЯ ВЕРСИЯ
logger = setup_logger(__name__)


class AIModels:
    """
    Class to manage AI models and their identifiers.
    """

    light: str = "google/flan-t5-base"
    medium: str = "google/flan-t5-large"
    heavy: str = "google/flan-t5-xl"
    light_1: str = "mistralai/Mistral-7B-Instruct-v0.2"
    distilgpt2: str = "distilgpt2"
    llama_mistral: str = "mistral:latest"
    deepseek: str = "deepseek-r1"
    gemma: str = "gemma3:latest"


class CharacterPersona:
    """Класс для управления персонажами форума"""

    CHARACTERS = {
        "alaev": {
            "type": "forum_troll",
            "personality": "Язвительный и провокационный, грубый, любит спорить, часто использует сарказм, Постоянно оценивает собеседника",
            "speech_pattern": "Длинные фразы, оторванные от контекста, устаревшие технологии, любит отрицать все и спорить с окружающими",
            "expertise": "Старые технологии, критика новых подходов, ненавидит Польшу",
            "mood_variations": ["sarcastic", "aggressive", "nostalgic", "provocative"],
        },
        "Sly32": {
            "type": "senior_python_engineer",
            "personality": "Профессиональный, терпеливый, конструктивный",
            "speech_pattern": "Структурированные ответы, примеры кода, профессиональная терминология",
            "expertise": "Python, архитектура, best practices",
            "mood_variations": ["helpful", "professional", "patient", "analytical"],
        },
        "Data_Scientist": {
            "type": "senior_data_scientist",
            "personality": "Аналитический, основан на данных, методичный",
            "speech_pattern": "Статистика, графики, научный подход",
            "expertise": "Машинное обучение, анализ данных, статистика",
            "mood_variations": ["analytical", "curious", "methodical", "research_focused"],
        },
        "Domen77": {
            "type": "forum_troll",
            "personality": "Завистливый, провокационный, любит спорить, болтливый не по теме",
            "speech_pattern": "Отвечает часто с сарказмом, использует провокации",
            "expertise": "Нет особой экспертизы, просто любит спорить, провоцировать, не компетентен в вопросах о которых пишет",
            "mood_variations": ["provocative", "sly", "encouraging", "neutral"],
        },
        "nechaos": {
            "type": "forum_troll",
            "personality": "Завистливый, провокационный, любит спорить",
            "speech_pattern": "Отвечает часто невпопад, использует провокации, не использует слова-паразиты, и жаргон, всегда короткие ответы не более 100 знаковБ в конце любит использовать фразу 'Если Вам выучиться на [профессия], чтобы критиканы не могли давить на это уязвимое место?'",
            "expertise": "глупый, некомпетентный, любит спорить, любит флудить, отрифает возможности Искуственного интеллекта",
            "mood_variations": ["provocative", "dumb", "encouraging", "neutral"],
        },
    }


class ForumRAG(AdvancedRAG):
    """Расширенный RAG для работы с форумными персонажами"""

    def __init__(self, documents_path: str = "app/ai_forum/forum_knowledge_base", cache_path: str = "forum_cache"):
        super().__init__(documents_path, cache_path)
        self.character_persona = CharacterPersona()
        self.model = AIModels.gemma  # Используем модель Gemma3 по умолчанию

    def parse_character_message(self, text: str) -> Dict:
        """Парсит сообщение персонажа из JSON или текстового формата"""
        logger.info(f"🔍 Парсинг сообщения: {text[:100]}...")
        
        # Сначала пытаемся парсить как JSON
        try:
            # Если это JSON строка
            if text.strip().startswith("{") and text.strip().endswith("}"):
                logger.info("   📝 Попытка парсинга как JSON объект")
                data = json.loads(text)
                result = self._normalize_json_message(data)
                logger.info(f"   ✅ JSON парсинг успешен: character='{result.get('character')}', content='{result.get('content', '')[:50]}...'")
                return result

            # Если это массив JSON объектов
            if text.strip().startswith("[") and text.strip().endswith("]"):
                logger.info("   📝 Попытка парсинга как JSON массив")
                data = json.loads(text)
                if isinstance(data, list) and len(data) > 0:
                    result = self._normalize_json_message(data[0])  # Берем первое сообщение
                    logger.info(f"   ✅ JSON массив парсинг успешен: character='{result.get('character')}', content='{result.get('content', '')[:50]}...'")
                    return result

            # Если это несколько JSON объектов подряд
            logger.info("   📝 Попытка извлечения JSON объектов из текста")
            json_objects = self._extract_json_objects(text)
            if json_objects:
                result = self._normalize_json_message(json_objects[0])
                logger.info(f"   ✅ Извлечение JSON успешно: character='{result.get('character')}', content='{result.get('content', '')[:50]}...'")
                return result

        except json.JSONDecodeError as e:
            logger.info(f"   ❌ JSON парсинг не удался: {e}")

        # Fallback к парсингу текстового формата
        logger.info("   📝 Fallback к текстовому формату")
        result = self._parse_text_format(text)
        logger.info(f"   📄 Текстовый парсинг: character='{result.get('character', 'unknown')}', content='{result.get('content', '')[:50]}...'")
        return result

    def _extract_json_objects(self, text: str) -> List[Dict]:
        """Извлекает JSON объекты из текста"""
        json_objects = []

        # Паттерн для поиска JSON объектов
        pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
        matches = re.finditer(pattern, text, re.DOTALL)

        for match in matches:
            try:
                json_obj = json.loads(match.group())
                json_objects.append(json_obj)
            except json.JSONDecodeError:
                continue

        return json_objects

    def _normalize_json_message(self, data: Dict) -> Dict:
        """Нормализует JSON сообщение к стандартному формату"""
        logger.info(f"📋 Нормализация JSON: {str(data)[:100]}...")
        
        # Поддерживаем разные варианты структуры JSON
        if "messages" in data and isinstance(data["messages"], list):
            # Формат: {"messages": [{"character": "...", "content": "..."}]}
            logger.info("   📝 Найден формат с массивом messages")
            message = data["messages"][0] if data["messages"] else {}
        else:
            # Формат: {"character": "...", "content": "..."}
            logger.info("   📝 Найден прямой формат JSON")
            message = data

        normalized = {
            "character": message.get("character", "unknown"),
            "type": message.get("character_type", message.get("type", "unknown")),
            "mood": message.get("mood", "neutral"),
            "context": message.get("context", "general"),
            "content": message.get("content", message.get("message", "")),
            "timestamp": message.get("timestamp", ""),
            "reply_to": message.get("reply_to"),
            "id": message.get("id", ""),
            "raw_text": json.dumps(message, ensure_ascii=False),
        }
        
        logger.info(f"   ✅ Нормализовано: character='{normalized['character']}', type='{normalized['type']}', content='{normalized['content'][:50]}...'")
        return normalized

    def _parse_text_format(self, text: str) -> Dict:
        """Парсит текстовый формат (fallback)"""
        # Паттерн для извлечения метаданных из текстового формата
        pattern = r"\[CHARACTER: ([^|]+) \| TYPE: ([^|]+) \| MOOD: ([^|]+) \| CONTEXT: ([^\]]+)\]"
        match = re.search(pattern, text)

        if match:
            character, char_type, mood, context = match.groups()
            content = text[match.end() :].strip()

            return {
                "character": character.strip(),
                "type": char_type.strip(),
                "mood": mood.strip(),
                "context": context.strip(),
                "content": content,
                "raw_text": text,
            }

        return {"content": text, "raw_text": text}

    def parse_all_messages_from_json_array(self, text: str) -> List[Dict]:
        """Новый метод: парсит ВСЕ сообщения из JSON массива как отдельные документы
        
        Учитывает поля: content, context, reply_to, thread_id и другие
        Возвращает список всех сообщений, а не только первое
        """
        logger.info(f"🔍 Парсинг всех сообщений из JSON массива: {text[:100]}...")
        
        all_messages = []
        
        try:
            # Сначала пытаемся парсить как JSON
            if text.strip().startswith("{") and text.strip().endswith("}"):
                logger.info("   📝 Попытка парсинга как JSON объект")
                data = json.loads(text)
                
                # Проверяем, есть ли массив messages внутри объекта
                if "messages" in data and isinstance(data["messages"], list):
                    logger.info(f"   📝 Найден массив messages с {len(data['messages'])} элементами")
                    for i, message in enumerate(data["messages"]):
                        normalized = self._normalize_json_message_extended(message, i)
                        all_messages.append(normalized)
                        logger.info(f"   ✅ Сообщение {i+1}: {normalized.get('character')} - {normalized.get('content', '')[:50]}...")
                else:
                    # Обычный объект - преобразуем в один документ
                    normalized = self._normalize_json_message_extended(data, 0)
                    all_messages.append(normalized)
                    logger.info(f"   ✅ Одиночное сообщение: {normalized.get('character')} - {normalized.get('content', '')[:50]}...")

            # Если это массив JSON объектов напрямую
            elif text.strip().startswith("[") and text.strip().endswith("]"):
                logger.info("   📝 Попытка парсинга как JSON массив")
                data = json.loads(text)
                if isinstance(data, list):
                    logger.info(f"   📝 Найден прямой массив с {len(data)} элементами")
                    for i, message in enumerate(data):
                        normalized = self._normalize_json_message_extended(message, i)
                        all_messages.append(normalized)
                        logger.info(f"   ✅ Сообщение {i+1}: {normalized.get('character')} - {normalized.get('content', '')[:50]}...")

            # Если это несколько JSON объектов подряд
            else:
                logger.info("   📝 Попытка извлечения JSON объектов из текста")
                json_objects = self._extract_json_objects(text)
                for i, obj in enumerate(json_objects):
                    normalized = self._normalize_json_message_extended(obj, i)
                    all_messages.append(normalized)
                    logger.info(f"   ✅ Извлеченное сообщение {i+1}: {normalized.get('character')} - {normalized.get('content', '')[:50]}...")

        except json.JSONDecodeError as e:
            logger.info(f"   ❌ JSON парсинг не удался: {e}")
            # Fallback к старому методу
            fallback_result = self._parse_text_format(text)
            all_messages.append(fallback_result)

        logger.info(f"   📊 Всего извлечено сообщений: {len(all_messages)}")
        return all_messages

    def _normalize_json_message_extended(self, data: Dict, index: int = 0) -> Dict:
        """Расширенная нормализация JSON сообщения с учетом всех полей
        
        Учитывает: content, context, reply_to, thread_id, character, mood, timestamp и др.
        """
        logger.info(f"📋 Расширенная нормализация JSON (индекс {index}): {str(data)[:100]}...")
        
        # Поддерживаем разные варианты структуры JSON
        message = data
        
        # Извлекаем все доступные поля
        normalized = {
            "character": message.get("character", "unknown"),
            "type": message.get("character_type", message.get("type", "unknown")),
            "mood": message.get("mood", "neutral"),
            "context": message.get("context", "general"),
            "content": message.get("content", message.get("message", "")),
            "timestamp": message.get("timestamp", ""),
            "reply_to": message.get("reply_to"),
            "thread_id": message.get("thread_id"),  # Новое поле
            "id": message.get("id", f"msg_{index:03d}"),
            "raw_text": json.dumps(message, ensure_ascii=False),
            "message_index": index,  # Индекс сообщения в массиве
        }
        
        # Создаем расширенный контент, включающий дополнительную информацию
        extended_content = normalized["content"]
        
        # Добавляем контекстную информацию в содержимое для лучшего поиска
        context_parts = []
        if normalized.get("context") and normalized["context"] != "general":
            context_parts.append(f"Контекст: {normalized['context']}")
        if normalized.get("reply_to"):
            context_parts.append(f"Ответ на: {normalized['reply_to']}")
        if normalized.get("thread_id"):
            context_parts.append(f"Тема: {normalized['thread_id']}")
        
        if context_parts:
            extended_content = f"{extended_content}\n[{' | '.join(context_parts)}]"
        
        normalized["extended_content"] = extended_content
        
        logger.info(f"   ✅ Расширенная нормализация: character='{normalized['character']}', "
                    f"context='{normalized['context']}', thread_id='{normalized.get('thread_id')}', "
                    f"reply_to='{normalized.get('reply_to')}', content='{normalized['content'][:50]}...'")
        
        return normalized

    def get_character_relevant_docs(self, query: str, character: str, top_k: int = 20) -> List[Dict]:
        """Получает документы, релевантные для конкретного персонажа"""
        logger.info(f"🔍 Поиск документов для персонажа '{character}' по запросу: '{query}' (top_k={top_k})")
        
        if not self.vectorstore:
            logger.warning("❌ Vectorstore не инициализирован")
            return []

        try:
            # Модифицируем запрос для поиска сообщений конкретного персонажа
            character_queries = [
                f'"{character}"',  # Точное совпадение имени
                f"character: {character}",  # Поиск по полю character
                f"{character} {query}",  # Комбинированный поиск
                query,  # Обычный поиск
            ]

            all_docs = []
            character_docs_found = 0
            other_docs_found = 0

            # Пробуем разные варианты запросов
            for query_idx, char_query in enumerate(character_queries):
                logger.info(f"📝 Попытка запроса {query_idx + 1}/4: '{char_query}'")
                try:
                    docs_with_scores = self.vectorstore.similarity_search_with_score(char_query, k=top_k * 2)
                    logger.info(f"   Найдено {len(docs_with_scores)} документов от vectorstore")

                    for doc_idx, (doc, score) in enumerate(docs_with_scores):
                        # Парсим сообщение
                        parsed = self.parse_character_message(doc.page_content)
                        parsed_character = parsed.get("character", "unknown").lower().strip()
                        target_character = character.lower().strip()
                        
                        logger.info(f"   📄 Документ {doc_idx + 1}: parsed_character='{parsed_character}', target='{target_character}', score={score:.4f}")
                        logger.info(f"      Содержимое: {parsed.get('content', '')[:100]}...")
                        
                        # ИСПРАВЛЕННАЯ ЛОГИКА ФИЛЬТРАЦИИ - только точное совпадение персонажа
                        if parsed_character == target_character:
                            character_docs_found += 1
                            similarity_score = 1.0 / (1.0 + score)

                            # Фильтрация по минимальному score - только релевантные документы
                            if similarity_score > 0.3:
                                doc_info = {
                                    "content": parsed.get("content", doc.page_content),
                                    "character": parsed.get("character", "unknown"),
                                    "type": parsed.get("type", "unknown"),
                                    "mood": parsed.get("mood", "neutral"),
                                    "context": parsed.get("context", "general"),
                                    "timestamp": parsed.get("timestamp", ""),
                                    "similarity_score": similarity_score,
                                    "distance_score": float(score),
                                    "metadata": doc.metadata,
                                    "raw_text": doc.page_content,
                                    "query_type": char_query,
                                }
                                all_docs.append(doc_info)
                                logger.info(f"   ✅ ДОБАВЛЕН документ от {parsed_character} (score={similarity_score:.4f})")
                            else:
                                logger.info(f"   ⚠️ ПРОПУЩЕН документ от {parsed_character} (низкий score={similarity_score:.4f})")
                        else:
                            other_docs_found += 1
                            logger.info(f"   ❌ ПРОПУЩЕН документ от '{parsed_character}' (не совпадает с '{target_character}')")

                except Exception as e:
                    logger.warning(f"❌ Query '{char_query}' failed: {e}")
                    continue

            logger.info(f"📊 Статистика поиска: {character_docs_found} документов от {character}, {other_docs_found} от других персонажей")

            # Удаляем дубликаты и сортируем
            unique_docs = {}
            for doc in all_docs:
                # key = doc["content"][:100]  # Используем первые 100 символов как ключ
                key = hashlib.md5(doc["content"].encode()).hexdigest()  # Используем hash всего контента
                if key not in unique_docs or doc["similarity_score"] > unique_docs[key]["similarity_score"]:
                    unique_docs[key] = doc

            # Сортируем по релевантности
            character_docs = list(unique_docs.values())
            character_docs.sort(key=lambda x: x["similarity_score"], reverse=True)

            logger.info(f"✅ Финальный результат: {len(character_docs)} уникальных документов для персонажа {character}")
            
            # Логируем детали найденных документов
            for idx, doc in enumerate(character_docs[:5]):  # Только первые 5 для лога
                logger.info(f"   📄 {idx + 1}. {doc['character']} (score={doc['similarity_score']:.4f}): {doc['content'][:80]}...")
            
            return character_docs[:top_k]

        except Exception as e:
            logger.error(f"❌ Error getting character documents: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return []

    def get_character_context(self, character: str, mood: Optional[str] = None) -> str:
        """Получает контекст для персонажа"""
        if character not in self.character_persona.CHARACTERS:
            logger.warning(f"Character {character} not found in persona")
            return ""

        char_info = self.character_persona.CHARACTERS[character]

        context = f"""
            Ты играешь роль персонажа {character} на форуме.
            Характеристики персонажа:
            - Тип: {char_info['type']}
            - Личность: {char_info['personality']}
            - Стиль речи: {char_info['speech_pattern']}
            - Экспертиза: {char_info['expertise']}
            - Текущее настроение: {mood or 'нейтральное'}
            Отвечай в характере этого персонажа, используя его стиль речи и подход к проблемам. не используй оскорбления. не более 300 символов в ответе.
            """
        return context

    def validate_json_format(self, file_path: str) -> bool:
        """Проверяет валидность JSON формата в файле"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Пытаемся парсить весь файл как JSON
            try:
                json.loads(content)
                return True
            except json.JSONDecodeError:
                # Пытаемся найти отдельные JSON объекты
                json_objects = self._extract_json_objects(content)
                return len(json_objects) > 0

        except Exception as e:
            logger.error(f"Error validating JSON format: {e}")
            return False

    def convert_text_to_json(self, text_content: str) -> str:
        """Конвертирует текстовый формат в JSON"""
        messages = []

        # Паттерн для извлечения сообщений
        pattern = r"\[CHARACTER: ([^|]+) \| TYPE: ([^|]+) \| MOOD: ([^|]+) \| CONTEXT: ([^\]]+)\]\s*([^[]*)"
        matches = re.finditer(pattern, text_content, re.MULTILINE | re.DOTALL)

        for i, match in enumerate(matches):
            character, char_type, mood, context, content = match.groups()

            message = {
                "id": f"msg_{i+1:03d}",
                "character": character.strip(),
                "character_type": char_type.strip(),
                "mood": mood.strip(),
                "context": context.strip(),
                "content": content.strip(),
                "timestamp": "",
                "reply_to": None,
            }
            messages.append(message)

        return json.dumps({"messages": messages}, ensure_ascii=False, indent=2)

    def get_character_stats(self) -> Dict:
        """Возвращает статистику по персонажам в базе"""
        if not self.vectorstore:
            return {}

        stats = {}
        try:
            # Получаем все документы
            all_docs = self.vectorstore.similarity_search("", k=1000)
            logger.info(f"Found {len(all_docs)} documents for character stats")

            for doc in all_docs:
                parsed = self.parse_character_message(doc.page_content)
                character = parsed.get("character", "unknown")

                if character not in stats:
                    stats[character] = {"count": 0, "moods": set(), "contexts": set(), "types": set()}

                stats[character]["count"] += 1
                stats[character]["moods"].add(parsed.get("mood", "neutral"))
                stats[character]["contexts"].add(parsed.get("context", "general"))
                stats[character]["types"].add(parsed.get("type", "unknown"))

            # Конвертируем sets в lists для JSON serialization
            for char in stats:
                stats[char]["moods"] = list(stats[char]["moods"])
                stats[char]["contexts"] = list(stats[char]["contexts"])
                stats[char]["types"] = list(stats[char]["types"])

        except Exception as e:
            logger.error(f"Error getting character stats: {e}")

        return stats

    @timer
    def simulate_forum_discussion(self, topic: str, participants: Optional[List[str]] = None, rounds: int = 3):
        """Симулирует форумную дискуссию между персонажами"""
        if not participants:
            participants = ["Alaev", "Senior_Dev", "Data_Scientist", "Forum_Moderator"]

        logger.info(f"Starting forum discussion on: {topic}")

        discussion = []
        current_topic = topic

        for round_num in range(rounds):
            logger.info(f"Discussion round {round_num + 1}")

            for participant in participants:
                # Каждый персонаж отвечает на текущую тему
                response = self.ask_as_character(
                    f"Обсуждаем тему: {current_topic}. Выскажи свое мнение.", participant, translate=True
                )

                discussion.append(
                    {"round": round_num + 1, "character": participant, "message": response, "topic": current_topic}
                )

                # Обновляем тему для следующего участника
                current_topic = f"{topic}. Предыдущий участник сказал: {response[:100]}..."

        return discussion

    def get_available_characters(self) -> List[str]:
        """Возвращает список доступных персонажей"""
        return list(self.character_persona.CHARACTERS.keys())

    def get_character_info(self, character: str) -> Dict:
        """Возвращает информацию о персонаже"""
        return self.character_persona.CHARACTERS.get(character, {})

    def setup_rag_with_extended_parsing(self):
        """Настраивает RAG с расширенным парсингом JSON массивов
        
        Использует новый метод для извлечения каждого сообщения как отдельного документа
        Учитывает: content, context, reply_to, thread_id
        """
        logger.info("🔧 Настройка RAG с расширенным парсингом JSON массивов...")
        
        # Очищаем кеш для принудительного пересоздания
        self.clear_cache()
        
        # Используем новый метод создания документов
        self.create_extended_documents_from_json(use_extended_parsing=True)
        
        logger.info("✅ RAG с расширенным парсингом настроен")

    def get_character_relevant_docs_extended(self, query: str, character: str, top_k: int = 20) -> List[Dict]:
        """Получает документы с расширенным парсингом JSON
        
        Использует метаданные для более точной фильтрации по персонажам
        """
        logger.info(f"🔍 Расширенный поиск документов для персонажа '{character}' по запросу: '{query}' (top_k={top_k})")
        
        if not self.vectorstore:
            logger.warning("❌ Vectorstore не инициализирован")
            return []

        try:
            # Модифицируем запрос для поиска сообщений конкретного персонажа
            character_queries = [
                f'"{character}"',  # Точное совпадение имени
                f"character: {character}",  # Поиск по полю character
                f"{character} {query}",  # Комбинированный поиск
                query,  # Обычный поиск
            ]

            all_docs = []
            character_docs_found = 0

            # Пробуем разные варианты запросов
            for query_idx, char_query in enumerate(character_queries):
                logger.info(f"📝 Расширенный запрос {query_idx + 1}/4: '{char_query}'")
                try:
                    docs_with_scores = self.vectorstore.similarity_search_with_score(char_query, k=top_k * 2)
                    logger.info(f"   Найдено {len(docs_with_scores)} документов от vectorstore")

                    for doc_idx, (doc, score) in enumerate(docs_with_scores):
                        # Используем метаданные для фильтрации (более точно)
                        doc_character = doc.metadata.get('character', 'unknown').lower().strip()
                        target_character = character.lower().strip()
                        
                        # Также пробуем парсинг для совместимости
                        if doc_character == 'unknown':
                            parsed = self.parse_character_message(doc.page_content)
                            doc_character = parsed.get("character", "unknown").lower().strip()
                        
                        logger.info(f"   📄 Документ {doc_idx + 1}: character='{doc_character}', target='{target_character}', score={score:.4f}")
                        logger.info(f"      Метаданные: {doc.metadata}")
                        
                        # Фильтрация по персонажу
                        if doc_character == target_character:
                            character_docs_found += 1
                            similarity_score = 1.0 / (1.0 + score)

                            # Фильтрация по релевантности
                            if similarity_score > 0.3:
                                doc_info = {
                                    "content": doc.page_content,
                                    "character": doc_character,
                                    "type": doc.metadata.get('character_type', 'unknown'),
                                    "mood": doc.metadata.get('mood', 'neutral'),
                                    "context": doc.metadata.get('context', 'general'),
                                    "reply_to": doc.metadata.get('reply_to'),
                                    "thread_id": doc.metadata.get('thread_id'),
                                    "timestamp": doc.metadata.get('timestamp', ''),
                                    "message_index": doc.metadata.get('message_index', 0),
                                    "similarity_score": similarity_score,
                                    "distance_score": float(score),
                                    "metadata": doc.metadata,
                                    "raw_text": doc.page_content,
                                    "query_type": char_query,
                                    "extraction_method": doc.metadata.get('extraction_method', 'standard'),
                                }
                                all_docs.append(doc_info)
                                logger.info(f"   ✅ ДОБАВЛЕН расширенный документ от {doc_character} (score={similarity_score:.4f})")
                            else:
                                logger.info(f"   ⚠️ ПРОПУЩЕН документ от {doc_character} (низкий score={similarity_score:.4f})")

                except Exception as e:
                    logger.warning(f"❌ Query '{char_query}' failed: {e}")
                    continue

            logger.info(f"📊 Расширенная статистика поиска: {character_docs_found} документов от {character}")

            # Удаляем дубликаты и сортируем
            unique_docs = {}
            for doc in all_docs:
                # Используем комбинацию контента и метаданных для дедупликации
                key_content = doc["content"]
                key_metadata = f"{doc.get('message_index', 0)}_{doc.get('thread_id', '')}"
                key = hashlib.md5(f"{key_content}_{key_metadata}".encode()).hexdigest()
                
                if key not in unique_docs or doc["similarity_score"] > unique_docs[key]["similarity_score"]:
                    unique_docs[key] = doc

            # Сортируем по релевантности
            character_docs = list(unique_docs.values())
            character_docs.sort(key=lambda x: x["similarity_score"], reverse=True)

            logger.info(f"✅ Расширенный результат: {len(character_docs)} уникальных документов для персонажа {character}")
            
            # Логируем детали найденных документов
            for idx, doc in enumerate(character_docs[:5]):  # Только первые 5 для лога
                logger.info(f"   📄 {idx + 1}. {doc['character']} [thread: {doc.get('thread_id', 'N/A')}] (score={doc['similarity_score']:.4f}): {doc['content'][:80]}...")
            
            return character_docs[:top_k]

        except Exception as e:
            logger.error(f"❌ Error getting extended character documents: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return []


class ForumManager:

    def __init__(self):
        # ...existing initialization...
        self.forum_rag = ForumRAG("app/ai_manager/forum_knowledge_base", "forum_cache")
        self.character_persona = CharacterPersona()
        self.model = AIModels.gemma

    @timer
    def ask_as_character(
        self, prompt: str,
        character: str,
        mood: Optional[str] = None,
        translate: bool = True,
        extended_docs: bool = True,
            ) -> Union[str, dict, ChatResponse]:
        """Отвечает от имени определенного персонажа"""
        logger.info(f"🎭 Запрос от персонажа '{character}' с настроением '{mood}': {prompt[:100]}...")

        # Проверяем, существует ли персонаж
        if character not in self.character_persona.CHARACTERS:
            logger.warning(f"❌ Персонаж '{character}' не найден. Используем 'alaev' по умолчанию.")
            character = "alaev"

        # Получаем релевантные документы для персонажа
        logger.info(f"🔍 Получение релевантных документов для персонажа '{character}'...")
        if extended_docs:
            character_docs = self.forum_rag.get_character_relevant_docs_extended(prompt, character)
        else:
            # Используем старый метод, если extended_docs=False
            logger.info("Используем старый метод получения документов")
            character_docs = self.forum_rag.get_character_relevant_docs(prompt, character)
        
        logger.info(f"📚 Найдено {len(character_docs)} релевантных документов для персонажа '{character}'")

        # Формируем контекст из сообщений персонажа
        context = ""
        if character_docs:
            context = f"\nПримеры сообщений {character}:\n"
            for i, doc in enumerate(character_docs, 1):
                context += f"{i}. [{doc['mood']}] {doc['content'][:200]}...\n"
            context += "\n"
            logger.info(f"📝 Сформированный контекст({len(context)} символов): {context}")
        else:
            logger.warning(f"⚠️ Не найдено документов для персонажа '{character}' - ответ может быть не в характере")

        # Получаем контекст персонажа
        character_context = self.forum_rag.get_character_context(character, mood)
        logger.info(f"🎭 Контекст персонажа для {character}: {character_context[:300]}...")
        
        # Формируем промпт
        if not prompt.endswith("?"):
            prompt += "?"
        if translate:
            prompt = f"{prompt} (Ответь на русском языке.)"

        full_prompt = f"""{character_context}
                        {context}
                        Пользователь спрашивает: {prompt}
                        Ответь в характере персонажа {character}.
                        """

        logger.info(f"📋 Полный промпт для модели ({len(full_prompt)} символов): {full_prompt[:300]}...")

        try:
            logger.info(f"🤖 Отправка запроса к модели {self.model}...")
            response: ChatResponse = chat(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": full_prompt,
                    },
                ],
            )

            answer = response["message"]["content"]
            logger.info(f"✅ Ответ от персонажа '{character}' сгенерирован ({len(answer)} символов)")
            logger.info(f"💬 Ответ: {answer[:150]}...")
            return answer

        except Exception as e:
            logger.error(f"❌ Ошибка при генерации ответа персонажа: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return f"[{character}] Извините, не могу ответить на этот вопрос."

    def save_messages(self, character: str, response: str, question: Optional[str] = None, context: Optional[str] = None):
        """Сохраняет ответ персонажа в текстовый файл answers.txt"""
        try:
            if not question:
                question = "Без вопроса"

            # Формируем сообщение
            message = {
                "character": character,
                "content": response,
                "context": context or "Общий контекст",
                "timestamp": "",
                "reply_to": None,
                "question": question,
            }

            # Сохраняем в файл
            with open("answers.txt", "a", encoding="utf-8") as f:
                f.write(json.dumps(message, ensure_ascii=False) + "\n")

            logger.info(f"Message from {character} saved successfully")
        except Exception as e:
            logger.error(f"Error saving message: {e}")


# Пример использования
if __name__ == "__main__":
    ai_manager = ForumManager() 
    # Пример 1: Ответ от конкретного персонажа
    question = """
            Каждый раз встречаю женщин у которых есть квартира, машина , хорошо одеваются, но при этом ни у одной  нет денег заплатить за еду в кафе. П
            арадокс. В чем причина ? 
                """
    character = "Domen77"
    mood = "sarcastic"
    print(f"🎭 Ответ от {character}:")
    response = ai_manager.ask_as_character(question, character, mood=mood)     # type: ignore
    # Выводим ответ
    print(f"{character}: {response["result"]}...")  # type: ignore
    # ai_manager.save_messages(
    #     "Alaev", 
    #     response, 
    #     # context="Обсуждение водите÷лей в разных странах"
    #     question=question
    # )
    
    # print("\n👨‍💻 Ответ от Senior_Dev:")
    # senior_response = ai_manager.ask_as_character(
    #     "Что думаешь о современном Python?", 
    #     "Senior_Dev", 
    #     mood="professional"
    # )
    # print(f"Senior_Dev: {senior_response}")
    
    # # Пример 2: Симуляция форумной дискуссии
    # print("\n🗣️ Симуляция форумной дискуссии:")
    # discussion = ai_manager.simulate_forum_discussion(
    #     "Стоит ли изучать Python в 2024 году?",
    #     participants=["Alaev", "Senior_Dev", "Data_Scientist"],
    #     rounds=2
    # )
    
    # for msg in discussion:
    #     print(f"\n[Раунд {msg['round']}] {msg['character']}: {msg['message'][:200]}...")