---
id: 002
title: Слэш-команда /status отвечает состоянием
channel: chat
timeout_min: 5
verdict: code
checks:
  - chat_reply_received
  - chat_reply_matches: "(?i)(worker|task|budget|бюджет|очеред|воркер|[$])"
---

## Задача
/status

## Предусловия (контекст «до»)
- context.json: `ts_fence`.

## Шаги исполнителя
1. `chat.py send "/status"`.
2. `chat.py wait --since <ts_fence> --timeout 120` → артефакт `reply.json`.

## Верификация
Программная: ответ пришёл и похож на статус (воркеры/очередь/бюджет).

## Откат
Не требуется.
