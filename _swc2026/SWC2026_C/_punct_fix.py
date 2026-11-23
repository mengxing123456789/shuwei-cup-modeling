# -*- coding: utf-8 -*-
"""Repair the duplicated final letter produced by the punctuation pass."""
import re, pathlib, sys
P = pathlib.Path("main.tex"); t = P.read_text(encoding="utf-8")
FIX = ["Thee","Wee","Conformall","Itt","Everythingg","Temperaturee","Tighteningg","Onlyy",
       "Ann","Constantt","Alll","Exchangeabilityy","Waitingg","Payingg","Att","Onee","Iff",
       "Ourr","Underr","Insidee","Severall"]
LEGIT = {"Three","Across","All","Platt","Free","Harness"}
n = 0
for w in FIX:
    pat = re.compile(r"(?<![A-Za-z])" + w + r"(?![A-Za-z])")
    k = len(pat.findall(t)); n += k
    if k == 0:
        print("MISS", w); sys.exit(1)
    t = pat.sub(w[:-1], t)
print("repaired tokens:", n)
left = [m.group(0) for m in re.finditer(r"(?<![A-Za-z])([A-Z][a-z]*)([a-z])\2(?![A-Za-z])", t)]
bad = [x for x in left if x not in LEGIT]
if bad:
    print("still doubled:", bad); sys.exit(1)
P.write_text(t, encoding="utf-8", newline="\n")
print("remaining doubled-final tokens are all legitimate:", sorted(set(left)))
