# -*- coding: utf-8 -*-
"""Quantify AI-style markers in the paper's prose (English analogues of the
lieflat-less-ai-tone indicators) so the AIGC risk can be judged with numbers."""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
PLAIN = os.path.join(os.path.dirname(PROJ), "_paper_plain.txt")

txt = io.open(PLAIN, encoding="utf-8").read()
words = len(txt.split())
per_k = lambda n: 1000.0 * n / max(words, 1)

def count(pat, flags=re.I):
    return len(re.findall(pat, txt, flags))

items = [
    ("em dash (--- or --)", r"---|--"),
    ("semicolon", r";"),
    ("colon as prompt", r":\s"),
    ("not X but Y", r"\bnot\b[^.;]{0,60}\bbut\b"),
    ("X is not Y, it is Z", r"\bis not\b[^.;]{0,60}\bit is\b"),
    ("rather than", r"\brather than\b"),
    ("more than (comparative)", r"\bmore than\b"),
    ("the fact that", r"\bthe fact that\b"),
    ("it is worth noting", r"\bit is worth (noting|stressing)\b"),
    ("In this paper", r"\bin this (paper|work|section)\b"),
    ("crucially / importantly", r"\b(crucially|importantly|notably)\b"),
    ("therefore / thus / hence", r"\b(therefore|thus|hence)\b"),
    ("however / moreover / furthermore", r"\b(however|moreover|furthermore)\b"),
    ("three-item list with commas", r"\b\w+,\s+\w+,\s+and\s+\w+"),
    ("hedge: we do not claim", r"\bwe do not claim\b"),
    ("first/second/third", r"\b(first|second|third)\b"),
    ("the key/crucial point", r"\b(key|crucial|central) (point|insight|observation)\b"),
]
print("plain words %d" % words)
print("%-42s %6s %8s" % ("marker", "n", "per 1k"))
for name, pat in items:
    n = count(pat)
    print("%-42s %6d %8.2f" % (name, n, per_k(n)))

print("\nsentence stats")
sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", txt) if len(s.strip()) > 3]
lens = [len(s.split()) for s in sents]
import statistics as st
print("  sentences %d  mean %.1f  sd %.1f  cv %.3f  min %d  max %d"
      % (len(sents), st.mean(lens), st.pstdev(lens),
         st.pstdev(lens) / st.mean(lens), min(lens), max(lens)))
print("  sentences > 40 words: %d" % sum(1 for x in lens if x > 40))
print("  sentences < 8 words: %d" % sum(1 for x in lens if x < 8))

print("\nrepeated sentence openings (first 3 words)")
from collections import Counter
c = Counter(" ".join(s.split()[:3]).lower() for s in sents)
for k, v in c.most_common(12):
    if v >= 4:
        print("  %-40s %d" % (k, v))
