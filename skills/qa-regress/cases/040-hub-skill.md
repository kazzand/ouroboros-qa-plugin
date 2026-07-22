---
id: 040
title: OuroborosHub — install скилла, lifecycle, uninstall
channel: api
timeout_min: 20
verdict: code
checks:
  - lifecycle_succeeded: "{{hub_slug}}"
  - hub_not_installed: "{{hub_name}}"
---

## Задача
(Кейс выполняется прямыми вызовами marketplace API, без текстовой задачи
агенту — тестируется механизм установки, а не понимание.)

## Предусловия (контекст «до»)
- `GET /api/marketplace/ouroboroshub/catalog` → артефакт `catalog.json`.
- Выбрать МИНИМАЛЬНЫЙ безобидный reviewed-скилл: НЕ транспорт-бридж
  (не telegram/a2a), без секретов в требованиях, БЕЗ scheduled-задач,
  желательно UI-виджет/простой тул. Записать его slug в context.json как
  `hub_slug`.
- `GET /api/marketplace/ouroboroshub/installed` «до» → `installed-before.json`.
  Если скилл уже установлен — выбрать другой.
- Важно про идентификаторы: install принимает slug; lifecycle-job несёт
  target=slug; а в installed и в пути uninstall используется САНИТИЗИРОВАННОЕ
  имя (может отличаться от slug). Поэтому:
  - `hub_slug` — для install и чека lifecycle_succeeded;
  - `hub_name` — санитизированное имя, которое исполнитель считывает из
    `skills[].name` в installed ПОСЛЕ установки; для hub_not_installed и
    для пути uninstall.

## Шаги исполнителя
1. `POST /api/marketplace/ouroboroshub/install` с телом `{"slug": "<hub_slug>"}`.
   Read-timeout запроса ≥ таймаута кейса (install синхронный: скачивание +
   review + deps держат соединение).
2. Поллить `GET /api/skills/lifecycle-queue` каждые 20 сек до
   succeeded/failed по target==hub_slug (таймаут кейса). Снимки → `lifecycle.json`.
   Если lifecycle не терминализовался за таймаут — BLOCKED с пометкой
   «возможен остаток частичной установки».
3. `GET .../installed` → найти запись, установленную этим кейсом, взять
   `name` → записать в context.json как `hub_name`. `installed-after.json`.
4. `POST /api/marketplace/ouroboroshub/uninstall/<hub_name>` (имя в ПУТИ).
5. Поллить installed до исчезновения `hub_name`. `installed-final.json`.

## Верификация
Программная: install дошёл до lifecycle succeeded (по slug); после uninstall
скилл (по sanitized name) не числится установленным.

## Откат
Встроен (uninstall — часть кейса). Если uninstall не сработал/вернул не-2xx —
пометить «откат не выполнен, остаток в data/skills/ouroboroshub» в отчёте и
НЕ удалять файлы руками (территория Уробороса).
