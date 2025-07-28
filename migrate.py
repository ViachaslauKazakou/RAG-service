#!/usr/bin/env python3
"""
Скрипт для безопасного применения миграций RAG Manager
"""
import asyncio
import logging
import os
import subprocess
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_database_connection():
    """Проверяем подключение к базе данных"""
    try:
        from sqlalchemy import text

        from app.database import engine
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            logger.info("✅ Подключение к базе данных успешно")
            return True
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к БД: {e}")
        return False

def run_migrations():
    """Применяем миграции"""
    try:
        # Проверяем текущее состояние миграций
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "current"],
            cwd=os.path.dirname(__file__),
            capture_output=True,
            text=True
        )
        
        logger.info(f"Текущее состояние миграций: {result.stdout.strip()}")
        
        # Применяем миграции
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=os.path.dirname(__file__),
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info("✅ Миграции применены успешно")
            if result.stdout.strip():
                logger.info(result.stdout)
            return True
        else:
            logger.error(f"❌ Ошибка применения миграций: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка выполнения миграций: {e}")
        return False

async def main():
    """Главная функция"""
    logger.info("🚀 Запуск миграций RAG Manager...")
    
    # Проверяем подключение к БД
    if not await check_database_connection():
        sys.exit(1)
    
    # Применяем миграции
    if not run_migrations():
        sys.exit(1)
    
    logger.info("🎉 Миграции RAG Manager завершены успешно!")

if __name__ == "__main__":
    asyncio.run(main())
