#!/usr/bin/env python3
"""Чат-клиент QA-харнесса — повторяет тракт web UI Уробороса.

Отправка = ровно то, что делает интерфейс: вложения грузятся через
POST /api/chat/upload, сообщение уходит по WebSocket type=chat.
Ответы читаются из chat.jsonl (direction=out) после ts_fence.

Использование:
    python3 chat.py send "текст" [--attach /путь/файл ...] [--chat-id 1] [--out send.json]
    python3 chat.py wait --since <ts_fence> [--contains ТЕКСТ] [--timeout 300] [--out reply.json]

Единственная внешняя зависимость: пакет websockets.
"""

import argparse
import asyncio
import datetime
import json
import mimetypes
import pathlib
import sys
import time
import urllib.parse
import urllib.request
import uuid

try:
    import websockets
except ModuleNotFoundError as exc:
    raise SystemExit(
        'Не установлен пакет websockets. Выполни: '
        'python3 -m pip install "websockets>=12,<17"'
    ) from exc

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from checks import ROOT, load_bindings, iter_jsonl  # noqa: E402


def upload_attachment(bindings, path):
    """Multipart-загрузка файла тем же эндпоинтом, что скрепка в UI."""
    p = pathlib.Path(path)
    data = p.read_bytes()
    boundary = uuid.uuid4().hex
    mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{p.name}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        bindings["api_base"] + "/api/chat/upload",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        resp = json.loads(r.read().decode("utf-8"))
    if not resp.get("ok"):
        raise SystemExit(f"upload не удался: {resp}")
    return {"filename": resp["filename"],
            "display_name": resp.get("display_name", p.name),
            "mime": resp.get("mime", mime)}


def websocket_url(api_base):
    """Преобразовать http(s) API base в корректный ws(s) URL."""
    parsed = urllib.parse.urlsplit(api_base)
    schemes = {"http": "ws", "https": "wss", "ws": "ws", "wss": "wss"}
    if parsed.scheme not in schemes or not parsed.netloc:
        raise ValueError(f"некорректный api_base: {api_base!r}")
    path = parsed.path.rstrip("/") + "/ws"
    return urllib.parse.urlunsplit(
        (schemes[parsed.scheme], parsed.netloc, path, "", "")
    )


async def ws_send(bindings, text, attachments, chat_id):
    ws_url = websocket_url(bindings["api_base"])
    cmid = f"qa-{uuid.uuid4().hex[:12]}"
    msg = {
        "type": "chat",
        "content": text,
        "chat_id": chat_id,
        "client_message_id": cmid,
    }
    if attachments:
        msg["attachments"] = attachments
    async with websockets.connect(ws_url, open_timeout=15) as ws:
        await ws.send(json.dumps(msg, ensure_ascii=False))
        # Даём серверу принять кадр до закрытия сокета.
        try:
            await asyncio.wait_for(ws.recv(), timeout=3)
        except (asyncio.TimeoutError, websockets.ConnectionClosed):
            pass
    return cmid


def confirm_delivery(bindings, cmid, timeout=20):
    """Сообщение реально принято? Ищем in-запись с нашим client_message_id в
    chat.jsonl. Если сервер был не готов (bridge initializing) — сообщение
    дропается, in-записи не будет → возвращаем False, чтобы не словить ложный
    FAIL «агент не ответил» на самом деле из-за потерянной отправки."""
    cl = bindings["chat_log"]
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            for rec in iter_jsonl(cl["file"], "chat log"):
                if rec.get("client_message_id") == cmid:
                    return True
        except Exception:
            pass
        time.sleep(2)
    return False


def channel_quiet(bindings, chat_id, quiet_sec=30, max_wait=180):
    """Дождаться тишины out-канала перед отправкой: нет новых out-сообщений
    quiet_sec подряд. Защищает ts-fence от чужих сообщений (wakeup сознания,
    поздний ответ на предыдущий кейс)."""
    cl = bindings["chat_log"]

    def last_out_ts():
        latest = ""
        try:
            for rec in iter_jsonl(cl["file"], "chat log"):
                if rec.get("direction") == cl["out_direction"] and \
                        rec.get("chat_id") in (chat_id, None):
                    ts = rec.get(cl["ts_field"], "")
                    if isinstance(ts, str) and ts > latest:
                        latest = ts
        except Exception:
            pass  # лог может временно отсутствовать (холодный старт/ротация)
        return latest

    deadline = time.monotonic() + max_wait
    prev = last_out_ts()
    quiet_start = time.monotonic()
    while time.monotonic() < deadline:
        time.sleep(5)
        cur = last_out_ts()
        if cur != prev:
            prev = cur
            quiet_start = time.monotonic()
        elif time.monotonic() - quiet_start >= quiet_sec:
            return True
    return False


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def cmd_send(args):
    bindings = load_bindings()
    if not args.no_quiet and not channel_quiet(
            bindings, args.chat_id, quiet_sec=args.quiet_sec):
        print("канал не затих за отведённое время; сообщение не отправлено",
              file=sys.stderr)
        sys.exit(2)
    attachments = [upload_attachment(bindings, a) for a in args.attach]
    ts_fence = now_iso()
    cmid = asyncio.run(ws_send(bindings, args.text, attachments, args.chat_id))
    delivered = confirm_delivery(bindings, cmid, timeout=args.confirm_timeout)
    out = {"client_message_id": cmid, "ts_fence": ts_fence,
           "chat_id": args.chat_id, "attachments": attachments,
           "delivered": delivered}
    print(json.dumps(out, ensure_ascii=False))
    if args.out:
        pathlib.Path(args.out).write_text(
            json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    if not delivered:
        sys.exit(2)  # сообщение не подтверждено сервером — исполнитель ставит BLOCKED


def collect_out(bindings, since, chat_id):
    cl = bindings["chat_log"]
    msgs = []
    try:
        for rec in iter_jsonl(cl["file"], "chat log"):
            if rec.get("direction") != cl["out_direction"]:
                continue
            if rec.get("chat_id") not in (chat_id, None):
                continue
            ts = rec.get(cl["ts_field"], "")
            if isinstance(ts, str) and ts > since:
                msgs.append({"ts": ts, "text": str(rec.get(cl["text_field"], ""))})
    except Exception:
        pass  # рестарт/ротация — просто попробуем в следующем поллинге
    return msgs


def cmd_wait(args):
    bindings = load_bindings()
    deadline = time.monotonic() + args.timeout
    settle_deadline = None
    seen = []
    while time.monotonic() < deadline:
        msgs = collect_out(bindings, args.since, args.chat_id)
        if args.contains:
            if any(args.contains.lower() in m["text"].lower() for m in msgs):
                seen = msgs
                break
        else:
            if len(msgs) > len(seen):
                seen = msgs
                settle_deadline = time.monotonic() + args.settle
            elif seen and settle_deadline and time.monotonic() > settle_deadline:
                break
        time.sleep(args.poll)
    else:
        seen = collect_out(bindings, args.since, args.chat_id)

    found = bool(seen) and (not args.contains or
                            any(args.contains.lower() in m["text"].lower() for m in seen))
    out = {"found": found, "messages": seen}
    print(json.dumps(out, ensure_ascii=False))
    if args.out:
        pathlib.Path(args.out).write_text(
            json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    sys.exit(0 if found else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("send")
    s.add_argument("text")
    s.add_argument("--attach", action="append", default=[])
    s.add_argument("--chat-id", type=int, default=1)
    s.add_argument("--out")
    s.add_argument("--no-quiet", action="store_true",
                   help="не ждать тишины канала перед отправкой")
    s.add_argument("--quiet-sec", type=int, default=30)
    s.add_argument("--confirm-timeout", type=int, default=20,
                   help="сколько ждать подтверждения доставки по client_message_id")
    s.set_defaults(fn=cmd_send)

    w = sub.add_parser("wait")
    w.add_argument("--since", required=True, help="ts_fence из send")
    w.add_argument("--contains")
    w.add_argument("--timeout", type=int, default=300)
    w.add_argument("--settle", type=int, default=20,
                   help="сколько секунд тишины считать концом ответа")
    w.add_argument("--poll", type=int, default=5)
    w.add_argument("--chat-id", type=int, default=1)
    w.add_argument("--out")
    w.set_defaults(fn=cmd_wait)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
