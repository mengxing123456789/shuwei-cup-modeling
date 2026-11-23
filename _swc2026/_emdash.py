# -*- coding: utf-8 -*-
"""Resolve the em-dash dispute: per 100 sentences, ours vs ALT vs the 5 awarded papers."""
import io
import os
import re

ROOT = r"E:\数学建模\_swc2026"
BENCH = os.path.join(ROOT, "_bench")
PLAIN = os.path.join(ROOT, "_paper_plain.txt")


def sentences(t):
    # split on sentence-final punctuation followed by space + capital/digit
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9(\\])", t)
    return [p for p in parts if len(p.split()) >= 3]


def metrics(t):
    s = sentences(t)
    em = len(re.findall(r"---|—|–", t))
    words = len(t.split())
    return dict(words=words, sents=len(s), em=em,
                per1k=1000.0 * em / max(words, 1),
                per100s=100.0 * em / max(len(s), 1))


print("%-22s %7s %6s %4s %9s %10s" % ("doc", "words", "sents", "em", "per1k", "per100sent"))
print("-" * 66)
rows = []
ours = metrics(io.open(PLAIN, encoding="utf-8").read())
print("%-22s %7d %6d %4d %9.3f %10.2f" % ("MAIN (ours)", ours["words"], ours["sents"],
                                          ours["em"], ours["per1k"], ours["per100s"]))
hum = []
for f in sorted(os.listdir(BENCH)):
    if not f.endswith(".txt"):
        continue
    t = io.open(os.path.join(BENCH, f), encoding="utf-8").read()
    m = metrics(t)
    hum.append(m)
    print("%-22s %7d %6d %4d %9.3f %10.2f" % (f[:-4], m["words"], m["sents"],
                                              m["em"], m["per1k"], m["per100s"]))
print("-" * 66)
for key, label in (("per1k", "per 1k words"), ("per100s", "per 100 sentences")):
    vals = [h[key] for h in hum]
    mean = sum(vals) / len(vals)
    mx = max(vals)
    print("human %-18s mean %.3f  max %.3f   ours %.3f   -> %s"
          % (label, mean, mx, ours[key],
             "WITHIN" if ours[key] <= mx else "ABOVE (%.2fx)" % (ours[key] / mx)))
