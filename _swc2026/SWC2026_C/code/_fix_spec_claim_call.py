# -*- coding: utf-8 -*-
"""Fix the spec claims block: this file's helper is check(), not add()."""
import io
import sys
from pathlib import Path

AUD = Path(r"audit\verify_claims.py")

OLD = r'''    add(
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
    )'''

NEW = r'''    _sw_ok = (
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
        and ("support material" in appc)
    )
    check("Appendix C names the software and points at the support material", _sw_ok,
          "Appendix C of main.tex", "ten versions and the support-material note", _sw_ok)'''


def main():
    apply = "--apply" in sys.argv
    text = io.open(AUD, encoding="utf-8").read()
    n = text.count(OLD)
    print("old hits:", n)
    if n != 1:
        print("ABORT")
        return 1
    new = text.replace(OLD, NEW)
    print("bytes %d -> %d" % (len(text), len(new)))
    if not apply:
        print("dry run")
        return 0
    io.open(AUD, "w", encoding="utf-8", newline="\n").write(new)
    print("written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
