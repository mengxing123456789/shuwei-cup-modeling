"""Drop the PEconSpan check: that macro is pruned because the body does not use it."""
from __future__ import annotations

import io
from pathlib import Path

P = Path(r"audit\verify_claims.py")
NEEDLE = '              and near(num(sl.get("PEconSpan", "x")), _cs_s.get("T_star_span_s", -1), tol=5e-3)\n'


def main() -> int:
    text = io.open(P, encoding="utf-8").read()
    if NEEDLE not in text:
        print("needle absent (already removed?)")
        return 0
    text = text.replace(NEEDLE, "")
    io.open(P, "w", encoding="utf-8", newline="\n").write(text)
    print("removed PEconSpan check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
