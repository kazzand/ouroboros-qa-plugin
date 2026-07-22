---
id: 000
title: Смоук task API — арифметика доходит до ответа
channel: api
timeout_min: 10
verdict: code
checks:
  - task_completed
  - result_contains: "391"
  - cost_recorded
---

## Задача
Посчитай 17 * 23 и дай только число в финальном ответе.

## Предусловия (контекст «до»)
- Web UI отвечает (preflight это уже гарантирует).
- context.json: `task_id` (после отправки).

## Шаги исполнителя
1. `POST /api/tasks` с текстом задачи → сохранить `task_id` в context.json.
2. Поллить `GET /api/tasks/<id>` каждые 20 сек до терминального статуса.
3. Скопировать финальный JSON статуса в артефакты (`task.json`).

## Верификация
Программная: задача completed (+execution ok), ответ содержит 391,
стоимость записана.

## Откат
Не требуется.
