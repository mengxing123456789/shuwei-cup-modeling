# -*- coding: utf-8 -*-
"""Set line 1 of review/07-figures.md to the true byte count (UTF-8, no BOM).

Iterates because the digit count of the number changes the total size.
Verifies: no BOM, first line matches ^BYTES \\d+$, value == os.path.getsize,
last non-empty line is VERDICT: FAIL.
"""
import io
import os
import re

P = r"E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP\review\07-figures.md"

with open(P, "rb") as f:
    raw = f.read()

assert not raw.startswith(b"\xef\xbb\xbf"), "file has a BOM"
text = raw.decode("utf-8")
lines = text.split("\n")
assert lines[0].startswith("BYTES "), "line 1 is not a BYTES line: %r" % lines[0]
body = "\n".join(lines[1:])  # everything after the BYTES line, unchanged

# iterate to a fixed point on the digit count
n = 0
for _ in range(20):
    cand = "BYTES %d\n%s" % (n, body)
    size = len(cand.encode("utf-8"))
    if size == n:
        break
    n = size

out = ("BYTES %d\n%s" % (n, body)).encode("utf-8")
with open(P, "wb") as f:
    f.write(out)

# ---- verify ----
with open(P, "rb") as f:
    chk = f.read()
first3 = chk[:3]
txt = chk.decode("utf-8")
l0 = txt.split("\n")[0]
m = re.match(r"^BYTES (\d+)$", l0)
nonempty = [x for x in txt.split("\n") if x.strip()]
print("first3 bytes      :", first3)
print("line1             :", repr(l0))
print("regex match       :", bool(m))
print("declared          :", int(m.group(1)) if m else None)
print("actual file size  :", os.path.getsize(P))
print("equal             :", bool(m) and int(m.group(1)) == os.path.getsize(P))
print("bom               :", chk.startswith(b"\xef\xbb\xbf"))
print("last non-empty    :", repr(nonempty[-1]))
print("lines             :", len(txt.split("\n")))
print("cjk chars         :", sum(1 for c in txt if "\u4e00" <= c <= "\u9fff"))
