"""Add slots that put the ridge and the GRU in the same unit.

The appendix paragraph compared a per-coordinate GRU error with a
three-dimensional ridge error and called the ratio "times better". That mixes
units: sqrt(3) relates the two. This script derives both units for both models
and appends the macros the rewritten paragraph needs.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

C = Path(r"E:\数学建模\_swc2026\SWC2026_C")
SLOTS = C / "slots.tex"
S3 = 1.7320508075688772  # sqrt(3)


def slot(name: str) -> float:
    txt = SLOTS.read_text(encoding="utf-8")
    m = re.search(rf"\\newcommand{{\\slot{name}}}{{([-\d.]+)}}", txt)
    if not m:
        raise SystemExit(f"slot {name} not found")
    return float(m.group(1))


gpu = json.loads((C / "data" / "p2_gpu.json").read_text(encoding="utf-8"))
# per-coordinate RMSE reported by the GRU runs
gru_a = slot("PGPUAWristRMSE")
gru_b = slot("PGPUBSTwoRMSE")
gru_c = slot("PGPUCBothRMSE")
gru_d = slot("PGPUDBothRMSE")
# three-dimensional RMSE reported by the ridge predictor
rdg_a, rdg_b, rdg_c, rdg_d = (slot(f"PTwo{x}RidgeRMSE") for x in "ABCD")

vals = {
    "PGpuAWristThreeD": gru_a * S3,
    "PGpuBThreeD": gru_b * S3,
    "PGpuCThreeD": gru_c * S3,
    "PGpuDThreeD": gru_d * S3,
    "PRidgeAPerCoord": rdg_a / S3,
    "PRidgeBPerCoord": rdg_b / S3,
    "PRidgeCPerCoord": rdg_c / S3,
    "PRidgeDPerCoord": rdg_d / S3,
}
vals["PGpuWinCPerCoordPct"] = 100.0 * (vals["PRidgeCPerCoord"] - gru_c) / vals["PRidgeCPerCoord"]
vals["PGpuWinDPerCoordPct"] = 100.0 * (vals["PRidgeDPerCoord"] - gru_d) / vals["PRidgeDPerCoord"]
vals["PGpuWinCThreeDPct"] = 100.0 * (rdg_c - vals["PGpuCThreeD"]) / rdg_c
vals["PGpuWinDThreeDPct"] = 100.0 * (rdg_d - vals["PGpuDThreeD"]) / rdg_d
vals["PGpuBPerCoordGapPct"] = 100.0 * (gru_b - vals["PRidgeBPerCoord"]) / vals["PRidgeBPerCoord"]

txt = SLOTS.read_text(encoding="utf-8")
marker = "% --- same-unit comparison of the two P2 predictors (derived from p2_gpu.json) ---"
if marker in txt:
    txt = txt.split(marker)[0].rstrip() + "\n"
lines = [marker]
for k, v in vals.items():
    lines.append(rf"\newcommand{{\slot{k}}}{{{v:.2f}}}")
lines.append(r"\\end{input}" if False else "")
SLOTS.write_text(txt + "\n".join(lines) + "\n", encoding="utf-8")

print("appended", len(vals), "slots")
for k, v in vals.items():
    print(f"  {k:24s} {v:7.2f}")
print("\ncheck: gru per-coord A/B/C/D =", gru_a, gru_b, gru_c, gru_d)
print("       ridge per-coord A/B/C/D =", round(vals['PRidgeAPerCoord'],2),
      round(vals['PRidgeBPerCoord'],2), round(vals['PRidgeCPerCoord'],2), round(vals['PRidgeDPerCoord'],2))
print("       gru 3D A/B/C/D =", round(vals['PGpuAWristThreeD'],2), round(vals['PGpuBThreeD'],2),
      round(vals['PGpuCThreeD'],2), round(vals['PGpuDThreeD'],2))