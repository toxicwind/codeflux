#!/bin/bash
# codeflux build job v3: seed real pip via uv (with --no-cache), then use
# plain pip for everything. uv's local archive cache is unreliable here.
# Logs to build_venv.log. Safe to re-run.
set -u
CF=/home/toxic/sovereign/codeflux
LOG=$CF/build_venv.log
exec > >(tee -a "$LOG") 2>&1
echo "=== codeflux build v3 start $(date -u +%FT%TZ)"
cd "$CF"
VPY=$CF/.venv/bin/python
if [ ! -x "$CF/.venv/bin/pip" ]; then
  uv pip install --no-cache --python "$VPY" pip 2>&1 | tail -1
fi
PIP=$CF/.venv/bin/pip
WHEEL=$(ls -t "$CF/dist"/watchfiles-*.whl 2>/dev/null | head -1)
if [ -z "$WHEEL" ]; then
  uv pip install --no-cache --python "$VPY" maturin 2>&1 | tail -1
  (cd "$CF/forks/watchfiles" && "$VPY" -m maturin build --release -o "$CF/dist" 2>&1 | tail -2)
  WHEEL=$(ls -t "$CF/dist"/watchfiles-*.whl 2>/dev/null | head -1)
fi
echo "wheel: ${WHEEL:-NONE}"
if [ -n "$WHEEL" ]; then
  $PIP install -q --force-reinstall "$WHEEL" 2>&1 | tail -2
fi
echo "--- pip install moulti fork (editable)"
(cd "$CF/forks/moulti" && $PIP install -q -e . 2>&1 | tail -2)
echo "--- pip install patchling fork (editable)"
(cd "$CF/forks/patchling" && ($PIP install -q -e . 2>&1 | tail -2 || $PIP install -q -e . --no-deps 2>&1 | tail -2))
echo "--- verify imports"
"$VPY" -c "import watchfiles; print('watchfiles OK', watchfiles.__version__)"
"$VPY" -c "from watchfiles.codeflux import watch_events, ChangeEvent; print('watchfiles.codeflux OK')"
"$VPY" -c "import moulti.streaming; print('moulti.streaming OK')"
"$VPY" -c "import patchling.mutate; from patchling import smartapply; print('patchling OK')"
"$VPY" -c "import sys; sys.path.insert(0, '$CF/forks/python-patch'); from patch_struct import StructuredPatchSet; print('patch_struct OK')"
echo "=== codeflux build v3 done $(date -u +%FT%TZ)"
