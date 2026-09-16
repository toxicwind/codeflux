#!/usr/bin/env python3
"""Live end-to-end verification for codeflux on awrawr-pc.

Runs `python -m codeflux demo` (venv), connects to /events DURING the run,
captures SSE PatchEvents, checks /health + /snapshot, then exercises
`moulti stream --dry-run` with real event JSON.
"""
import json
import subprocess
import sys
import time
import urllib.request

CF = "/home/toxic/sovereign/codeflux"
VPY = CF + "/.venv/bin/python"
PORT = 18771
N = 10

print("== starting live demo ==", flush=True)
proc = subprocess.Popen(
    [VPY, "-m", "codeflux", "demo", "--events", str(N),
     "--interval", "0.5", "--port", str(PORT), "--seed", "11"],
    cwd=CF, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

health = None
for _ in range(150):
    try:
        health = json.load(urllib.request.urlopen(
            "http://127.0.0.1:%d/health" % PORT, timeout=2))
        break
    except Exception:
        if proc.poll() is not None:
            break
        time.sleep(0.2)
assert health and health.get("ok"), "server never healthy: %s" % health
print("health:", health, flush=True)

events = []
t_end = time.time() + 60
req = urllib.request.Request("http://127.0.0.1:%d/events" % PORT)
with urllib.request.urlopen(req, timeout=65) as resp:
    empty_streak = 0
    while len(events) < N and time.time() < t_end:
        line = resp.readline().decode("utf-8", "replace").strip()
        if not line:
            # stream closed (EOF): fail fast instead of spinning to deadline
            empty_streak += 1
            if empty_streak >= 10:
                break
            continue
        empty_streak = 0
        if line.startswith("data:"):
            try:
                events.append(json.loads(line[5:].strip()))
            except Exception:
                pass
print("sse events captured:", len(events), flush=True)
assert len(events) >= N, "expected %d events, got %d" % (N, len(events))

e0 = events[0]
print("event0 keys:", sorted(e0.keys()))
print("event0 path/change/goal:", e0.get("path"), e0.get("change"),
      "|", (e0.get("goal") or "")[:70])
hunks = e0.get("hunks") or []
nlines = sum(len(h.get("lines", [])) for h in hunks)
print("event0 hunks:", len(hunks), "tagged lines:", nlines)
assert hunks and nlines > 0, "no structured hunks in event"
tags = {ln.get("tag") for h in hunks for ln in h.get("lines", [])}
print("line tags seen:", sorted(tags))
assert tags & {"add", "del"}, "no add/del tags: %s" % tags
assert e0.get("sha_before") and e0.get("sha_after"), "missing content hashes"
assert e0["sha_before"] != e0["sha_after"], "hashes identical"

goals = [e.get("goal") for e in events]
print("goals seen (%d):" % len(goals))
for g in goals:
    print("  -", (g or "")[:72])

snap = json.load(urllib.request.urlopen(
    "http://127.0.0.1:%d/snapshot" % PORT, timeout=5))
print("snapshot replay buffer size:", len(snap))
assert len(snap) >= N

rc = proc.wait(timeout=60)
out = proc.stdout.read()
print("demo exit:", rc)
summary = None
for ln in out.splitlines():
    s = ln.strip()
    if s.startswith("DEMO_RESULT"):
        s = s[len("DEMO_RESULT"):].strip()
    if s.startswith("{") and '"events"' in s:
        try:
            summary = json.loads(s)
        except Exception:
            pass
if summary:
    print("demo summary: events=%s duration_s=%s workdir=%s" % (
        summary.get("events"), summary.get("duration_s"),
        summary.get("workdir")))
    import os
    wd = summary.get("workdir") or ""
    if os.path.isdir(wd):
        changed = []
        for rel in sorted(os.listdir(wd)):
            p = os.path.join(wd, rel)
            if os.path.isfile(p):
                changed.append((rel, os.path.getsize(p)))
        print("workdir files after run:", changed)
assert summary and summary.get("ok"), "demo summary not ok"

print("== moulti stream --dry-run ==", flush=True)
moulti_bin = CF + "/.venv/bin/moulti"
payload = "\n".join(json.dumps(e) for e in events[:3]) + "\n"
r = subprocess.run([moulti_bin, "stream", "--dry-run"], input=payload,
                   capture_output=True, text=True, timeout=30)
print("moulti stream rc:", r.returncode)
print("moulti stream out head:", (r.stdout or "")[:400].replace("\n", " | "))
assert r.returncode == 0, r.stderr[:300]

print("LIVE VERIFICATION: ALL OK")
