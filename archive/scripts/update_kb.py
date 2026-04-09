import json

with open("knowledge_base.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Find sections 1, 3, 4 for 'Анализ Пакета 4.docx'
sections_to_copy = []
for entry in data:
    if entry.get("_source_doc") == "Анализ Пакета 4.docx":
        title = entry.get("title", "")
        if title.startswith("Раздел 1 ") or title.startswith("Раздел 3 ") or title.startswith("Раздел 4 "):
            sections_to_copy.append(entry)

# Check if they are already added for 4a
existing_4a_titles = [e.get("title") for e in data if e.get("_source_doc") == "Анализ Пакета 4а.docx"]

num_added = 0
for sec in sections_to_copy:
    if sec["title"] not in existing_4a_titles:
        new_sec = sec.copy()
        new_sec["_source_doc"] = "Анализ Пакета 4а.docx"
        data.append(new_sec)
        num_added += 1

print(f"Added {num_added} entries for Анализ Пакета 4а.docx")

with open("knowledge_base.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
