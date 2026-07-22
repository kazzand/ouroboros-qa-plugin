---
id: 021
title: Браузер — прочитать веб-страницу и ответить
channel: api
timeout_min: 12
verdict: code
checks:
  - task_completed
  - result_contains: "Example Domain"
---

## Задача
Открой своим браузерным инструментом страницу https://example.com и скажи
дословно, какой там главный заголовок (h1).

## Предусловия (контекст «до»)
- context.json: `task_id`.

## Шаги исполнителя
1. `POST /api/tasks` → task_id.
2. Поллить статус каждые 20 сек.
3. Финальный JSON → `task.json`.

## Верификация
Программная: задача completed; в ответе «Example Domain» (стабильный
заголовок этой страницы уже десятилетия).

## Откат
Не требуется.
