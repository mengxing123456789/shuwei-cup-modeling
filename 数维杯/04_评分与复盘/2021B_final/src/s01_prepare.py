#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Step 1: load the official attachment + external GHCN stations, build tidy daily files,
annual indices, and a data-quality audit. Nothing here depends on later modelling."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import common as C

ATTACH = C.PROBLEM / "2021_“ShuWei Cup”B_Problem" / "Attachment 1：Data of three meteorological stations in zhengzhou annex.xlsx"
GHCN_DIR = C.RESULTS / "ghcn"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    print("A load attachment", flush=True)
    audit = {"attachment": {"path": ATTACH.name, "sha256": sha256(ATTACH), "bytes": ATTACH.stat().st_size}}
    raw = C.load_gsod_workbook(ATTACH)
    raw.to_csv(C.RESULTS / "attachment_daily_tidy.csv", index=False)

    st_audit = []
    for sid, g in raw.groupby("station"):
        d = C.daily_grid(g[["date", "prcp_mm", "tmax_c", "tmin_c"]])
        st_audit.append({
            "station": sid,
            "start": str(d.index.min().date()), "end": str(d.index.max().date()),
            "rows": int(len(g)), "calendar_days": int(len(d)),
            "prcp_missing_pct": round(float(d["prcp_mm"].isna().mean() * 100), 2),
            "prcp_zero_pct": round(float((d["prcp_mm"] == 0).mean() * 100), 2),
            "years_with_300d": int(C.annual_indices(d).shape[0]),
            "max_daily_mm": round(float(d["prcp_mm"].max()), 1),
        })
    audit["attachment_stations"] = st_audit
    print("B attachment ok", flush=True)

    ext = []
    for path in sorted(GHCN_DIR.glob("CHM*.csv")):
        if path.stat().st_size < 5000:
            continue
        g = C.load_ghcn_wide(path)
        if g.empty:
            continue
        d = C.daily_grid(g[["date", "prcp_mm", "tmax_c", "tmin_c"]])
        ai = C.annual_indices(d)
        window = ai[(ai.index >= 1961) & (ai.index <= 2021)]
        ext.append({
            "file": path.name, "station": g["station"].iloc[0], "name": g["name"].iloc[0],
            "lat": float(g.get("lat", pd.Series([np.nan])).iloc[0]) if "lat" in g else np.nan,
            "start": str(d.index.min().date()), "end": str(d.index.max().date()),
            "prcp_missing_pct": round(float(d["prcp_mm"].isna().mean() * 100), 2),
            "years_300d": int(ai.shape[0]),
            "years_1961_2021": int(window.shape[0]),
            "first_full_year": int(ai.index.min()) if len(ai) else None,
            "last_full_year": int(ai.index.max()) if len(ai) else None,
            "max_daily_mm": round(float(d["prcp_mm"].max()), 1),
        })
    audit["ghcn_stations"] = ext
    print("C ghcn ok", flush=True)

    att = raw[raw.station == "57083099999"]
    att_d = C.daily_grid(att[["date", "prcp_mm"]]).rename(columns={"prcp_mm": "gsod"})
    gh_path = GHCN_DIR / "CHM00057083.csv"
    cross = {}
    if gh_path.exists() and gh_path.stat().st_size > 5000:
        gh = C.load_ghcn_wide(gh_path)
        gh_d = C.daily_grid(gh[["date", "prcp_mm"]]).rename(columns={"prcp_mm": "ghcn"})
        both = att_d.join(gh_d, how="inner").dropna()
        both = both[(both.index >= "1961-01-01") & (both.index <= "2021-11-30")]
        if len(both) > 1000:
            cross = {
                "overlap_days": int(len(both)),
                "corr_daily": round(float(both["gsod"].corr(both["ghcn"])), 4),
                "mean_gsod_mm": round(float(both["gsod"].mean()), 3),
                "mean_ghcn_mm": round(float(both["ghcn"].mean()), 3),
                "ratio_mean": round(float(both["gsod"].mean() / both["ghcn"].mean()), 4),
                "exact_equal_pct": round(float((both["gsod"].round(1) == both["ghcn"].round(1)).mean() * 100), 2),
                "annual_total_corr": round(float(
                    both.groupby(both.index.year)["gsod"].sum().corr(both.groupby(both.index.year)["ghcn"].sum())
                ), 4),
            }
    audit["zhengzhou_cross_source"] = cross

    for sid in raw["station"].unique():
        g = raw[raw.station == sid]
        d = C.daily_grid(g[["date", "prcp_mm", "tmax_c", "tmin_c"]])
        d.to_csv(C.RESULTS / f"daily_{sid}.csv")
        C.annual_indices(d).to_csv(C.RESULTS / f"annual_{sid}.csv")

    C.write_json(audit, C.RESULTS / "audit_step1.json")
    pd.DataFrame(st_audit).to_csv(C.RESULTS / "audit_attachment_stations.csv", index=False)
    pd.DataFrame(ext).to_csv(C.RESULTS / "audit_ghcn_stations.csv", index=False)
    print(pd.DataFrame(st_audit).to_string(index=False), flush=True)
    print("\nGHCN coverage (1961-2021 full years):", flush=True)
    print(pd.DataFrame(ext)[["name", "first_full_year", "last_full_year", "years_1961_2021", "prcp_missing_pct", "max_daily_mm"]].to_string(index=False), flush=True)
    print("\nZhengzhou cross-source:", cross, flush=True)


if __name__ == "__main__":
    main()