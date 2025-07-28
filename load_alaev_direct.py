#!/usr/bin/env python3
"""
Прямая загрузка данных для alaev в БД
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime

from sqlalchemy.sql import text

from app.database import get_db

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def load_alaev_data():
    """Загружает данные для alaev напрямую в БД"""
    
    # Получаем сессию БД
    db_gen = get_db()
    db = await anext(db_gen)
    
    try:
        print("=== Прямая загрузка данных для alaev ===")
        
        # 1. Загружаем знания из JSON
        print("\n1. Читаем JSON файл...")
        with open('forum_knowledge_base/alaev.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ Загружен: {data['name']}")
        
        # 2. Проверяем существует ли запись в user_knowledge
        result = await db.execute(
            text("SELECT id FROM user_knowledge WHERE user_id = :user_id"),
            {"user_id": data["user_id"]}
        )
        existing = result.fetchone()
        
        if existing:
            print("   Обновляем существующую запись...")
            await db.execute(text("""
                UPDATE user_knowledge SET 
                    character_id = :character_id,
                    name = :name,
                    personality = :personality,
                    background = :background,
                    expertise = :expertise,
                    communication_style = :communication_style,
                    preferences = :preferences,
                    updated_at = NOW()
                WHERE user_id = :user_id
            """), {
                "user_id": data["user_id"],
                "character_id": "alaev",
                "name": data["name"],
                "personality": data["personality"],
                "background": data["background"],
                "expertise": json.dumps(data["expertise"]),
                "communication_style": data["communication_style"],
                "preferences": json.dumps(data["preferences"])
            })
        else:
            print("   Создаем новую запись...")
            await db.execute(text("""
                INSERT INTO user_knowledge (
                    id, user_id, character_id, name, personality, background, 
                    expertise, communication_style, preferences
                ) VALUES (
                    :id, :user_id, :character_id, :name, :personality, :background,
                    :expertise, :communication_style, :preferences
                )
            """), {
                "id": str(uuid.uuid4()),
                "user_id": data["user_id"],
                "character_id": "alaev", 
                "name": data["name"],
                "personality": data["personality"],
                "background": data["background"],
                "expertise": json.dumps(data["expertise"]),
                "communication_style": data["communication_style"],
                "preferences": json.dumps(data["preferences"])
            })
        
        await db.commit()
        print("✅ Знания сохранены в БД")
        
        # 3. Загружаем примеры сообщений
        print("\n2. Загружаем примеры сообщений...")
        with open('forum_knowledge_base/messages_examples/alaev_messages.json', 'r', encoding='utf-8') as f:
            messages_data = json.load(f)
        
        messages = messages_data if isinstance(messages_data, list) else messages_data.get('messages', [])
        print(f"   Найдено {len(messages)} сообщений")
        
        # Очищаем старые сообщения для этого пользователя
        await db.execute(
            text("DELETE FROM user_message_examples WHERE user_id = :user_id"),
            {"user_id": data["user_id"]}
        )
        
        # Загружаем новые сообщения
        loaded_count = 0
        for msg in messages:
            await db.execute(text("""
                INSERT INTO user_message_examples (
                    user_id, character_id, context, content, thread_id, 
                    reply_to, timestamp, extra_metadata, source_file
                ) VALUES (
                    :user_id, :character_id, :context, :content, :thread_id,
                    :reply_to, :timestamp, :extra_metadata, :source_file
                )
            """), {
                "user_id": data["user_id"],
                "character_id": "alaev",
                "context": msg.get('context', ''),
                "content": msg.get('content', ''),
                "thread_id": msg.get('thread_id', ''),
                "reply_to": msg.get('reply_to'),
                "timestamp": datetime.now(),
                "extra_metadata": json.dumps({
                    'character_type': msg.get('character_type'),
                    'mood': msg.get('mood'),
                    'based_on': msg.get('based_on'),
                    'original_timestamp': msg.get('timestamp')
                }),
                "source_file": "forum_knowledge_base/messages_examples/alaev_messages.json"
            })
            loaded_count += 1
        
        await db.commit()
        print(f"✅ Загружено {loaded_count} примеров сообщений")
        
        # 4. Проверяем результат
        print("\n3. Проверяем результат...")
        
        # Проверяем знания
        result = await db.execute(
            text("SELECT name, character_id FROM user_knowledge WHERE user_id = :user_id"),
            {"user_id": data["user_id"]}
        )
        knowledge_row = result.fetchone()
        if knowledge_row:
            print(f"✅ Знания: {knowledge_row[0]} (character_id: {knowledge_row[1]})")
        
        # Проверяем сообщения
        result = await db.execute(
            text("SELECT COUNT(*) FROM user_message_examples WHERE user_id = :user_id"),
            {"user_id": data["user_id"]}
        )
        message_count = result.scalar()
        print(f"✅ Примеров сообщений: {message_count}")
        
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(load_alaev_data())
