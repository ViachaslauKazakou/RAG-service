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

### Установка зависимостей

Используйте скрипт для автоматической установки всех зависимостей:

```bash
./install_deps.sh
```

Или вручную:

```bash
# Основные зависимости через Poetry
poetry install

# HuggingFace зависимости через pip в Poetry environment
poetry run pip install -r requirements-hf.txt
```

### Запуск сервиса

```bash
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Отладка

Для отладки в VS Code доступны готовые конфигурации:
- `Python Debugger: FastAPI Local` - локальная отладка
- `Python Debugger: Container Attach` - подключение к контейнеру

```bash
# Запуск в development режиме с отладкой
docker-compose -f docker-compose.dev.yml up --build
```

```
docker exec -it forum_postgres psql -U docker -d postgres -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

```
docker network ls | grep ai_network
```

```
sleep 5 && docker logs forum_postgres --tail 10
```

```
docker volume rm rag-service_postgres_data
```

```
docker exec -it forum_postgres cat /var/lib/postgresql/data/pg_hba.conf | tail -5
```

```
psql "postgresql://docker:docker@localhost:5433/postgres" -c "SELECT 1 as external_test;"
```
