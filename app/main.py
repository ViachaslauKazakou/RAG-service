"""
Основное FastAPI приложение для RAG менеджера
"""
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.default import router
from app.api.openai import router as openai_router
from app.config import get_settings
from app.database import init_db
from app.services.knowledge_service import KnowledgeService

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

settings = get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управление жизненным циклом приложения
    """
    # Запуск
    logger.info("Starting RAG Manager service...")

    try:
        # Инициализация БД (можно пропустить в dev режиме)
        if settings.skip_db_init:
            logger.info("Skipping database initialization (SKIP_DB_INIT=true)")
        else:
            logger.info("Initializing database...")
            await init_db()

        # Инициализация кэша знаний
        # logger.info("Initializing knowledge cache...")
        # knowledge_service = KnowledgeService()
        # await knowledge_service.warm_cache()

        logger.info("RAG Manager service started successfully")

    except Exception as e:
        logger.error(f"Failed to start RAG Manager service: {e}")
        raise

    yield

    # Завершение
    logger.info("Shutting down RAG Manager service...")


# Создание приложения
app = FastAPI(
    title="RAG Manager",
    description="Микросервис для обработки RAG запросов в AI форуме",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware для логирования запросов
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Логирование HTTP запросов
    """
    start_time = time.time()

    logger.info(f"Request: {request.method} {request.url}")

    response = await call_next(request)

    process_time = time.time() - start_time
    logger.info(f"Response: {response.status_code} in {process_time:.3f}s")

    return response


# Обработчик ошибок
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Глобальный обработчик ошибок
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error_type": type(exc).__name__, "path": str(request.url)},
    )


# Подключение роутов
app.include_router(router, prefix="/api/v1")
app.include_router(openai_router)


# Корневой endpoint
@app.get("/")
async def root():
    """
    Корневой endpoint
    """
    return {
        "service": "RAG Manager",
        "version": "1.0.0",
        "status": "running (dev mode)",
        "docs": "/docs",
        "health": "/api/v1/health",
    }


# Endpoint для проверки готовности
@app.get("/ready")
async def ready():
    """
    Проверка готовности сервиса
    """
    try:
        # Простая проверка готовности
        knowledge_service = KnowledgeService()
        user_ids = await knowledge_service.get_all_user_ids()

        return {"status": "ready", "available_users": len(user_ids)}

    except Exception as e:
        logger.error(f"Service not ready: {e}")
        return JSONResponse(status_code=503, content={"status": "not ready", "error": str(e)})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True, log_level="info")
