"""Append the up21 cost-sweep assertion to audit/verify_claims.py (idempotent)."""
from __future__ import annotations

import io
from pathlib import Path

AUD = Path(r"audit\verify_claims.py")
ANCHOR = '    out = AUD / "verify_c'

BLOCK = '''    _cs_path = C / "data" / "up21_p2_cost_sweep.json"
    _cs = json.loads(_cs_path.read_text(encoding="utf-8")) if _cs_path.exists() else {}
    _cs_s = _cs.get("summary", {})
    _cs_oat = {row["knob"]: row for row in _cs_s.get("one_at_a_time", [])}
    _cs_ok = (bool(_cs) and _cs_s.get("n_cells", 0) >= 100
              and 0.3 < _cs_s.get("frac_interior", 0) < 0.9
              and _cs_s.get("n_interior", 0) > 20
              and near(num(sl.get("PEconSpan", "x")), _cs_s.get("T_star_span_s", -1), tol=5e-3)
              and near(num(sl.get("PEconTMin", "x")), _cs_s.get("T_star_min_s", -1), tol=5e-3)
              and near(num(sl.get("PEconTMax", "x")), _cs_s.get("T_star_max_s", -1), tol=5e-3)
              and int(float(sl.get("PEconNCell", "-1"))) == int(_cs_s.get("n_cells", -2))
              and int(float(sl.get("PEconInterior", "-1"))) == int(_cs_s.get("n_interior", -2))
              and near(num(sl.get("PEconCOneSpan", "x")),
                       _cs_oat.get("C1", {}).get("span_s", -1), tol=5e-3)
              and near(num(sl.get("PEconCZeroSpan", "x")),
                       _cs_oat.get("C0", {}).get("span_s", -1), tol=5e-3)
              and _cs_oat.get("C1", {}).get("span_s", 1) == 0.0
              and "coefficient triples" in flat_text
              and "no fallback" in flat_text)
    check("Part II priced rule re-solved over cost coefficients (up21)", _cs_ok,
          "up21_p2_cost_sweep.json",
          f"cells={_cs_s.get('n_cells')} interior={_cs_s.get('n_interior')} "
          f"span={_cs_s.get('T_star_span_s')} c1span={_cs_oat.get('C1', {}).get('span_s')}",
          _cs_ok)

'''


def main() -> int:
    text = io.open(AUD, encoding="utf-8").read()
    if "up21_p2_cost_sweep" in text:
        print("already present")
        return 0
    if ANCHOR not in text:
        raise SystemExit("anchor missing")
    text = text.replace(ANCHOR, BLOCK + ANCHOR, 1)
    io.open(AUD, "w", encoding="utf-8", newline="\n").write(text)
    print("appended up21 assertion")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
