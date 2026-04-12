#!/bin/bash
# Запуск V6 сервера из корневой директории

# Переходим в папку с v6
cd "$(dirname "$0")/../v6"

# Останавливаем старые процессы
pkill -f "web_server_v6.py" 2>/dev/null
sleep 1

echo "🚀 Запуск V6 сервера (CoT Reasoning + KB Fallback)..."
echo "📍 Адрес: http://172.31.130.149:5006"

# Запускаем в фоне, логи сохраняем в корне
nohup python3 web_server_v6.py > ../logs/v6_server.log 2>&1 &

sleep 2

if pgrep -f "web_server_v6.py" > /dev/null; then
    echo "✅ Сервер V6 запущен успешно!"
    echo "📋 Логи: tail -f ../logs/v6_server.log"
else
    echo "❌ Ошибка запуска. Проверьте v6_server.log"
fi
