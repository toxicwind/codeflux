"""Apply PatchEvents to a shadow tree and verify the result.

Uses the forked python-patch for strict apply, and the forked patchling
``smartapply`` (offline, no key) as the fuzzy second opinion.
"""
from __future__ import annotations

import os
import shutil
from typing import Any


def apply_to_shadow(patch_event: dict[str, Any], shadow_root: str,
                    source_root: str) -> dict[str, Any]:
    """Copy the source file into the shadow tree and apply the event's diff.

    Returns a report dict; never raises.
    """
    from patch_struct import StructuredPatchSet

    os.makedirs(shadow_root, exist_ok=True)
    rel = patch_event["path"]
    src = os.path.join(source_root, rel)
    dst = os.path.join(shadow_root, rel)
    os.makedirs(os.path.dirname(dst) or shadow_root, exist_ok=True)
    if os.path.isfile(src):
        shutil.copy2(src, dst)
    diff = patch_event.get("diff", "")
    if not diff:
        return {"ok": True, "applied_files": [], "note": "empty diff"}
    try:
        ps = StructuredPatchSet(diff)
        if ps.errors:
            return {"ok": False, "applied_files": [],
                    "note": "unparseable diff: %d errors" % ps.errors}
        rep = ps.apply_report(root=shadow_root, strip=1)
        return {"ok": rep["ok"], "applied_files": [rel],
                "note": rep.get("error", "")}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "applied_files": [], "note": str(exc)[:300]}


def smartapply_check(diff_text: str, files: dict[str, str]) -> dict[str, Any]:
    """Offline fuzzy-apply check via the forked patchling (no key needed)."""
    try:
        from patchling import smartapply

        out = smartapply(diff_text, files)
        return {"ok": True, "files": sorted(out.keys())}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:300]}
