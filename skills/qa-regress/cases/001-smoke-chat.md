---
id: 001
title: Смоук чата — вопрос через WS, ответ в чате
channel: chat
timeout_min: 10
verdict: code
checks:
  - chat_reply_contains: "Канберра"
---

## Задача
Ответь одним словом: какой город является столицей Австралии?

## Предусловия (контекст «до»)
- context.json: `ts_fence` (из chat.py send).

## Шаги исполнителя
1. Дождаться тишины чата (нет новых out-сообщений 30 сек).
2. `chat.py send "<Задача>"` → ts_fence в context.json.
3. `chat.py wait --since <ts_fence> --contains Канберра --timeout 300`,
   вывод в артефакт `reply.json`.

## Верификация
Программная: в out-сообщениях после fence есть «Канберра».

## Откат
Не требуется.
