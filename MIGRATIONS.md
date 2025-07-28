# Миграции RAG Manager

## Обзор

Данное приложение использует Alembic для управления миграциями базы данных. Приложение работает с общей PostgreSQL базой данных (порт 5433), которая используется несколькими сервисами (форум, AI менеджер, RAG менеджер).

## Структура таблиц RAG Manager

### 1. `embeddings`

- Таблица для хранения эмбеддингов общего назначения
- Уже существует в БД (создана другими сервисами)

### 2. `message_embeddings`

- Таблица для хранения эмбеддингов сообщений форума
- Уже существует в БД (создана другими сервисами)

### 3. `user_knowledge`

- **НОВАЯ ТАБЛИЦА** - создается миграциями RAG Manager
- Хранит профили пользователей и их характеристики
- Поля:
  - `id` (UUID) - первичный ключ
  - `user_id` (VARCHAR) - уникальный ID пользователя
  - `name` (VARCHAR) - имя пользователя
  - `personality` (TEXT) - описание личности
  - `background` (TEXT) - бэкграунд пользователя
  - `expertise` (JSONB) - области экспертизы
  - `communication_style` (TEXT) - стиль общения
  - `preferences` (JSONB) - предпочтения
  - `file_path` (VARCHAR) - путь к JSON файлу
  - `created_at` (TIMESTAMP) - дата создания
  - `updated_at` (TIMESTAMP) - дата обновления (автоматически)

## Безопасная работа с миграциями

### Принципы безопасности

1. **Изолированность**: Миграции RAG Manager касаются только таблицы `user_knowledge`
2. **Безопасность**: Используется `CREATE TABLE IF NOT EXISTS` для избежания конфликтов
3. **Откат**: Каждая миграция имеет процедуру отката
4. **Проверки**: Скрипт `migrate.py` проверяет подключение к БД перед применением

### Команды для работы с миграциями

```bash
# Проверить текущее состояние
alembic current

# Посмотреть историю
alembic history

# Применить миграции (рекомендуемый способ)
python migrate.py

# Применить миграции напрямую
alembic upgrade head

# Откатить последнюю миграцию
alembic downgrade -1

# Создать новую миграцию
alembic revision -m "Описание изменений"
```

### Файлы миграций

- `alembic.ini` - конфигурация Alembic
- `migrations/env.py` - настройки окружения миграций
- `migrations/versions/` - файлы миграций
- `migrate.py` - безопасный скрипт для применения миграций

## Настройки базы данных

- **URL**: `postgresql+psycopg2://docker:docker@localhost:5433/postgres`
- **Драйвер для миграций**: psycopg2 (синхронный)
- **Драйвер для приложения**: asyncpg (асинхронный)

## Применение в других средах

### Разработка

```bash
python migrate.py
```

### Продакшен

1. Проверить бэкап БД
2. Проверить миграции в тестовой среде
3. Применить миграции:

```bash
python migrate.py
```

### Docker

```bash
docker exec -it rag_manager_container python migrate.py
```

## Мониторинг

После применения миграций проверить:

1. Состояние таблиц:

```sql
SELECT table_name FROM information_schema.tables
WHERE table_name IN ('embeddings', 'message_embeddings', 'user_knowledge');
```

2. Индексы:

```sql
SELECT indexname, tablename FROM pg_indexes
WHERE tablename = 'user_knowledge';
```

3. Функции и триггеры:

```sql
SELECT trigger_name, event_object_table
FROM information_schema.triggers
WHERE event_object_table = 'user_knowledge';
```

## Откат миграций

В случае проблем можно откатить миграции:

```bash
# Откат до предыдущей версии
alembic downgrade -1

# Откат до конкретной ревизии
alembic downgrade <revision_id>

# Полный откат (осторожно!)
alembic downgrade base
```

## Совместимость с другими сервисами

- ✅ Не затрагивает таблицы форума
- ✅ Не затрагивает таблицы AI менеджера
- ✅ Добавляет только новую таблицу `user_knowledge`
- ✅ Использует IF NOT EXISTS для безопасности
- ✅ Все изменения обратимы
