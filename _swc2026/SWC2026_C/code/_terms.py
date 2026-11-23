import io
import re
import sys

p = sys.argv[1] if len(sys.argv) > 1 else "main.tex"
t = io.open(p, encoding="utf-8").read()
body = t.split("\\section{Notation}")[0]
terms = [
    "time interval",
    "product state",
    "wait time",
    "compute cost",
    "computational cost",
    "valid protocol",
    "representative point",
    "21 keypoints",
    "retention",
    "on-time",
    "tardiness",
    "overrun",
    "reserved idle",
    "censoring",
    "invalid action",
    "elapsed",
    "review",
]
for k in terms:
    print("%-22s %d" % (k, len(re.findall(re.escape(k), body, re.I))))
print("body words", len(body.split()))
