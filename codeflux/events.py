"""codeflux event model: JSON-serializable change and patch events."""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any


def _uid() -> str:
    return uuid.uuid4().hex[:12]


@dataclass
class ChangeEvent:
    id: str = field(default_factory=_uid)
    path: str = ""
    change: str = ""  # added | modified | deleted
    sha256: str | None = None
    size: int | None = None
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


@dataclass
class PatchEvent:
    id: str = field(default_factory=_uid)
    path: str = ""
    change: str = ""
    diff: str = ""
    hunks: list = field(default_factory=list)   # flattened structured hunks
    files: list = field(default_factory=list)   # structured per-file patches
    sha_before: str | None = None
    sha_after: str | None = None
    goal: str | None = None  # synthetic/NL goal that produced the change
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())
