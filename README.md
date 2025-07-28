# RAG Manager Service

FastAPI сервис для обработки RAG запросов в AI Forum.

## Возможности

- Обработка запросов с контекстом пользователей и топиков
- Поиск по векторной базе данных (pgvector)
- Загрузка знаний пользователей из JSON файлов
- REST API для интеграции с основным форумом

## API Endpoints

- `POST /rag/process` - Обработка RAG запроса
- `GET /health` - Проверка здоровья сервиса
- `GET /users/{user_id}/knowledge` - Получение знаний пользователя

## Запуск

```bash
poetry install
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8080
```
