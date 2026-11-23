# -*- coding: utf-8 -*-
"""Compare AI-style marker density in our prose against the five awarded C-problem
papers of the same competition (AsterLink 2025 autumn). The comparison is the only
honest proxy we have for the organiser's AIGC screen: a human prize-winning corpus
measured with the same yardstick."""
import io
import json
import os
import re
import statistics as st

BENCH = r"_bench"
OURS = os.path.join(BENCH, "OURS.txt")
PAPERS = ["CSHUWEICUP2551760.txt", "CSHUWEICUP2556711.txt", "CSHUWEICUP2556821.txt",
          "CSHUWEICUP2559001.txt", "CSHUWEICUP2561635.txt"]

MARKERS = [
    ("em dash", r"---|\u2014"),
    ("semicolon", r";"),
    ("rather than", r"\brather than\b"),
    ("not X but Y", r"\bnot\b[^.;]{0,60}\bbut\b"),
    ("the fact that", r"\bthe fact that\b"),
    ("it is worth noting", r"\bit is worth (noting|stressing)\b"),
    ("crucially/importantly", r"\b(crucially|importantly|notably)\b"),
    ("therefore/thus/hence", r"\b(therefore|thus|hence)\b"),
    ("however/moreover/furthermore", r"\b(however|moreover|furthermore)\b"),
    ("first/second/third", r"\b(first|second|third)\b"),
    ("triple comma list", r"\b\w+,\s+\w+,\s+and\s+\w+"),
    ("we do not claim", r"\bwe do not claim\b"),
]


def load(path):
    t = io.open(path, encoding="utf-8", errors="replace").read()
    # drop reference lists and appendix-ish tails so we compare prose to prose
    t = re.split(r"\bReferences\b", t)[0]
    return t


def metrics(t):
    words = len(t.split())
    out = {"words": words}
    for name, pat in MARKERS:
        n = len(re.findall(pat, t, re.I))
        out[name] = 1000.0 * n / max(words, 1)
    sents = [s for s in re.split(r"(?<=[.!?])\s+", t) if len(s.split()) > 3]
    lens = [len(s.split()) for s in sents]
    out["sent_cv"] = st.pstdev(lens) / st.mean(lens) if lens else 0.0
    out["sent_mean"] = st.mean(lens) if lens else 0.0
    return out


rows = {}
rows["ours"] = metrics(load(OURS))
for p in PAPERS:
    rows[p.replace(".txt", "")] = metrics(load(os.path.join(BENCH, p)))

names = [k for k, _ in MARKERS] + ["sent_cv", "sent_mean"]
human = [rows[p.replace(".txt", "")] for p in PAPERS]

print("%-30s %10s %10s %10s %8s" % ("marker (per 1k words)", "ours", "human mean",
                                    "human max", "verdict"))
print("-" * 76)
for n in names:
    o = rows["ours"][n]
    h = [r[n] for r in human]
    hm, hx = st.mean(h), max(h)
    verdict = "above max" if o > hx else ("above mean" if o > hm else "within")
    print("%-30s %10.3f %10.3f %10.3f %8s" % (n, o, hm, hx, verdict))

print("\nwords: ours %d, human %s" % (rows["ours"]["words"],
                                      [r["words"] for r in human]))

out = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "_aigc_bench.json")
io.open(out, "w", encoding="utf-8").write(json.dumps(rows, indent=2, ensure_ascii=False))
print("\nwritten", out)
