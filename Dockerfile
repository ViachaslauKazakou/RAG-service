# Multi-stage build для оптимизации
FROM python:3.12-bullseye as builder

# Установка Poetry для экспорта зависимостей
RUN pip install poetry==2.1.3 poetry-plugin-export

WORKDIR /app

# Копируем файлы Poetry
COPY rag_manager/pyproject.toml rag_manager/poetry.lock* ./

# Экспортируем зависимости в requirements.txt
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes --only=main

# Production stage
FROM python:3.11-slim

# Копируем requirements.txt из builder
COPY --from=builder /app/requirements.txt /tmp/requirements.txt

# Устанавливаем зависимости через pip
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

WORKDIR /app

# Копируем код приложения
COPY rag_manager/app ./app
COPY rag_manager/forum_knowledge_base ./forum_knowledge_base

# Создаем пользователя для безопасности
RUN useradd --create-home --shell /bin/bash --system app_user && \
    chown -R app_user:app_user /app

USER app_user

# Экспортируем порт
EXPOSE 8080

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8080/health')" || exit 1

# Запуск приложения
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
