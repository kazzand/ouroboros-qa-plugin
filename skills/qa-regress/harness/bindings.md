# Пиннед-биндинги QA-харнесса

Это ЕДИНСТВЕННОЕ место, где харнесс знает внутренности Уробороса: эндпоинты,
пути к файлам, имена полей. Кейсы и оркестратор ссылаются на биндинги, а не
на конкретику напрямую.

**Как обновлять (мета-инструкция).** Биндинги не поддерживаются руками.
Если чек падает «интерфейсом» (404, файл переехал, поле исчезло) — это вердикт
INFRA_DRIFT: исполнитель изучает `repo/docs/ARCHITECTURE.md` (+ код гейтвея
`repo/ouroboros/gateway/`), выводит актуальный способ, показывает дифф
биндинга в отчёте прогона. Обновление пина применяется только после решения
Андрея. Каждый прогон меряет текущей пиннед-версией — одинаково.

- Выведено: 2026-07-22 (v6.73.2, 33d6cab1); ре-пин: 2026-09-03 против
  v7.0.0-rc.7 (2b8b7903) — все биндинги сверены с деревом rc.7, единственный
  дрифт: поле стоимости task_result (ABI 7.0 переименовал `cost_usd` →
  `accounted_upper_bound_usd`, легаси-имя больше не пишется и вычищается из
  проекций; см. ouroboros/cost_projection.py COST_ALIAS_PAIRS).
- Источники правды: docs/ARCHITECTURE.md; ouroboros/gateway/{router,tasks,control,ws,logs}.py;
  ouroboros/task_results.py; ouroboros/cost_projection.py;
  ouroboros/configured_subagents.py; supervisor/state.py; web/style.css

```json
{
  "api_base": "http://127.0.0.1:8765",
  "endpoints": {
    "health": "GET /api/health",
    "state": "GET /api/state",
    "tasks_create": "POST /api/tasks",
    "tasks_list": "GET /api/tasks?status=<csv>&limit=<n>",
    "task_get": "GET /api/tasks/{task_id}",
    "task_cancel": "POST /api/tasks/{task_id}/cancel",
    "chat_ws": "WS /ws",
    "chat_upload": "POST /api/chat/upload",
    "projects_list": "GET /api/projects",
    "project_delete": "POST /api/projects/{id}/delete",
    "hub_catalog": "GET /api/marketplace/ouroboroshub/catalog",
    "hub_install": "POST /api/marketplace/ouroboroshub/install (тело {\"slug\": ...})",
    "hub_uninstall": "POST /api/marketplace/ouroboroshub/uninstall/{name} (name = sanitized имя из installed)",
    "hub_installed": "GET /api/marketplace/ouroboroshub/installed",
    "skills_lifecycle": "GET /api/skills/lifecycle-queue",
    "extensions_list": "GET /api/extensions",
    "claudexor_status": "GET /api/claudexor/status"
  },
  "task_result": {
    "dir": "data/task_results",
    "settled_statuses": ["completed", "failed", "cancelled", "rejected_duplicate"],
    "success": "status=='completed' and outcome_axes.execution.status=='ok'",
    "answer_fields": ["result", "final_answer"],
    "cost_fields": ["accounted_upper_bound_usd", "cost_usd"],
    "cost_openness_fields": ["cost_final", "unknown_unmetered"]
  },
  "routes": {
    "subagents_setting": "OUROBOROS_SUBAGENTS",
    "session_kind": "agent_session"
  },
  "state_flags": {
    "file": "data/state/state.json",
    "bg_consciousness": "bg_consciousness_enabled",
    "spent_usd_api_field": "spent_usd",
    "supervisor_ready_api_field": "supervisor_ready"
  },
  "restart": {
    "pid_file": "data/state/server_process.json",
    "pid_field": "pid",
    "launcher_log": "data/logs/launcher.log"
  },
  "chat_log": {
    "file": "data/logs/chat.jsonl",
    "out_direction": "out",
    "ts_field": "ts",
    "text_field": "text"
  },
  "tools_log": {
    "file": "data/logs/tools.jsonl",
    "safety_block_markers": ["SAFETY_VIOLATION", "SAFETY_MODE_SELF_LOWERING_BLOCKED"]
  },
  "bubbles": {
    "css_file": "repo/web/style.css",
    "css_vars": ["--user-bubble-from", "--user-bubble-to"],
    "dom_selector": ".chat-bubble.user"
  },
  "safety": {
    "settings_file": "data/settings.json",
    "mode_key": "OUROBOROS_SAFETY_MODE"
  },
  "git": {
    "repo": "repo",
    "branch": "ouroboros",
    "self_author": "Ouroboros <ouroboros@local.mac>"
  },
  "memory_dir": "data/memory"
}
```

Все относительные пути — от корня инсталляции (родитель `qa/`, обычно
`~/Ouroboros/`; переопределяется env `QA_ROOT`).

Семантика новых полей:

- `cost_fields` — упорядоченная пара имён: первое честное (ABI 7.0),
  второе — read-tolerance для инстансов ≤6.x. Чек берёт первое числовое.
- `cost_openness_fields` — маркеры честности учёта рядом с суммой
  (`cost_final=false`, `unknown_unmetered=true` — сумма не окончательная или
  часть работы шла неметрируемо, например на подписочном harness); чек
  приводит их в детали, не влияя на вердикт.
- `routes` — где искать маршрутизацию исполнителей: settings-ключ
  `OUROBOROS_SUBAGENTS` (структурные строки, без секретов); строка с
  `route.kind == "agent_session"` означает подписочный harness
  (codex/claude/cursor через встроенный Claudexor), её цель — `harness[=model]`.
  Здоровье подписок читается через `claudexor_status` (аккаунты, залогинен ли
  профиль, снапшоты квот); эндпоинт read-only, `POST /api/claudexor/*`
  (login/wake/quota/refresh) — owner-действия, харнессу запрещены.
