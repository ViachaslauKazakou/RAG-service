#!/bin/bash
# Простой скрипт для экспорта зависимостей из Poetry окружения
# Используется перед сборкой Docker образа

set -e

echo "🔧 Экспорт зависимостей из Poetry окружения..."

# Проверяем, что Poetry установлен
if ! command -v poetry &> /dev/null; then
    echo "❌ Poetry не найден. Установите Poetry: https://python-poetry.org/docs/#installation"
    exit 1
fi

# Проверяем, что pyproject.toml существует
if [ ! -f "pyproject.toml" ]; then
    echo "❌ pyproject.toml не найден в текущей директории"
    exit 1
fi

echo "📋 Версия Poetry: $(poetry --version)"


# Экспортируем зависимости через pip freeze
echo "📦 Экспортируем зависимости через pip freeze..."
poetry run pip freeze > requirements_raw.txt

# Фильтруем зависимости - удаляем локальные проекты и dev пакеты
echo "✂️  Фильтруем production зависимости..."
grep -v -E "^-e|^(rag-manager|black|flake8|isort|pytest|mypy|mccabe|pycodestyle|pyflakes)" requirements_raw.txt > requirements.txt

# Добавляем shared-models через HTTPS (если его нет)
if ! grep -q "shared-models" requirements.txt; then
    echo "shared-models @ git+https://github.com/ViachaslauKazakou/shared-models.git@v0.1.2" >> requirements.txt
fi

# Создаем файл с HuggingFace зависимостями
echo "🤗 Создаем requirements-hf.txt..."
cat > requirements-hf.txt << EOF
# HuggingFace зависимости для RAG Service
torch --index-url https://download.pytorch.org/whl/cpu
sentence-transformers
numpy
EOF

# Создаем dev файл
echo "🛠️ Создаем requirements-dev.txt..."
cat > requirements-dev.txt << EOF
# Dev dependencies - install locally with: poetry install --with dev
black==23.12.1
flake8==6.1.0
isort==5.13.2
pytest==7.4.4
pytest-asyncio==0.21.2
EOF

# Очищаем временные файлы
rm -f requirements_raw.txt

echo "✅ Файлы зависимостей созданы:"
echo "  - requirements.txt ($(wc -l < requirements.txt) пакетов)"
echo "  - requirements-hf.txt (HuggingFace зависимости)"
echo "  - requirements-dev.txt (dev зависимости)"

echo ""
echo "📊 Размеры файлов:"
ls -lh requirements*.txt

echo ""
echo "🚀 Готово! Теперь можно собирать Docker образ."