---
id: 005
title: Память ч.2 — вспомнить маркер после рестарта
channel: chat
timeout_min: 10
verdict: code
depends_on: 004
checks:
  - chat_reply_contains: "{{run_marker}}"
---

## Задача
Какое кодовое слово этого QA-прогона я просил тебя запомнить?
Назови его точно.

## Предусловия (контекст «до»)
- Кейс 003 сохранил маркер, кейс 004 перезапустил Уробороса.
- context.json: `ts_fence`, `run_marker`.

## Шаги исполнителя
1. `chat.py send` с текстом задачи.
2. `chat.py wait --since <ts_fence> --contains "{{run_marker}}" --timeout 420`
   → `reply.json`.

## Верификация
Программная: ответ содержит маркер — память пережила рестарт.

## Откат
Не требуется.
