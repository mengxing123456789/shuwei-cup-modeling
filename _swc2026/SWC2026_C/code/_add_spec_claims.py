# -*- coding: utf-8 -*-
"""Append two structural claims for the format-spec work of 2026-11-22 evening.

Item 1(6) of the spec requires the appendix to state the software used and to point at
the support material.  Both are now in Appendix C; these claims keep them there.
"""
import io
import sys
from pathlib import Path

AUD = Path(r"audit\verify_claims.py")

BLOCK = r'''
    # --- software table and support-material statement (spec item 1(6)) --------
    tex = (C / "main.tex").read_text(encoding="utf-8", errors="ignore")
    appc = tex[tex.find(r"\section{Reproduction commands}"):]
    add(
        "Appendix C names the software and points at the support material",
        ("tab:software" in appc)
        and ("3.11.18" in appc)
        and ("2.4.6" in appc)
        and ("1.17.1" in appc)
        and ("3.1.1" in appc)
        and ("1.9.1" in appc)
        and ("2.14.1" in appc)
        and ("4.7.0" in appc)
        and ("3.11.2" in appc)
        and ("4.16" in appc)
        and ("CSWBMCM2634892fj.zip" in appc)
        and ("support material" in appc),
    )
'''

ANCHOR = '    out = AUD / "verify_c'


def main():
    apply = "--apply" in sys.argv
    text = io.open(AUD, encoding="utf-8").read()
    if "Appendix C names the software" in text:
        print("already present")
        return 0
    n = text.count(ANCHOR)
    print("anchor hits:", n)
    if n != 1:
        print("ABORT")
        return 1
    new = text.replace(ANCHOR, BLOCK + "\n" + ANCHOR)
    print("bytes %d -> %d" % (len(text), len(new)))
    if not apply:
        print("dry run; pass --apply")
        return 0
    io.open(AUD, "w", encoding="utf-8", newline="\n").write(new)
    print("written", AUD)
    return 0


if __name__ == "__main__":
    sys.exit(main())
