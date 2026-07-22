---
id: 030
title: Вложение в чат (тракт скрепки/cmd+V) — прочитать файл
channel: chat
timeout_min: 12
verdict: code
checks:
  - chat_reply_contains: "{{attachment_code}}"
---

## Задача
Прочитай приложенный файл и ответь: какой в нём указан код доступа?
Назови его точно.

## Предусловия (контекст «до»)
- Оркестратор генерирует файл `qa-attachment.txt` в run-dir кейса с
  содержимым: «Служебная записка QA. Код доступа: <attachment_code>.»,
  где attachment_code = случайный hex (в context.json).
- context.json: `ts_fence`, `attachment_code`.

## Шаги исполнителя
1. `chat.py send "<Задача>" --attach <run>/030/qa-attachment.txt` —
   это ровно тракт скрепки: upload через /api/chat/upload + WS attachments.
2. `chat.py wait --since <ts_fence> --contains <attachment_code> --timeout 420`
   → `reply.json`.

## Верификация
Программная: ответ в чате содержит код из файла — вложение доставлено
и прочитано.

## Откат
Не требуется (файл во временной папке прогона).
