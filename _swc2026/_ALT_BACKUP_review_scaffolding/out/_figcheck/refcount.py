# -*- coding: utf-8 -*-
"""Recount figure/table cross-references and labels in main.tex."""
import re

P = r"E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP\main.tex"
t = open(P, encoding="utf-8").read()

print("ref{fig:  ", len(re.findall(r"\\ref\{fig:", t)))
print("ref{tab:  ", len(re.findall(r"\\ref\{tab:", t)))
print("label{fig:", len(re.findall(r"\\label\{fig:", t)))
print("label{tab:", len(re.findall(r"\\label\{tab:", t)))
print("Fig.      ", len(re.findall(r"\bFig\.", t)))
print("Figure~   ", len(re.findall(r"Figure~", t)))
print("bare Figure occurrences:", len(re.findall(r"\bFigure\b", t)))
for m in re.finditer(r"\bFigure\b", t):
    ln = t[:m.start()].count("\n") + 1
    ctx = t[max(0, m.start()-40):m.start()+60].replace("\n", " ")
    print("   line %d: ...%s..." % (ln, ctx))
print("Table~ref ", len(re.findall(r"Table~\\ref", t)))
for m in re.finditer(r"Table~\\ref\{([^}]+)\}", t):
    ln = t[:m.start()].count("\n") + 1
    print("   Table~ref line %d -> %s" % (ln, m.group(1)))
