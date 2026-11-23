# -*- coding: utf-8 -*-
"""List every semicolon and every first/second/third site with context, so the
rewrites can be chosen by reading, not by regex."""
import io
import os
import re

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
plain = io.open(r"_paper_plain.txt", encoding="utf-8").read()

print("=== semicolons: %d ===" % plain.count(";"))
for i, m in enumerate(re.finditer(r";", plain), 1):
    a = max(0, m.start() - 95)
    b = min(len(plain), m.end() + 95)
    print("%2d ...%s..." % (i, plain[a:b].replace("\n", " ")))

print()
print("=== first/second/third: %d ==="
      % len(re.findall(r"\b(first|second|third)\b", plain, re.I)))
for i, m in enumerate(re.finditer(r"\b(first|second|third)\b", plain, re.I), 1):
    a = max(0, m.start() - 60)
    b = min(len(plain), m.end() + 60)
    print("%2d ...%s..." % (i, plain[a:b].replace("\n", " ")))

print()
print("=== therefore/thus/hence: %d ==="
      % len(re.findall(r"\b(therefore|thus|hence)\b", plain, re.I)))
for i, m in enumerate(re.finditer(r"\b(therefore|thus|hence)\b", plain, re.I), 1):
    a = max(0, m.start() - 60)
    b = min(len(plain), m.end() + 60)
    print("%2d ...%s..." % (i, plain[a:b].replace("\n", " ")))
