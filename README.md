# codeflux

A live, code-forward streaming system inside Sovereign: a continuously operating
pipeline that watches code, transforms changes into structured patches, and
streams them live — over SSE and into a TUI.

```
file changes  →  transformed patches  →  streamed output
 (watcher)         (differ+transform)      (SSE endpoint + TUI)
```

## Quickstart

```bash
# demo: synthetic code updates streamed end-to-end (watcher → diff → SSE)
python -m codeflux demo --events 10 --port 8765

# continuously operating mode: watch a real tree, serve patch events
python -m codeflux serve --watch /path/to/tree --port 8765

# render the live stream in the moulti TUI (needs a terminal)
moulti init
python -m codeflux tui --port 8765
```

Endpoints: `GET /health`, `GET /snapshot` (replay buffer), `GET /events` (SSE).

## Architecture

| Stage | Module | Fork powering it |
|---|---|---|
| file watcher / live-reload | `codeflux/watcher.py` | `forks/watchfiles` — new `watchfiles.codeflux` structured events (debounced, content-hashed, JSONL) |
| TUI streaming diffs/logs | `codeflux/tui.py` | `forks/moulti` — new `moulti stream` subcommand ingests JSONL patch events into live steps |
| patch parse/apply | `codeflux/differ.py`, `codeflux/transform.py` | `forks/python-patch` — new `StructuredPatchSet` (hunks-as-data, `apply_report`) |
| code transformation | `codeflux/demo.py` | `forks/patchling` — new offline deterministic `patchling.mutate` backend (no LLM/key) |

`codeflux/server.py` is a stdlib-only SSE server (`EventBus` + `ThreadingHTTPServer`,
no dependencies). The watcher falls back to a stdlib mtime poller when the
watchfiles Rust extension is not built, so the pipeline runs anywhere.

## Forks

Each fork lives in `forks/<name>/` as a plain directory with its own `.git`
(not submodules), pushed to its own repo — see `forks/README.md`.

## Improvement backlog

- [ ] `codeflux serve` as a pitchfork service watching the sovereign tree
- [ ] websocket transport alongside SSE (bidirectional control: pause/replay)
- [ ] moulti `stream --as-diff` rendering diffs with delta colors
- [ ] watchfiles: build + publish the Rust extension in CI for the fork
- [ ] patchling.mutate: more rules (extract function, reorder imports, type-annotate)
- [ ] event persistence: append patch events to a local parquet log for replay
- [ ] auth/token on the SSE endpoint for non-localhost exposure
