#!/usr/bin/env python3
"""Smoke tests round 2: str/bytes normalization, lazy patchling, transform."""
import io
import json
import os
import sys
import tempfile

F = "/home/toxic/sovereign/codeflux/forks"
C = "/home/toxic/sovereign/codeflux"
for _p in (C, F + "/python-patch", F + "/patchling"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

results = []


def check(name, fn):
    try:
        fn()
        results.append((name, "PASS"))
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc(limit=4)
        results.append((name, "FAIL: %s: %s" % (type(e).__name__, str(e)[:160])))


DIFF = ("--- a/app.py\n+++ b/app.py\n@@ -1,2 +1,3 @@\n"
        " x = 1\n-y = 2\n+y = 3\n+z = 4\n")


def t_struct_str():
    from patch_struct import StructuredPatchSet
    ps = StructuredPatchSet(DIFF)  # str input now accepted
    assert ps.errors == 0, ps.errors
    d = ps.to_dict()
    assert len(d["files"]) == 1
    tags = [ln["tag"] for ln in d["files"][0]["hunks"][0]["lines"]]
    assert tags == ["ctx", "del", "add", "add"], tags
    json.dumps(d)  # JSON-safe (bytes decoded)


def t_struct_bytes():
    from patch_struct import StructuredPatchSet
    ps = StructuredPatchSet(io.BytesIO(DIFF.encode()))
    assert ps.errors == 0
    assert ps.to_dict()["files"][0]["source"] == "app.py"


def t_apply_report():
    from patch_struct import StructuredPatchSet
    d = tempfile.mkdtemp(prefix="cf-apply-")
    open(os.path.join(d, "app.py"), "w").write("x = 1\ny = 2\n")
    ps = StructuredPatchSet(DIFF)
    rep = ps.apply_report(root=d, strip=1)
    assert rep["ok"], rep
    content = open(os.path.join(d, "app.py")).read()
    assert "y = 3" in content and "z = 4" in content, content


def t_patchling_lazy():
    import patchling
    from patchling.mutate import mutate_diff  # offline, no openai needed
    g, d = mutate_diff({"a.py": "X = 1\n"}, seed=1)
    assert g and d
    # full lazy API still resolves the attribute name (import may fail only
    # if openai is truly missing — acceptable, recorded not asserted)
    assert "smartapply" in patchling.__all__


def t_transform_shadow():
    from codeflux.transform import apply_to_shadow
    src = tempfile.mkdtemp(prefix="cf-src-")
    shd = tempfile.mkdtemp(prefix="cf-shd-")
    open(os.path.join(src, "app.py"), "w").write("x = 1\ny = 2\n")
    ev = {"path": "app.py", "diff": DIFF}
    rep = apply_to_shadow(ev, shd, src)
    assert rep["ok"], rep
    assert "z = 4" in open(os.path.join(shd, "app.py")).read()


def t_smartapply_offline():
    from codeflux.transform import smartapply_check
    r = smartapply_check(DIFF, {"app.py": "x = 1\ny = 2\n"})
    # offline venv provides openai dep; bare interpreter degrades gracefully
    assert isinstance(r, dict) and "ok" in r, r
    if r["ok"]:
        assert "app.py" in r["files"]


check("StructuredPatchSet str input + to_dict", t_struct_str)
check("StructuredPatchSet bytes input", t_struct_bytes)
check("apply_report real apply", t_apply_report)
check("patchling lazy offline import", t_patchling_lazy)
check("transform.apply_to_shadow", t_transform_shadow)
check("transform.smartapply_check offline", t_smartapply_offline)

print("SMOKE2 RESULTS:")
for name, res in results:
    print("  %-42s %s" % (name, res))
