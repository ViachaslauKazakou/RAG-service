"""
Основной RAG сервис
"""
import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import ContextDocument, RAGRequest, RAGResponse, UserKnowledge
from app.services.knowledge_service import KnowledgeService
from app.services.vector_service import VectorService

logger = logging.getLogger(__name__)


class RAGService:
    """Основной RAG сервис для обработки запросов"""
    
    def __init__(self):
        self.knowledge_service = KnowledgeService()
        self.vector_service = VectorService()
        self._http_client = None
    
    async def get_http_client(self) -> httpx.AsyncClient:
        """Получает HTTP клиент (ленивая инициализация)"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client
    
    async def close(self):
        """Закрывает HTTP клиент"""
        if self._http_client:
            await self._http_client.aclose()
    
    async def process_rag_request(
        self, 
        request: RAGRequest, 
        db: AsyncSession
    ) -> RAGResponse:
        """
        Обрабатывает RAG запрос
        
        Args:
            request: Запрос для обработки
            db: Сессия базы данных
            
        Returns:
            Ответ с сгенерированным промптом
        """
        start_time = time.time()
        
        try:
            # 1. Загружаем знания пользователя
            user_knowledge = await self.knowledge_service.load_user_knowledge(
                request.user_id, db
            )
            
            if not user_knowledge:
                # Создаем базовые знания если пользователь не найден
                user_knowledge = self._create_default_user_knowledge(request.user_id)
            
            # 2. Получаем эмбеддинг вопроса (пока используем фиктивный)
            query_embedding = await self._get_query_embedding(request.question)
            
            # 3. Ищем релевантные документы
            context_documents = await self._search_context_documents(
                query_embedding=query_embedding,
                topic=request.topic,
                db=db,
                limit=request.context_limit,
                similarity_threshold=request.similarity_threshold
            )
            
            # 4. Создаем промпт
            generated_prompt = await self.knowledge_service.create_character_prompt(
                user_knowledge=user_knowledge,
                question=request.question,
                context_docs=[doc.dict() for doc in context_documents],
                reply_to=request.reply_to
            )
            
            # 5. Вычисляем оценку уверенности
            confidence_score = self._calculate_confidence_score(context_documents)
            
            processing_time = time.time() - start_time
            
            response = RAGResponse(
                generated_prompt=generated_prompt,
                user_id=request.user_id,
                topic=request.topic,
                context_documents=[doc.dict() for doc in context_documents],
                user_knowledge=user_knowledge.dict(),
                confidence_score=confidence_score,
                processing_time=processing_time
            )
            
            logger.info(
                f"Processed RAG request for user {request.user_id} "
                f"in {processing_time:.3f}s with confidence {confidence_score:.3f}"
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing RAG request: {e}")
            processing_time = time.time() - start_time
            
            # Возвращаем базовый ответ в случае ошибки
            return RAGResponse(
                generated_prompt=f"Ошибка при обработке запроса: {str(e)}",
                user_id=request.user_id,
                topic=request.topic,
                context_documents=[],
                user_knowledge={},
                confidence_score=0.0,
                processing_time=processing_time
            )
    
    async def _search_context_documents(
        self,
        query_embedding: List[float],
        topic: str,
        db: AsyncSession,
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[ContextDocument]:
        """Ищет контекстные документы"""
        
        # Ищем в сообщениях форума
        message_docs = await self.vector_service.search_similar_messages(
            query_embedding=query_embedding,
            db=db,
            topic=topic,
            limit=limit,
            similarity_threshold=similarity_threshold
        )
        
        # Если нашли мало документов, ищем в общих эмбеддингах
        if len(message_docs) < limit // 2:
            general_docs = await self.vector_service.search_general_embeddings(
                query_embedding=query_embedding,
                db=db,
                limit=limit - len(message_docs),
                similarity_threshold=similarity_threshold
            )
            message_docs.extend(general_docs)
        
        # Сортируем по релевантности
        message_docs.sort(key=lambda x: x.similarity_score, reverse=True)
        
        return message_docs[:limit]
    
    async def _get_query_embedding(self, query: str) -> List[float]:
        """
        Получает эмбеддинг запроса
        TODO: Интегрировать с реальной моделью эмбеддингов
        """
        # Пока возвращаем фиктивный эмбеддинг
        # В реальной реализации здесь будет вызов к модели эмбеддингов
        import random
        return [random.random() for _ in range(1536)]
    
    def _create_default_user_knowledge(self, user_id: str) -> UserKnowledge:
        """Создает базовые знания для неизвестного пользователя"""
        from datetime import datetime
        
        return UserKnowledge(
            user_id=user_id,
            name=f"User_{user_id}",
            personality="Дружелюбный и помогающий пользователь форума.",
            background="Участник форума, интересуется различными техническими темами.",
            expertise=["General Discussion"],
            communication_style="Дружелюбный, вежливый, стремится помочь.",
            preferences={
                "response_length": "medium",
                "include_code_examples": False,
                "cite_sources": False,
                "technical_level": "intermediate"
            },
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def _calculate_confidence_score(self, context_documents: List[ContextDocument]) -> float:
        """Вычисляет оценку уверенности на основе найденных документов"""
        if not context_documents:
            return 0.0
        
        # Средняя схожесть документов
        avg_similarity = sum(doc.similarity_score for doc in context_documents) / len(context_documents)
        
        # Количество документов (нормализованное)
        doc_count_score = min(len(context_documents) / 10.0, 1.0)
        
        # Итоговая оценка
        confidence = (avg_similarity * 0.7) + (doc_count_score * 0.3)
        
        return min(confidence, 1.0)
