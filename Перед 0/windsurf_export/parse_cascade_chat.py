#!/usr/bin/env python3
"""
Парсер истории диалога Windsurf Cascade из .pb файла.
Извлекает сообщения пользователя и AI в читаемом виде.

Запуск:
  python3 parse_cascade_chat.py
  python3 parse_cascade_chat.py --pb ~/.codeium/chat_state/your_file.pb
  python3 parse_cascade_chat.py --all   # все .pb файлы в chat_state
"""

import re
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

# ──────────────────────────────────────────────
# Читаем бинарный .pb и извлекаем текстовые блоки
# ──────────────────────────────────────────────

def read_pb_strings(pb_path: Path) -> bytes:
    return pb_path.read_bytes()


def extract_text_blocks(data: bytes) -> list[str]:
    """
    Protobuf хранит строки как: [field+wiretype varint(len)] [utf8 bytes]
    Ищем все UTF-8 строки длиннее 8 байт.
    """
    blocks = []
    i = 0
    while i < len(data):
        # Ищем varint длину за которой идёт читаемый UTF-8 текст
        if data[i] > 0x0a and data[i] < 0xf0:
            # Попробуем прочитать varint
            length = 0
            shift = 0
            j = i
            while j < len(data) and j < i + 5:
                b = data[j]
                length |= (b & 0x7f) << shift
                shift += 7
                j += 1
                if not (b & 0x80):
                    break
            if 8 < length < 50000 and j + length <= len(data):
                chunk = data[j:j + length]
                try:
                    text = chunk.decode('utf-8')
                    if _is_readable(text):
                        blocks.append(text)
                        i = j + length
                        continue
                except UnicodeDecodeError:
                    pass
        i += 1
    return blocks


def _is_readable(s: str) -> bool:
    """Проверяем что строка — это реальный текст, не бинарный мусор."""
    if len(s) < 8:
        return False
    # Считаем долю читаемых символов
    readable = sum(1 for c in s if c.isprintable() or c in '\n\t\r')
    ratio = readable / len(s)
    if ratio < 0.85:
        return False
    # Отсеиваем base64 и UUID-подобные строки
    if re.match(r'^[A-Za-z0-9+/=\-]{20,}$', s.strip()):
        return False
    # Должно быть хоть несколько слов или знаков препинания
    if len(s.split()) < 2 and not any(p in s for p in '.,!?:;()[]{}'):
        return False
    return True


# ──────────────────────────────────────────────
# Определяем роль (user / bot) по контексту
# ──────────────────────────────────────────────

USER_MARKERS = ['user-', '%user', 'пользователь', '@user']
BOT_MARKERS  = ['bot-', '%bot', 'cascade', 'codeium']

def classify_blocks(raw_data: bytes, blocks: list[str]) -> list[dict]:
    """
    Сопоставляем текстовые блоки с маркерами user/bot из бинарника.
    """
    messages = []
    raw_str = raw_data.decode('latin-1')  # latin-1 не теряет байты

    for block in blocks:
        # Найдём позицию блока в raw данных
        try:
            encoded = block.encode('utf-8')
            pos = raw_str.find(block[:20].encode('utf-8').decode('latin-1'))
        except Exception:
            pos = -1

        # Ищем ближайший маркер роли перед блоком
        role = 'unknown'
        if pos > 0:
            context = raw_str[max(0, pos-200):pos]
            if any(m in context for m in USER_MARKERS):
                role = 'user'
            elif any(m in context for m in BOT_MARKERS):
                role = 'bot'

        messages.append({'role': role, 'text': block})

    return messages


# ──────────────────────────────────────────────
# Простой метод: разбить по маркерам напрямую
# ──────────────────────────────────────────────

def parse_by_markers(data: bytes) -> list[dict]:
    """
    Более надёжный метод: ищем маркеры %user- и bot- прямо в байтах,
    затем извлекаем следующий текстовый блок.
    """
    messages = []
    
    # Декодируем с заменой нечитаемых байт
    text = data.decode('utf-8', errors='replace')
    
    # Разбиваем по паттернам сообщений
    # Маркеры выглядят как: %user-XXXX или (bot-XXXX
    pattern = re.compile(
        r'(?:%user-[A-Za-z0-9]+|'
        r'\(bot-[a-f0-9\-]+)'
    )
    
    parts = pattern.split(text)
    markers = pattern.findall(text)
    
    for i, marker in enumerate(markers):
        if i + 1 >= len(parts):
            break
            
        chunk = parts[i + 1]
        
        # Убираем бинарный мусор в начале
        # Берём только читаемые строки
        lines = []
        for line in chunk.split('\n'):
            clean = re.sub(r'[^\x20-\x7e\u0400-\u04ff\u00c0-\u024f\n\t .,!?:;()\[\]{}\-"\'`#@_=/\\*+<>%&^~|]', '', line)
            clean = clean.strip()
            if len(clean) > 3:
                lines.append(clean)
        
        content = '\n'.join(lines).strip()
        
        # Убираем служебные строки
        content = re.sub(r'\b[A-Za-z0-9]{32,}\b', '', content)  # хэши
        content = re.sub(r'file:///[^\s]+', lambda m: f'[файл: {Path(m.group()).name}]', content)
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = content.strip()
        
        if len(content) < 5:
            continue
        
        role = 'user' if '%user' in marker else 'bot'
        messages.append({'role': role, 'text': content})
    
    return messages


# ──────────────────────────────────────────────
# Форматирование
# ──────────────────────────────────────────────

def format_dialog(messages: list[dict], title: str = "") -> str:
    lines = [
        f"# Windsurf Cascade — История диалога",
    ]
    if title:
        lines.append(f"**Проект:** {title}")
    lines += [
        f"_Экспортировано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_",
        f"_Сообщений: {len(messages)}_",
        "",
        "---",
        "",
    ]
    
    prev_role = None
    for i, msg in enumerate(messages):
        role = msg['role']
        text = msg['text']
        
        if role == 'user':
            lines.append(f"### 🧑 Пользователь")
        elif role == 'bot':
            lines.append(f"### 🤖 Cascade AI")
        else:
            lines.append(f"### ❓ Неизвестно")
        
        lines.append("")
        lines.append(text)
        lines.append("")
        lines.append("---")
        lines.append("")
        
        prev_role = role
    
    return '\n'.join(lines)


# ──────────────────────────────────────────────
# Главная функция
# ──────────────────────────────────────────────

def process_file(pb_path: Path, output_dir: Path):
    print(f"\n📖 Читаю: {pb_path.name}")
    
    data = pb_path.read_bytes()
    print(f"   Размер: {len(data):,} байт")
    
    messages = parse_by_markers(data)
    print(f"   Найдено сообщений: {len(messages)}")
    
    if not messages:
        print("   ⚠️  Сообщения не найдены, пробую альтернативный метод...")
        blocks = extract_text_blocks(data)
        messages = classify_blocks(data, blocks)
        print(f"   Найдено блоков: {len(messages)}")
    
    # Имя проекта из имени файла
    title = pb_path.stem.replace('codeium_chat_state_file_', '').replace('_', '/')
    
    md_content = format_dialog(messages, title)
    
    out_name = pb_path.stem + "_dialog.md"
    out_path = output_dir / out_name
    out_path.write_text(md_content, encoding='utf-8')
    print(f"   ✅ Сохранено: {out_path}")
    
    return out_path


def main():
    parser = argparse.ArgumentParser(description='Парсер диалогов Windsurf Cascade')
    parser.add_argument('--pb', help='Путь к конкретному .pb файлу')
    parser.add_argument('--all', action='store_true', help='Все .pb файлы в chat_state')
    parser.add_argument('--output', default='./windsurf_export', help='Папка для сохранения')
    args = parser.parse_args()
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    chat_state_dir = Path.home() / '.codeium' / 'chat_state'
    
    if args.pb:
        pb_files = [Path(args.pb)]
    elif args.all:
        pb_files = list(chat_state_dir.glob('*.pb'))
    else:
        # Авто: все файлы в chat_state
        pb_files = list(chat_state_dir.glob('*.pb'))
    
    if not pb_files:
        print(f"❌ .pb файлы не найдены в {chat_state_dir}")
        sys.exit(1)
    
    print(f"✅ Найдено .pb файлов: {len(pb_files)}")
    
    saved = []
    for pb in pb_files:
        out = process_file(pb, output_dir)
        saved.append(out)
    
    print(f"\n🎉 Готово! Файлы сохранены в: {output_dir.resolve()}")
    for f in saved:
        print(f"   📄 {f.name}")


if __name__ == '__main__':
    main()