# -*- coding: utf-8 -*-
"""Clean em-dash-only measurement (exclude en dash used for page ranges) + Q1 prevalence."""
import io
import json
import os
import re

ROOT = r"E:\数学建模\_swc2026"
BENCH = os.path.join(ROOT, "_bench")
M = os.path.join(ROOT, "SWC2026_C")


def sents(t):
    return [p for p in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9(\\])", t) if len(p.split()) >= 3]


def em_only(t):
    # em dash only: LaTeX --- and unicode EM DASH.  exclude en dash (–/-) page ranges.
    return len(re.findall(r"---|\u2014", t))


print("%-22s %7s %6s %4s %8s %11s" % ("doc", "words", "sents", "em", "per1k", "per100sent"))
print("-" * 64)
rows = []
for f in ["_paper_plain.txt"] + sorted(x for x in os.listdir(BENCH) if x.endswith(".txt")):
    p = os.path.join(ROOT, f) if f.startswith("_") else os.path.join(BENCH, f)
    t = io.open(p, encoding="utf-8").read()
    w, s, e = len(t.split()), len(sents(t)), em_only(t)
    rows.append((f, w, s, e, 1000.0 * e / max(w, 1), 100.0 * e / max(s, 1)))
    print("%-22s %7d %6d %4d %8.3f %11.2f" % (f[:22], w, s, e, rows[-1][4], rows[-1][5]))

ours = rows[0]
hum = rows[1:]
print("-" * 64)
for idx, label in ((4, "per 1k words"), (5, "per 100 sentences")):
    vals = [h[idx] for h in hum]
    print("human %-18s mean %7.3f  max %7.3f   ours %7.3f  -> %s"
          % (label, sum(vals) / len(vals), max(vals), ours[idx],
             "WITHIN" if ours[idx] <= max(vals) else "ABOVE %.2fx" % (ours[idx] / max(vals))))

print("\n=== Q1 bad-frame prevalence ===")
d = json.loads(io.open(os.path.join(M, "data", "p1b_loto.json"), encoding="utf-8").read())
print("  p1b_loto keys:", list(d.keys())[:10])
s = json.dumps(d)
for pat in (r'"n_[a-z_]*":\s*\d+', r'"n_?pos[a-z_]*":\s*\d+'):
    print("  ", re.findall(pat, s)[:8])
tot = re.findall(r'"n_(?:train|test|all|frames|records)[a-z_]*":\s*(\d+)', s)
print("  count-like:", tot[:10])

d2 = json.loads(io.open(os.path.join(M, "data", "up2_p1b.json"), encoding="utf-8").read())
s2 = json.dumps(d2)
print("  up2_p1b 'pos' keys:", re.findall(r'"[a-z_]*pos[a-z_]*":\s*[\d.]+', s2)[:8])
print("  up2_p1b n_ keys  :", re.findall(r'"n_[a-z_]*":\s*\d+', s2)[:8])
