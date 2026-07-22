# Ouroboros QA Regress — плагин Claude Code

QA-регресс живого инстанса [Ouroboros](https://github.com/razzant/ouroboros):
16 e2e-кейсов «как человек» — от смоука и памяти сквозь рестарт до
самомодификации (смена цвета баблов с обязательным откатом), computer-use
(котик в Numbers) и safety-fuse. Программная верификация без LLM + двойные
независимые vision-судьи. Отчёт с вердиктами PASS / FAIL / NEEDS_HUMAN /
BLOCKED / INFRA_DRIFT.

## Установка

```bash
# один раз: добавить маркетплейс и поставить плагин
/plugin marketplace add <owner>/ouroboros-qa-plugin
/plugin install ouroboros-qa@ouroboros-qa

# зависимость чат-клиента
pip3 install websockets
```

## Требования

- Запущенный инстанс Ouroboros (web UI/API на 127.0.0.1:8765).
- Claude Code запускается ИЗ корня инсталляции Ouroboros (`~/Ouroboros` —
  каталог, где лежат `data/` и `repo/`): харнесс определяет корень по cwd.
- macOS-разрешения Screen Recording/Accessibility — для computer-use кейса.
- Опционально: плагин claudexor — второй vision-судья. Без него vision-кейсы
  дают NEEDS_HUMAN вместо PASS (одним судьёй PASS не выносится).

## Запуск

```bash
cd ~/Ouroboros && claude
> /ouroboros-qa:qa-regress       # все 16 кейсов, ~1.5–2 часа, ~$10–20
> /ouroboros-qa:qa-regress 00    # дешёвое ядро 000–006, ~20 минут
```

Во время прогона за маком не работать: кейсы двигают реальные окна и мышь.
Очередь задач Уробороса должна быть пуста, фоновое сознание и автоэволюция —
выключены (preflight это проверяет и остановится сам).

## Что важно знать

- Прогон работает по ЖИВОМУ инстансу: самомодификация реально коммитит в
  репу Уробороса (с обязательным откатом), кейс памяти оставляет след
  (маркер прогона) в живой памяти — намеренно.
- Харнессу жёстко запрещены: /panic, /api/reset, git rollback/promote,
  /api/update/*, правка settings.json (кроме аварийного восстановления из
  бэкапа при CRITICAL).
- Отчёты и артефакты: `qa/runs/<дата>/` в рабочей папке.
- Тесты самого харнесса: `python3 "$(plugin)/skills/qa-regress/harness/test_checks.py"`
  (63 проверки, без касания живой системы).

## Устройство

```
skills/qa-regress/
├── SKILL.md      ← оркестратор (исполнитель ≠ судья, CRITICAL-протокол)
├── cases/        ← 16 кейсов (frontmatter: канал, чеки, vision-рубрики)
└── harness/
    ├── checks.py     ← программный верификатор (stdlib, без LLM)
    ├── chat.py       ← WS-клиент чата (тракт скрепки/cmd+V)
    ├── bindings.md   ← пиннед-конкретика + мета-обновление при дрифте
    └── test_checks.py
```
