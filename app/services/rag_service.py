"""
Основной RAG сервис
"""
import logging
import os
import time
from sentence_transformers import SentenceTransformer
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

    async def process_rag_request(self, request: RAGRequest, db: AsyncSession, rag_type: str = "default") -> RAGResponse:
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
            user_knowledge = await self.knowledge_service.load_user_knowledge(request.user_id, db)
            logger.info(f"Loaded user knowledge for user {request.user_id}: {user_knowledge.name}...")

            if not user_knowledge:
                # Создаем базовые знания если пользователь не найден
                user_knowledge = self._create_default_user_knowledge(request.user_id)

            # 2. Получаем эмбеддинг вопроса 
            query_embedding = await self._get_query_embedding(request.question)

            # 3. Ищем релевантные документы
            context_documents = await self._search_context_documents(
                query_embedding=query_embedding,
                user_id=request.user_id,
                db=db,
                limit=request.context_limit,
                similarity_threshold=request.similarity_threshold,
            )

            # 4. Создаем промпт
            generated_prompt = await self.knowledge_service.create_character_prompt(
                rag_type=rag_type,
                user_knowledge=user_knowledge,
                question=request.question,
                topic=request.topic,
                context_docs=[doc.model_dump() for doc in context_documents],
                reply_to=request.reply_to,
            )

            # 5. Вычисляем оценку уверенности
            confidence_score = self._calculate_confidence_score(context_documents)

            processing_time = time.time() - start_time

            response = RAGResponse(
                generated_prompt=generated_prompt,
                user_id=request.user_id,
                topic=request.topic,
                context_documents=[doc.model_dump() for doc in context_documents],
                user_knowledge=user_knowledge.model_dump(),
                confidence_score=confidence_score,
                processing_time=processing_time,
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
                processing_time=processing_time,
            )

    async def _search_context_documents(
        self,
        query_embedding: List[float],
        user_id: int,
        db: AsyncSession,
        limit: int = 10,
        similarity_threshold: float = 0.1,
    ) -> List[ContextDocument]:
        """Ищет контекстные документы"""

        # Ищем в сообщениях пользователя
        message_docs = await self.vector_service.search_similar_messages(
            query_embedding=query_embedding, db=db, user_id=user_id, limit=limit, similarity_threshold=similarity_threshold
        )

        logger.info(f"Found {len(message_docs)} similar messages")

        # Если нашли мало документов, ищем в общих эмбеддингах
        if len(message_docs) < limit // 2:
            general_docs = await self.vector_service.search_general_embeddings(
                query_embedding=query_embedding,
                db=db,
                limit=limit - len(message_docs),
                similarity_threshold=similarity_threshold * 0.8,  # Более низкий порог для общих эмбеддингов
            )
            logger.info(f"Found {len(general_docs)} general embeddings")
            message_docs.extend(general_docs)

        # Сортируем по релевантности
        message_docs.sort(key=lambda x: x.similarity_score, reverse=True)

        return message_docs[:limit]

    async def _get_query_embedding(self, query: str) -> List[float]:
        """
        Получает эмбеддинг запроса через HuggingFace (приоритет) или Ollama (fallback)
        
        Args:
            query: Текст для получения эмбеддинга
            
        Returns:
            Список чисел представляющий эмбеддинг
        """
        logger.info(f"Getting embedding for query: {query[:50]}...")
        try:
            if not query.strip():
                logger.warning("Empty query provided, returning zero vector")
                return [0.0] * 1536  # 1536 размерность для совместимости с базой

            # Приоритет: HuggingFace локально (должна совпадать с моделью в knowledge_service)
            try:
                logger.debug(f"Creating HuggingFace embedding for text: {query[:100]}...")
                return self._create_hf_embedding(query)
            except Exception as e:
                logger.warning(f"HuggingFace embedding failed, trying Ollama: {e}")
                
            # Fallback: Ollama через HTTP
            try:
                return await self._get_ollama_embedding(query)
            except Exception as e:
                logger.error(f"Ollama embedding also failed: {e}")
                
        except Exception as e:
            logger.error(f"All embedding methods failed: {e}")
            # Последний fallback - простое хеширование
            return self._create_hash_embedding(query)

    async def _get_ollama_embedding(self, query: str) -> List[float]:
        """
        Получает эмбеддинг через Ollama (fallback метод)
        
        Args:
            query: Текст для получения эмбеддинга
            
        Returns:
            Эмбеддинг через Ollama
        """
        logger.info("Getting embedding from Ollama...")
        try:
            http_client = await self.get_http_client()
            
            # Пытаемся подключиться к Ollama (проверяем разные адреса)
            ollama_base_url = os.getenv("OLLAMA_BASE_URL")
            if ollama_base_url:
                ollama_urls = [ollama_base_url]
            else:
                ollama_urls = [
                    "http://host.docker.internal:11434",  # Docker Desktop на Mac/Windows
                    "http://172.17.0.1:11434",            # Docker на Linux
                    "http://localhost:11434",             # Fallback (если не в контейнере)
                ]
            
            ollama_url = None
            # Проверяем доступность Ollama
            for url in ollama_urls:
                try:
                    models_endpoint = f"{url}/api/tags"
                    logger.debug(f"Trying Ollama at {url}...")
                    models_response = await http_client.get(models_endpoint, timeout=3.0)
                    if models_response.status_code == 200:
                        ollama_url = url
                        logger.info(f"Successfully connected to Ollama at {url}")
                        break
                except Exception as e:
                    logger.debug(f"Cannot connect to {url}: {e}")
                    continue
            
            if not ollama_url:
                raise Exception("Ollama service not accessible from any known address")
            
            # Сначала проверяем доступность модели
            models_endpoint = f"{ollama_url}/api/tags"
            logger.info(f"Checking available Ollama models at {models_endpoint}...")
            try:
                models_response = await http_client.get(models_endpoint, timeout=5.0)
                if models_response.status_code == 200:
                    models_data = models_response.json()
                    available_models = [model.get('name', '') for model in models_data.get('models', [])]
                    logger.info(f"Available Ollama models: {available_models}")
                    
                    # Выбираем первую доступную модель для эмбеддингов
                    embedding_model = None
                    preferred_models = ['nomic-embed-text', 'all-minilm', 'mxbai-embed-large']
                    
                    for preferred in preferred_models:
                        if any(preferred in model for model in available_models):
                            embedding_model = next(model for model in available_models if preferred in model)
                            break
                    
                    if not embedding_model:
                        logger.warning("No suitable embedding model found in Ollama")
                        raise Exception("No suitable embedding model available")
                        
                    logger.debug(f"Using Ollama model: {embedding_model}")
                    
                else:
                    logger.warning(f"Cannot check Ollama models: {models_response.status_code}")
                    embedding_model = "nomic-embed-text"  # Fallback
                    
            except Exception as e:
                logger.warning(f"Cannot check Ollama models: {e}")
                embedding_model = "nomic-embed-text"  # Fallback
            
            embedding_endpoint = f"{ollama_url}/api/embeddings"
            
            payload = {
                "model": embedding_model,
                "prompt": query.strip()
            }
            
            logger.debug(f"Requesting Ollama embedding for text: {query[:100]}...")
            
            response = await http_client.post(
                embedding_endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60.0
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if "embedding" in result:
                    embedding = result["embedding"]
                    # Расширяем до 1536 размерности для совместимости
                    expanded_embedding = self._expand_embedding_to_1536(embedding)
                    logger.debug(f"Successfully got Ollama embedding of length {len(expanded_embedding)}")
                    return expanded_embedding
                else:
                    logger.error(f"Invalid Ollama embedding response format: {result}")
                    raise Exception("Invalid Ollama response format")
            else:
                error_text = response.text
                logger.error(f"Ollama embedding request failed with status {response.status_code}: {error_text}")
                
                if response.status_code == 404 and "not found" in error_text:
                    raise Exception(f"Ollama model '{embedding_model}' not found. Please install it with: ollama pull {embedding_model}")
                else:
                    raise Exception(f"Ollama request failed: {response.status_code}")
                
        except httpx.RequestError as e:
            logger.error(f"Ollama connection error: {e}")
            raise Exception(f"Ollama service not available at http://localhost:11434: {e}")
        except Exception as e:
            logger.error(f"Ollama embedding error: {e}")
            raise

    def _get_fallback_embedding(self, query: str) -> List[float]:
        """
        Создает эмбеддинг через HuggingFace Sentence Transformers
        Используется когда AI Manager недоступен
        
        Args:
            query: Текст для эмбеддинга
            
        Returns:
            Эмбеддинг через HuggingFace
        """
        try:
            # Пытаемся использовать HuggingFace
            return self._create_hf_embedding(query)
        except Exception as e:
            logger.error(f"HuggingFace embedding failed: {e}")
            # Последний fallback - простое хеширование
            return self._create_hash_embedding(query)

    def _create_hf_embedding(self, query: str) -> List[float]:
        """
        Создает эмбеддинг через HuggingFace Sentence Transformers
        
        Args:
            query: Текст для эмбеддинга
            
        Returns:
            Эмбеддинг вектор размерности 1536 для совместимости с базой
        """
        try:
            from sentence_transformers import SentenceTransformer
            import os
            
            # Ленивая инициализация модели
            if not hasattr(self, '_hf_model'):
                logger.info("Loading HuggingFace embedding model...")
                
                # Устанавливаем кеш в доступную для записи директорию
                cache_dir = '/tmp/hf_cache'
                os.makedirs(cache_dir, exist_ok=True)
                os.environ['TRANSFORMERS_CACHE'] = cache_dir
                os.environ['HF_HOME'] = cache_dir
                
                # Используем модель с более высокой размерностью
                self._hf_model = SentenceTransformer(
                    'sentence-transformers/all-mpnet-base-v2',
                    cache_folder=cache_dir
                )
                self._hf_model_name = 'all-mpnet-base-v2'
                logger.info(f"Loaded HuggingFace model: {self._hf_model_name} (768 dimensions)")
            
            # Создаем эмбеддинг
            embedding = self._hf_model.encode(query, convert_to_tensor=False)
            
            # Конвертируем в список
            if hasattr(embedding, 'tolist'):
                embedding = embedding.tolist()
            elif hasattr(embedding, 'numpy'):
                embedding = embedding.numpy().tolist()
            
            # Расширяем до 1536 размерности для совместимости с базой
            embedding = self._expand_embedding_to_1536(embedding)
            
            logger.debug(f"Created HuggingFace embedding of length {len(embedding)}")
            return embedding
            
        except ImportError:
            logger.error("sentence-transformers not installed")
            raise Exception("HuggingFace dependencies not available")
        except Exception as e:
            logger.error(f"Error creating HuggingFace embedding: {e}")
            raise

    def _expand_embedding_to_1536(self, embedding: List[float]) -> List[float]:
        """
        Расширяет эмбеддинг до размерности 1536 для совместимости с базой данных
        
        Args:
            embedding: Исходный эмбеддинг
            
        Returns:
            Эмбеддинг размерности 1536
        """
        import numpy as np
        
        current_dim = len(embedding)
        target_dim = 1536
        
        if current_dim == target_dim:
            return embedding
        elif current_dim > target_dim:
            # Обрезаем до нужной размерности
            return embedding[:target_dim]
        else:
            # Расширяем различными методами для лучшего покрытия пространства
            embedding_array = np.array(embedding)
            
            # Метод 1: Дублирование и масштабирование
            repeat_factor = target_dim // current_dim
            remainder = target_dim % current_dim
            
            expanded = np.tile(embedding_array, repeat_factor)
            
            # Добавляем остаток с небольшим шумом для разнообразия
            if remainder > 0:
                noise_factor = 0.1
                remainder_part = embedding_array[:remainder] * (1 + noise_factor * np.random.randn(remainder))
                expanded = np.concatenate([expanded, remainder_part])
            
            # Нормализуем итоговый вектор
            norm = np.linalg.norm(expanded)
            if norm > 0:
                expanded = expanded / norm
            
            return expanded.tolist()

    def _create_hash_embedding(self, query: str) -> List[float]:
        """
        Создает простой fallback эмбеддинг на основе хеша текста
        Используется только в крайнем случае
        
        Args:
            query: Текст для эмбеддинга
            
        Returns:
            Детерминированный эмбеддинг на основе хеша
        """
        import hashlib
        import struct
        
        # Создаем детерминированный эмбеддинг на основе хеша текста
        text_hash = hashlib.sha256(query.encode('utf-8')).digest()
        
        # Преобразуем хеш в вектор фиксированной длины (1536 для совместимости с базой)
        embedding = []
        target_dim = 1536  # Размерность для совместимости с базой данных
        
        for i in range(0, min(len(text_hash), target_dim * 4), 4):
            if i + 4 <= len(text_hash):
                # Интерпретируем 4 байта как float
                value = struct.unpack('f', text_hash[i:i + 4])[0]
                # Нормализуем значение в диапазон [-1, 1]
                normalized_value = max(-1.0, min(1.0, value / 1e10))
                embedding.append(normalized_value)
        
        # Дополняем до нужной длины нулями если нужно
        while len(embedding) < target_dim:
            embedding.append(0.0)
            
        logger.warning(f"Using hash-based fallback embedding for query: {query[:50]}...")
        return embedding[:target_dim]

    async def get_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Получает эмбеддинги для списка текстов пакетом
        
        Args:
            texts: Список текстов для получения эмбеддингов
            
        Returns:
            Список эмбеддингов для каждого текста
        """
        try:
            if not texts:
                return []

            # Фильтруем пустые тексты
            filtered_texts = [text.strip() for text in texts if text and text.strip()]
            
            if not filtered_texts:
                return [[0.0] * 1536] * len(texts)  # 1536 для совместимости с базой

            # Приоритет: HuggingFace пакетная обработка
            try:
                logger.debug(f"Creating HuggingFace batch embeddings for {len(filtered_texts)} texts")
                return self._create_hf_batch_embeddings(filtered_texts)
            except Exception as e:
                logger.warning(f"HuggingFace batch embedding failed, trying Ollama: {e}")
                
                # Fallback: Ollama по одному
                embeddings = []
                for text in filtered_texts:
                    try:
                        embedding = await self._get_ollama_embedding(text)
                        embeddings.append(embedding)
                    except Exception as ollama_error:
                        logger.error(f"Ollama embedding failed for text: {ollama_error}")
                        # Hash fallback для этого текста
                        embeddings.append(self._create_hash_embedding(text))
                
                return embeddings
                
        except Exception as e:
            logger.error(f"Error getting batch embeddings: {e}")
            return [self._create_hash_embedding(text) for text in texts]

    def _create_hf_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Создает эмбеддинги для списка текстов через HuggingFace пакетом
        
        Args:
            texts: Список текстов для эмбеддинга
            
        Returns:
            Список эмбеддинг векторов размерности 1536
        """
        try:
            
            # Ленивая инициализация модели
            if not hasattr(self, '_hf_model'):
                logger.info("Loading HuggingFace embedding model for batch processing...")
                
                # Устанавливаем кеш в доступную для записи директорию
                cache_dir = '/tmp/hf_cache'
                os.makedirs(cache_dir, exist_ok=True)
                os.environ['TRANSFORMERS_CACHE'] = cache_dir
                os.environ['HF_HOME'] = cache_dir
                
                self._hf_model = SentenceTransformer(
                    'sentence-transformers/all-mpnet-base-v2',
                    cache_folder=cache_dir
                )
                self._hf_model_name = 'all-mpnet-base-v2'
                logger.info(f"Loaded HuggingFace model: {self._hf_model_name} (768 dimensions)")
            
            # Создаем эмбеддинги пакетом
            embeddings = self._hf_model.encode(texts, convert_to_tensor=False)
            
            # Конвертируем в список списков
            if hasattr(embeddings, 'tolist'):
                embeddings_list = embeddings.tolist()
            elif hasattr(embeddings, 'numpy'):
                embeddings_list = embeddings.numpy().tolist()
            else:
                # Если это уже список numpy arrays
                embeddings_list = [embedding.tolist() if hasattr(embedding, 'tolist') else embedding for embedding in embeddings]
            
            # Расширяем каждый эмбеддинг до 1536 размерности
            expanded_embeddings = []
            for embedding in embeddings_list:
                expanded_embedding = self._expand_embedding_to_1536(embedding)
                expanded_embeddings.append(expanded_embedding)
            
            logger.debug(f"Created {len(expanded_embeddings)} HuggingFace embeddings (1536 dimensions)")
            return expanded_embeddings
            
        except ImportError:
            logger.error("sentence-transformers not installed")
            raise Exception("HuggingFace dependencies not available")
        except Exception as e:
            logger.error(f"Error creating HuggingFace batch embeddings: {e}")
            raise

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
                "technical_level": "intermediate",
            },
            created_at=datetime.now(),
            updated_at=datetime.now(),
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
