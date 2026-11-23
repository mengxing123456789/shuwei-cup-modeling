# -*- coding: utf-8 -*-
"""Punctuation pass: semicolon -> period only where it joins two independent clauses,
and paired em-dashes -> parentheses.  Refuses to write if any guard fails."""
import re, pathlib, sys

P = pathlib.Path("main.tex")
t = P.read_text(encoding="utf-8")
orig = t

# --- regions that must not be touched -------------------------------------
def protected_spans(s):
    spans = []
    for env in ("tabular", "longtable", "lstlisting", "equation", "align", "figure", "table"):
        for m in re.finditer(r"\\begin\{%s\*?\}.*?\\end\{%s\*?\}" % (env, env), s, re.S):
            spans.append((m.start(), m.end()))
    m = re.search(r"\\keywords\{.*?\}", s, re.S)
    if m:
        spans.append((m.start(), m.end()))
    return spans

def inside(i, spans):
    return any(a <= i < b for a, b in spans)

STOP = {"and", "so", "but", "or", "which", "whereas", "while", "then", "yet", "nor"}
report_semi, report_dash = [], []

# --- pass 1: semicolons ----------------------------------------------------
spans = protected_spans(t)
out, last = [], 0
for m in re.finditer(r";(\s+)([A-Za-z\\$][^\s]*)", t):
    i = m.start()
    if inside(i, spans):
        continue
    word = m.group(2)
    if not re.match(r"^[a-z]", word):
        continue
    if word.lower() in STOP:
        continue
    if not re.search(r"[A-Za-z0-9\)\}\$]", t[i-1:i]):
        continue
    new = ". " + word[0].upper() + word[1:]
    report_semi.append((t[max(0, i-32):i+len(m.group(2))+1].replace("\n", " "), new))
    out.append(t[last:i]); out.append(new); last = i + len(m.group(1)) + len(m.group(2))
out.append(t[last:]); t = "".join(out)

# --- pass 2: paired em-dashes -> parentheses -------------------------------
def dash_pairs(s):
    pat = re.compile(r"\s---\s([^;:{}()]{2,140}?)\s---\s")
    res, pos = [], 0
    for m in pat.finditer(s):
        if inside(m.start(), protected_spans(s)):
            continue
        body = m.group(1)
        if "\\begin" in body or "\\end" in body or "\n\n" in body:
            continue
        res.append((m.start(), m.end(), body))
    return res

for a, b, body in sorted(dash_pairs(t), reverse=True):
    report_dash.append((t[max(0, a-30):b+30].replace("\n", " "), "(" + body + ")"))
    t = t[:a] + " (" + body + ") " + t[b:]

if t == orig:
    print("nothing changed"); sys.exit(1)
if len(report_semi) < 25 or len(report_semi) > 60:
    print("semicolon count out of band:", len(report_semi)); sys.exit(1)
if len(report_dash) < 4:
    print("dash pair count too low:", len(report_dash)); sys.exit(1)

P.write_text(t, encoding="utf-8", newline="\n")
print("semicolons -> periods:", len(report_semi))
for old, new in report_semi[:6]:
    print("   ...", old, "==>", new)
print("dash pairs -> parentheses:", len(report_dash))
for old, new in report_dash:
    print("   >>", new[:110])
print("delta chars:", len(t) - len(orig))
