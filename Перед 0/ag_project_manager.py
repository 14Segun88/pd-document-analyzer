def save_project(name: str, ag_dir: Path, projects_dir: Path, index: dict, description: str = ""):
    """Самая надёжная версия для Antigravity 2026 — копируем каждую UUID-папку отдельно"""
    proj_path = projects_dir / name
    proj_path.mkdir(parents=True, exist_ok=True)

    print(yellow(f"\n🔄 Сохраняем проект '{name}'..."))
    total_mb = 0.0

    for d in PROJECT_DIRS:
        src = ag_dir / d
        dst = proj_path / d

        if not src.exists():
            print(f"   ⚠️  {d}/ не найдена")
            continue

        if dst.exists():
            shutil.rmtree(dst, ignore_errors=True)
        dst.mkdir(parents=True, exist_ok=True)

        if d == "brain":
            # Специальная обработка для brain — копируем каждую UUID-папку отдельно
            uuid_dirs = [p for p in src.iterdir() if p.is_dir()]
            print(f"   Найдено {len(uuid_dirs)} UUID-папок в brain")
            for uuid_dir in uuid_dirs:
                dst_uuid = dst / uuid_dir.name
                shutil.copytree(uuid_dir, dst_uuid, dirs_exist_ok=True, copy_function=shutil.copy2)
                print(f"     ✓ {uuid_dir.name[:12]}... скопировано")
        else:
            # Для остальных папок — обычное копирование
            shutil.copytree(src, dst, dirs_exist_ok=True, copy_function=shutil.copy2)

        mb = dir_size_mb(dst)
        total_mb += mb
        print(f"   📁 {d}/ → сохранено ({mb:.2f} MB)")

    # Сохраняем mcp_config.json
    for f in PROJECT_FILES:
        src = ag_dir / f
        if src.exists():
            shutil.copy2(src, proj_path / f)
            print(f"   📄 {f} сохранён")

    # Meta
    brain_uuid_count = len([p for p in (ag_dir / "brain").iterdir() if p.is_dir()]) if (ag_dir / "brain").exists() else 0

    meta = {
        "name": name,
        "description": description,
        "saved_at": datetime.now().isoformat(),
        "size_mb": round(total_mb, 2),
        "brain_uuid_folders": brain_uuid_count,
    }

    (proj_path / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    index["projects"][name] = meta
    save_index(projects_dir, index)

    print(green(f"\n✅ Проект '{name}' успешно сохранён ({total_mb:.2f} MB)"))
    print(f"   UUID-папок в brain: {brain_uuid_count}")