"""
Тесты для RAG Manager сервиса
"""
import asyncio
import json

import pytest
from httpx import AsyncClient

from app.database import get_db, init_db
from app.main import app
from app.services.knowledge_service import KnowledgeService


@pytest.fixture(scope="session")
def event_loop():
    """Создает event loop для всей сессии тестирования"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def setup_database():
    """Настройка тестовой базы данных"""
    await init_db()
    return True


@pytest.fixture
async def client(setup_database):
    """HTTP клиент для тестирования"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def knowledge_service():
    """Сервис знаний для тестирования"""
    service = KnowledgeService()
    await service.warm_cache()
    return service


class TestHealthEndpoints:
    """Тесты health проверок"""
    
    async def test_health_check(self, client):
        """Тест проверки здоровья сервиса"""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "database_status" in data
        assert "uptime" in data
    
    async def test_ready_check(self, client):
        """Тест проверки готовности сервиса"""
        response = await client.get("/ready")
        assert response.status_code in [200, 503]  # Может быть не готов в тестах
        
        data = response.json()
        assert "status" in data
    
    async def test_root_endpoint(self, client):
        """Тест корневого endpoint"""
        response = await client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["service"] == "RAG Manager"
        assert "version" in data


class TestRAGEndpoints:
    """Тесты RAG обработки"""
    
    async def test_rag_process_valid_request(self, client):
        """Тест валидного RAG запроса"""
        request_data = {
            "topic": "Machine Learning Fundamentals",
            "user_id": "alice_researcher",
            "question": "What are the key differences between supervised and unsupervised learning?",
            "reply_to": None
        }
        
        response = await client.post("/api/v1/rag/process", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "enhanced_prompt" in data
        assert "context_items" in data
        assert "user_persona" in data
        assert "processing_time" in data
        assert "timestamp" in data
    
    async def test_rag_process_missing_user(self, client):
        """Тест RAG запроса с несуществующим пользователем"""
        request_data = {
            "topic": "Test Topic",
            "user_id": "nonexistent_user",
            "question": "Test question",
            "reply_to": None
        }
        
        response = await client.post("/api/v1/rag/process", json=request_data)
        # Должен обработать даже с неизвестным пользователем
        assert response.status_code in [200, 404]
    
    async def test_rag_process_invalid_request(self, client):
        """Тест невалидного RAG запроса"""
        request_data = {
            "topic": "",  # Пустой топик
            "user_id": "",  # Пустой user_id
            "question": "",  # Пустой вопрос
        }
        
        response = await client.post("/api/v1/rag/process", json=request_data)
        assert response.status_code == 422  # Validation error


class TestUserEndpoints:
    """Тесты пользовательских endpoint"""
    
    async def test_list_users(self, client):
        """Тест получения списка пользователей"""
        response = await client.get("/api/v1/users")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        # Должны быть наши тестовые пользователи
        expected_users = ["alice_researcher", "bob_developer", "charlie_student"]
        for user in expected_users:
            assert user in data
    
    async def test_get_user_knowledge(self, client):
        """Тест получения знаний пользователя"""
        response = await client.get("/api/v1/users/alice_researcher/knowledge")
        assert response.status_code == 200
        
        data = response.json()
        assert data["user_id"] == "alice_researcher"
        assert "role" in data
        assert "expertise" in data
        assert "experience_level" in data
    
    async def test_get_nonexistent_user_knowledge(self, client):
        """Тест получения знаний несуществующего пользователя"""
        response = await client.get("/api/v1/users/nonexistent/knowledge")
        assert response.status_code == 404


class TestUtilityEndpoints:
    """Тесты служебных endpoint"""
    
    async def test_clear_cache(self, client):
        """Тест очистки кэша"""
        response = await client.post("/api/v1/cache/clear")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
    
    async def test_get_stats(self, client):
        """Тест получения статистики"""
        response = await client.get("/api/v1/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "uptime_seconds" in data
        assert "database_stats" in data
        assert "available_users" in data
        assert "user_list" in data


class TestKnowledgeService:
    """Тесты сервиса знаний"""
    
    async def test_load_user_knowledge(self, knowledge_service):
        """Тест загрузки знаний пользователя"""
        knowledge = await knowledge_service.load_user_knowledge("alice_researcher")
        
        assert knowledge is not None
        assert knowledge.user_id == "alice_researcher"
        assert knowledge.role == "AI Research Scientist"
        assert "machine learning" in knowledge.expertise
    
    async def test_get_all_user_ids(self, knowledge_service):
        """Тест получения всех ID пользователей"""
        user_ids = await knowledge_service.get_all_user_ids()
        
        assert isinstance(user_ids, list)
        assert len(user_ids) >= 3  # Как минимум наши тестовые пользователи
        assert "alice_researcher" in user_ids
        assert "bob_developer" in user_ids
        assert "charlie_student" in user_ids
    
    async def test_generate_user_prompt(self, knowledge_service):
        """Тест генерации пользовательского промпта"""
        knowledge = await knowledge_service.load_user_knowledge("alice_researcher")
        prompt = knowledge_service.generate_user_prompt(
            knowledge, 
            "What is machine learning?",
            "Machine Learning Basics"
        )
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "AI Research Scientist" in prompt
        assert "machine learning" in prompt.lower()


class TestErrorHandling:
    """Тесты обработки ошибок"""
    
    async def test_invalid_json(self, client):
        """Тест невалидного JSON"""
        response = await client.post(
            "/api/v1/rag/process",
            content="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    async def test_missing_required_fields(self, client):
        """Тест отсутствующих обязательных полей"""
        request_data = {
            "topic": "Test Topic"
            # Отсутствуют user_id и question
        }
        
        response = await client.post("/api/v1/rag/process", json=request_data)
        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
