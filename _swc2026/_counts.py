# -*- coding: utf-8 -*-
"""Report the exact slot and script counts for README sync."""
import io
import os
import re

C = r"E:\数学建模\_swc2026\SWC2026_C"
PAT = re.compile(r"\\newcommand\{\\slot(\w+)\}")


def count(p):
    t = io.open(p, encoding="utf-8").read()
    return len(PAT.findall(t))


print("slots.tex      :", count(os.path.join(C, "slots.tex")))
print("slots.full.tex :", count(os.path.join(C, "slots.full.tex")))
print("code scripts   :", len([x for x in os.listdir(os.path.join(C, "code"))
                              if x.endswith(".py")]))
