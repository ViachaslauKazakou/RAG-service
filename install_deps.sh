#!/bin/bash

# Скрипт для установки всех зависимостей RAG Service

echo "🚀 Установка зависимостей RAG Service..."

# Установка основных зависимостей через Poetry
echo "📦 Установка основных зависимостей через Poetry..."
poetry install

# Установка HuggingFace зависимостей через pip
echo "🤗 Установка HuggingFace зависимостей через pip..."
poetry run pip install -r requirements-hf.txt

# Исправление совместимости NumPy с PyTorch
echo "🔧 Исправление совместимости NumPy с PyTorch..."
poetry run pip install "numpy<2" --force-reinstall

echo "✅ Установка завершена!"
echo "🎯 Теперь можно запустить сервис: poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
