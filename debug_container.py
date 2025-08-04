#!/usr/bin/env python3
"""
Вспомогательный скрипт для отладки в контейнере
"""
import subprocess
import sys
import os
import time

def check_container():
    """Проверяет, запущен ли контейнер для отладки"""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=rag_service_dev", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=True
        )
        return "rag_service_dev" in result.stdout
    except subprocess.CalledProcessError:
        return False

def start_container():
    """Запускает контейнер для отладки"""
    print("🐳 Запускаем Docker контейнер для отладки...")
    try:
        subprocess.run(
            ["docker-compose", "-f", "docker-compose.dev.yml", "up", "-d"],
            check=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        print("✅ Контейнер запущен!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка запуска контейнера: {e}")
        return False

def wait_for_debugger():
    """Ждет готовности отладчика"""
    print("⏳ Ждем готовности отладчика...")
    import socket
    for _ in range(30):  # Ждем до 30 секунд
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', 5678))
            sock.close()
            if result == 0:
                print("🎯 Отладчик готов!")
                return True
        except:
            pass
        time.sleep(1)
    print("⚠️ Отладчик не готов, но продолжаем...")
    return False

def main():
    print("🚀 Запуск отладки RAG Service в Docker")
    
    # Проверяем контейнер
    if not check_container():
        if not start_container():
            sys.exit(1)
    else:
        print("✅ Контейнер уже запущен")
    
    # Ждем готовности отладчика
    wait_for_debugger()
    
    print("\n📋 Инструкции:")
    print("1. В VS Code перейдите в Debug Panel (Cmd+Shift+D)")
    print("2. Выберите конфигурацию 'Python: Attach to Container'")
    print("3. Нажмите F5 или кнопку ▶️")
    print("4. Установите breakpoints в коде")
    print("5. Тестируйте API: http://localhost:8001")
    print("\n🔗 Полезные ссылки:")
    print("   API: http://localhost:8001")
    print("   Health: http://localhost:8001/health")
    print("   Debug port: localhost:5678")
    
if __name__ == "__main__":
    main()
