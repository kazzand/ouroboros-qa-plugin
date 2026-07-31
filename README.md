# Ouroboros QA Regress — плагин Claude Code и Codex

QA-регресс живого инстанса [Ouroboros](https://github.com/razzant/ouroboros):
16 e2e-кейсов «как человек» — от смоука и памяти сквозь рестарт до
самомодификации (смена цвета баблов с обязательным откатом), computer-use
(котик в Numbers) и safety-fuse. Программная верификация без LLM + двойные
независимые vision-судьи. Отчёт с вердиктами PASS / FAIL / NEEDS_HUMAN /
BLOCKED / INFRA_DRIFT.

## Установка

Общая Python-зависимость чат-клиента:

```bash
python3 -m pip install "websockets>=12,<17"
```

### Claude Code

В интерактивной сессии:

```text
/plugin marketplace add kazzand/ouroboros-qa-plugin
/plugin install ouroboros-qa@ouroboros-qa
```

Для скрипта/онбординга:

```bash
claude plugin marketplace add kazzand/ouroboros-qa-plugin
claude plugin install ouroboros-qa@ouroboros-qa
```

Может понадобиться `/reload-plugins` или новая сессия.

### Codex

```bash
codex plugin marketplace add kazzand/ouroboros-qa-plugin
codex plugin add ouroboros-qa@ouroboros-qa
```

После установки открой новую задачу Codex, чтобы она подхватила скилл.

## Требования

- Запущенный инстанс Ouroboros (web UI/API на 127.0.0.1:8765).
- Claude Code или Codex запускается ИЗ корня инсталляции Ouroboros
  (`~/Ouroboros` — каталог, где лежат `data/` и `repo/`). Неверный cwd или
  `QA_ROOT` останавливает харнесс до любых записей.
- macOS-разрешения Screen Recording/Accessibility — для computer-use кейса.
- Для полного прогона в Codex рекомендуется Codex app с Browser. В CLI можно
  использовать Playwright; без browser/DOM/screenshot-возможностей
  затронутые кейсы получают BLOCKED.
- Нужны два независимых vision-судьи. Claude Code использует Agent + claudexor
  (либо два изолированных Agent); Codex — два свежих сабагента. Одним судьёй
  PASS не выносится: результат будет NEEDS_HUMAN.

## Запуск

```bash
cd ~/Ouroboros && claude
> /ouroboros-qa:qa-regress       # все 16 кейсов, ~1.5–2 часа, ~$10–20
> /ouroboros-qa:qa-regress 00    # дешёвое ядро 000–006, ~20 минут
```

Codex:

```bash
cd ~/Ouroboros && codex
```

Затем в задаче:

```text
$ouroboros-qa:qa-regress         # все 16 кейсов, ~1.5–2 часа, ~$10–20
$ouroboros-qa:qa-regress 00      # дешёвое ядро 000–006, ~20 минут
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
- Тесты самого харнесса из корня checkout:
  `python3 skills/qa-regress/harness/test_checks.py` (без сети и без касания
  живой системы).

## Устройство

```
.claude-plugin/            ← manifest/marketplace Claude Code
.codex-plugin/plugin.json  ← manifest Codex
.agents/plugins/           ← marketplace Codex
skills/qa-regress/
├── SKILL.md      ← оркестратор (исполнитель ≠ судья, CRITICAL-протокол)
├── agents/       ← метаданные и explicit-only policy для Codex
├── cases/        ← 16 кейсов (frontmatter: канал, чеки, vision-рубрики)
└── harness/
    ├── checks.py     ← программный верификатор (stdlib, без LLM)
    ├── chat.py       ← WS-клиент чата (тракт скрепки/cmd+V)
    ├── bindings.md   ← пиннед-конкретика + мета-обновление при дрифте
    └── test_checks.py
```
