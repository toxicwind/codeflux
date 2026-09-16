"""Watch a tree and yield change dicts.

Prefers the forked watchfiles structured events (Rust notify core); falls back
to a stdlib mtime/size poller when the extension is unavailable, so the
pipeline never depends on a native build to run.
"""
from __future__ import annotations

import os
import time
from typing import Iterator


def _rel(root: str, p: str) -> str:
    return os.path.relpath(p, root)


def iter_watchfiles(root: str, debounce_ms: int = 500) -> Iterator[dict]:
    from watchfiles.codeflux import watch_events

    for ev in watch_events(root, debounce_ms=debounce_ms):
        yield {"path": _rel(root, ev.path), "abspath": ev.path,
               "change": ev.change, "sha256": ev.sha256,
               "size": ev.size, "mtime": ev.mtime}


def iter_poll(root: str, interval: float = 0.5) -> Iterator[dict]:
    def scan() -> dict:
        cur: dict[str, tuple[float, int]] = {}
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in dn if d != "__pycache__"]
            for f in fn:
                p = os.path.join(dp, f)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                cur[p] = (st.st_mtime, st.st_size)
        return cur

    prev = scan()
    while True:
        time.sleep(interval)
        cur = scan()
        for p, meta in cur.items():
            if p not in prev:
                yield {"path": _rel(root, p), "abspath": p, "change": "added"}
            elif prev[p] != meta:
                yield {"path": _rel(root, p), "abspath": p, "change": "modified"}
        for p in prev:
            if p not in cur:
                yield {"path": _rel(root, p), "abspath": p, "change": "deleted"}
        prev = cur


def iter_changes(root: str, debounce_ms: int = 500,
                 poll_interval: float = 0.5) -> Iterator[dict]:
    """Yield change dicts; watchfiles first, stdlib poll fallback."""
    try:
        yield from iter_watchfiles(root, debounce_ms=debounce_ms)
    except Exception:
        yield from iter_poll(root, interval=poll_interval)
