#!/usr/bin/env python3
"""
Тестируем новую структуру с foreign key связями
"""
import asyncio
import logging

from app.database import get_db
from app.services.knowledge_service import KnowledgeService

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_new_structure():
    """Тестирует новую структуру с foreign key связями"""
    service = KnowledgeService()
    
    # Получаем сессию БД
    db_gen = get_db()
    db = await anext(db_gen)
    
    try:
        # Находим пользователя по character_id
        character_id = "alice_researcher"
        user_id = await service.get_user_by_character_id(character_id, db)
        logger.info(f"User ID for character '{character_id}': {user_id}")
        
        if user_id:
            # Загружаем знания пользователя
            knowledge = await service.load_user_knowledge(user_id, db)
            if knowledge:
                logger.info(f"Loaded knowledge for user {user_id}: {knowledge.name}")
                logger.info(f"Character ID: {knowledge.character_id}")
                logger.info(f"Personality: {knowledge.personality[:100]}...")
            
            # Проверяем количество примеров сообщений
            messages_count = await service.get_message_examples_count(user_id, db)
            logger.info(f"Message examples for user {user_id}: {messages_count}")
        
        # Общее количество сообщений
        total_messages = await service.get_message_examples_count(None, db)
        logger.info(f"Total message examples: {total_messages}")
        
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(test_new_structure())
