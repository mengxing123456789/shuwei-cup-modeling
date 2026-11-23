# -*- coding: utf-8 -*-
"""Head-to-head: what ALT really has that the main paper does not, and vice versa."""
import io
import json
import os
import re

A = r"E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP"
M = r"E:\数学建模\_swc2026\SWC2026_C"
ROOT = r"E:\数学建模\_swc2026"

alt = io.open(os.path.join(A, "main.tex"), encoding="utf-8").read()
main = io.open(os.path.join(M, "main.tex"), encoding="utf-8").read()

print("=== size ===")
print("  ALT  main.tex %6d B  %4d lines" % (len(alt), alt.count("\n") + 1))
print("  MAIN main.tex %6d B  %4d lines" % (len(main), main.count("\n") + 1))

print("\n=== structure ===")
for name, t in (("ALT", alt), ("MAIN", main)):
    print("  %-4s sections %2d  subsections %2d  tables %2d  figures %2d  equations %2d"
          % (name,
             len(re.findall(r"\\section\{", t)),
             len(re.findall(r"\\subsection\{", t)),
             len(re.findall(r"\\begin\{table\}", t)),
             len(re.findall(r"\\begin\{figure\}", t)),
             len(re.findall(r"\\begin\{equation\}", t)) + len(re.findall(r"\\\[", t))))

print("\n=== em dash in prose (per 1k words) ===")
for name, path in (("ALT", os.path.join(A, "main.tex")), ("MAIN", os.path.join(M, "main.tex"))):
    t = io.open(path, encoding="utf-8").read()
    body = t.split(r"\section{Notation}")[0] if name == "MAIN" else t.split("Appendix A")[0]
    body = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^{}]*\})?", " ", body)
    body = re.sub(r"[{}$\\]", " ", body)
    words = len(body.split())
    em = len(re.findall(r"---|—|–", body))
    print("  %-4s words %5d  em/en dash %3d  = %.3f per 1k" % (name, words, em, 1000.0 * em / max(words, 1)))

print("\n=== verification machinery ===")
for name, root in (("ALT", A), ("MAIN", M)):
    vn = os.path.join(root, "code", "verify_numbers.py")
    if os.path.exists(vn):
        t = io.open(vn, encoding="utf-8").read()
        print("  %-4s verify_numbers.py %6d B  asserts~%d  claims~%d"
              % (name, len(t), len(re.findall(r"\bassert\b", t)),
                 len(re.findall(r"claim\(|add_claim\(", t))))
    else:
        print("  %-4s verify_numbers.py MISSING" % name)

print("\n=== ALT-only content keywords ===")
for kw in ("solver fallback", "epsilon", "Epsilon", "chance constraint",
           "re-plan", "replan", "value of information", "VoI",
           "Beta-Binomial", "Beta–Binomial", "change point", "BOCPD",
           "five mappings", "pass mark", "GroupKFold", "grouped cross"):
    print("  %-22s ALT %3d | MAIN %3d" % (kw, alt.count(kw), main.count(kw)))
