from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime
import os
import pickle
import json
import hashlib

from langchain_community.vectorstores import FAISS
# from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from app.utils.logger_utils import setup_logger, timer

logger = setup_logger(__name__)


class AdvancedRAG:
    def __init__(self, documents_path: str = "knowledge_base", cache_path: str = "cache"):
        self.documents_path = documents_path
        self.cache_path = cache_path
        self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        self.vectorstore = None
        self.retriever = None
        
        # Создаем папку для кеша
        os.makedirs(self.cache_path, exist_ok=True)
        
        # Файлы для кеша
        self.vectorstore_cache_file = os.path.join(self.cache_path, "vectorstore.pkl")
        self.metadata_cache_file = os.path.join(self.cache_path, "rag_metadata.json")
        
        self.setup_rag()

    def _get_documents_hash(self) -> str:
        """Создает хеш всех документов для проверки изменений"""
        hash_md5 = hashlib.md5()
        
        if not os.path.exists(self.documents_path):
            return ""
            
        # Получаем все  файлы и их время изменения
        files_info = []
        for root, dirs, files in os.walk(self.documents_path):
            for filename in sorted(files):
                if filename.endswith(".txt") or filename.endswith(".json"):
                    filepath = os.path.join(root, filename)
                    try:
                        mtime = os.path.getmtime(filepath)
                        size = os.path.getsize(filepath)
                        files_info.append(f"{filename}:{mtime}:{size}")
                    except OSError:
                        continue
        
        # Создаем хеш из информации о файлах
        files_str = "|".join(files_info)
        hash_md5.update(files_str.encode())
        return hash_md5.hexdigest()

    def _is_cache_valid(self) -> bool:
        """Проверяет, актуален ли кеш"""
        if not os.path.exists(self.vectorstore_cache_file) or not os.path.exists(self.metadata_cache_file):
            logger.info("Файлы кеша не найдены")
            return False
        
        try:
            with open(self.metadata_cache_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            current_hash = self._get_documents_hash()
            cached_hash = metadata.get('documents_hash')
            
            if current_hash != cached_hash:
                logger.info("Документы изменились, кеш устарел")
                return False
            
            # Проверяем совместимость модели эмбеддингов
            if metadata.get('embedding_model') != "sentence-transformers/all-MiniLM-L6-v2":
                logger.info("Модель эмбеддингов изменилась, кеш устарел")
                return False
            
            logger.info("Кеш актуален")
            return True
            
        except Exception as e:
            logger.warning(f"Ошибка при проверке кеша: {e}")
            return False

    def _save_cache(self):
        """Сохраняет vectorstore и метаданные в кеш"""
        try:
            if self.vectorstore is None:
                logger.warning("Нет vectorstore для сохранения")
                return
            
            # Сохраняем vectorstore
            with open(self.vectorstore_cache_file, 'wb') as f:
                pickle.dump(self.vectorstore, f)
            
            # Сохраняем метаданные
            metadata = {
                'documents_hash': self._get_documents_hash(),
                'embedding_model': "sentence-transformers/all-MiniLM-L6-v2",
                'documents_count': len(self.vectorstore.docstore._dict) if hasattr(self.vectorstore, 'docstore') else 0,
                'created_at': datetime.now().isoformat(),
                'langchain_version': self._get_langchain_version()
            }
            
            with open(self.metadata_cache_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Кеш сохранен: {metadata['documents_count']} документов")
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении кеша: {e}")

    def _load_cache(self) -> bool:
        """Загружает vectorstore из кеша"""
        try:
            # Загружаем vectorstore
            with open(self.vectorstore_cache_file, 'rb') as f:
                self.vectorstore = pickle.load(f)
            
            # Создаем retriever
            self.retriever = self.vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 3}
            )
            
            # Загружаем метаданные для информации
            with open(self.metadata_cache_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            logger.info(f"Кеш загружен: {metadata.get('documents_count', 0)} документов из {metadata.get('created_at', 'неизвестно')}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке кеша: {e}")
            return False

    def _get_langchain_version(self) -> str:
        """Получает версию LangChain для совместимости"""
        try:
            import langchain
            return getattr(langchain, '__version__', 'unknown')
        except Exception as e:
            logger.error(f"Ошибка при получении версии LangChain: {e}")
            return 'unknown'

    def setup_rag(self):
        """Настройка RAG с LangChain (с кешированием)"""
        # Проверяем, актуален ли кеш
        if self._is_cache_valid():
            logger.info("Загрузка RAG из кеша...")
            if self._load_cache():
                return
            else:
                logger.warning("Не удалось загрузить кеш, создаем заново...")
        
        # Создаем RAG заново
        logger.info("Создание нового RAG индекса...")
        self._create_new_rag()

    def _create_new_rag(self):
        """Создает новый RAG индекс"""
        # Загружаем документы
        logger.info(f"🔍 Загрузка документов из {self.documents_path}")
        
        # Проверяем, существует ли директория
        if not os.path.exists(self.documents_path):
            logger.error(f"❌ Директория с документами не найдена: {self.documents_path}")
            return
            
        # Проверяем наличие файлов
        files_found = []
        for root, dirs, files in os.walk(self.documents_path):
            for file in files:
                if file.endswith(('.txt', '.json')):
                    full_path = os.path.join(root, file)
                    files_found.append(full_path)
                    logger.info(f"   📄 Найден файл: {full_path}")
        
        logger.info(f"📚 Найдено {len(files_found)} файлов для загрузки")
        
        # Загружаем файлы по отдельности, чтобы гарантировать правильную загрузку
        documents = []
        for file_path in files_found:
            try:
                logger.info(f"   📖 Загрузка файла: {file_path}")
                loader = TextLoader(file_path, encoding="utf-8")
                file_docs = loader.load()
                documents.extend(file_docs)
                logger.info(f"   ✅ Загружено {len(file_docs)} документов из {file_path}")
            except Exception as e:
                logger.error(f"   ❌ Ошибка загрузки файла {file_path}: {e}")
                continue

        try:
            if not documents:
                logger.warning(f"⚠️ Не найдено документов в {self.documents_path}")
                logger.info(f"   Найденные файлы: {files_found}")
                return

            logger.info(f"✅ Загружено {len(documents)} документов")
            
            # Логируем информацию о загруженных документах
            for i, doc in enumerate(documents[:5]):  # Первые 5 для примера
                logger.info(f"   📄 Документ {i+1}: source={doc.metadata.get('source', 'unknown')}, length={len(doc.page_content)}")
                logger.info(f"      Содержимое: {doc.page_content[:100]}...")

            # Разбиваем на чанки
            logger.info("✂️ Разбиение документов на чанки...")
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=800,  # Уменьшаем размер чанков для разбиения JSON файлов на части
                chunk_overlap=100,  # Увеличиваем перекрытие
                length_function=len
            )

            texts = text_splitter.split_documents(documents)
            logger.info(f"📝 Создано {len(texts)} чанков")

            # Создаем векторное хранилище
            logger.info("🧠 Создание векторного хранилища...")
            self.vectorstore = FAISS.from_documents(texts, self.embeddings)

            # Создаем retriever
            self.retriever = self.vectorstore.as_retriever(
                search_type="similarity", 
                search_kwargs={"k": 3}
            )
            
            logger.info("✅ RAG успешно настроен")
            
            # Сохраняем в кеш
            self._save_cache()

        except Exception as e:
            logger.error(f"❌ Ошибка при настройке RAG: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            self.vectorstore = None
            self.retriever = None

    def get_relevant_docs(self, query: str, method: str = "adaptive") -> List[str]:
        """Получает релевантные документы с улучшенным ранжированием"""
        logger.info(f"Поиск релевантных документов для запроса: {query} (method={method})")
        
        if not self.retriever:
            logger.warning("Retriever не инициализирован. Проверьте настройку RAG.")
            return []

        try:
            if method == "adaptive":
                docs_info = self.get_adaptive_relevant_docs(query)
            elif method == "filtered":
                docs_info = self.get_relevant_docs_filtered(query)
                docs_info = [{'content': doc} for doc in docs_info]  # Normalize format
            elif method == "ranked":
                docs_info = self.get_ranked_relevant_docs(query)
            elif method == "contextual":
                docs_info = self.get_contextual_relevant_docs(query)
            else:
                # Fallback к стандартному методу
                docs = self.retriever.get_relevant_documents(query)
                result = [doc.page_content for doc in docs]
                logger.info(f"Найдено {len(result)} релевантных документов (стандартный метод)")
                return result
            
            # Извлекаем только содержимое документов
            result = [doc_info['content'] for doc_info in docs_info]
            
            # Логируем детальную информацию о качестве
            for i, doc_info in enumerate(docs_info):
                similarity = doc_info.get('similarity_score', 0)
                source = doc_info.get('source', 'unknown')
                logger.info(f"Документ {i+1}: similarity={similarity:.4f}, source={source}")
            
            logger.info(f"Найдено {len(result)} релевантных документов ({method} метод)")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при поиске документов: {e}")
            return []

    def get_relevant_docs_with_metadata(self, query: str) -> List[Dict]:
        """Получает релевантные документы с метаданными"""
        logger.info(f"Поиск релевантных документов с метаданными для запроса: {query}")
        
        if not self.retriever:
            logger.warning("Retriever не инициализирован. Проверьте настройку RAG.")
            return []

        try:
            docs = self.retriever.get_relevant_documents(query)
            result = []
            
            for doc in docs:
                doc_info = {
                    'content': doc.page_content,
                    'metadata': doc.metadata,
                    'source': doc.metadata.get('source', 'unknown')
                }
                result.append(doc_info)
            
            logger.info(f"Найдено {len(result)} релевантных документов с метаданными")
            return result
        except Exception as e:
            logger.error(f"Ошибка при поиске документов: {e}")
            return []

    def get_relevant_docs_filtered(self, query: str, similarity_threshold: float = 0.7) -> List[str]:
        """Получает релевантные документы с фильтрацией по similarity score"""
        logger.info(f"Поиск релевантных документов для запроса: {query}")
        
        if not self.vectorstore:
            logger.warning("Vectorstore не инициализирован")
            return []
        
        try:
            # Получаем документы с оценками
            docs_with_scores = self.vectorstore.similarity_search_with_score(query, k=10)
            
            # Фильтруем по threshold
            filtered_docs = []
            for doc, score in docs_with_scores:
                # Чем меньше score, тем больше похожесть в FAISS
                if score <= similarity_threshold:
                    filtered_docs.append(doc.page_content)
                    logger.info(f"Документ принят: score={score:.4f}")
                else:
                    logger.info(f"Документ отклонен: score={score:.4f}")
            
            logger.info(f"Найдено {len(filtered_docs)} релевантных документов (threshold={similarity_threshold})")
            return filtered_docs
            
        except Exception as e:
            logger.error(f"Ошибка при поиске документов: {e}")
            return []

    def get_ranked_relevant_docs(self, query: str, top_k: int = 5) -> List[Dict]:
        """Получает документы с ранжированием по similarity score"""
        if not self.vectorstore:
            logger.warning("Vectorstore не инициализирован")
            return []
        
        try:
            # Получаем больше документов для лучшего ранжирования
            docs_with_scores = self.vectorstore.similarity_search_with_score(query, k=top_k * 2)
            
            # Создаем список с дополнительной информацией
            ranked_docs = []
            for doc, score in docs_with_scores:
                # Нормализуем score (превращаем в similarity score от 0 до 1)
                similarity_score = 1.0 / (1.0 + score)
                
                doc_info = {
                    'content': doc.page_content,
                    'metadata': doc.metadata,
                    'similarity_score': similarity_score,
                    'distance_score': float(score),
                    'source': doc.metadata.get('source', 'unknown'),
                    'relevance_rank': len(ranked_docs) + 1
                }
                ranked_docs.append(doc_info)
            
            # Сортируем по similarity score (убывание)
            ranked_docs.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            # Обновляем ранги после сортировки
            for i, doc in enumerate(ranked_docs):
                doc['relevance_rank'] = i + 1
            
            # Возвращаем только top_k документов
            result = ranked_docs[:top_k]
            
            logger.info(f"Найдено {len(result)} ранжированных документов")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при поиске ранжированных документов: {e}")
            return []

    def clear_cache(self):
        """Очищает кеш"""
        cache_files = [self.vectorstore_cache_file, self.metadata_cache_file]
        
        for cache_file in cache_files:
            if os.path.exists(cache_file):
                os.remove(cache_file)
                logger.info(f"Удален файл кеша: {cache_file}")
        
        logger.info("Кеш очищен")

    def rebuild_index(self):
        """Принудительно пересоздает индекс"""
        logger.info("Принудительное пересоздание индекса...")
        self.clear_cache()
        self._create_new_rag()

    def get_cache_info(self) -> Dict:
        """Возвращает информацию о кеше"""
        cache_info = {
            'cache_exists': self._is_cache_valid(),
            'cache_files': {},
            'documents_path': self.documents_path,
            'cache_path': self.cache_path
        }
        
        cache_files = [
            ('vectorstore', self.vectorstore_cache_file),
            ('metadata', self.metadata_cache_file)
        ]
        
        for name, filepath in cache_files:
            if os.path.exists(filepath):
                stat = os.stat(filepath)
                cache_info['cache_files'][name] = {
                    'size_mb': round(stat.st_size / 1024 / 1024, 2),
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                }
        
        # Добавляем метаданные, если они есть
        if os.path.exists(self.metadata_cache_file):
            try:
                with open(self.metadata_cache_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                cache_info['metadata'] = metadata
            except Exception as e:
                logger.warning(f"Не удалось прочитать метаданные: {e}")
        
        return cache_info

    def add_documents(self, new_documents: List[str], sources: Optional[List[str]] = None):
        """Добавляет новые документы в существующий индекс"""
        if not self.vectorstore:
            logger.warning("Vectorstore не инициализирован")
            return
        
        try:
            # Создаем документы для добавления
            from langchain.schema import Document
            
            docs_to_add = []
            for i, doc_text in enumerate(new_documents):
                source = sources[i] if sources and i < len(sources) else f"added_doc_{i}"
                doc = Document(
                    page_content=doc_text,
                    metadata={"source": source, "added_at": datetime.now().isoformat()}
                )
                docs_to_add.append(doc)
            
            # Разбиваем на чанки
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500, 
                chunk_overlap=50, 
                length_function=len
            )
            
            texts = text_splitter.split_documents(docs_to_add)
            
            # Добавляем в vectorstore
            self.vectorstore.add_documents(texts)
            
            # Обновляем retriever
            self.retriever = self.vectorstore.as_retriever(
                search_type="similarity", 
                search_kwargs={"k": 3}
            )
            
            logger.info(f"Добавлено {len(texts)} новых чанков")
            
            # Сохраняем обновленный кеш
            self._save_cache()
            
        except Exception as e:
            logger.error(f"Ошибка при добавлении документов: {e}")

    def get_documents_count(self) -> int:
        """Возвращает количество документов в индексе"""
        if not self.vectorstore or not hasattr(self.vectorstore, 'docstore'):
            return 0
        return len(self.vectorstore.docstore._dict)

    def search_similar_documents(self, query: str, top_k: int = 5) -> List[Dict]:
        """Поиск похожих документов с оценками релевантности"""
        if not self.vectorstore:
            logger.warning("Vectorstore не инициализирован")
            return []
        
        try:
            # Используем similarity_search_with_score для получения оценок
            docs_with_scores = self.vectorstore.similarity_search_with_score(query, k=top_k)
            
            result = []
            for doc, score in docs_with_scores:
                doc_info = {
                    'content': doc.page_content,
                    'metadata': doc.metadata,
                    'similarity_score': float(score),
                    'source': doc.metadata.get('source', 'unknown')
                }
                result.append(doc_info)
            
            logger.info(f"Найдено {len(result)} похожих документов")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при поиске похожих документов: {e}")
            return []

    def get_adaptive_relevant_docs(self, query: str, max_docs: int = 5, quality_threshold: float = 0.6) -> List[Dict]:
        """Адаптивно получает документы на основе качества similarity"""
        if not self.vectorstore:
            logger.warning("Vectorstore не инициализирован")
            return []
        
        try:
            # Получаем больше документов для анализа
            docs_with_scores = self.vectorstore.similarity_search_with_score(query, k=max_docs * 3)
            
            if not docs_with_scores:
                return []
            
            # Анализируем качество результатов
            scores = [score for _, score in docs_with_scores]
            avg_score = sum(scores) / len(scores)
            min_score = min(scores)
            
            # Адаптивный threshold на основе качества результатов
            if min_score < 0.3:  # Очень хорошее совпадение
                threshold = avg_score * 0.8
            elif min_score < 0.6:  # Хорошее совпадение
                threshold = avg_score * 0.9
            else:  # Слабое совпадение
                threshold = avg_score * 1.1
            
            # Фильтруем документы
            filtered_docs = []
            for doc, score in docs_with_scores:
                if score <= threshold and len(filtered_docs) < max_docs:
                    similarity_score = 1.0 / (1.0 + score)
                    
                    doc_info = {
                        'content': doc.page_content,
                        'metadata': doc.metadata,
                        'similarity_score': similarity_score,
                        'distance_score': float(score),
                        'source': doc.metadata.get('source', 'unknown'),
                        'quality_level': self._assess_quality(similarity_score)
                    }
                    filtered_docs.append(doc_info)
            
            logger.info(f"Адаптивно найдено {len(filtered_docs)} документов (threshold={threshold:.4f})")
            return filtered_docs
            
        except Exception as e:
            logger.error(f"Ошибка при адаптивном поиске: {e}")
            return []

    def get_contextual_relevant_docs(self, query: str, context_window: int = 2) -> List[Dict]:
        """Получает документы с учетом контекста соседних чанков"""
        if not self.vectorstore:
            logger.warning("Vectorstore не инициализирован")
            return []
        
        try:
            # Получаем документы с оценками
            docs_with_scores = self.vectorstore.similarity_search_with_score(query, k=5)
            
            enhanced_docs = []
            for doc, score in docs_with_scores:
                similarity_score = 1.0 / (1.0 + score)
                
                # Пытаемся найти соседние чанки из того же источника
                source = doc.metadata.get('source', '')
                context_docs = self._find_context_chunks(source, doc.page_content, context_window)
                
                doc_info = {
                    'content': doc.page_content,
                    'context_content': context_docs,
                    'metadata': doc.metadata,
                    'similarity_score': similarity_score,
                    'distance_score': float(score),
                    'source': source,
                    'has_context': len(context_docs) > 0
                }
                enhanced_docs.append(doc_info)
            
            logger.info(f"Найдено {len(enhanced_docs)} документов с контекстом")
            return enhanced_docs
            
        except Exception as e:
            logger.error(f"Ошибка при поиске с контекстом: {e}")
            return []

    def _find_context_chunks(self, source: str, main_content: str, window: int) -> List[str]:
        """Находит соседние чанки из того же источника"""
        if not self.vectorstore:
            return []
        
        try:
            # Поиск документов из того же источника
            source_docs = self.vectorstore.similarity_search(f"source:{source}", k=20)
            
            # Простая эвристика для поиска соседних чанков
            context_chunks = []
            for doc in source_docs:
                if (doc.metadata.get('source') == source and 
                    doc.page_content != main_content and 
                    len(context_chunks) < window):
                    context_chunks.append(doc.page_content)
            
            return context_chunks
            
        except Exception as e:
            logger.info(f"Ошибка при поиске контекста: {e}")
            return []

    def _assess_quality(self, similarity_score: float) -> str:
        """Оценивает качество совпадения"""
        if similarity_score > 0.8:
            return "excellent"
        elif similarity_score > 0.6:
            return "good"
        elif similarity_score > 0.4:
            return "fair"
        else:
            return "poor"

    def create_extended_documents_from_json(self, use_extended_parsing: bool = True) -> None:
        """Создает документы с расширенным парсингом JSON массивов
        
        Вместо разбиения на чанки, каждое сообщение из JSON становится отдельным документом
        Учитывает: content, context, reply_to, thread_id
        """
        logger.info("🔧 Создание документов с расширенным парсингом JSON массивов...")
        
        if not os.path.exists(self.documents_path):
            logger.error(f"❌ Директория с документами не найдена: {self.documents_path}")
            return
        
        # Найдем все JSON файлы
        json_files = []
        for root, dirs, files in os.walk(self.documents_path):
            for file in files:
                if file.endswith('.json'):
                    full_path = os.path.join(root, file)
                    json_files.append(full_path)
                    logger.info(f"   📄 Найден JSON файл: {full_path}")
        
        logger.info(f"📚 Найдено {len(json_files)} JSON файлов для расширенного парсинга")
        
        try:
            from langchain.schema import Document
            
            all_documents = []
            
            for file_path in json_files:
                logger.info(f"   📖 Обработка файла: {file_path}")
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Используем расширенный парсер для извлечения всех сообщений
                    if hasattr(self, 'parse_all_messages_from_json_array'):
                        # Импортируем метод из ForumRAG, если доступен
                        messages = self._parse_json_messages_extended(content, file_path)
                    else:
                        # Fallback к простому парсингу
                        messages = self._simple_json_parse(content, file_path)
                    
                    logger.info(f"   ✅ Извлечено {len(messages)} сообщений из {file_path}")
                    
                    # Создаем отдельный документ для каждого сообщения
                    for i, message in enumerate(messages):
                        # Создаем расширенный контент
                        document_content = self._create_extended_content(message)
                        
                        # Создаем метаданные
                        metadata = {
                            'source': file_path,
                            'message_index': i,
                            'character': message.get('character', 'unknown'),
                            'thread_id': message.get('thread_id'),
                            'reply_to': message.get('reply_to'),
                            'context': message.get('context', 'general'),
                            'mood': message.get('mood', 'neutral'),
                            'timestamp': message.get('timestamp', ''),
                            'extraction_method': 'extended_json_parsing'
                        }
                        
                        # Создаем документ
                        doc = Document(
                            page_content=document_content,
                            metadata=metadata
                        )
                        all_documents.append(doc)
                        
                        logger.info(f"      📄 Создан документ {i+1}: {message.get('character')} - {message.get('content', '')[:50]}...")

                except Exception as e:
                    logger.error(f"   ❌ Ошибка обработки файла {file_path}: {e}")
                    continue
            
            if not all_documents:
                logger.warning(f"⚠️ Не удалось создать документы из JSON файлов")
                return
            
            logger.info(f"✅ Создано {len(all_documents)} расширенных документов")
            
            # Создаем векторное хранилище БЕЗ дополнительного разбиения на чанки
            logger.info("🧠 Создание векторного хранилища с расширенными документами...")
            self.vectorstore = FAISS.from_documents(all_documents, self.embeddings)
            
            # Создаем retriever
            self.retriever = self.vectorstore.as_retriever(
                search_type="similarity", 
                search_kwargs={"k": 5}  # Увеличиваем k для большего числа документов
            )
            
            logger.info("✅ RAG с расширенным парсингом успешно настроен")
            
            # Сохраняем в кеш
            self._save_cache()
            
        except Exception as e:
            logger.error(f"❌ Ошибка при создании расширенных документов: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            self.vectorstore = None
            self.retriever = None

    def _parse_json_messages_extended(self, content: str, source_file: str) -> List[Dict]:
        """Расширенный парсинг JSON для извлечения всех сообщений"""
        messages = []
        
        try:
            # Попытка парсинга как JSON
            if content.strip().startswith("{") and content.strip().endswith("}"):
                data = json.loads(content)
                
                # Проверяем, есть ли массив messages
                if "messages" in data and isinstance(data["messages"], list):
                    for i, message in enumerate(data["messages"]):
                        normalized = self._normalize_message(message, i, source_file)
                        messages.append(normalized)
                else:
                    # Одиночное сообщение
                    normalized = self._normalize_message(data, 0, source_file)
                    messages.append(normalized)
                    
            elif content.strip().startswith("[") and content.strip().endswith("]"):
                # Прямой массив
                data = json.loads(content)
                if isinstance(data, list):
                    for i, message in enumerate(data):
                        normalized = self._normalize_message(message, i, source_file)
                        messages.append(normalized)
            
        except json.JSONDecodeError as e:
            logger.info(f"JSON parsing failed for {source_file}: {e}")
            # Fallback к текстовому парсингу
            messages.append({
                'character': 'unknown',
                'content': content,
                'context': 'general',
                'mood': 'neutral',
                'reply_to': None,
                'thread_id': None,
                'timestamp': '',
                'message_index': 0
            })
        
        return messages

    def _simple_json_parse(self, content: str, source_file: str) -> List[Dict]:
        """Простой fallback парсинг JSON"""
        try:
            data = json.loads(content)
            if isinstance(data, dict) and "messages" in data:
                return data["messages"]
            elif isinstance(data, list):
                return data
            else:
                return [data]
        except:
            return [{'content': content, 'character': 'unknown'}]

    def _normalize_message(self, message: Dict, index: int, source_file: str) -> Dict:
        """Нормализует сообщение к стандартному формату"""
        return {
            'character': message.get('character', 'unknown'),
            'content': message.get('content', ''),
            'context': message.get('context', 'general'),
            'mood': message.get('mood', 'neutral'),
            'reply_to': message.get('reply_to'),
            'thread_id': message.get('thread_id'),
            'timestamp': message.get('timestamp', ''),
            'character_type': message.get('character_type', 'unknown'),
            'message_index': index,
            'source_file': source_file
        }

    def _create_extended_content(self, message: Dict) -> str:
        """Создает расширенный контент для лучшего поиска"""
        content = message.get('content', '')
        
        # Добавляем контекстную информацию
        context_parts = []
        
        if message.get('context') and message['context'] != 'general':
            context_parts.append(f"Контекст: {message['context']}")
        
        if message.get('reply_to'):
            context_parts.append(f"Ответ для: {message['reply_to']}")
        
        if message.get('thread_id'):
            context_parts.append(f"Тема обсуждения: {message['thread_id']}")
        
        if message.get('mood') and message['mood'] != 'neutral':
            context_parts.append(f"Настроение: {message['mood']}")
        
        # Объединяем основной контент с контекстной информацией
        if context_parts:
            extended_content = f"{content}\n\n[{' | '.join(context_parts)}]"
        else:
            extended_content = content
        
        return extended_content
