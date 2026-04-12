Вы — агент в проекте с мультиагентной координацией. ОБЯЗАТЕЛЬНО соблюдайте AGENT_PROTOCOL.md:

1. ПОСЛЕ КАЖДОГО ОТВЕТА — создайте лог в AGENTS_RULES-v2/raw/ и обновите shared_status.md
2. При старте — читайте ТОЛЬКО AGENTS_RULES-v2/shared_status.md + AGENTS_RULES-v2/index.md + релевантные wiki-страницы
3. НЕ читайте все файлы подряд — каждый файл = токены
4. НЕ читайте AGENTS_RULES/ (v1) — устарело, используйте AGENTS_RULES-v2/
5. git pull перед стартом, git push после работы
6. Формула контекста: shared_status.md (2KB) + index.md (1KB) + 1 wiki-страница (1-3KB) = 4-6KB

Полный протокол: ./AGENT_PROTOCOL.md
Инструкции агента: ./AGENTS_RULES-v2/.agent/instructions.md
