#!/bin/bash
# Запуск V6 сервера (CoT Reasoning + KB Fallback)

cd "/home/segun/CascadeProjects/Перед 0_2"

# Останавливаем старые процессы
pkill -f "web_server_v6.py" 2>/dev/null
pkill -f "web_app_v6" 2>/dev/null
sleep 2

echo "🚀 Запуск V6 сервера (CoT Reasoning + KB Fallback)..."
echo "📍 Адрес: http://172.31.130.149:5006"
echo ""

# Запускаем в фоне
nohup python3 web_server_v6.py > v6_server.log 2>&1 &

sleep 3

# Проверяем запуск
if pgrep -f "web_server_v6.py" > /dev/null; then
    echo "✅ Сервер V6 запущен успешно!"
    echo "📋 Логи: tail -f /home/segun/CascadeProjects/Перед 0_2/v6_server.log"
    echo ""
    echo "🎯 Особенности V6:"
    echo "   - CoT (Chain-of-Thought) - 7 шагов анализа"
    echo "   - Fallback на KB структуру"
    echo "   - Улучшенный Semantic Matching"
    echo "   - KB Override для известных документов"
    echo ""
    echo "📊 Ожидаемая точность: 75-85%"
    echo ""
    echo "🌐 Открыть в браузере: http://172.31.130.149:5006"
else
    echo "❌ Ошибка запуска. Проверьте логи:"
    echo "   cat v6_server.log"
fi
