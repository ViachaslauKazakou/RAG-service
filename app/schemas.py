"""
Pydantic модели для RAG Manager
"""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum as PyEnum

from pydantic import BaseModel, Field


class RAGRequest(BaseModel):
    """Запрос для обработки RAG"""

    topic: str = Field(..., description="Топик обсуждения")
    user_id: int = Field(..., description="ID пользователя от имени которого ответ")
    question: str = Field(..., description="Вопрос для обработки")
    reply_to: Optional[str] = Field(None, description="ID пользователя, кому ответ")
    context_limit: Optional[int] = Field(10, description="Лимит контекстных документов")
    similarity_threshold: Optional[float] = Field(0.5, description="Порог схожести для поиска")


class ContextItem(BaseModel):
    """
    Элемент контекста
    """

    content: str = Field(..., description="Содержимое контекста")
    source: Optional[str] = Field(None, description="Источник контекста")
    similarity_score: float = Field(..., description="Оценка схожести")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Дополнительные метаданные")


class RAGResponse(BaseModel):
    """Ответ от RAG системы"""

    generated_prompt: str = Field(..., description="Сгенерированный промпт")
    user_id: int = Field(..., description="ID пользователя от имени которого ответ")
    topic: str = Field(..., description="Топик обсуждения")
    context_documents: List[ContextItem] = Field(..., description="Контекстные документы")
    user_knowledge: Dict[str, Any] = Field(..., description="Знания пользователя")
    confidence_score: float = Field(..., description="Оценка уверенности в ответе")
    processing_time: float = Field(..., description="Время обработки запроса в секундах")


class UserKnowledge(BaseModel):
    """Знания пользователя"""

    user_id: int  # Теперь integer - ID реального пользователя
    character_id: Optional[str] = None  # Строковый идентификатор персонажа
    name: str
    personality: str
    background: str
    expertise: List[str]
    communication_style: str
    preferences: Dict[str, Any]
    created_at: datetime


class LoadKnowledgeRequest(BaseModel):
    """Запрос на загрузку знаний пользователя"""

    user_id: int = Field(..., description="ID пользователя")
    user_kb_profile: str = Field(..., description="Профиль пользователя с его знаниями и предпочтениями")


class LoadKnowledgeResponse(BaseModel):
    """Ответ на загрузку знаний"""

    success: bool = Field(..., description="Успешно ли выполнена загрузка")
    user_id: Optional[int] = Field(None, description="ID созданного/найденного пользователя")
    character_id: str = Field(..., description="Строковый идентификатор персонажа")
    message: str = Field(..., description="Сообщение о результате")
    created_user: bool = Field(False, description="Был ли создан новый пользователь")


class LoadMessagesRequest(BaseModel):
    """Запрос на загрузку примеров сообщений в БД"""

    character_id: str = Field(..., description="Строковый идентификатор персонажа")
    user_id: int = Field(..., description="Числовой идентификатор пользователя в базе данных")


class LoadMessagesResponse(BaseModel):
    """Ответ на загрузку примеров сообщений"""

    success: bool = Field(..., description="Успешно ли выполнена загрузка")
    character_id: str = Field(..., description="Строковый идентификатор персонажа")
    loaded_count: int = Field(..., description="Количество загруженных сообщений")
    message: str = Field(..., description="Сообщение о результате")


class LoadAllDataRequest(BaseModel):
    """Запрос на загрузку всех данных для персонажа"""

    character_id: str = Field(..., description="Строковый идентификатор персонажа")


class LoadAllDataResponse(BaseModel):
    """Ответ на загрузку всех данных"""

    success: bool = Field(..., description="Успешно ли выполнена загрузка")
    user_id: Optional[int] = Field(None, description="ID пользователя")
    character_id: str = Field(..., description="Строковый идентификатор персонажа")
    knowledge_loaded: bool = Field(..., description="Загружены ли знания")
    messages_loaded: int = Field(..., description="Количество загруженных сообщений")
    created_user: bool = Field(False, description="Был ли создан новый пользователь")
    message: str = Field(..., description="Сообщение о результате")


class UserListResponse(BaseModel):
    """Список доступных пользователей"""

    users: List[Dict[str, Any]] = Field(..., description="Список пользователей")
    total_count: int = Field(..., description="Общее количество пользователей")


class ContextDocument(BaseModel):
    """Контекстный документ из векторной БД"""

    id: int
    content: str
    similarity_score: float
    metadata: Dict[str, Any]
    topic_id: Optional[int] = None
    message_id: Optional[int] = None


class UserMessageExampleSSchema(BaseModel):
    """Пример сообщения пользователя"""

    # id: Optional[int] = None
    user_id: int  # Теперь integer - ID реального пользователя
    character_id: Optional[str] = None  # Строковый идентификатор персонажа
    topic_id: Optional[str] = None
    parent_message_id: Optional[int] = None
    context: Optional[str] = None
    content: str
    reply_to: Optional[str] = None
    # timestamp: datetime
    source_file: Optional[str] = None
    extra_metadata: Optional[Dict[str, Any]] = None


class MessageContextRequest(BaseModel):
    """Запрос на создание контекста для ответа"""

    user_id: str = Field(..., description="ID пользователя который отвечает")
    topic_id: int = Field(..., description="ID топика")
    parent_message_id: Optional[int] = Field(None, description="ID сообщения на которое отвечаем")
    question: str = Field(..., description="Вопрос/контекст для ответа")
    similarity_threshold: Optional[float] = Field(0.7, description="Порог похожести для поиска примеров")
    max_examples: Optional[int] = Field(5, description="Максимальное количество примеров")


class MessageContextResponse(BaseModel):
    """Ответ с контекстом для генерации сообщения"""

    user_knowledge: UserKnowledge = Field(..., description="Профиль пользователя")
    similar_examples: List[UserMessageExampleSSchema] = Field(..., description="Похожие примеры сообщений")
    context_prompt: str = Field(..., description="Сгенерированный промпт")
    processing_time: float = Field(..., description="Время обработки")


class LoadExamplesRequest(BaseModel):
    """Запрос на загрузку примеров из JSON файлов"""

    user_id: str = Field(..., description="ID пользователя")
    force_reload: bool = Field(False, description="Принудительная перезагрузка")
    timestamp: datetime
    extra_metadata: Optional[Dict[str, Any]] = None
    source_file: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserMessageExampleCreate(BaseModel):
    """Схема для создания примера сообщения"""

    user_knowledge_id: uuid.UUID
    topic_id: Optional[int] = None
    context: Optional[str] = None
    content: str = Field(..., description="Содержимое сообщения")
    reply_to: Optional[str] = None
    timestamp: datetime
    extra_metadata: Optional[Dict[str, Any]] = None
    source_file: Optional[str] = None


class UserMessageExampleUpdate(BaseModel):
    """Схема для обновления примера сообщения"""

    context: Optional[str] = None
    content: Optional[str] = None
    reply_to: Optional[str] = None
    extra_metadata: Optional[Dict[str, Any]] = None


class SimilaritySearchRequest(BaseModel):
    """Запрос поиска похожих сообщений"""

    query: str = Field(..., description="Текст для поиска")
    user_knowledge_id: Optional[uuid.UUID] = Field(None, description="ID пользователя для фильтрации")
    topic_id: Optional[int] = Field(None, description="ID топика для фильтрации")
    limit: int = Field(5, description="Максимальное количество результатов")
    similarity_threshold: float = Field(0.7, description="Минимальный порог схожести")


class SimilaritySearchResponse(BaseModel):
    """Результат поиска похожих сообщений"""

    examples: List[UserMessageExampleSSchema]
    query_embedding_time: float
    search_time: float
    total_results: int


class HealthStatus(BaseModel):
    """Статус здоровья сервиса"""

    status: str
    timestamp: datetime
    database_status: str
    vector_db_status: str
    knowledge_base_status: str
    uptime: float


class UserMessageExample(BaseModel):
    """Пример сообщения пользователя"""

    id: Optional[int] = None
    user_id: str
    character: str
    character_type: Optional[str] = None
    mood: Optional[str] = None
    context: Optional[str] = None
    content: str
    thread_id: Optional[str] = None
    reply_to: Optional[str] = None
    timestamp: datetime
    extra_metadata: Optional[Dict[str, Any]] = None
    source_file: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MessageSearchRequest(BaseModel):
    """Запрос поиска подходящих сообщений"""

    user_id: str
    query: str
    context: Optional[str] = None
    mood: Optional[str] = None
    limit: int = Field(default=10, le=50)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class MessageSearchResponse(BaseModel):
    """Ответ поиска сообщений"""

    user_id: str
    query: str
    examples: List[UserMessageExample]
    total_found: int
    processing_time: float


####################


class Status(str, PyEnum):
    pending = "pending"
    active = "active"
    disabled = "disabled"
    blocked = "Забанен"
    deleted = "deleted"


# Enum for user roles
class UserRole(str, PyEnum):
    admin = "admin"
    user = "user"
    ai_bot = "ai_bot"  # AI user with both admin and user capabilities
    mixed = "mixed"  # User with both admin and user capabilities
    mentor = "mentor"  # User with mentor capabilities
    mentee = "mentee"  # User with mentee capabilities
