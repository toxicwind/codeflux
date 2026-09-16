"""Stdlib SSE server broadcasting patch events as JSON.

Endpoints:
- GET /health   -> {"ok": true, "events": N}
- GET /snapshot -> JSON array of recent events (replay buffer)
- GET /events   -> text/event-stream; replays history, then streams live
"""
from __future__ import annotations

import json
import queue
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


class EventBus:
    def __init__(self, history: int = 500):
        self._hist: deque = deque(maxlen=history)
        self._subs: list[queue.Queue] = []
        self._lock = threading.Lock()
        self.count = 0
        self._delivered = 0

    def mark_delivered(self) -> None:
        """Record one event flushed to a subscriber's socket."""
        with self._lock:
            self._delivered += 1

    @property
    def delivered(self) -> int:
        with self._lock:
            return self._delivered

    def wait_delivered(self, target: int, timeout_s: float = 10.0) -> bool:
        """Block until at least ``target`` events were flushed to subscribers.

        Observable-condition wait (no fixed sleep): returns True as soon as
        the count is reached, False on timeout.
        """
        end = time.monotonic() + timeout_s
        while time.monotonic() < end:
            if self.delivered >= target:
                return True
            time.sleep(0.02)
        return self.delivered >= target

    def publish(self, event: dict[str, Any]) -> None:
        with self._lock:
            self.count += 1
            self._hist.append(event)
            dead = []
            for q in self._subs:
                try:
                    q.put_nowait(event)
                except queue.Full:
                    dead.append(q)
            self._subs = [q for q in self._subs if q not in dead]

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=1000)
        with self._lock:
            self._subs.append(q)
        return q

    def history(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._hist)


def make_handler(bus: EventBus):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a: Any) -> None:  # quiet
            pass

        def _json(self, obj: Any, code: int = 200) -> None:
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/health":
                return self._json({"ok": True, "events": bus.count})
            if self.path == "/snapshot":
                return self._json(bus.history())
            if self.path == "/events":
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.end_headers()
                q = bus.subscribe()
                try:
                    for ev in bus.history():
                        self.wfile.write(f"data: {json.dumps(ev)}\n\n".encode())
                        self.wfile.flush()
                        bus.mark_delivered()
                    while True:
                        ev = q.get()
                        self.wfile.write(f"data: {json.dumps(ev)}\n\n".encode())
                        self.wfile.flush()
                        bus.mark_delivered()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                return
            return self._json({"error": "not found"}, 404)

    return Handler


def serve(bus: EventBus, port: int = 8765,
          host: str = "127.0.0.1") -> ThreadingHTTPServer:
    srv = ThreadingHTTPServer((host, port), make_handler(bus))
    threading.Thread(target=srv.serve_forever, daemon=True,
                     name="codeflux-sse").start()
    return srv
