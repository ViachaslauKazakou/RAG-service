from typing import Dict, List, Any, Optional

from app.schemas import UserKnowledge
from app.services.knowledge_service import KnowledgeService


class OpenAIKnowledgeService(KnowledgeService):
    """
    Сервис для работы с OpenAI Knowledge Base
    """

    def __init__(self):
        super().__init__()
        self.knowledge_base_path = "./openai_knowledge_base"  # Путь к базе знаний OpenAI
        self.embedding_model = "text-embedding-ada-002"  # Модель для создания эмбеддингов
        self.chunk_size = 1000  # Размер чанка для обработки документов
        self.chunk_overlap = 100  # Перекрытие между чанками
        
    async def create_character_prompt(
        self,
        user_knowledge: UserKnowledge,
        question: str,
        context_docs: List[Dict[str, Any]],
        reply_to: Optional[str] = None,
    ) -> str:
        """
        Создание промпта для персонажа на основе пользовательских знаний и контекста

        Args:
            user_knowledge: Знания пользователя
            question: Вопрос для персонажа
            context_docs: Документы контекста
            reply_to: ID сообщения, на которое нужно ответить (если есть)

        Returns:
            Сформированный промпт для персонажа
        """
        # Здесь будет логика создания промпта
        prompt = f"User Knowledge: {user_knowledge}\nQuestion: {question}\nContext: {context_docs}"
        if reply_to:
            prompt += f"\nReplying to: {reply_to}"
        return prompt   