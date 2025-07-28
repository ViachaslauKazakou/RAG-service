"""
Конфигурация для pytest
"""
import os
import sys

# Добавляем путь к app в Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

# Настройки для тестирования
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/ai_forum_test"
