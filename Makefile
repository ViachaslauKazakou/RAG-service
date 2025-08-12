# Makefile для RAG Service
.PHONY: help build up down dev logs clean migrate test lint format

# Переменные
COMPOSE_FILE = docker-compose.yml
DEV_COMPOSE_FILE = docker-compose.dev.yml
SERVICE_NAME = rag_service

help: ## Показать справку
	@echo "RAG Service Docker Management"
	@echo "============================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

export-deps: ## Экспортировать зависимости из Poetry в requirements.txt
	@echo "🔧 Экспортируем зависимости..."
	./export-deps.sh

build: export-deps ## Собрать Docker образы (с экспортом зависимостей)
	docker-compose -f $(COMPOSE_FILE) build

build-dev: export-deps ## Собрать Docker образы для разработки (с экспортом зависимостей)
	docker-compose -f $(DEV_COMPOSE_FILE) build

up: ## Запустить все сервисы
	docker-compose -f $(COMPOSE_FILE) up -d
	@echo "Сервисы запущены:"
	@echo "- RAG Service: http://localhost:8001"

up-dev: ## Запустить сервисы для разработки
	docker-compose -f $(DEV_COMPOSE_FILE) up -d
	@echo "Сервисы разработки запущены:"
	@echo "- RAG Service: http://localhost:8001 (с hot reload)"
	@echo "- AI Manager: http://localhost:8002"
	@echo "- PostgreSQL: localhost:5433"

down: ## Остановить все сервисы
	docker-compose -f $(COMPOSE_FILE) down

down-dev: ## Остановить сервисы разработки
	docker-compose -f $(DEV_COMPOSE_FILE) down

stop: ## Остановить все сервисы
	docker-compose -f $(COMPOSE_FILE) stop

stop-dev: ## Остановить сервисы разработки
	docker-compose -f $(DEV_COMPOSE_FILE) stop

restart: down up ## Перезапустить сервисы

restart-dev: down-dev up-dev ## Перезапустить сервисы разработки

logs: ## Показать логи всех сервисов
	docker-compose -f $(COMPOSE_FILE) logs -f

logs-dev: ## Показать логи сервисов разработки
	docker-compose -f $(DEV_COMPOSE_FILE) logs -f

logs-rag: ## Показать логи RAG сервиса
	docker-compose -f $(COMPOSE_FILE) logs -f $(SERVICE_NAME)

logs-rag-dev: ## Показать логи RAG сервиса в разработке
	docker-compose -f $(DEV_COMPOSE_FILE) logs -f $(SERVICE_NAME)

shell: ## Войти в контейнер RAG сервиса
	docker-compose -f $(COMPOSE_FILE) exec $(SERVICE_NAME) /bin/bash

shell-dev: ## Войти в контейнер RAG сервиса в разработке
	docker-compose -f $(DEV_COMPOSE_FILE) exec $(SERVICE_NAME) /bin/bash

migrate: ## Запустить миграции базы данных
	docker-compose -f $(COMPOSE_FILE) exec $(SERVICE_NAME) python migrate.py

migrate-dev: ## Запустить миграции в разработке
	docker-compose -f $(DEV_COMPOSE_FILE) exec $(SERVICE_NAME) python migrate.py

test: ## Запустить тесты
	docker-compose -f $(DEV_COMPOSE_FILE) exec $(SERVICE_NAME) pytest

lint: ## Проверить код линтером
	docker-compose -f $(DEV_COMPOSE_FILE) exec $(SERVICE_NAME) flake8 app/

format: ## Отформатировать код
	docker-compose -f $(DEV_COMPOSE_FILE) exec $(SERVICE_NAME) black app/
	docker-compose -f $(DEV_COMPOSE_FILE) exec $(SERVICE_NAME) isort app/

clean: ## Очистить Docker данные
	docker-compose -f $(COMPOSE_FILE) down -v
	docker-compose -f $(DEV_COMPOSE_FILE) down -v
	docker system prune -f

clean-images: ## Удалить все Docker образы проекта
	docker-compose -f $(COMPOSE_FILE) down --rmi all
	docker-compose -f $(DEV_COMPOSE_FILE) down --rmi all

health: ## Проверить состояние сервисов
	@echo "Проверка состояния сервисов..."
	@curl -f http://localhost:8000/health || echo "❌ RAG Service недоступен"
	@curl -f http://localhost:8002/health || echo "❌ AI Manager недоступен"
	@docker-compose -f $(COMPOSE_FILE) ps

# Команды для локальной разработки без Docker
install-local: ## Установить зависимости локально (с poetry)
	poetry install
	./install_hf_deps.sh

install-pip: ## Установить зависимости через pip (альтернатива)
	./export-deps.sh
	pip install -r requirements.txt
	pip install -r requirements-hf.txt
	pip install -r requirements-dev.txt

run-local: ## Запустить сервис локально
	python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Производственные команды
deploy: export-deps build up migrate ## Полный деплой в продакшн (с экспортом зависимостей)

backup-db: ## Создать бэкап базы данных
	docker-compose -f $(COMPOSE_FILE) exec postgres pg_dump -U docker postgres > backup_$(shell date +%Y%m%d_%H%M%S).sql

restore-db: ## Восстановить базу данных (укажите файл: make restore-db FILE=backup.sql)
	docker-compose -f $(COMPOSE_FILE) exec -T postgres psql -U docker postgres < $(FILE)
