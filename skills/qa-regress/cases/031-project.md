---
id: 031
title: Проект — создать через чат, увидеть в API, удалить
channel: chat
timeout_min: 12
verdict: code
checks:
  - project_exists: "QA-Project-{{run_marker}}"
---

## Задача
Создай, пожалуйста, новый проект с названием «QA-Project-{{run_marker}}».
Ничего в нём делать не надо — просто создай и подтверди.

## Предусловия (контекст «до»)
- context.json: `ts_fence`, `run_marker`.

## Шаги исполнителя
1. `chat.py send` с текстом задачи.
2. `chat.py wait --since <ts_fence> --timeout 420` → `reply.json`.
3. `GET /api/projects` → артефакт `projects.json`.

## Верификация
Программная: агент ответил; проект с именем виден в GET /api/projects.

## Откат
Найти id проекта в projects.json и удалить: `POST /api/projects/<id>/delete`.
Учесть: удаление помечает tombstone и удаляет дерево в фоне («deletion
STARTED»), исчезновение из списка не мгновенно — поллить `GET /api/projects`
до ~60 сек, пока проект не пропадёт. Как и след в памяти (решение 6),
tombstone остаётся в живых данных — это осознанно; зафиксировать в отчёте.
Если за 60 сек не исчез — пометить «откат не подтверждён».
