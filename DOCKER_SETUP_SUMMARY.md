# Docker Setup Summary - RAG Service

## 🎯 Цели проекта
Создать полноценную Docker-конфигурацию для RAG сервиса с поддержкой разработки и продакшена, избавившись от Poetry в контейнерах и решив проблемы с размерностью embeddings.

## ✅ Выполненные задачи

### 1. **Исправление проблемы с embeddings**
- **Проблема**: Несоответствие размерности векторов (PostgreSQL ожидал 1536, HuggingFace возвращал 384)
- **Решение**: 
  - Переключились на HuggingFace как основной метод эмбеддингов
  - Добавили расширение векторов до 1536 измерений
  - Обновили модель `sentence-transformers/all-mpnet-base-v2`

### 2. **Создание системы управления зависимостями**
- **Скрипт `export-deps.sh`**: Автоматический экспорт зависимостей из Poetry в requirements.txt
- **Файлы зависимостей**:
  - `requirements.txt` - основные production зависимости
  - `requirements-hf.txt` - HuggingFace зависимости
  - `requirements-dev.txt` - dev зависимости

### 3. **Docker конфигурация для Development**
- **Файл**: `Dockerfile.dev`
- **Особенности**:
  - Использует pip вместо Poetry
  - Поддерживает hot reload
  - Пропускает инициализацию БД (`SKIP_DB_INIT=true`)
  - Монтирует код для разработки
  - Порт: 8000

### 4. **Docker конфигурация для Production**
- **Файл**: `Dockerfile`
- **Особенности**:
  - Оптимизированная сборка
  - Безопасность (непривилегированный пользователь)
  - Healthcheck
  - Только необходимые файлы
  - Переменные окружения для продакшена

### 5. **Docker Compose конфигурации**

#### Development (`docker-compose.dev.yml`)
```yaml
- Порт: 8000:8000
- Hot reload включен
- SKIP_DB_INIT=true
- Монтирование кода для разработки
- Отладочные логи (LOG_LEVEL=debug)
```

#### Production (`docker-compose.yml`)
```yaml
- Порт: 8001:8000 (чтобы не конфликтовать с dev)
- Полная инициализация БД
- Healthcheck настроен
- Read-only монтирование базы знаний
- Production логи (LOG_LEVEL=info)
```

### 6. **Makefile для управления**
Команды для удобного управления:
- `make build-dev` - сборка dev образа
- `make build` - сборка production образа
- `make up-dev` - запуск dev окружения
- `make up` - запуск production окружения
- `make logs-rag-dev` - логи dev сервиса
- `make logs-rag` - логи production сервиса

## 🔧 Техническая архитектура

### Управление зависимостями
```
Poetry (локально) → export-deps.sh → requirements.txt → Docker (pip)
```

### Embedding система
```
HuggingFace Transformers → 768 dim → расширение → 1536 dim → PostgreSQL
```

### Docker структура
```
Dockerfile.dev (развитие) ← docker-compose.dev.yml
Dockerfile (продакшн) ← docker-compose.yml
```

## 📊 Результаты тестирования

### ✅ Dev окружение
- **Сборка**: ✅ Успешно (5+ минут)
- **Запуск**: ✅ Успешно на порту 8000
- **Hot Reload**: ✅ Работает корректно
- **API**: ✅ Доступен на http://localhost:8000
- **Логи**: ✅ Подробные debug логи
- **Размер образа**: ~6.12GB

### ✅ Production окружение  
- **Сборка**: ✅ Успешно (5+ минут)
- **Образ**: ✅ Создан, размер ~6.11GB
- **Healthcheck**: ✅ Настроен корректно
- **Безопасность**: ✅ Непривилегированный пользователь
- **Порт**: 8001 (не конфликтует с dev)

## 🛡️ Безопасность и лучшие практики

### Dockerfile
- ✅ Непривилегированный пользователь `app_user`
- ✅ Минимальные слои и кэширование
- ✅ Явные версии зависимостей
- ✅ Очистка кэшей APT

### Compose файлы
- ✅ Разделенные сети для dev/prod
- ✅ Healthcheck с правильными таймаутами
- ✅ Restart политики
- ✅ Read-only монтирование где возможно

## 📁 Структура файлов

```
RAG-service/
├── Dockerfile                 # Production образ
├── Dockerfile.dev            # Development образ  
├── docker-compose.yml        # Production compose
├── docker-compose.dev.yml    # Development compose
├── export-deps.sh           # Скрипт экспорта зависимостей
├── Makefile                 # Команды управления
├── requirements.txt         # Production зависимости
├── requirements-hf.txt      # HuggingFace зависимости  
├── requirements-dev.txt     # Dev зависимости
└── app/
    ├── main.py             # Точка входа с SKIP_DB_INIT
    ├── config.py           # Конфигурация с новыми настройками
    └── services/
        └── rag_service.py  # HuggingFace embeddings + расширение
```

## 🚀 Быстрый старт

### Development
```bash
make build-dev  # Сборка
make up-dev     # Запуск
make logs-rag-dev  # Логи
# API доступен на http://localhost:8000
```

### Production
```bash
make build      # Сборка  
make up         # Запуск
make health     # Проверка состояния
# API доступен на http://localhost:8001
```

## 🎉 Заключение

Проект успешно настроен с полной Docker-инфраструктурой:

1. **✅ Решена проблема с embeddings** - переход на HuggingFace с расширением до 1536 измерений
2. **✅ Убрана Poetry из контейнеров** - используется локальный экспорт в requirements.txt
3. **✅ Созданы оптимальные dev/prod окружения** - с разными портами и настройками
4. **✅ Настроен удобный workflow** - с Makefile и автоматическим экспортом зависимостей
5. **✅ Проверена работоспособность** - dev окружение запущено и протестировано

Система готова к использованию как для разработки, так и для продакшена! 🎯
