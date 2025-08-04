"""
Конфигурация приложения
"""
import os
import logging

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


def get_database_url() -> str:
    """
    Автоматически определяет правильный URL базы данных для Docker
    """
    # Сначала проверяем переменную окружения
    if db_url := os.getenv("DATABASE_URL"):
        return db_url
    
    # Определяем, работаем ли мы в Docker контейнере
    is_docker = os.path.exists('/.dockerenv') or os.getenv('ENV') == 'development'
    
    if is_docker:
        # В Docker контейнере используем host.docker.internal
        return "postgresql+asyncpg://docker:docker@host.docker.internal:5433/postgres"
    else:
        # Локально используем localhost
        return "postgresql+asyncpg://docker:docker@localhost:5433/postgres"


class Settings(BaseSettings):
    """Настройки приложения"""

    # Database
    database_url: str = get_database_url()
    skip_db_init: bool = os.getenv("SKIP_DB_INIT", "false").lower() == "true"

    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # AI Manager
    ai_manager_url: str = os.getenv("AI_MANAGER_URL", "http://localhost:8080")

    # Paths
    knowledge_base_path: str = os.getenv("KNOWLEDGE_BASE_PATH", "./forum_knowledge_base")

    # API Settings
    api_title: str = "RAG Manager API"
    api_version: str = "1.0.0"
    api_description: str = "RAG Manager Service for AI Forum"

    # Vector DB Settings
    embedding_dimension: int = 1536  # OpenAI ada-002

    # Performance
    max_context_documents: int = 20
    default_similarity_threshold: float = 0.7
    cache_ttl: int = 300  # 5 minutes

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    class Config:
        env_file = ".env"
        extra = "ignore"  # Игнорируем дополнительные поля из переменных окружения


# Глобальный экземпляр настроек
get_settings = Settings()
