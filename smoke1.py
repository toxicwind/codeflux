#!/usr/bin/env python3
"""Smoke tests for codeflux fork improvements. Run on awrawr-pc."""
import io
import sys

F = "/home/toxic/sovereign/codeflux/forks"
results = []


def check(name, fn):
    try:
        fn()
        results.append((name, "PASS"))
    except Exception as e:  # noqa: BLE001
        results.append((name, "FAIL: %s: %s" % (type(e).__name__, str(e)[:160])))


def t_patch_struct():
    sys.path.insert(0, F + "/python-patch")
    from patch_struct import StructuredPatchSet
    d = ("--- a/app.py\n+++ b/app.py\n@@ -1,3 +1,4 @@\n"
         " x = 1\n-y = 2\n+y = 3\n+z = 4\n")
    ps = StructuredPatchSet(io.StringIO(d))
    assert ps.errors == 0, "parse errors: %s" % ps.errors
    dd = ps.to_dict()
    assert len(dd["files"]) == 1
    hunk = dd["files"][0]["hunks"][0]
    tags = [ln["tag"] for ln in hunk["lines"]]
    assert tags == ["ctx", "del", "add", "add"], tags
    rep = ps.apply_report(root="/tmp/cf-shadow-test")
    assert isinstance(rep["ok"], bool)


def t_mutate():
    sys.path.insert(0, F + "/patchling")
    from patchling.mutate import mutate_diff, mutate_stream, RULE_NAMES
    assert len(RULE_NAMES) == 5, RULE_NAMES
    files = {"app.py": "def hello():\n    pass\n"}
    g1, d1 = mutate_diff(files, seed=3)
    g2, d2 = mutate_diff(files, seed=3)
    assert (g1, d1) == (g2, d2) and d1, "not deterministic / empty"
    assert d1.startswith("--- a/app.py"), d1.splitlines()[0]
    steps = list(mutate_stream({"app.py": "def hello():\n    pass\n",
                                "c.py": "N = 1\n"}, n=4, seed=5))
    assert len(steps) == 4 and all(s["diff"] for s in steps)
    print("   sample goal:", g1)


def t_moulti_stream_cli():
    sys.path.insert(0, F + "/moulti/src")
    from moulti.cli import build_arg_parser
    p = build_arg_parser()
    a = p.parse_args(["stream", "--dry-run"])
    assert a.func.__name__ == "stream" and a.dry_run is True
    b = p.parse_args(["step", "add", "x", "--title", "t"])
    assert b.func is not None  # pre-existing step CLI intact


def t_watchfiles_import():
    sys.path.insert(0, F + "/watchfiles")
    import watchfiles  # noqa: F401
    from watchfiles.codeflux import ChangeEvent  # noqa: F401


check("python-patch StructuredPatchSet", t_patch_struct)
check("patchling mutate (offline, deterministic)", t_mutate)
check("moulti stream CLI wiring", t_moulti_stream_cli)
check("watchfiles import (+codeflux module)", t_watchfiles_import)

print("SMOKE RESULTS:")
for name, res in results:
    print("  %-42s %s" % (name, res))
