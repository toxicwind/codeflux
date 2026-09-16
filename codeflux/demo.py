"""Demo mode: synthetic code updates streamed end-to-end.

Seeds a sample project, starts the SSE server + watcher, then applies
deterministic synthetic mutations (forked patchling offline backend) on an
interval. Every real filesystem change is picked up by the watcher,
diffed against the snapshot, parsed into a structured PatchEvent, and
broadcast on the SSE endpoint. Stops after ``events`` patch events.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import threading
import time
from typing import Any

from .differ import Snapshot, parse_structured
from .events import PatchEvent
from .server import EventBus, serve
from .watcher import iter_changes

SAMPLE_FILES = {
    "app.py": '''"""Sample app mutated by the codeflux demo."""


MAX_RETRIES = 3


def greet(name):
    return f"hello {name}"


def main():
    for i in range(MAX_RETRIES):
        print(greet("world"))


if __name__ == "__main__":
    main()
''',
    "utils.py": '''"""Sample utilities."""


def add(a, b):
    return a + b


def slugify(text):
    return text.lower().replace(" ", "-")
''',
    "config.py": '''"""Sample config."""


DEBUG = False
WORKERS = 4
TIMEOUT_S = 30
''',
}


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def _read(ap: str) -> str | None:
    try:
        with open(ap, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return None


def run_demo(events: int = 10, interval: float = 1.5, port: int = 8765,
             seed: int = 7, root: str | None = None) -> dict[str, Any]:
    from patchling.mutate import mutate_stream  # forked patchling, stdlib-only

    t0 = time.monotonic()
    work = root or tempfile.mkdtemp(prefix="codeflux-demo-")
    os.makedirs(work, exist_ok=True)
    for rel, content in SAMPLE_FILES.items():
        with open(os.path.join(work, rel), "w") as f:
            f.write(content)

    bus = EventBus()
    srv = serve(bus, port=port)
    snap = Snapshot(work)
    snap.refresh()  # seed BEFORE the watcher starts: no phantom events

    produced: list[dict] = []
    stop = threading.Event()
    pending_goals: list[str] = []
    # Readiness canary: stock watch() baselines asynchronously; the first
    # real mutation must not land before the watcher is observing, or it is
    # silently missed (measured 3/3 runs -> 9/10 events without this).
    CANARY = ".codeflux-canary"
    watch_ready = threading.Event()

    def watch_loop() -> None:
        for ch in iter_changes(work, debounce_ms=250):
            if stop.is_set():
                break
            rel, ap = ch["path"], ch["abspath"]
            if rel == CANARY:
                # readiness canary: proves the watcher baseline exists and
                # live changes are observed; never published or counted.
                watch_ready.set()
                continue
            old = snap.files.get(rel)
            new = _read(ap)
            if old == new:
                continue
            diff = snap.diff_file(rel, old or "", new or "")
            parsed = parse_structured(diff)
            hunks = [h for p in parsed["patches"] for h in p["hunks"]]
            goal = pending_goals.pop(0) if pending_goals else None
            pe = PatchEvent(path=rel, change=ch["change"], diff=diff,
                            hunks=hunks, files=parsed["patches"],
                            sha_before=_sha(old or ""), sha_after=_sha(new or ""),
                            goal=goal)
            bus.publish(pe.to_dict())
            snap.files[rel] = new
            produced.append(pe.to_dict())
            if len(produced) >= events:
                stop.set()
                break

    wt = threading.Thread(target=watch_loop, daemon=True, name="codeflux-watch")
    wt.start()

    # Prove the watcher is live before the first real mutation.
    with open(os.path.join(work, CANARY), "w") as f:
        f.write("ready\n")
    t_ready = time.monotonic() + 10
    while (not watch_ready.is_set() and not stop.is_set()
           and time.monotonic() < t_ready):
        time.sleep(0.05)

    # synthetic mutator: real file writes, one file per step
    cur = dict(SAMPLE_FILES)
    steps = list(mutate_stream(cur, n=events, seed=seed))
    deadline = time.monotonic() + events * interval + 45
    i = 0
    while not stop.is_set() and time.monotonic() < deadline:
        if i >= len(steps):
            break
        step = steps[i]
        i += 1
        pending_goals.append(step["goal"])
        # handshake: the next write happens only after the watcher has turned
        # THIS write into a patch event, so rapid successive writes can never
        # coalesce into a single event (each write is observed first).
        want = len(produced) + 1
        with open(os.path.join(work, step["path"]), "w") as f:
            f.write(step["files"][step["path"]])
        cur = step["files"]
        t_catch = time.monotonic() + max(interval, 5.0)
        while not stop.is_set() and len(produced) < want \
                and time.monotonic() < t_catch:
            time.sleep(0.05)
        # pace the stream; wake early when done
        end = time.monotonic() + interval
        while not stop.is_set() and time.monotonic() < end:
            time.sleep(0.1)

    stop.set()
    wt.join(timeout=10)
    try:
        os.unlink(os.path.join(work, CANARY))
    except OSError:
        pass
    dt = round(time.monotonic() - t0, 3)
    # drain: don't shut down until every produced event has been flushed to
    # SSE subscribers, so the final event can't be lost to process exit.
    bus.wait_delivered(len(produced), timeout_s=10)
    srv.shutdown()
    summary = {
        "ok": len(produced) >= events,
        "events": len(produced),
        "port": port,
        "workdir": work,
        "duration_s": dt,
        "goals": [p["goal"] for p in produced],
        "sample_event": produced[0] if produced else None,
    }
    return summary


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="codeflux-demo")
    ap.add_argument("--events", type=int, default=10)
    ap.add_argument("--interval", type=float, default=1.5)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args(argv)
    summary = run_demo(events=args.events, interval=args.interval,
                       port=args.port, seed=args.seed)
    print("DEMO_RESULT " + json.dumps(summary)[:4000])
    return 0 if summary["ok"] else 1
