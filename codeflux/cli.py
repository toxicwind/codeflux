"""codeflux CLI: demo | serve | watch | tui."""
from __future__ import annotations

import argparse
import json
import sys
import threading
import urllib.request

from .differ import Snapshot, parse_structured
from .events import PatchEvent
from .server import EventBus, serve
from .watcher import iter_changes


def _read(ap: str):
    try:
        with open(ap, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return None


def cmd_demo(args) -> int:
    from .demo import run_demo

    summary = run_demo(events=args.events, interval=args.interval,
                       port=args.port, seed=args.seed)
    print("DEMO_RESULT " + json.dumps(summary)[:6000])
    return 0 if summary["ok"] else 1


def cmd_serve(args) -> int:
    """Continuously operating mode: watch DIR, serve patch events as SSE."""
    import hashlib

    root = args.watch
    bus = EventBus()
    serve(bus, port=args.port)
    snap = Snapshot(root)
    snap.refresh()
    print(f"codeflux serve: watching {root} -> SSE :{args.port}/events",
          flush=True)

    def sha(s: str) -> str:
        return hashlib.sha256(s.encode()).hexdigest()

    try:
        for ch in iter_changes(root):
            rel, ap = ch["path"], ch["abspath"]
            old = snap.files.get(rel)
            new = _read(ap)
            if old == new:
                continue
            diff = snap.diff_file(rel, old or "", new or "")
            parsed = parse_structured(diff)
            pe = PatchEvent(path=rel, change=ch["change"], diff=diff,
                            hunks=[h for p in parsed["patches"] for h in p["hunks"]],
                            files=parsed["patches"],
                            sha_before=sha(old or ""), sha_after=sha(new or ""))
            bus.publish(pe.to_dict())
            snap.files[rel] = new
            print(f"event {pe.id} {rel} {ch['change']} "
                  f"{len(pe.hunks)} hunks", flush=True)
    except KeyboardInterrupt:
        print("\ncodeflux serve: stopped")
    return 0


def cmd_watch(args) -> int:
    try:
        for ch in iter_changes(args.path):
            print(json.dumps({k: ch[k] for k in ("path", "change")}))
            sys.stdout.flush()
    except KeyboardInterrupt:
        pass
    return 0


def cmd_tui(args) -> int:
    """Consume the SSE stream and render it in the forked moulti TUI."""
    from .tui import feed_moulti

    url = f"http://127.0.0.1:{args.port}/events"

    def event_iter():
        with urllib.request.urlopen(url, timeout=30) as resp:
            buf = b""
            for chunk in resp:
                buf += chunk
                while b"\n\n" in buf:
                    raw, buf = buf.split(b"\n\n", 1)
                    for line in raw.split(b"\n"):
                        if line.startswith(b"data: "):
                            yield json.loads(line[6:])

    res = feed_moulti(event_iter(), dry_run=args.dry_run)
    print(json.dumps(res))
    return 0 if res["ok"] else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="codeflux")
    sub = ap.add_subparsers(required=True, dest="cmd")

    d = sub.add_parser("demo", help="synthetic code updates streamed end-to-end")
    d.add_argument("--events", type=int, default=10)
    d.add_argument("--interval", type=float, default=1.5)
    d.add_argument("--port", type=int, default=8765)
    d.add_argument("--seed", type=int, default=7)
    d.set_defaults(func=cmd_demo)

    s = sub.add_parser("serve", help="watch a dir, serve patch events as SSE")
    s.add_argument("--watch", required=True)
    s.add_argument("--port", type=int, default=8765)
    s.set_defaults(func=cmd_serve)

    w = sub.add_parser("watch", help="print change events as JSONL")
    w.add_argument("path", nargs="?", default=".")
    w.set_defaults(func=cmd_watch)

    t = sub.add_parser("tui", help="render the SSE stream in moulti")
    t.add_argument("--port", type=int, default=8765)
    t.add_argument("--dry-run", action="store_true")
    t.set_defaults(func=cmd_tui)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
