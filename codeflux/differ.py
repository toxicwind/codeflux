"""Snapshot a tree, diff before/after, parse patches into structured data."""
from __future__ import annotations

import difflib
import io
import os
from typing import Any


def _read(p: str) -> str:
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


class Snapshot:
    """Content snapshot of a directory tree (text files)."""

    def __init__(self, root: str):
        self.root = root
        self.files: dict[str, str | None] = {}

    def _all(self) -> list[str]:
        out = []
        for dp, dn, fn in os.walk(self.root):
            dn[:] = [d for d in dn if d != "__pycache__"]
            for f in fn:
                out.append(os.path.relpath(os.path.join(dp, f), self.root))
        return out

    def refresh(self, relpaths: list[str] | None = None) -> None:
        for rel in relpaths if relpaths is not None else self._all():
            ap = os.path.join(self.root, rel)
            self.files[rel] = _read(ap) if os.path.isfile(ap) else None

    def diff_file(self, rel: str, old: str | None, new: str | None) -> str:
        if old == new:
            return ""
        a = (old or "").splitlines(keepends=True)
        b = (new or "").splitlines(keepends=True)
        return "".join(difflib.unified_diff(a, b, fromfile="a/" + rel,
                                           tofile="b/" + rel))


def parse_structured(diff_text: str) -> dict[str, Any]:
    """Parse a unified diff with the forked python-patch structured view."""
    try:
        from patch_struct import StructuredPatchSet

        ps = StructuredPatchSet(io.StringIO(diff_text))
        d = ps.to_dict()
        return {"ok": ps.errors == 0, "errors": ps.errors,
                "warnings": ps.warnings, "patches": d["files"]}
    except Exception as exc:  # noqa: BLE001 - structured error, not a raise
        return {"ok": False, "errors": 1, "warnings": 0, "patches": [],
                "error": str(exc)[:200]}
