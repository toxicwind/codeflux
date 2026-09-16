"""codeflux integration tests (stdlib only; forks resolved via sys.path)."""
import io
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (ROOT,
           os.path.join(ROOT, "forks", "python-patch"),
           os.path.join(ROOT, "forks", "patchling")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from codeflux.differ import Snapshot, parse_structured  # noqa: E402
from codeflux.events import ChangeEvent, PatchEvent  # noqa: E402
from codeflux.server import EventBus, serve  # noqa: E402


def test_events_json_roundtrip():
    pe = PatchEvent(path="app.py", change="modified", diff="--- a/app.py\n",
                    goal="demo")
    d = json.loads(pe.to_json())
    assert d["path"] == "app.py" and d["goal"] == "demo"
    ce = ChangeEvent(path="x.py", change="added")
    assert json.loads(ce.to_json())["change"] == "added"


def test_snapshot_diff_and_parse(tmp_path=None):
    import tempfile
    d = tempfile.mkdtemp()
    p = os.path.join(d, "a.py")
    open(p, "w").write("x = 1\n")
    snap = Snapshot(d)
    snap.refresh()
    open(p, "w").write("x = 2\n")
    diff = snap.diff_file("a.py", snap.files["a.py"], open(p).read())
    assert "-x = 1" in diff and "+x = 2" in diff
    parsed = parse_structured(diff)
    assert parsed["ok"], parsed
    assert parsed["patches"][0]["hunks"][0]["lines"]


def test_mutate_deterministic():
    from patchling.mutate import mutate_diff, mutate_stream

    files = {"app.py": "def hello():\n    pass\n"}
    g1, d1 = mutate_diff(files, seed=3)
    g2, d2 = mutate_diff(files, seed=3)
    assert (g1, d1) == (g2, d2) and d1
    steps = list(mutate_stream(files, n=3, seed=3))
    assert len(steps) == 3
    assert all(s["diff"] for s in steps)


def test_server_health_and_snapshot():
    bus = EventBus()
    bus.publish({"id": "e1", "path": "a.py"})
    srv = serve(bus, port=18765)
    try:
        health = json.load(urllib.request.urlopen("http://127.0.0.1:18765/health", timeout=5))
        assert health == {"ok": True, "events": 1}
        snap = json.load(urllib.request.urlopen("http://127.0.0.1:18765/snapshot", timeout=5))
        assert snap[0]["id"] == "e1"
    finally:
        srv.shutdown()
