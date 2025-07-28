from sqlalchemy import String, Text, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import Optional, List
from datetime import datetime
from app.schemas import UserRole, Status


# Базовый класс для моделей
class Base(DeclarativeBase):
    pass


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Внешний ключ на пользователя
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)

    # Связи
    user: Mapped["User"] = relationship("User", back_populates="topics")
    messages: Mapped[List["Message"]] = relationship("Message", back_populates="topic", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    author_name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Внешние ключи
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("messages.id"), nullable=True)

    # Связи
    topic: Mapped["Topic"] = relationship("Topic", back_populates="messages")
    user: Mapped["User"] = relationship("User", back_populates="messages")
    parent: Mapped[Optional["Message"]] = relationship("Message", remote_side=[id], back_populates="replies")
    replies: Mapped[List["Message"]] = relationship("Message", back_populates="parent", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, server_default=func.now())
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    firstname: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    lastname: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    user_type: Mapped[Optional[UserRole]] = mapped_column(
        Enum(UserRole, name="user_type", native_enum=False),
        default=UserRole.user,
        nullable=True,
    )
    status: Mapped[Optional[Status]] = mapped_column(
        Enum(Status, name="user_status", native_enum=False),
        default=Status.pending,
        nullable=True,
    )

    # Relationships
    topics: Mapped[List["Topic"]] = relationship("Topic", back_populates="user")
    messages: Mapped[List["Message"]] = relationship("Message", back_populates="user")


class UsersContext(Base):
    __tablename__ = "users_base_context"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=True)
    character: Mapped[str] = mapped_column(String, nullable=False)
    character_type: Mapped[str] = mapped_column(String, nullable=False)
    mood: Mapped[str] = mapped_column(String, nullable=False)
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reply_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # reply_to: Mapped[Optional[int]] = mapped_column(ForeignKey("messages.id"), nullable=True)
    topic: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), nullable=True)

    # Связи
    # topic: Mapped["Topic"] = relationship("Topic", back_populates="userscontext")
    # user: Mapped["User"] = relationship("User", back_populates="userscontext")
    # replies: Mapped[List["Message"]] = relationship("Message", back_populates="parent", cascade="all, delete-orphan")
