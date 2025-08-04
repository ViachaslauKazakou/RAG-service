# RAG Service Docker Deployment

Этот документ описывает, как развернуть и использовать RAG Service с помощью Docker.

## Быстрый старт

### Предварительные требования

- Docker 20.10+
- Docker Compose 2.0+
- Make (опционально, для удобства)

### Запуск для разработки

```bash
# Клонируйте репозиторий
git clone <repository-url>
cd RAG-service

# Скопируйте переменные окружения
cp .env.example .env

# Запустите сервисы для разработки
make up-dev
# или
docker-compose -f docker-compose.dev.yml up -d

# Запустите миграции
make migrate-dev

# Проверьте статус
make health
```

### Запуск для продакшн

```bash
# Соберите образы
make build

# Запустите сервисы
make up

# Запустите миграции
make migrate

# Проверьте статус
make health
```

## Структура проекта

```
RAG-service/
├── app/                    # Код приложения
├── migrations/             # Миграции базы данных
├── forum_knowledge_base/   # База знаний
├── docker/                 # Docker конфигурации
├── logs/                   # Логи (для разработки)
├── Dockerfile             # Продакшн образ
├── Dockerfile.dev         # Образ для разработки
├── docker-compose.yml     # Продакшн конфигурация
├── docker-compose.dev.yml # Конфигурация для разработки
├── Makefile              # Команды для управления
└── .env.example          # Пример переменных окружения
```

## Доступные сервисы

### RAG Service
- **URL**: http://localhost:8000
- **Описание**: Основной API для RAG функций
- **Endpoints**:
  - `GET /health` - Проверка здоровья
  - `GET /users` - Список пользователей
  - `POST /rag/process` - Обработка RAG запросов

### PostgreSQL + pgvector
- **Host**: localhost:5433
- **Database**: postgres
- **User**: docker
- **Password**: docker

### AI Manager (в dev режиме)
- **URL**: http://localhost:8002
- **Ollama**: http://localhost:11434

## Команды Make

```bash
# Основные команды
make help           # Показать справку
make build          # Собрать образы
make up             # Запустить продакшн
make up-dev         # Запустить разработку
make down           # Остановить сервисы
make restart        # Перезапустить

# Логи и мониторинг
make logs           # Показать все логи
make logs-rag       # Логи RAG сервиса
make health         # Проверить состояние

# Разработка
make shell-dev      # Войти в контейнер
make test           # Запустить тесты
make lint           # Проверить код
make format         # Отформатировать код

# База данных
make migrate        # Запустить миграции
make backup-db      # Создать бэкап
make restore-db     # Восстановить бэкап

# Очистка
make clean          # Очистить данные
make clean-images   # Удалить образы
```

## Конфигурация

### Переменные окружения

Основные переменные в `.env`:

```bash
# База данных
POSTGRES_URL=postgresql+asyncpg://docker:docker@localhost:5433/postgres

# AI Manager
AI_MANAGER_URL=http://localhost:8002

# Приложение
LOG_LEVEL=info
ENV=production
```

### Volumes

- `postgres_data` - Данные PostgreSQL
- `rag_service_logs` - Логи RAG сервиса
- `ollama_models` - Модели Ollama

## Мониторинг и отладка

### Проверка состояния

```bash
# Статус контейнеров
docker-compose ps

# Логи в реальном времени
make logs

# Проверка health endpoints
curl http://localhost:8000/health
```

### Отладка

```bash
# Войти в контейнер
make shell-dev

# Посмотреть логи конкретного сервиса
docker-compose logs rag_service

# Перезапустить сервис
docker-compose restart rag_service
```

## Разработка

### Hot Reload

В режиме разработки (`make up-dev`) код автоматически перезагружается при изменениях.

### Тестирование

```bash
# Запустить все тесты
make test

# Запустить конкретный тест
docker-compose -f docker-compose.dev.yml exec rag_service poetry run pytest tests/test_specific.py
```

### Работа с базой данных

```bash
# Создать миграцию
docker-compose -f docker-compose.dev.yml exec rag_service poetry run alembic revision --autogenerate -m "Description"

# Применить миграции
make migrate-dev

# Откатить миграцию
docker-compose -f docker-compose.dev.yml exec rag_service poetry run alembic downgrade -1
```

## Продакшн

### Настройки безопасности

1. Измените пароли в `.env`
2. Настройте SSL/TLS
3. Ограничьте доступ к портам
4. Настройте мониторинг

### Масштабирование

```bash
# Запустить несколько экземпляров RAG сервиса
docker-compose up -d --scale rag_service=3
```

### Бэкапы

```bash
# Автоматический бэкап
make backup-db

# Восстановление
make restore-db FILE=backup_20240729_120000.sql
```

## Устранение неполадок

### Проблемы с зависимостями

```bash
# Пересобрать образы
docker-compose build --no-cache

# Очистить все и начать заново
make clean
make build
make up
```

### Проблемы с портами

Проверьте, что порты 8000, 5433, 8002, 11434 не заняты другими приложениями.

### Проблемы с памятью

Убедитесь, что у Docker достаточно памяти (рекомендуется минимум 4GB для полного стека).

## Дополнительная информация

- [Документация по API](../README.md)
- [Миграции базы данных](../MIGRATIONS.md)
- [Troubleshooting](../docs/troubleshooting.md)

## Отладка в VS Code

### Настройка Docker Debug

Проект уже настроен для отладки в Docker контейнере:

```bash
# Собрать dev контейнер с поддержкой отладки
docker-compose -f docker-compose.dev.yml build

# Запустить с отладкой (debugpy будет ждать подключения)
docker-compose -f docker-compose.dev.yml up -d

# Посмотреть логи
docker-compose -f docker-compose.dev.yml logs -f rag_service

# Остановить
docker-compose -f docker-compose.dev.yml down

# Войти в контейнер
docker exec -it rag_service_dev /bin/bash
```

### Способы отладки

1. **Dev Containers** (рекомендуется):
   - `Cmd+Shift+P` → `Dev Containers: Reopen in Container`
   - Установите breakpoints и нажмите F5

2. **Attach to Container**:
   - Запустите контейнер с отладкой
   - В VS Code: Debug panel → `Python: Attach to Container`
   - Порт отладки: 5678

3. **Remote Debugging**:
   - Контейнер автоматически ждет подключения отладчика
   - Используйте конфигурацию `Python: Attach to Container`

### Устранение проблем отладки

Если видите предупреждения debugpy:
- `frozen modules` - уже исправлено флагом `-Xfrozen_modules=off`
- `file validation` - отключено переменной `PYDEVD_DISABLE_FILE_VALIDATION=1`