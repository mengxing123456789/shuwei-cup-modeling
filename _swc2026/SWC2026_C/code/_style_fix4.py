# -*- coding: utf-8 -*-
"""Split the last prose semicolons by explicit key, with whitespace-flexible
matching so a line break inside the key does not cause a MISS. Each key holds
exactly one semicolon; that semicolon becomes a full stop and the following word
is capitalised. Nothing else in the file changes."""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.join(os.path.dirname(HERE), "main.tex")
APPLY = "--apply" in sys.argv
src = io.open(MAIN, encoding="utf-8").read()

KEYS = [
    "Part I estimates a hand state and its reliability; Part II extrapolates",
    "An autoencoder front end is worse still (\\slotPSegAEHMMARI{}); multi-scale Ward lands",
    "buys on a heavy-tailed error; Appendix~\\ref{app:ablation} tabulates the four masks",
    "on the same seeds includes zero; Section~\\ref{sec:limits} reads the gap",
    "is the valid protocol flag the statement asks for; the audit in Appendix",
    "the classes score at all; each also leaves its environment unseen",
    "for the fused route; it is the model we would deploy",
    "and \\slotPTCNSeconds{} s of training; its lift of",
    "on capacity pressure; \\textsc{rollout} re-solves",
    "by one wearer; a \\emph{time interval} is the half-open span",
    "are not calibrated and are not fused; they are",
    "on a subset of recordings; EgoPro ships",
    "Nothing else in the protocol enters; three consequences follow",
    "point gate (\\slotPInfoTrueMax{} points); Appendix~\\ref{app:propositions} carries",
    "the segmentation annotation; each is stated where it bears",
    "in the support package; they sit outside the one-command chain",
]


def flex(needle):
    return r"\s+".join(re.escape(t) for t in needle.split())


out = src
n = 0
for key in KEYS:
    m = re.search(flex(key), out)
    if not m:
        print("MISS:", key[:58])
        continue
    seg = m.group(0)
    i = seg.index(";")
    head, tail = seg[:i], seg[i + 1:].lstrip()
    rep = head + ". " + tail[:1].upper() + tail[1:]
    out = out[:m.start()] + rep + out[m.end():]
    n += 1

print("splits applied: %d / %d" % (n, len(KEYS)))
print("semicolons %d -> %d" % (src.count(";"), out.count(";")))

if not APPLY:
    print("\ndry run; pass --apply to write")
    sys.exit(0)
io.open(MAIN, "w", encoding="utf-8", newline="\n").write(out)
print("written", MAIN)
