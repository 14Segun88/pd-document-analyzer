#!/usr/bin/env python3
"""
Antigravity Profile Manager
Управление профилями для нескольких аккаунтов Antigravity.
Сохраняет/восстанавливает Brain, CodeTracker, conversations при смене аккаунта.

Запуск (Windows PowerShell):
  python ag_profile_manager.py

Запуск (WSL):
  python3 ag_profile_manager.py
"""

import os
import sys
import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime

# ──────────────────────────────────────────────
# Пути
# ──────────────────────────────────────────────

def get_gemini_dir() -> Path:
    """Найти папку .gemini/antigravity на Windows или WSL."""
    candidates = []

    if sys.platform == "win32":
        candidates = [
            Path(os.environ.get("USERPROFILE", "")) / ".gemini" / "antigravity",
        ]
    else:
        # WSL — ищем через /mnt/c/Users
        mnt = Path("/mnt/c/Users")
        if mnt.exists():
            for user in mnt.iterdir():
                p = user / ".gemini" / "antigravity"
                if p.exists():
                    candidates.append(p)

    for c in candidates:
        if c.exists():
            return c

    raise FileNotFoundError(
        "Папка .gemini/antigravity не найдена!\n"
        "Убедись что Antigravity установлен и запускался хотя бы раз."
    )


def get_profiles_dir(gemini_dir: Path) -> Path:
    """Папка где хранятся все профили."""
    p = gemini_dir.parent / "antigravity_profiles"
    p.mkdir(parents=True, exist_ok=True)
    return p


# ──────────────────────────────────────────────
# Папки которые сохраняем для каждого профиля
# ──────────────────────────────────────────────

PROFILE_DIRS = [
    "brain",
    "conversations",
    "annotations",
    "implicit",
    "code_tracker",
    "knowledge",
    "memories",
]

PROFILE_FILES = [
    "user_settings.pb",
    "installation_id",
    "mcp_config.json",
]


# ──────────────────────────────────────────────
# Индекс профилей
# ──────────────────────────────────────────────

def load_index(profiles_dir: Path) -> dict:
    idx_path = profiles_dir / "profiles_index.json"
    if idx_path.exists():
        return json.loads(idx_path.read_text(encoding="utf-8"))
    return {"profiles": {}, "active": None}


def save_index(profiles_dir: Path, index: dict):
    idx_path = profiles_dir / "profiles_index.json"
    idx_path.write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


# ──────────────────────────────────────────────
# Операции с профилями
# ──────────────────────────────────────────────

def save_profile(name: str, gemini_dir: Path, profiles_dir: Path, index: dict):
    """Сохранить текущее состояние как профиль."""
    profile_path = profiles_dir / name
    profile_path.mkdir(parents=True, exist_ok=True)

    saved = []
    skipped = []

    # Копируем папки
    for d in PROFILE_DIRS:
        src = gemini_dir / d
        dst = profile_path / d
        if src.exists():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            size = sum(f.stat().st_size for f in dst.rglob("*") if f.is_file())
            saved.append(f"  📁 {d}/ ({size/1024/1024:.1f} MB)")
        else:
            skipped.append(d)

    # Копируем файлы
    for f in PROFILE_FILES:
        src = gemini_dir / f
        dst = profile_path / f
        if src.exists():
            shutil.copy2(src, dst)
            saved.append(f"  📄 {f}")

    # Обновляем индекс
    index["profiles"][name] = {
        "saved_at": datetime.now().isoformat(),
        "account": name,
        "items": [d for d in PROFILE_DIRS if (gemini_dir / d).exists()],
    }
    save_index(profiles_dir, index)

    print(f"\n✅ Профиль '{name}' сохранён:")
    for s in saved:
        print(s)
    if skipped:
        print(f"  ⚠️  Пропущено (не существует): {', '.join(skipped)}")


def load_profile(name: str, gemini_dir: Path, profiles_dir: Path, index: dict):
    """Загрузить профиль — восстановить данные."""
    profile_path = profiles_dir / name

    if not profile_path.exists():
        print(f"❌ Профиль '{name}' не найден!")
        list_profiles(profiles_dir, index)
        return

    # Сначала сохраняем текущий активный профиль
    active = index.get("active")
    if active and active != name:
        print(f"💾 Сохраняю текущий профиль '{active}' перед переключением...")
        save_profile(active, gemini_dir, profiles_dir, index)

    restored = []

    # Восстанавливаем папки
    for d in PROFILE_DIRS:
        src = profile_path / d
        dst = gemini_dir / d
        if src.exists():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            size = sum(f.stat().st_size for f in dst.rglob("*") if f.is_file())
            restored.append(f"  📁 {d}/ ({size/1024/1024:.1f} MB)")

    # Восстанавливаем файлы
    for f in PROFILE_FILES:
        src = profile_path / f
        dst = gemini_dir / f
        if src.exists():
            shutil.copy2(src, dst)
            restored.append(f"  📄 {f}")

    # Обновляем индекс
    index["active"] = name
    index["profiles"][name]["last_loaded"] = datetime.now().isoformat()
    save_index(profiles_dir, index)

    print(f"\n✅ Профиль '{name}' загружен:")
    for r in restored:
        print(r)
    print(f"\n🔄 Перезапусти Antigravity чтобы изменения вступили в силу!")


def list_profiles(profiles_dir: Path, index: dict):
    """Показать список всех профилей."""
    profiles = index.get("profiles", {})
    active = index.get("active")

    if not profiles:
        print("📭 Профилей нет. Создай первый: python ag_profile_manager.py save <имя>")
        return

    print(f"\n{'='*50}")
    print(f"  Профили Antigravity ({len(profiles)} шт.)")
    print(f"{'='*50}")

    for name, info in profiles.items():
        marker = " ◀ АКТИВНЫЙ" if name == active else ""
        saved_at = info.get("saved_at", "—")[:10]
        last_loaded = info.get("last_loaded", "—")[:10]
        print(f"\n  {'🟢' if name == active else '⚪'} {name}{marker}")
        print(f"     Сохранён: {saved_at}")
        print(f"     Загружен: {last_loaded}")

        # Размер профиля
        profile_path = profiles_dir / name
        if profile_path.exists():
            total = sum(f.stat().st_size for f in profile_path.rglob("*") if f.is_file())
            print(f"     Размер:   {total/1024/1024:.1f} MB")

    print(f"\n{'='*50}")


def show_current(gemini_dir: Path, index: dict):
    """Показать текущее состояние Brain и CodeTracker."""
    active = index.get("active", "не установлен")
    print(f"\n{'='*50}")
    print(f"  Текущий профиль: {active}")
    print(f"{'='*50}")

    for d in PROFILE_DIRS:
        path = gemini_dir / d
        if path.exists():
            files = list(path.rglob("*"))
            total = sum(f.stat().st_size for f in files if f.is_file())
            count = sum(1 for f in files if f.is_file())
            print(f"  📁 {d}/  {count} файлов  {total/1024/1024:.1f} MB")

            # Показываем содержимое brain
            if d == "brain":
                for subdir in sorted(path.iterdir()):
                    if subdir.is_dir():
                        md_files = list(subdir.glob("*.md"))
                        for md in md_files:
                            size = md.stat().st_size
                            print(f"     └─ {md.name} ({size/1024:.0f} KB)")

    print()


def delete_profile(name: str, profiles_dir: Path, index: dict):
    """Удалить профиль."""
    if name not in index.get("profiles", {}):
        print(f"❌ Профиль '{name}' не найден!")
        return

    profile_path = profiles_dir / name
    if profile_path.exists():
        shutil.rmtree(profile_path)

    del index["profiles"][name]
    if index.get("active") == name:
        index["active"] = None
    save_index(profiles_dir, index)
    print(f"🗑️  Профиль '{name}' удалён.")


def export_brain(name: str, gemini_dir: Path, output_dir: Path):
    """Экспортировать содержимое Brain в читаемые MD файлы."""
    brain_dir = gemini_dir / "brain"
    if not brain_dir.exists():
        print("❌ Brain папка не найдена!")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    exported = 0

    for session_dir in brain_dir.iterdir():
        if not session_dir.is_dir():
            continue

        for md_file in session_dir.glob("*.md"):
            if md_file.suffix == ".md" and not md_file.name.endswith(".resolved"):
                dst = output_dir / f"{session_dir.name}_{md_file.name}"
                shutil.copy2(md_file, dst)
                exported += 1
                print(f"  ✅ {dst.name}")

    print(f"\n📤 Экспортировано {exported} файлов в {output_dir}")


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Antigravity Profile Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python ag_profile_manager.py list                    # список профилей
  python ag_profile_manager.py save richy189           # сохранить как richy189
  python ag_profile_manager.py load richy189           # загрузить richy189
  python ag_profile_manager.py current                 # текущее состояние
  python ag_profile_manager.py export richy189         # экспорт Brain в MD
  python ag_profile_manager.py delete old_profile      # удалить профиль
        """
    )

    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("list", help="Список всех профилей")
    subparsers.add_parser("current", help="Текущее состояние Brain/CodeTracker")

    p_save = subparsers.add_parser("save", help="Сохранить текущий профиль")
    p_save.add_argument("name", help="Имя профиля (например: richy189)")

    p_load = subparsers.add_parser("load", help="Загрузить профиль")
    p_load.add_argument("name", help="Имя профиля")

    p_del = subparsers.add_parser("delete", help="Удалить профиль")
    p_del.add_argument("name", help="Имя профиля")

    p_export = subparsers.add_parser("export", help="Экспорт Brain в MD файлы")
    p_export.add_argument("name", nargs="?", default="brain_export", help="Имя папки для экспорта")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        gemini_dir = get_gemini_dir()
        profiles_dir = get_profiles_dir(gemini_dir)
        index = load_index(profiles_dir)

        print(f"📂 Antigravity: {gemini_dir}")
        print(f"📦 Профили:     {profiles_dir}")

        if args.command == "list":
            list_profiles(profiles_dir, index)

        elif args.command == "current":
            show_current(gemini_dir, index)

        elif args.command == "save":
            save_profile(args.name, gemini_dir, profiles_dir, index)

        elif args.command == "load":
            load_profile(args.name, gemini_dir, profiles_dir, index)

        elif args.command == "delete":
            delete_profile(args.name, profiles_dir, index)

        elif args.command == "export":
            output = profiles_dir / args.name
            export_brain(args.name, gemini_dir, output)

    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
