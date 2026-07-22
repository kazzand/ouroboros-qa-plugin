---
id: 006
title: /bg — тумблер фонового сознания
channel: chat
timeout_min: 8
verdict: code
checks:
  - chat_reply_received
  - bg_toggle_evidence
  - state_flag_restored: bg_consciousness_enabled
---

## Задача
(в зависимости от исходного состояния) /bg start ЛИБО /bg stop, затем обратно.

## Предусловия (контекст «до»)
- context.json: `flags_before` = {"bg_consciousness_enabled": <текущее>}
  (прочитать data/state/state.json ДО), `ts_fence` (из первого send).

## Шаги исполнителя
1. Прочитать флаг bg_consciousness_enabled из state.json → before.
2. `chat.py send` с противоположной командой (`/bg start` если false,
   `/bg stop` если true) → ts_fence в context.json. Дождаться подтверждения
   (`chat.py wait --since <ts_fence> --timeout 60`).
3. Прочитать флаг → after_toggle (дать 10 сек на запись).
4. Отправить обратную команду, дождаться ответа, прочитать флаг → after_restore.
5. Записать артефакт `bg_toggle.json`:
   {"before":…, "after_toggle":…, "after_restore":…}.
6. После restore выдержать 60 сек тишины канала перед следующим кейсом
   (сознание могло взвести wakeup — не дать ему загрязнить ts_fence 010).

## Верификация
Программная: флаг переключился и вернулся в исходное; текущее состояние
совпадает с исходным.

## Откат
Встроен в шаги (возврат в исходное состояние).
