#!/usr/bin/env python3
"""
Тестирование загрузки данных для пользователя alaev (user_id=1)
"""
import asyncio
import logging

from app.database import get_db
from app.services.knowledge_service import KnowledgeService

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_alaev_loading():
    """Тестирует загрузку данных для alaev"""
    service = KnowledgeService()

    # Получаем сессию БД
    db_gen = get_db()
    db = await anext(db_gen)

    try:
        print("=== Тестирование загрузки для alaev (user_id=1) ===")

        # 1. Загружаем знания из JSON
        print("\n1. Загружаем знания из JSON файла...")
        knowledge = await service._load_from_json_file("alaev")
        if knowledge:
            print(f"✅ Знания загружены: {knowledge.name}")
            print(f"   user_id: {knowledge.user_id}")
            print(f"   personality: {knowledge.personality[:50]}...")
        else:
            print("❌ Не удалось загрузить знания")
            return

        # 2. Сохраняем знания в БД с character_id
        print("\n2. Сохраняем знания в БД...")
        try:
            await service._save_to_database_with_character_id(knowledge, "alaev", db)
            await db.commit()
            print("✅ Знания сохранены в БД")
        except Exception as e:
            print(f"❌ Ошибка сохранения знаний: {e}")
            await db.rollback()

        # 3. Проверяем что знания сохранились
        print("\n3. Проверяем сохраненные знания...")
        saved_knowledge = await service.load_user_knowledge(1, db)
        if saved_knowledge:
            print(f"✅ Знания найдены в БД: {saved_knowledge.name}")
        else:
            print("❌ Знания не найдены в БД")

        # 4. Загружаем примеры сообщений
        print("\n4. Загружаем примеры сообщений...")
        message_count = await service.load_message_examples_from_json("alaev", db)
        print(f"✅ Загружено {message_count} примеров сообщений")

        # 5. Проверяем количество сообщений в БД
        print("\n5. Проверяем сообщения в БД...")
        total_messages = await service.get_message_examples_count(None, db)
        user_messages = await service.get_message_examples_count(1, db)
        print(f"✅ Всего сообщений в БД: {total_messages}")
        print(f"✅ Сообщений для user_id=1: {user_messages}")

    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(test_alaev_loading())
