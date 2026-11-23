"""Peak-hour waterlogging excess for the 2021-07-20 Zhengzhou hour.

The manuscript quotes an excess of about 1.4e8 m3 arriving within one hour:
SCS-CN runoff for 201.9 mm at CN 85 minus the one-year drainage capacity of
36 mm, spread over the 1180 km2 study area.  This script produces that number
as a stored artefact instead of leaving it as a number typed into the text.
"""
import json
from pathlib import Path

import numpy as np

import common as C

AREA_KM2 = 1180.0
PEAK_MM = 201.9
CAP_MM_H = 36.0


def scs_runoff(p_mm: float, cn: float) -> float:
    s = 25400.0 / cn - 254.0
    ia = 0.2 * s
    if p_mm <= ia:
        return 0.0
    return (p_mm - ia) ** 2 / (p_mm + 0.8 * s)


def main() -> None:
    q = scs_runoff(PEAK_MM, 85.0)
    excess_mm = q - CAP_MM_H
    excess_m3 = excess_mm / 1000.0 * AREA_KM2 * 1e6
    out = {
        "peak_hour_mm": PEAK_MM,
        "cn": 85.0,
        "runoff_mm": round(q, 3),
        "capacity_mm_per_h": CAP_MM_H,
        "excess_depth_mm": round(excess_mm, 3),
        "excess_volume_m3": round(excess_m3, 1),
        "excess_volume_Mm3": round(excess_m3 / 1e6, 3),
        "area_km2": AREA_KM2,
        "note": "SCS-CN runoff of the peak hour minus the one-year drainage depth",
    }
    path = C.RESULTS / "q1_peak_hour.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()