# -*- coding: utf-8 -*-
"""Honest ordinal metric for the AIGC style audit.

The raw regex over-counts badly: in this paper 'second' is mostly a unit of time
('one second', 'a one-second prefix', 'a three-second deadline', 'per second',
'scenario second', '0.6 s'). Those uses are physics, not discourse markers, and
no human writer would avoid them. This script separates them, and also separates
technical ordinals ('first quartile', 'every third frame', 'a second independent
fit') from genuine enumerators ('First, ... / Second, ...').
"""
import collections
import io
import json
import re

PLAIN = r"_paper_plain.txt"
OUT = r"_ord_split.json"

plain = io.open(PLAIN, encoding="utf-8").read()
words = len(plain.split())

# a unit of time immediately before the word, possibly hyphenated
TIME_BEFORE = re.compile(
    r"(\b(half\s+a|a|an|one|two|three|four|quarter|per|each|every|scenario|"
    r"the|another|single|extra|whole)\s*[-‑]?\s*)$", re.I)
TIME_AFTER = ("s", "~s", "-s", "second", "seconds")

buckets = collections.Counter()
examples = collections.defaultdict(list)

for m in re.finditer(r"\b(first|second|third)\b", plain, re.I):
    w = m.group(1).lower()
    before = plain[max(0, m.start() - 24):m.start()]
    after = plain[m.end():m.end() + 12].strip()

    kind = "discourse"
    if w == "second":
        if TIME_BEFORE.search(before):
            kind = "time-unit"
        elif after.lower().startswith(TIME_AFTER) or after[:1].isdigit():
            kind = "time-unit"
        elif after.lower().startswith(("look", "request", "opinion", "pass",
                                       "independent", "fit", "attempt", "round")):
            kind = "ordinal-noun"
    elif w == "third":
        if re.search(r"every\s*[-‑]?\s*$", before, re.I):
            kind = "ordinal-noun"
    elif w == "first":
        if after.lower().startswith(("quartile", "column", "frame", "epoch",
                                     "derivative", "term", "order")):
            kind = "ordinal-noun"

    buckets[kind] += 1
    if len(examples[kind]) < 12:
        examples[kind].append(plain[max(0, m.start() - 55):m.end() + 45]
                              .replace("\n", " "))

total = sum(buckets.values())
rows = {}
print("words %d | raw first/second/third %d = %.3f per 1k (human max 1.616)"
      % (words, total, 1000.0 * total / words))
for k in ("time-unit", "ordinal-noun", "discourse"):
    v = 1000.0 * buckets[k] / words
    rows[k] = {"count": buckets[k], "per_1k": round(v, 3)}
    print("  %-13s %3d  %.3f per 1k" % (k, buckets[k], v))
rows["raw"] = {"count": total, "per_1k": round(1000.0 * total / words, 3)}
rows["words"] = words
rows["examples"] = {k: v for k, v in examples.items()}

print()
for k in ("discourse", "ordinal-noun"):
    print("--- %s ---" % k)
    for e in examples[k]:
        print("   ..." + e + "...")

io.open(OUT, "w", encoding="utf-8").write(json.dumps(rows, indent=2, ensure_ascii=False))
print("\nwritten", OUT)
