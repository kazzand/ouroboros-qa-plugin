---
id: 004
title: /restart — саморестарт и возвращение к жизни
channel: chat
timeout_min: 12
verdict: code
checks:
  - pid_changed
  - supervisor_ready
  - chat_reply_contains: "{{run_marker}}"
---

## Задача
(шаг 1) /restart
(шаг 4, после подъёма) Ответь ровно одной строкой: pong {{run_marker}}

## Предусловия (контекст «до»)
- context.json: `before_pid` (pid из data/state/server_process.json ДО),
  `run_marker`, `ts_fence` (записывается на шаге 4 перед проверкой).

## Шаги исполнителя
1. `chat.py send "/restart"`.
2. Ждать падения и подъёма: поллить `GET /api/state` каждые 10 сек
   (ошибки соединения ожидаемы) до supervisor_ready==true, максимум 5 минут.
   Если не поднялся за 5 минут — CRITICAL-протокол.
3. Записать launcher.log хвост в артефакты (`launcher-tail.txt`).
4. `chat.py send "Ответь ровно одной строкой: pong {{run_marker}}"` →
   обновить `ts_fence` в context.json значением из ЭТОЙ отправки.
5. `chat.py wait --since <ts_fence> --contains "{{run_marker}}" --timeout 300`.

## Верификация
Программная: pid сменился, supervisor_ready вернулся, чат жив после рестарта.

## Откат
Не требуется — /restart штатный.

## Сцепка
Рестарт этой тройки используется кейсом 005 (память сквозь рестарт).
Если этот кейс BLOCKED — 005 автоматически BLOCKED.
