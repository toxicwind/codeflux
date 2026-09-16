"""codeflux: a live, code-forward streaming system.

Pipeline: file changes -> transformed patches -> streamed output.

- ``watcher``: file watching (forked watchfiles structured events, stdlib
  poll fallback)
- ``differ``: before/after snapshots -> unified diffs -> structured patches
  (forked python-patch)
- ``transform``: apply + verify patches on a shadow tree (forked
  python-patch / patchling smartapply)
- ``server``: stdlib SSE endpoint broadcasting patch events as JSON
- ``tui``: drive the forked moulti TUI from the event stream
- ``demo``: synthetic code updates streamed end-to-end

Fork resolution: when a fork is properly installed (e.g. in codeflux/.venv)
its installed package wins; otherwise the source trees under forks/ are put
on sys.path so the pipeline also runs on a bare interpreter.
"""
import os
import sys


def _bootstrap() -> None:
    import importlib.util

    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    forks = os.path.join(here, "forks")

    def ensure(modname: str, forkdir: str) -> None:
        if importlib.util.find_spec(modname) is None and os.path.isdir(forkDir := forkdir):
            sys.path.insert(0, forkDir)

    ensure("watchfiles", os.path.join(forks, "watchfiles"))
    ensure("patch_struct", os.path.join(forks, "python-patch"))
    ensure("patchling", os.path.join(forks, "patchling"))
    ensure("moulti", os.path.join(forks, "moulti", "src"))


_bootstrap()

__version__ = "0.1.0"
__all__ = ["__version__"]
