"""
Модели базы данных
"""
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, ForeignKey, String, Text, func, Enum, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.schemas import UserRole, Status

from datetime import datetime


class Base(DeclarativeBase):
    pass


class Embedding(Base):
    """Таблица эмбеддингов"""

    __tablename__ = "embeddings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[Vector] = mapped_column(Vector(1536))
    extra_metadata: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class MessageEmbedding(Base):
    """Таблица эмбеддингов сообщений форума"""

    __tablename__ = "message_embeddings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    message_id: Mapped[int] = mapped_column(index=True)
    topic_id: Mapped[int] = mapped_column(index=True)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[Vector] = mapped_column(Vector(1536))
    extra_metadata: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class UserKnowledgeRecord(Base):
    """Таблица знаний пользователей"""

    __tablename__ = "user_knowledge"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Связь с реальным пользователем
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)

    # Дополнительное поле для хранения строкового идентификатора (например, alice_researcher)
    character_id: Mapped[Optional[str]] = mapped_column(String(50), unique=True, index=True, nullable=True)

    name: Mapped[str] = mapped_column(String(100))
    personality: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    background: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expertise: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    communication_style: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preferences: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class UserMessageExample(Base):
    """Таблица примеров сообщений пользователей"""

    __tablename__ = "user_message_examples"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Связь с реальным пользователем
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    # Дополнительное поле для хранения строкового идентификатора (например, alaev)
    character_id: Mapped[Optional[str]] = mapped_column(String(50), index=True, nullable=True)

    # Основные поля сообщения
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text)
    thread_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reply_to: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column()

    # Эмбеддинги для similarity search
    content_embedding: Mapped[Optional[Vector]] = mapped_column(Vector(1536), nullable=True)
    context_embedding: Mapped[Optional[Vector]] = mapped_column(Vector(1536), nullable=True)

    # Метаданные и служебные поля
    extra_metadata: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    source_file: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
