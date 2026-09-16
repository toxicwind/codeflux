"""Drive the forked moulti TUI from a codeflux event stream."""
from __future__ import annotations

import json
import subprocess
import sys
from typing import Any, Iterable


def feed_moulti(events: Iterable[dict[str, Any]],
                dry_run: bool = False) -> dict[str, Any]:
    """Pipe codeflux patch events as JSONL into ``moulti stream``.

    Falls back to printing JSONL on stdout when moulti is not installed.
    """
    cmd = ["moulti", "stream"] + (["--dry-run"] if dry_run else [])
    try:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, text=True)
    except FileNotFoundError:
        for ev in events:
            sys.stdout.write(json.dumps(ev) + "\n")
        return {"ok": False, "note": "moulti not installed; printed JSONL"}
    assert proc.stdin is not None
    n = 0
    for ev in events:
        line = json.dumps({
            "type": "patch",
            "id": ev.get("id"),
            "title": f"{ev.get('path')} {ev.get('change')}",
            "file": ev.get("path"),
            "diff": ev.get("diff", ""),
            "goal": ev.get("goal"),
        }) + "\n"
        proc.stdin.write(line)
        proc.stdin.flush()
        n += 1
    proc.stdin.close()
    proc.wait()
    return {"ok": proc.returncode == 0, "events": n}
