#!/bin/bash
# Очистка проекта - удаление временных файлов

cd "/home/segun/CascadeProjects/Перед 0_2"

echo "🧹 Очистка временных файлов..."

# Удаляем __pycache__
rm -rf __pycache__ 2>/dev/null
rm -rf .kilo/worktrees/playful-flower/__pycache__ 2>/dev/null

# Удаляем старые логи в корне
rm -f *.log 2>/dev/null
rm -f benchmark_run.log 2>/dev/null

# Удаляем временные файлы
rm -f changes_summary.txt 2>/dev/null
rm -f temp_*.txt 2>/dev/null
rm -f failed_*.json 2>/dev/null
rm -f parse_test_out.txt 2>/dev/null

# Удаляем старые скрипты запуска (оставляем только start_v6.sh)
rm -f start_server.sh 2>/dev/null
rm -f start_web.sh 2>/dev/null
rm -f restart_v6.sh 2>/dev/null

# Удаляем uploads (временные файлы)
rm -rf uploads/* 2>/dev/null

echo "✅ Очистка завершена!"
echo ""
echo "📂 Текущая структура:"
echo "   web_app_v6_cot_fallback.py - ГЛАВНЫЙ ФАЙЛ"
echo "   web_server_v6.py           - Сервер"
echo "   start_v6.sh                - Запуск"
echo "   knowledge_base.json        - База знаний"
echo "   README_V6.md               - Документация"
echo ""
echo "📦 Архив в archive/"
echo "   old_versions/ - старые версии"
echo "   tests/        - тесты"
echo "   scripts/      - скрипты"
echo "   docs/         - документация"
echo "   logs/         - логи"
echo ""
echo "🚀 Для запуска: bash start_v6.sh"
