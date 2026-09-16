# forks

Each fork is a plain directory with its own `.git` (not a submodule).
Upstream history is preserved; the `upstream` remote points at the original
repo and `origin` at the toxicwind fork.

| dir | upstream | toxicwind fork | codeflux improvement |
|---|---|---|---|
| `watchfiles/` | [samuelcolvin/watchfiles](https://github.com/samuelcolvin/watchfiles) | [toxicwind/codeflux-watchfiles](https://github.com/toxicwind/codeflux-watchfiles) | `watchfiles.codeflux`: debounced, content-hashed structured change events + JSONL |
| `moulti/` | [xavierog/moulti](https://github.com/xavierog/moulti) | [toxicwind/codeflux-moulti](https://github.com/toxicwind/codeflux-moulti) | `moulti stream`: ingest JSONL patch events from stdin into live TUI steps |
| `python-patch/` | [techtonik/python-patch](https://github.com/techtonik/python-patch) | [toxicwind/codeflux-python-patch](https://github.com/toxicwind/codeflux-python-patch) | `patch_struct.StructuredPatchSet`: hunks-as-data, `to_json`, `apply_report` |
| `patchling/` | [255BITS/patchling-py](https://github.com/255BITS/patchling-py) | [toxicwind/codeflux-patchling](https://github.com/toxicwind/codeflux-patchling) | `patchling.mutate`: offline deterministic mutation backend (no LLM/key) |

The integration project itself lives at
[toxicwind/codeflux](https://github.com/toxicwind/codeflux).
