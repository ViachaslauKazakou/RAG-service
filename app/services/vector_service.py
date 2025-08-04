"""
Сервис для работы с векторной базой данных
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared_models.models import Embedding, MessageEmbedding, UserMessageExample
from app.schemas import ContextDocument

logger = logging.getLogger(__name__)


class VectorService:
    """Сервис для работы с векторной базой данных"""

    def __init__(self):
        pass

    async def search_similar_messages(
        self,
        query_embedding: List[float],
        db: AsyncSession,
        user_id: Optional[int] = None,
        limit: int = 10,
        similarity_threshold: float = 0.1,
    ) -> List[ContextDocument]:
        """
        Поиск похожих сообщений в векторной базе

        Args:
            query_embedding: Вектор запроса
            db: Сессия базы данных
            user_id: ID пользователя для фильтрации (опционально)
            limit: Максимальное количество результатов
            similarity_threshold: Порог схожести

        Returns:
            Список найденных документов
        """
        try:
            # Создаем базовый запрос к user_message_examples
            base_query = select(
                UserMessageExample.id,
                UserMessageExample.user_id,
                UserMessageExample.content,
                UserMessageExample.context,
                UserMessageExample.extra_metadata,
                (1 - UserMessageExample.content_embedding.cosine_distance(query_embedding)).label('similarity')
            ).where(
                UserMessageExample.content_embedding.is_not(None)
            )
            
            # Применяем фильтры
            base_query = base_query.where(
                (1 - UserMessageExample.content_embedding.cosine_distance(query_embedding)) > similarity_threshold
            )
            
            # Фильтр по пользователю если указан
            if user_id:
                base_query = base_query.where(UserMessageExample.user_id == user_id)
            
            # Сортировка по схожести и ограничение
            base_query = base_query.order_by(
                UserMessageExample.content_embedding.cosine_distance(query_embedding)
            ).limit(limit)

            result = await db.execute(base_query)
            rows = result.fetchall()

            documents = []
            for row in rows:
                doc = ContextDocument(
                    id=row.id,
                    content=row.content,
                    similarity_score=float(row.similarity),
                    metadata=row.extra_metadata or {},
                    topic_id=None,  # В user_message_examples нет topic_id
                    message_id=None,  # В user_message_examples нет message_id
                )
                documents.append(doc)

            logger.info(f"Found {len(documents)} similar messages for user_id '{user_id}'")
            return documents

        except Exception as e:
            logger.error(f"Error searching similar messages: {e}")
            return []

    async def search_general_embeddings(
        self, query_embedding: List[float], db: AsyncSession, limit: int = 5, similarity_threshold: float = 0.08
    ) -> List[ContextDocument]:
        """
        Поиск в общих эмбеддингах

        Args:
            query_embedding: Вектор запроса
            db: Сессия базы данных
            limit: Максимальное количество результатов
            similarity_threshold: Порог схожести

        Returns:
            Список найденных документов
        """
        try:
            # Создаем запрос для общих эмбеддингов
            query = select(
                Embedding.id,
                Embedding.content,
                Embedding.extra_metadata,
                (1 - Embedding.embedding.cosine_distance(query_embedding)).label('similarity')
            ).where(
                (1 - Embedding.embedding.cosine_distance(query_embedding)) > similarity_threshold
            ).order_by(
                Embedding.embedding.cosine_distance(query_embedding)
            ).limit(limit)

            result = await db.execute(query)
            rows = result.fetchall()

            documents = []
            for row in rows:
                doc = ContextDocument(
                    id=row.id, 
                    content=row.content, 
                    similarity_score=float(row.similarity), 
                    metadata=row.extra_metadata or {}
                )
                documents.append(doc)

            logger.info(f"Found {len(documents)} general embeddings")
            return documents

        except Exception as e:
            logger.error(f"Error searching general embeddings: {e}")
            return []

    async def add_message_embedding(
        self,
        message_id: int,
        topic_id: int,
        content: str,
        embedding: List[float],
        metadata: Dict[str, Any],
        db: AsyncSession,
    ) -> bool:
        """
        Добавляет эмбеддинг сообщения в базу

        Args:
            message_id: ID сообщения
            topic_id: ID топика
            content: Содержимое сообщения
            embedding: Вектор эмбеддинга
            metadata: Метаданные
            db: Сессия базы данных

        Returns:
            True если успешно добавлено
        """
        try:
            message_embedding = MessageEmbedding(
                message_id=message_id, topic_id=topic_id, content=content, embedding=embedding, metadata=metadata
            )

            db.add(message_embedding)
            await db.commit()

            logger.info(f"Added embedding for message {message_id}")
            return True

        except Exception as e:
            logger.error(f"Error adding message embedding: {e}")
            await db.rollback()
            return False

    async def get_database_stats(self, db: AsyncSession) -> Dict[str, int]:
        """
        Получает статистику базы данных

        Args:
            db: Сессия базы данных

        Returns:
            Словарь со статистикой
        """
        try:
            # Считаем количество записей в таблицах
            message_count_result = await db.execute(text("SELECT COUNT(*) FROM message_embeddings"))
            message_count = message_count_result.scalar()

            embedding_count_result = await db.execute(text("SELECT COUNT(*) FROM embeddings"))
            embedding_count = embedding_count_result.scalar()

            return {
                "message_embeddings": message_count,
                "general_embeddings": embedding_count,
                "total_embeddings": message_count + embedding_count,
            }

        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {"message_embeddings": 0, "general_embeddings": 0, "total_embeddings": 0}
