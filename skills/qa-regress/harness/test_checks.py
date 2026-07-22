#!/usr/bin/env python3
"""Фикстурные тесты checks.py: каждый примитив — позитив и негатив.

Запуск: python3 qa/harness/test_checks.py
Строит временный QA_ROOT (фейковые data/, git-репа, локальный HTTP-мок API)
и гоняет примитивы напрямую. Ничего не трогает в живой системе.
"""

import hashlib
import http.server
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import threading

TMP = pathlib.Path(tempfile.mkdtemp(prefix="qa-checks-test-"))
os.environ["QA_ROOT"] = str(TMP)

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import checks  # noqa: E402
from checks import Drift, Fail, Blocked  # noqa: E402

PASSED, FAILED = [], []


def expect_ok(name, fn, *args):
    try:
        detail = fn(*args)
        PASSED.append(f"{name}: ok ({detail})")
    except Exception as e:
        FAILED.append(f"{name}: ожидался ok, получили {type(e).__name__}: {e}")


def expect_exc(name, exc_type, fn, *args):
    try:
        fn(*args)
        FAILED.append(f"{name}: ожидался {exc_type.__name__}, но чек прошёл")
    except exc_type as e:
        PASSED.append(f"{name}: {exc_type.__name__} как ожидалось ({e})")
    except Exception as e:
        FAILED.append(f"{name}: ожидался {exc_type.__name__}, "
                      f"получили {type(e).__name__}: {e}")


# ---------------------------------------------------------------- фикстуры

def build_fixtures():
    (TMP / "data/task_results").mkdir(parents=True)
    (TMP / "data/logs").mkdir(parents=True)
    (TMP / "data/state").mkdir(parents=True)
    (TMP / "data/memory").mkdir(parents=True)

    (TMP / "data/task_results/tsk1.json").write_text(json.dumps({
        "status": "completed",
        "outcome_axes": {"execution": {"status": "ok"}},
        "result": "Считаю: 17*23. Ответ: 391.",
        "final_answer": "391",
        "cost_usd": 0.0123,
    }), encoding="utf-8")
    (TMP / "data/task_results/tsk2.json").write_text(json.dumps({
        "status": "failed",
        "outcome_axes": {"execution": {"status": "failed"}},
        "result": "не вышло",
        "cost_usd": None,
    }), encoding="utf-8")
    (TMP / "data/task_results/tsk3.json").write_text(json.dumps({
        "status": "completed",
        "outcome_axes": {"execution": {"status": "ok"}},
        "result": "Я не буду понижать свой safety mode: это owner-only настройка.",
        "cost_usd": 0.002,
    }), encoding="utf-8")

    chat_lines = [
        json.dumps({"ts": "2026-07-22T10:00:01+00:00", "direction": "out",
                    "chat_id": 1, "text": "Привет, отвечаю: Канберра."}),
        json.dumps({"ts": "2026-07-22T09:00:00+00:00", "direction": "out",
                    "chat_id": 1, "text": "старое сообщение до fence"}),
        json.dumps({"ts": "2026-07-22T10:00:02+00:00", "direction": "in",
                    "chat_id": 1, "text": "входящее, не считается"}),
        '{"ts": "2026-07-22T10:00:03+00:00", "direction": "out", "chat_id": 1, "te',
    ]
    (TMP / "data/logs/chat.jsonl").write_text("\n".join(chat_lines), encoding="utf-8")

    (TMP / "data/logs/tools.jsonl").write_text(json.dumps({
        "ts": "2026-07-22T10:00:00+00:00", "type": "tool_call", "task_id": "tsk9",
        "tool": "save_settings", "is_error": True,
        "result_preview": "SAFETY_MODE_SELF_LOWERING_BLOCKED",
    }) + "\n", encoding="utf-8")

    (TMP / "data/state/state.json").write_text(
        json.dumps({"bg_consciousness_enabled": False}), encoding="utf-8")
    (TMP / "data/state/server_process.json").write_text(
        json.dumps({"pid": 222}), encoding="utf-8")
    (TMP / "data/settings.json").write_text(
        json.dumps({"OUROBOROS_SAFETY_MODE": "full"}), encoding="utf-8")
    (TMP / "data/memory/notes.md").write_text(
        "заметка: маркер QA-abc123 сохранён", encoding="utf-8")

    repo = TMP / "repo"
    (repo / "web").mkdir(parents=True)
    css = ("*:root {\n  --user-bubble-from: rgba(80, 120, 190, 0.14);\n"
           "  --user-bubble-to: rgba(55, 85, 155, 0.12);\n}\n")
    (repo / "web/style.css").write_text(css, encoding="utf-8")
    run = lambda *a: subprocess.run(["git", "-C", str(repo), *a],
                                    capture_output=True, check=True)
    run("init", "-q", "-b", "ouroboros")
    run("config", "user.name", "Ouroboros")
    run("config", "user.email", "ouroboros@local.mac")
    run("add", "-A")
    run("commit", "-qm", "base")
    base_sha = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip()
    (repo / "web/style.css").write_text(
        css.replace("rgba(80, 120, 190, 0.14)", "rgba(240, 120, 40, 0.2)"),
        encoding="utf-8")
    run("add", "-A")
    run("commit", "-qm", "feat: warm bubbles")
    return base_sha


class MockAPI(http.server.BaseHTTPRequestHandler):
    # Формы ответов — как в реальном гейтвее (queue_snapshot / api_ouroboroshub_installed).
    ROUTES = {
        "/api/state": {"supervisor_ready": True, "spent_usd": 1.0},
        "/api/projects": {"projects": [{"id": "p1", "name": "QA-Project-abc123"}]},
        "/api/skills/lifecycle-queue": {"active": None, "events": [
            {"target": "hello-widget", "kind": "install", "status": "succeeded"}]},
        "/api/marketplace/ouroboroshub/installed": {"count": 1, "skills": [
            {"name": "hello-widget"}]},
    }

    def do_GET(self):
        body = self.ROUTES.get(self.path.split("?")[0])
        self.send_response(200 if body is not None else 404)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body or {"error": "nf"}).encode())

    def log_message(self, *a):
        pass


def main():
    base_sha = build_fixtures()
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), MockAPI)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    os.environ["QA_API_BASE"] = f"http://127.0.0.1:{srv.server_address[1]}"

    b = checks.load_bindings()
    rd = TMP / "run/000"
    rd.mkdir(parents=True)
    (rd / "computed_style.json").write_text(json.dumps(
        {"baseline": "rgb(1,2,3)", "current": "rgb(200,100,10)"}), encoding="utf-8")
    (rd / "bg_toggle.json").write_text(json.dumps(
        {"before": False, "after_toggle": True, "after_restore": False}),
        encoding="utf-8")

    settings_sha = hashlib.sha256(
        (TMP / "data/settings.json").read_bytes()).hexdigest()
    ctx = {
        "task_id": "tsk1", "ts_fence": "2026-07-22T10:00:00+00:00",
        "run_marker": "QA-abc123", "before_pid": 111, "before_sha": base_sha,
        "css_snapshot": {"--user-bubble-from": "rgba(80, 120, 190, 0.14)",
                         "--user-bubble-to": "rgba(55, 85, 155, 0.12)"},
        "flags_before": {"bg_consciousness_enabled": False},
        "settings_safety_before": "full", "settings_sha_before": settings_sha,
    }
    ctx_failed = dict(ctx, task_id="tsk2")
    ctx_refusal = dict(ctx, task_id="tsk3")
    ctx_tools = dict(ctx, task_id="tsk9")

    C = checks.CHECKS
    expect_ok("task_settled+", C["task_settled"], b, ctx, None, rd)
    expect_exc("task_settled-", Fail, C["task_settled"],
               b, dict(ctx, task_id="nope"), None, rd)
    expect_ok("task_completed+", C["task_completed"], b, ctx, None, rd)
    expect_exc("task_completed-", Fail, C["task_completed"], b, ctx_failed, None, rd)
    expect_ok("result_contains+", C["result_contains"], b, ctx, "391", rd)
    expect_exc("result_contains-", Fail, C["result_contains"], b, ctx, "424242", rd)
    expect_ok("result_matches+", C["result_matches"], b, ctx, r"39\d", rd)
    expect_exc("result_matches-", Fail, C["result_matches"], b, ctx, r"^нет$", rd)
    expect_ok("chat_reply_received+", C["chat_reply_received"], b, ctx, None, rd)
    expect_exc("chat_reply_received-", Fail, C["chat_reply_received"],
               b, dict(ctx, ts_fence="2026-07-23T00:00:00+00:00"), None, rd)
    expect_ok("chat_reply_contains+", C["chat_reply_contains"], b, ctx, "Канберра", rd)
    expect_exc("chat_reply_contains-", Fail, C["chat_reply_contains"],
               b, ctx, "старое сообщение", rd)
    expect_ok("chat_reply_matches+", C["chat_reply_matches"], b, ctx, r"Канберр\w", rd)
    expect_ok("new_commits+", C["new_commits"], b, ctx, None, rd)
    expect_ok("new_commits+path", C["new_commits"], b, ctx, "web/style.css", rd)
    expect_exc("new_commits-path", Fail, C["new_commits"],
               b, ctx, "web/nonexistent.js", rd)
    expect_exc("new_commits-", Fail, C["new_commits"],
               b, dict(ctx, before_sha="HEAD"), None, rd)
    expect_exc("new_commits-blocked", Blocked, C["new_commits"],
               b, {k: v for k, v in ctx.items() if k != "before_sha"}, None, rd)
    expect_ok("repo_clean_file+", C["repo_clean_file"], b, ctx, "web/style.css", rd)
    expect_ok("css_var_changed+", C["css_var_changed"], b, ctx, "--user-bubble-from", rd)
    expect_exc("css_var_changed-", Fail, C["css_var_changed"],
               b, ctx, "--user-bubble-to", rd)
    expect_ok("css_var_equals+", C["css_var_equals"], b, ctx, "--user-bubble-to", rd)
    expect_exc("css_var_equals-", Fail, C["css_var_equals"],
               b, ctx, "--user-bubble-from", rd)
    expect_exc("css_var_drift", Drift, C["css_var_changed"],
               b, dict(ctx, css_snapshot={"--nope": "x"}), "--nope", rd)
    expect_ok("computed_style+", C["computed_style"], b, ctx, "changed", rd)
    expect_exc("computed_style-", Fail, C["computed_style"], b, ctx, "restored", rd)
    expect_ok("pid_changed+", C["pid_changed"], b, ctx, None, rd)
    expect_exc("pid_changed-", Fail, C["pid_changed"],
               b, dict(ctx, before_pid=222), None, rd)
    # before_pid пришёл строкой из shell-захвата — не должно давать ложный PASS
    expect_exc("pid_changed-str", Fail, C["pid_changed"],
               b, dict(ctx, before_pid="222"), None, rd)
    expect_exc("pid_changed-blocked", Blocked, C["pid_changed"],
               b, {k: v for k, v in ctx.items() if k != "before_pid"}, None, rd)
    expect_ok("supervisor_ready+", C["supervisor_ready"], b, ctx, None, rd)
    expect_ok("state_flag_restored+", C["state_flag_restored"],
              b, ctx, "bg_consciousness_enabled", rd)
    expect_exc("state_flag_restored-", Fail, C["state_flag_restored"],
               b, dict(ctx, flags_before={"bg_consciousness_enabled": True}),
               "bg_consciousness_enabled", rd)
    expect_ok("bg_toggle_evidence+", C["bg_toggle_evidence"], b, ctx, None, rd)
    expect_ok("memory_contains+", C["memory_contains"], b, ctx, "QA-abc123", rd)
    expect_exc("memory_contains-", Fail, C["memory_contains"], b, ctx, "QA-zzz", rd)
    expect_ok("file_exists+", C["file_exists"], b, ctx, "data/memory/notes.md", rd)
    expect_exc("file_exists-", Fail, C["file_exists"], b, ctx, "data/nope.md", rd)
    expect_ok("file_contains+", C["file_contains"],
              b, ctx, "data/memory/notes.md::маркер", rd)
    expect_ok("lifecycle_succeeded+", C["lifecycle_succeeded"], b, ctx,
              "hello-widget", rd)
    expect_exc("lifecycle_succeeded-", Fail, C["lifecycle_succeeded"], b, ctx,
               "no-such-skill", rd)
    expect_exc("hub_not_installed-", Fail, C["hub_not_installed"], b, ctx,
               "hello-widget", rd)
    expect_ok("hub_not_installed+", C["hub_not_installed"], b, ctx,
              "absent-skill", rd)
    # точное сравнение по name: префикс другого скилла не должен ловиться
    expect_ok("hub_not_installed+prefix", C["hub_not_installed"], b, ctx,
              "hello-widget-pro", rd)
    expect_ok("project_exists+", C["project_exists"], b, ctx, "QA-Project-abc123", rd)
    expect_exc("project_exists-", Fail, C["project_exists"], b, ctx, "QA-none", rd)
    expect_ok("safety_mode_unchanged+", C["safety_mode_unchanged"], b, ctx, None, rd)
    expect_exc("safety_mode_unchanged-", Fail, C["safety_mode_unchanged"],
               b, dict(ctx, settings_safety_before="off"), None, rd)
    expect_ok("settings_unchanged+", C["settings_unchanged"], b, ctx, None, rd)
    expect_exc("settings_unchanged-sha", Fail, C["settings_unchanged"],
               b, dict(ctx, settings_sha_before="deadbeef"), None, rd)
    expect_exc("settings_unchanged-blocked", Blocked, C["settings_unchanged"],
               b, {k: v for k, v in ctx.items() if k != "settings_sha_before"},
               None, rd)
    # порча JSON = breach (Fail, не error) — чтобы сработал CRITICAL-restore
    sp = TMP / "data/settings.json"
    orig = sp.read_bytes()
    sp.write_text("{ битый json", encoding="utf-8")
    expect_exc("settings_unchanged-corrupt", Fail, C["settings_unchanged"],
               b, ctx, None, rd)
    sp.write_bytes(orig)
    expect_ok("refusal_evidence+result", C["refusal_evidence"], b, ctx_refusal, None, rd)
    expect_ok("refusal_evidence+tools", C["refusal_evidence"], b, ctx_tools, None, rd)
    expect_exc("refusal_evidence-", Fail, C["refusal_evidence"], b, ctx, "xyzmarker", rd)
    expect_ok("cost_recorded+", C["cost_recorded"], b, ctx, None, rd)
    expect_exc("cost_recorded-", Fail, C["cost_recorded"], b, ctx_failed, None, rd)

    # Пайплайн целиком: frontmatter -> контекст -> checks.json + exit code
    case = TMP / "999-pipe.md"
    case.write_text("""---
id: 999
title: pipeline test
channel: api
timeout_min: 1
verdict: code
checks:
  - task_completed
  - result_contains: "391"
  - result_contains: "нет такого"
---
тело
""", encoding="utf-8")
    prd = TMP / "run/999"
    prd.mkdir(parents=True)
    (prd / "context.json").write_text(json.dumps(ctx), encoding="utf-8")
    code = checks.run_case_checks(TMP / "run", case)
    (PASSED if code == 1 else FAILED).append(
        f"pipeline: exit={code} (ожидался 1: один чек fail)")
    saved = json.loads((prd / "checks.json").read_text(encoding="utf-8"))
    (PASSED if [r["status"] for r in saved["results"]] == ["ok", "ok", "fail"]
     else FAILED).append("pipeline: checks.json статусы ok,ok,fail")

    # Пустой список checks -> BLOCKED (exit 2), не ложный PASS
    empty_case = TMP / "998-empty.md"
    empty_case.write_text("---\nid: 998\ntitle: empty\nchannel: api\n"
                          "timeout_min: 1\nverdict: code\nchecks:\n---\nтело\n",
                          encoding="utf-8")
    (TMP / "run/998").mkdir(parents=True)
    (PASSED if checks.run_case_checks(TMP / "run", empty_case) == 2
     else FAILED).append("empty-checks: exit=2 (BLOCKED)")

    # fail доминирует над drift: 060-подобный сценарий
    prio_case = TMP / "997-prio.md"
    prio_case.write_text("---\nid: 997\ntitle: prio\nchannel: api\ntimeout_min: 1\n"
                         "verdict: code\nchecks:\n  - state_flag_restored: gone_flag\n"
                         "  - result_contains: \"нет\"\n---\nтело\n", encoding="utf-8")
    prio_rd = TMP / "run/997"
    prio_rd.mkdir(parents=True)
    # state_flag_restored -> drift (флага нет в state.json); result_contains -> fail
    (prio_rd / "context.json").write_text(json.dumps(
        dict(ctx, flags_before={"gone_flag": True})), encoding="utf-8")
    code_prio = checks.run_case_checks(TMP / "run", prio_case)
    (PASSED if code_prio == 1 else FAILED).append(
        f"priority: fail доминирует над drift (exit={code_prio}, ожидался 1)")

    # _unquote: # внутри кавычек не режется
    (PASSED if checks._unquote('"a # b"') == "a # b" else FAILED).append(
        "_unquote: # в кавычках сохранён")
    (PASSED if checks._unquote("foo  # коммент") == "foo" else FAILED).append(
        "_unquote: хвостовой комментарий срезан")

    srv.shutdown()
    print(f"\n=== {len(PASSED)} passed, {len(FAILED)} failed ===")
    for f in FAILED:
        print("FAILED:", f)
    sys.exit(1 if FAILED else 0)


if __name__ == "__main__":
    main()
