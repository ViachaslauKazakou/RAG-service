"""
Сервис для работы с знаниями пользователей
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from app.config import get_settings
from app.imported_models import Message, Topic, User
from app.models import UserKnowledgeRecord, UserMessageExample
from app.schemas import UserKnowledge

logger = logging.getLogger(__name__)


class KnowledgeService:
    """Сервис для работы с знаниями пользователей"""
    
    def __init__(self):
        self.knowledge_base_path = Path(get_settings.knowledge_base_path)
        self._cache = {}  # Простой кэш в памяти
    
    async def load_user_knowledge(self, user_id: int, db: AsyncSession) -> Optional[UserKnowledge]:
        """
        Загружает знания пользователя из БД
        
        Args:
            user_id: ID пользователя (integer)
            db: Сессия базы данных
            
        Returns:
            Знания пользователя или None
        """
        # Проверяем кэш по user_id
        if user_id in self._cache:
            return self._cache[user_id]
        
        # Загружаем из БД
        knowledge = await self._load_from_database(user_id, db)
        if knowledge:
            self._cache[user_id] = knowledge
            return knowledge
        
        logger.warning(f"Knowledge not found for user {user_id}")
        return None
    
    async def _load_from_database(self, user_id: int, db: AsyncSession) -> Optional[UserKnowledge]:
        """Загружает знания из базы данных"""
        try:
            result = await db.execute(
                select(UserKnowledgeRecord).where(UserKnowledgeRecord.user_id == user_id)
            )
            record = result.scalar_one_or_none()
            
            if record:
                return UserKnowledge(
                    user_id=record.user_id,
                    character_id=record.character_id,
                    name=record.name,
                    personality=record.personality,
                    background=record.background,
                    expertise=record.expertise,
                    communication_style=record.communication_style,
                    preferences=record.preferences,
                    created_at=record.created_at,
                    updated_at=record.updated_at
                )
        except Exception as e:
            logger.error(f"Error loading from database: {e}")
        
        return None
    
    async def _load_from_json_file(self, user_id: str) -> Optional[UserKnowledge]:
        """Загружает знания из JSON файла"""
        file_path = self.knowledge_base_path / f"{user_id}.json"
        
        if not file_path.exists():
            logger.info(f"JSON file not found: {file_path}")
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return UserKnowledge(**data)
        except Exception as e:
            logger.error(f"Error loading JSON file {file_path}: {e}")
            return None
    
    async def _save_to_database_with_character_id(self, knowledge: UserKnowledge, user_id: int, db: AsyncSession):
        """Сохраняет знания в базу данных с character_id"""
        try:
            # Проверяем, существует ли запись - используем правильный SQL запрос
            result = await db.execute(
                text("SELECT * FROM user_knowledge WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            existing_record = result.fetchone()
            
            if existing_record:
                # Обновляем существующую запись
                await db.execute(
                    text("""
                        UPDATE user_knowledge 
                        SET name = :name,
                            personality = :personality,
                            background = :background,
                            expertise = :expertise,
                            communication_style = :communication_style,
                            preferences = :preferences,
                            character_id = :character_id,
                            updated_at = NOW()
                        WHERE user_id = :user_id
                    """),
                    {
                        "user_id": user_id,
                        "character_id": knowledge.character_id,
                        "name": knowledge.name,
                        "personality": knowledge.personality,
                        "background": knowledge.background,
                        "expertise": json.dumps(knowledge.expertise) if knowledge.expertise else None,
                        "communication_style": knowledge.communication_style,
                        "preferences": json.dumps(knowledge.preferences) if knowledge.preferences else None
                    }
                )
                logger.info(f"Updated existing knowledge record for user_id: {user_id}")
            else:
                # Создаем новую запись
                await db.execute(
                    text("""
                        INSERT INTO user_knowledge 
                        (id, user_id, character_id, name, personality, background, 
                         expertise, communication_style, preferences, created_at, updated_at)
                        VALUES 
                        (gen_random_uuid(), :user_id, :character_id, :name, :personality, :background,
                         :expertise, :communication_style, :preferences, NOW(), NOW())
                    """),
                    {
                        "user_id": user_id,
                        "character_id": knowledge.character_id,
                        "name": knowledge.name,
                        "personality": knowledge.personality,
                        "background": knowledge.background,
                        "expertise": json.dumps(knowledge.expertise) if knowledge.expertise else None,
                        "communication_style": knowledge.communication_style,
                        "preferences": json.dumps(knowledge.preferences) if knowledge.preferences else None
                    }
                )
                logger.info(f"Created new knowledge record for user_id: {user_id}")
            
        except Exception as e:
            logger.error(f"Error saving to database: {e}")
            raise

    async def get_user_by_character_id(self, character_id: str, db: AsyncSession) -> Optional[int]:
        """
        Получает user_id по character_id
        
        Args:
            character_id: Строковый идентификатор персонажа
            db: Сессия базы данных
            
        Returns:
            user_id или None
        """
        logger.info(f"Finding user by character_id: {character_id}")
        if not character_id:
            logger.warning("Character ID is empty, cannot find user")
            return None
            
        try:
            result = await db.execute(
                text("SELECT user_id FROM user_knowledge WHERE character_id = :character_id"),
                {"character_id": character_id}
            )
            row = result.fetchone()
            if row:
                user_id = row[0]
                logger.info(f"Found user_id: {user_id} for character_id: {character_id}")
                return user_id
            else:
                logger.warning(f"No user found for character_id: {character_id}")
                return None
        except Exception as e:
            logger.error(f"Error finding user by character_id {character_id}: {e}")
            return None


    async def load_and_save_knowledge_from_json(self, user_id: str, character_id: str, db: AsyncSession) -> bool:
        """
        Загружает знания из JSON файла и сохраняет в БД
        
        Args:
            character_id: Строковый идентификатор персонажа
            db: Сессия базы данных
            
        Returns:
            True если успешно загружено
        """
        try:
            # Загружаем данные из JSON
            knowledge = await self._load_from_json_file(character_id)
            if not knowledge:
                logger.error(f"Failed to load knowledge from JSON for {character_id}")
                return False
            
            # Проверяем, есть ли уже пользователь в таблице users по JSON user_id
            json_user_id = knowledge.user_id
            
            result = await db.execute(
                text("SELECT id FROM users WHERE id = :user_id"),
                {"user_id": json_user_id}
            )
            existing_user = result.fetchone()
            
            if existing_user:
                user_id = existing_user[0]
                logger.info(f"Found existing user with ID: {user_id}")
            else:
                # Создаем нового пользователя
                result = await db.execute(
                    text("""
                        INSERT INTO users (username, email, firstname, password, status, user_type) 
                        VALUES (:username, :email, :firstname, :password, :status, :user_type)
                        RETURNING id
                    """),
                    {
                        "username": character_id,
                        "email": f"{character_id}@forum.local", 
                        "firstname": knowledge.name,
                        "password": "dummy_password",  # Заглушка
                        "status": "active",
                        "user_type": "user"
                    }
                )
                user_id = result.scalar_one()
                logger.info(f"Created new user: {character_id} with ID: {user_id}")
            
            # Устанавливаем правильные значения для сохранения
            knowledge.user_id = user_id
            knowledge.character_id = character_id
            
            # Сохраняем знания с правильным character_id
            await self._save_to_database_with_character_id(knowledge, user_id, db)
            await db.commit()
            
            logger.info(f"Successfully uploaded knowledge for {character_id} (user_id: {user_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error loading and saving knowledge for {character_id}: {e}")
            await db.rollback()
            return False
    
    async def _save_to_database(self, knowledge: UserKnowledge, db: AsyncSession):
        """Сохраняет знания в базу данных"""
        try:
            # Проверяем, существует ли запись
            result = await db.execute(
                select(UserKnowledgeRecord).where(
                    UserKnowledgeRecord.user_id == knowledge.user_id
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                # Обновляем существующую запись
                existing.name = knowledge.name
                existing.personality = knowledge.personality
                existing.background = knowledge.background
                existing.expertise = knowledge.expertise
                existing.communication_style = knowledge.communication_style
                existing.preferences = knowledge.preferences
            else:
                # Создаем новую запись
                record = UserKnowledgeRecord(
                    user_id=knowledge.user_id,
                    name=knowledge.name,
                    personality=knowledge.personality,
                    background=knowledge.background,
                    expertise=knowledge.expertise,
                    communication_style=knowledge.communication_style,
                    preferences=knowledge.preferences,
                    file_path=str(self.knowledge_base_path / f"{knowledge.user_id}.json")
                )
                db.add(record)
            
            await db.commit()
            logger.info(f"Saved knowledge for user {knowledge.user_id} to database")
            
        except Exception as e:
            logger.error(f"Error saving to database: {e}")
            await db.rollback()
    
    async def get_all_user_ids(self) -> List[str]:
        """Возвращает список всех доступных пользователей"""
        user_ids = []
        
        # Сканируем JSON файлы
        if self.knowledge_base_path.exists():
            for file_path in self.knowledge_base_path.glob("*.json"):
                user_id = file_path.stem
                user_ids.append(user_id)
        
        return user_ids
    
    def clear_cache(self):
        """Очищает кэш"""
        self._cache.clear()
    
    async def warm_cache(self):
        """
        Предварительно загружает все знания пользователей в кэш
        Используется при запуске приложения для улучшения производительности
        """
        logger.info("Starting cache warming...")
        
        try:
            # Получаем список всех пользователей
            user_ids = await self.get_all_user_ids()
            
            # Загружаем знания каждого пользователя в кэш
            loaded_count = 0
            skipped_count = 0
            
            for user_id in user_ids:
                try:
                    # Загружаем из JSON файла напрямую для кэша
                    knowledge = await self._load_from_json_file(user_id)
                    if knowledge:
                        self._cache[user_id] = knowledge
                        loaded_count += 1
                        logger.debug(f"Loaded knowledge for user: {user_id}")
                    else:
                        skipped_count += 1
                        logger.debug(f"Skipped invalid knowledge file for user: {user_id}")
                        
                except Exception as e:
                    skipped_count += 1
                    logger.debug(f"Skipped knowledge file for user {user_id} (not a valid profile): {e}")
                    continue
            
            logger.info(f"Cache warming completed. Loaded: {loaded_count}, Skipped: {skipped_count} (Total files: {len(user_ids)})")
            
        except Exception as e:
            logger.error(f"Error during cache warming: {e}")
            # Не поднимаем исключение, чтобы приложение могло запуститься
            logger.warning("Cache warming failed, but application will continue to work")
    
    async def create_character_prompt(
        self, 
        user_knowledge: UserKnowledge, 
        question: str,
        context_docs: List[Dict[str, Any]],
        reply_to: Optional[str] = None
    ) -> str:
        """
        Создает промпт для генерации ответа от имени пользователя
        
        Args:
            user_knowledge: Знания пользователя
            question: Вопрос
            context_docs: Контекстные документы
            reply_to: Кому адресован ответ
            
        Returns:
            Сгенерированный промпт
        """
        # Формируем контекст из найденных документов
        context_text = "\n\n".join([
            f"Документ {i+1} (similarity: {doc.get('similarity_score', 0):.3f}):\n{doc.get('content', '')}"
            for i, doc in enumerate(context_docs[:5])  # Берем топ-5
        ])
        
        # Формируем информацию о целевом пользователе
        reply_context = ""
        if reply_to:
            reply_context = f"\n\nТы отвечаешь пользователю: {reply_to}"
        
        # Создаем промпт
        prompt = f"""Ты - {user_knowledge.name} ({user_knowledge.user_id}).

ТВОЯ ЛИЧНОСТЬ И ХАРАКТЕР:
{user_knowledge.personality}

ТВОЙ БЭКГРАУНД:
{user_knowledge.background}

ТВОЯ ЭКСПЕРТИЗА:
{', '.join(user_knowledge.expertise)}

ТВОЙ СТИЛЬ ОБЩЕНИЯ:
{user_knowledge.communication_style}

ТВОИ ПРЕДПОЧТЕНИЯ:
- Длина ответа: {user_knowledge.preferences.get('response_length', 'medium')}
- Включать примеры кода: {user_knowledge.preferences.get('include_code_examples', False)}
- Ссылаться на источники: {user_knowledge.preferences.get('cite_sources', False)}
- Технический уровень: {user_knowledge.preferences.get('technical_level', 'intermediate')}

РЕЛЕВАНТНЫЙ КОНТЕКСТ ИЗ ПРЕДЫДУЩИХ ОБСУЖДЕНИЙ:
{context_text if context_text.strip() else "Контекст не найден - отвечай на основе своих знаний."}

ВОПРОС:
{question}{reply_context}

ИНСТРУКЦИЯ:
Ответь на вопрос как {user_knowledge.name}, используя свою личность, стиль общения и экспертизу. 
Опирайся на предоставленный контекст, но если он недостаточен, используй свои знания в области твоей экспертизы.
Сохраняй характерный для тебя стиль и манеру изложения.
"""
        
        return prompt.strip()
    
    async def get_user_by_character_id(self, user_id: str, db: AsyncSession) -> Optional[int]:
        """
        Получает user_id по character_id
        
        Args:
            character_id: Строковый идентификатор персонажа
            db: Сессия базы данных
            
        Returns:
            user_id или None
        """
        logger.info(f"Finding user by character_id: {user_id}")
        if not user_id:
            logger.warning("Character ID is empty, cannot find user")
            return None
        try:
            result = await db.execute(
                select(UserKnowledgeRecord.user_id).where(
                    UserKnowledgeRecord.user_id == user_id
                )
            )
            user_id = result.scalar_one_or_none()
            return user_id
        except Exception as e:
            logger.error(f"Error finding user by character_id {character_id}: {e}")
            return None
    
    async def load_message_examples_from_json(self, character_id: str, db: AsyncSession) -> int:
        """
        Загружает примеры сообщений пользователя из JSON файла в базу данных
        
        Args:
            character_id: Строковый идентификатор пользователя (например, 'alice_researcher')
            db: Сессия базы данных
            
        Returns:
            Количество загруженных сообщений
        """
        file_path = self.knowledge_base_path / "messages_examples" / f"{character_id}_messages.json"
        
        if not file_path.exists():
            logger.info(f"Message examples file not found: {file_path}")
            return 0
        
        # Получаем integer user_id по character_id
        user_id = await self.get_user_by_character_id(character_id, db)
        if not user_id:
            logger.warning(f"User not found for character_id: {character_id}")
            return 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Обрабатываем разные форматы JSON
            if isinstance(data, list):
                # Если файл содержит массив напрямую
                messages = data
            elif isinstance(data, dict) and 'messages' in data:
                # Если файл содержит объект с полем messages
                messages = data['messages']
            else:
                logger.warning(f"Unknown JSON format in {file_path}")
                return 0
            
            loaded_count = 0
            
            for msg in messages:
                # Проверяем, не существует ли уже такое сообщение
                # Используем комбинацию user_id и content для уникальности (убираем timestamp из-за проблем с типами)
                existing_result = await db.execute(
                    select(UserMessageExample).where(
                        UserMessageExample.user_id == user_id,
                        UserMessageExample.content == msg.get('content', '')
                    )
                )
                
                if existing_result.scalar_one_or_none():
                    logger.debug(f"Message already exists for {user_id}, skipping")
                    continue
                
                # Создаем новую запись
                message_example = UserMessageExample(
                    user_id=user_id,
                    character_id=character_id,  # Сохраняем character_id
                    context=msg.get('context', ''),
                    content=msg.get('content', ''),
                    thread_id=msg.get('thread_id', ''),
                    reply_to=msg.get('reply_to'),
                    timestamp=datetime.now(),  # Используем текущее время
                    extra_metadata={
                        'character_type': msg.get('character_type'),
                        'mood': msg.get('mood'),
                        'based_on': msg.get('based_on'),
                        'original_timestamp': msg.get('timestamp')  # Сохраняем оригинальный timestamp в метаданных
                    },
                    source_file=str(file_path)
                )
                
                db.add(message_example)
                loaded_count += 1
            
            await db.commit()
            logger.info(f"Loaded {loaded_count} message examples for character {character_id} (user_id: {user_id})")
            return loaded_count
            
        except Exception as e:
            logger.error(f"Error loading message examples from {file_path}: {e}")
            await db.rollback()
            return 0
    
    async def load_all_message_examples(self, db: AsyncSession) -> Dict[str, int]:
        """
        Загружает примеры сообщений для всех пользователей
        
        Args:
            db: Сессия базы данных
            
        Returns:
            Словарь {character_id: количество_загруженных_сообщений}
        """
        results = {}
        messages_dir = self.knowledge_base_path / "messages_examples"
        
        if not messages_dir.exists():
            logger.warning(f"Messages examples directory not found: {messages_dir}")
            return results
        
        # Сканируем файлы с примерами сообщений
        for file_path in messages_dir.glob("*_messages.json"):
            character_id = file_path.stem.replace('_messages', '')
            try:
                count = await self.load_message_examples_from_json(character_id, db)
                results[character_id] = count
            except Exception as e:
                logger.error(f"Failed to load messages for {character_id}: {e}")
                results[character_id] = 0
        
        total_loaded = sum(results.values())
        logger.info(f"Message loading completed. Total loaded: {total_loaded} messages for {len(results)} users")
        
        return results
    
    async def get_message_examples_count(self, user_id: Optional[int], db: AsyncSession) -> int:
        """
        Возвращает количество примеров сообщений для пользователя или всех пользователей
        
        Args:
            user_id: ID пользователя (если None, то для всех)
            db: Сессия базы данных
            
        Returns:
            Количество сообщений
        """
        try:
            query = select(UserMessageExample)
            if user_id:
                query = query.where(UserMessageExample.user_id == user_id)
            
            result = await db.execute(query)
            messages = result.scalars().all()
            return len(messages)
            
        except Exception as e:
            logger.error(f"Error counting message examples: {e}")
            return 0
    
    async def get_all_available_characters(self) -> List[str]:
        """Возвращает список всех доступных character_id из JSON файлов"""
        character_ids = []
        
        if self.knowledge_base_path.exists():
            for file_path in self.knowledge_base_path.glob("*.json"):
                character_id = file_path.stem
                character_ids.append(character_id)
        
        return sorted(character_ids)
    
    async def get_loaded_users_info(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """Возвращает информацию о загруженных пользователях"""
        try:
            result = await db.execute(
                text("""
                    SELECT uk.user_id, uk.character_id, uk.name, 
                           COUNT(ume.id) as message_count,
                           uk.created_at, uk.updated_at
                    FROM user_knowledge uk
                    LEFT JOIN user_message_examples ume ON uk.user_id = ume.user_id
                    GROUP BY uk.user_id, uk.character_id, uk.name, uk.created_at, uk.updated_at
                    ORDER BY uk.created_at DESC
                """)
            )
            
            users = []
            for row in result:
                users.append({
                    "user_id": row[0],
                    "character_id": row[1],
                    "name": row[2],
                    "message_count": row[3],
                    "created_at": row[4].isoformat() if row[4] else None,
                    "updated_at": row[5].isoformat() if row[5] else None
                })
            
            return users
            
        except Exception as e:
            logger.error(f"Error getting users info: {e}")
            return []
    
    async def load_character_data_complete(self, character_id: str, db: AsyncSession) -> Dict[str, Any]:
        """
        Полная загрузка данных персонажа (знания + сообщения)
        
        Args:
            character_id: Строковый идентификатор персонажа
            db: Сессия базы данных
            
        Returns:
            Словарь с результатами загрузки
        """
        result = {
            "success": False,
            "user_id": None,
            "character_id": character_id,
            "knowledge_loaded": False,
            "messages_loaded": 0,
            "created_user": False,
            "message": "",
            "errors": []
        }
        
        try:
            # 1. Загружаем знания
            logger.info(f"Loading knowledge for character: {character_id}")
            knowledge_success = await self.load_and_save_knowledge_from_json(character_id, db)
            
            if knowledge_success:
                result["knowledge_loaded"] = True
                
                # Получаем user_id
                user_id = await self.get_user_by_character_id(character_id, db)
                if user_id:
                    result["user_id"] = user_id
                    
                    # 2. Загружаем примеры сообщений
                    logger.info(f"Loading messages for character: {character_id}")
                    message_count = await self.load_message_examples_from_json(character_id, db)
                    result["messages_loaded"] = message_count
                    
                    result["success"] = True
                    result["message"] = f"Successfully loaded knowledge and {message_count} messages for {character_id}"
                else:
                    result["errors"].append("Failed to get user_id after knowledge loading")
                    result["message"] = "Knowledge loaded but failed to get user_id"
            else:
                result["errors"].append("Failed to load knowledge")
                result["message"] = f"Failed to load knowledge for {character_id}"
                
        except Exception as e:
            error_msg = f"Error loading data for {character_id}: {e}"
            logger.error(error_msg)
            result["errors"].append(error_msg)
            result["message"] = error_msg
            
        return result
