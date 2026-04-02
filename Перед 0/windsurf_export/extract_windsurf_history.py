#!/usr/bin/env python3
"""
Скрипт для извлечения истории переписки из Windsurf (VS Code extension).
Сохраняет историю в markdown и JSON файлы.

Запуск:
  python extract_windsurf_history.py
  python extract_windsurf_history.py --output ./my_history
"""

import os
import sys
import json
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime

# ──────────────────────────────────────────────
# 1. Найти базу данных Windsurf
# ──────────────────────────────────────────────

def find_windsurf_db() -> list[Path]:
    """Ищет SQLite базы данных Windsurf на типичных путях."""
    candidates = []

    if sys.platform == "win32":
        base_paths = [
            Path(os.environ.get("APPDATA", "")) / "Windsurf" / "User",
            Path(os.environ.get("APPDATA", "")) / "Code" / "User",  # если через VS Code
            Path(os.environ.get("LOCALAPPDATA", "")) / "Windsurf",
        ]
    elif sys.platform == "darwin":
        base_paths = [
            Path.home() / "Library" / "Application Support" / "Windsurf" / "User",
            Path.home() / "Library" / "Application Support" / "Windsurf",
        ]
    else:  # Linux
        base_paths = [
            Path.home() / ".config" / "Windsurf" / "User",
            Path.home() / ".config" / "Windsurf",
            Path.home() / ".windsurf",
        ]

    db_names = [
        "workspaceStorage",
        "globalStorage",
        "state.vscdb",
        "backup.vscdb",
    ]

    for base in base_paths:
        if not base.exists():
            continue
        # Рекурсивно ищем .vscdb файлы
        for db_file in base.rglob("*.vscdb"):
            candidates.append(db_file)
        # Также проверяем workspaceStorage папки
        ws = base / "workspaceStorage"
        if ws.exists():
            for db_file in ws.rglob("state.vscdb"):
                candidates.append(db_file)

    return list(set(candidates))


# ──────────────────────────────────────────────
# 2. Читать данные из БД
# ──────────────────────────────────────────────

WINDSURF_KEYS = [
    "cascade",
    "windsurf",
    "codeium",
    "chat",
    "conversation",
    "history",
    "messages",
    "aiChat",
]

def extract_from_db(db_path: Path) -> list[dict]:
    """Извлекает записи Windsurf/Cascade из SQLite БД."""
    results = []
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # VS Code хранит всё в таблице ItemTable
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        for table in tables:
            try:
                cursor.execute(f"SELECT key, value FROM [{table}]")
                rows = cursor.fetchall()
                for key, value in rows:
                    key_lower = str(key).lower()
                    if any(k in key_lower for k in WINDSURF_KEYS):
                        results.append({
                            "db": str(db_path),
                            "table": table,
                            "key": key,
                            "raw_value": value,
                        })
            except sqlite3.OperationalError:
                continue

        conn.close()
    except Exception as e:
        print(f"  ⚠️  Ошибка при чтении {db_path}: {e}")
    return results


# ──────────────────────────────────────────────
# 3. Парсить сообщения
# ──────────────────────────────────────────────

def parse_value(raw_value) -> any:
    """Пытается распарсить значение как JSON."""
    if raw_value is None:
        return None
    try:
        if isinstance(raw_value, bytes):
            raw_value = raw_value.decode("utf-8", errors="replace")
        return json.loads(raw_value)
    except (json.JSONDecodeError, TypeError):
        return str(raw_value)


def extract_messages(parsed: any) -> list[dict]:
    """Рекурсивно ищет сообщения в распарсенных данных."""
    messages = []

    if isinstance(parsed, list):
        for item in parsed:
            messages.extend(extract_messages(item))

    elif isinstance(parsed, dict):
        # Прямые сообщения
        if "role" in parsed and "content" in parsed:
            messages.append(parsed)
        # Вложенные conversations/messages
        for key in ["messages", "conversation", "history", "turns", "items"]:
            if key in parsed:
                messages.extend(extract_messages(parsed[key]))
        # Обходим остальные ключи
        for v in parsed.values():
            if isinstance(v, (dict, list)):
                messages.extend(extract_messages(v))

    return messages


# ──────────────────────────────────────────────
# 4. Форматировать вывод
# ──────────────────────────────────────────────

def format_markdown(all_records: list[dict]) -> str:
    """Формирует Markdown-конспект из всех найденных записей."""
    lines = [
        "# Windsurf — История переписки",
        f"_Экспортировано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_",
        "",
    ]

    session_num = 0
    for record in all_records:
        parsed = parse_value(record["raw_value"])
        messages = extract_messages(parsed)

        if not messages:
            # Попробуем показать raw данные если нет сообщений
            if isinstance(parsed, str) and len(parsed) > 10:
                session_num += 1
                lines += [
                    f"## Запись #{session_num} (raw)",
                    f"**Ключ:** `{record['key']}`",
                    "",
                    "```",
                    parsed[:2000],
                    "```",
                    "",
                ]
            continue

        session_num += 1
        lines += [
            f"## Сессия #{session_num}",
            f"**Ключ:** `{record['key']}`",
            f"**БД:** `{record['db']}`",
            "",
        ]

        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            # content может быть списком блоков
            if isinstance(content, list):
                text_parts = []
                for block in content:
                    if isinstance(block, dict):
                        text_parts.append(block.get("text", str(block)))
                    else:
                        text_parts.append(str(block))
                content = "\n".join(text_parts)

            emoji = "🧑" if role == "user" else "🤖"
            label = "**Пользователь**" if role == "user" else "**Windsurf AI**"
            lines += [
                f"### {emoji} {label}",
                "",
                str(content).strip(),
                "",
                "---",
                "",
            ]

    if session_num == 0:
        lines.append("_Ничего не найдено. Попробуйте указать путь к БД вручную._")

    return "\n".join(lines)


# ──────────────────────────────────────────────
# 5. Главная функция
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Экспорт истории Windsurf")
    parser.add_argument("--db", help="Путь к .vscdb файлу (если авто-поиск не сработал)")
    parser.add_argument("--output", default="./windsurf_export", help="Папка для сохранения")
    parser.add_argument("--json", action="store_true", help="Также сохранить raw JSON")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Найти базы данных
    if args.db:
        db_paths = [Path(args.db)]
    else:
        print("🔍 Ищу базы данных Windsurf...")
        db_paths = find_windsurf_db()

    if not db_paths:
        print("❌ Базы данных не найдены!")
        print("\nПопробуйте запустить с явным путём:")
        print("  python extract_windsurf_history.py --db /path/to/state.vscdb")
        print("\nТипичные пути:")
        print("  Windows: %APPDATA%\\Windsurf\\User\\globalStorage\\")
        print("  Mac:     ~/Library/Application Support/Windsurf/")
        print("  Linux:   ~/.config/Windsurf/User/")
        sys.exit(1)

    print(f"✅ Найдено баз данных: {len(db_paths)}")
    for p in db_paths:
        print(f"   {p}")

    # Извлечь данные
    all_records = []
    for db_path in db_paths:
        print(f"\n📖 Читаю: {db_path.name}")
        records = extract_from_db(db_path)
        print(f"   Найдено Windsurf-записей: {len(records)}")
        all_records.extend(records)

    if not all_records:
        print("\n⚠️  Записи Windsurf не найдены в базах данных.")
        print("Возможно история хранится в другом месте или ключи изменились.")
        sys.exit(1)

    # Сохранить Markdown
    md_path = output_dir / "history.md"
    md_content = format_markdown(all_records)
    md_path.write_text(md_content, encoding="utf-8")
    print(f"\n✅ Markdown сохранён: {md_path}")

    # Сохранить JSON (опционально)
    if args.json:
        json_records = []
        for record in all_records:
            parsed = parse_value(record["raw_value"])
            json_records.append({
                "db": record["db"],
                "table": record["table"],
                "key": record["key"],
                "data": parsed,
            })
        json_path = output_dir / "history_raw.json"
        json_path.write_text(
            json.dumps(json_records, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"✅ JSON сохранён:     {json_path}")

    print(f"\n🎉 Готово! Файлы в папке: {output_dir.resolve()}")


if __name__ == "__main__":
    main()