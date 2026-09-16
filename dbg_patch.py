#!/usr/bin/env python3
"""Debug the python-patch parse TypeError with full traceback."""
import io
import sys
import traceback

sys.path.insert(0, "/home/toxic/sovereign/codeflux/forks/python-patch")
import patch

d = ("--- a/app.py\n+++ b/app.py\n@@ -1,3 +1,4 @@\n"
     " x = 1\n-y = 2\n+y = 3\n+z = 4\n")

for label, mk in [("StringIO(str)", lambda: io.StringIO(d)),
                  ("fromstring", lambda: patch.fromstring(d)),
                  ("PatchSet(StringIO)", lambda: patch.PatchSet(io.StringIO(d)))]:
    try:
        ps = mk()
        print(label, "-> OK, errors =", ps.errors if ps else "False")
    except Exception:
        print(label, "-> EXC:")
        traceback.print_exc(limit=6)
