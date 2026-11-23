import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import pandas as pd
import common as C

rows = []
for f in sorted((C.RESULTS / "ghcn").glob("CHM*.csv")):
    try:
        g = C.load_ghcn_wide(f)
        if len(g) == 0:
            raise ValueError("empty")
        d = C.daily_grid(g[["date", "prcp_mm"]])
        ai = C.annual_indices(d)
        sub = ai.loc[1961:2020]
        ok = sub[sub["n_valid"] >= 300]
        rows.append({"file": f.stem, "name": g["name"].iloc[0] if "name" in g else "",
                     "rows": len(d), "valid_years": len(ok),
                     "first": d.index.min().date(), "last": d.index.max().date(),
                     "status": "ok"})
    except Exception as exc:  # noqa: BLE001
        rows.append({"file": f.stem, "name": "", "rows": 0, "valid_years": 0,
                     "first": pd.NaT, "last": pd.NaT, "status": f"unusable: {exc}"})
t = pd.DataFrame(rows)
t.to_csv(C.RESULTS / "audit_station_years.csv", index=False)
print("files", len(t), "| unusable", int((t["status"] != "ok").sum()))
print(t[t["status"] != "ok"].to_string(index=False))
ok = t[t["status"] == "ok"]
print("with data:", len(ok), "| >=45 yrs:", int((ok["valid_years"] >= 45).sum()),
      "| 1-44 yrs:", int(((ok["valid_years"] > 0) & (ok["valid_years"] < 45)).sum()))
print(ok[ok["valid_years"] < 45].sort_values("valid_years")[
    ["file", "valid_years", "first", "last"]].to_string(index=False))
