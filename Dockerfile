# Dockerfile для RAG Service (без Poetry в контейнере)
FROM python:3.12-bullseye

# Устанавливаем runtime зависимости
RUN apt-get update && apt-get install -y \
    gcc\
    g++ \
    make \
    curl \
    postgresql-client \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /app

# Копируем файлы с зависимостями (сгенерированы локально)
COPY requirements.txt requirements-hf.txt ./

# Устанавливаем основные Python зависимости
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Устанавливаем HuggingFace зависимости
RUN pip install --no-cache-dir -r requirements-hf.txt

# Копируем код приложения
COPY app/ ./app/
COPY forum_knowledge_base/ ./forum_knowledge_base/

# Создаем пользователя для безопасности
RUN useradd --create-home --shell /bin/bash --system app_user && \
    mkdir -p /app/logs /tmp/hf_cache && \
    chown -R app_user:app_user /app && \
    chown -R app_user:app_user /tmp/hf_cache

USER app_user

# Переменные окружения
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    POSTGRES_URL=postgresql+asyncpg://docker:docker@postgres:5432/postgres \
    AI_MANAGER_URL=http://ai_manager:8080

# Экспортируем порт
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Запуск приложения
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
