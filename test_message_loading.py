#!/usr/bin/env python3
"""
Скрипт для тестирования загрузки примеров сообщений
"""
import asyncio
import logging

from app.database import get_db
from app.services.knowledge_service import KnowledgeService

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_message_loading():
    """Тестирует загрузку примеров сообщений"""
    service = KnowledgeService()
    
    # Получаем сессию БД
    db_gen = get_db()
    db = await anext(db_gen)
    
    try:
        # Проверяем текущее количество сообщений
        current_count = await service.get_message_examples_count(None, db)
        logger.info(f"Current message examples in DB: {current_count}")
        
        # Загружаем все примеры сообщений
        results = await service.load_all_message_examples(db)
        
        # Выводим результаты
        logger.info("Loading results:")
        for user_id, count in results.items():
            logger.info(f"  {user_id}: {count} messages")
        
        # Проверяем итоговое количество
        final_count = await service.get_message_examples_count(None, db)
        logger.info(f"Final message examples in DB: {final_count}")
        
        # Проверяем количество для конкретного пользователя
        if results:
            first_character_id = list(results.keys())[0]
            # Получаем user_id по character_id
            user_id = await service.get_user_by_character_id(first_character_id, db)
            if user_id:
                user_count = await service.get_message_examples_count(user_id, db)
                logger.info(f"Messages for {first_character_id} (user_id: {user_id}): {user_count}")
            else:
                logger.info(f"User not found for character: {first_character_id}")
        
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(test_message_loading())
