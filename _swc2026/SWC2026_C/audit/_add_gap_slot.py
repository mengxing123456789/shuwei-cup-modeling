from pathlib import Path
import re

S = Path(r"E:\数学建模\_swc2026\SWC2026_C\slots.tex")
t = S.read_text(encoding="utf-8")


def g(n: str) -> float:
    m = re.search(r"\\newcommand\{\\slot" + n + r"\}\{([-\d.]+)\}", t)
    if not m:
        raise SystemExit(f"missing slot {n}")
    return float(m.group(1))


gru = g("PGPUAWristRMSE")
rdg = g("PTwoARidgeRMSE") / 1.7320508075688772
v = 100.0 * (gru - rdg) / rdg
if "\\slotPGpuAPerCoordGapPct" not in t:
    S.write_text(t + "\\newcommand{\\slotPGpuAPerCoordGapPct}{%.1f}\n" % v, encoding="utf-8")
print("PGpuAPerCoordGapPct %.1f" % v)