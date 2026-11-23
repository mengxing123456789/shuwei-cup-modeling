#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Download GHCN-Daily station files for candidate Chinese cities and report PRCP coverage.

Source pattern: https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/{ID}.csv
Each row: STATION,DATE,ELEMENT,DATA_VALUE,MFLAG,QFLAG,SFLAG,OBS_TIME
PRCP unit: tenths of mm; missing flagged with QFLAG / DATA_VALUE -9999.
"""
import csv, io, json, sys, time, urllib.request, pathlib

CITIES = [
    ("Zhengzhou", "CHM00057083"), ("Beijing", "CHM00054511"), ("Shanghai", "CHM00058362"),
    ("Guangzhou", "CHM00059287"), ("Nanjing", "CHM00058238"), ("Wuhan", "CHM00057494"),
    ("Chengdu", "CHM00056294"), ("Xian", "CHM00057036"), ("Taiyuan", "CHM00053772"),
    ("Jinan", "CHM00054823"), ("Shijiazhuang", "CHM00053798"), ("Changsha", "CHM00057687"),
    ("Hangzhou", "CHM00058457"), ("Fuzhou", "CHM00058847"), ("Nanchang", "CHM00058606"),
    ("Hefei", "CHM00058321"), ("Lanzhou", "CHM00052889"), ("Xining", "CHM00052866"),
    ("Harbin", "CHM00050953"), ("Shenyang", "CHM00054342"), ("Urumqi", "CHM00051463"),
    ("Kunming", "CHM00056778"), ("Guiyang", "CHM00057816"), ("Nanning", "CHM00059431"),
    ("Haikou", "CHM00059758"), ("Changzhi", "CHM00053882"), ("Linfen", "CHM00053868"),
    ("Yuncheng", "CHM00053959"), ("Jincheng", "CHM00053976"), ("Yinchuan", "CHM00053614"),
    ("Hohhot", "CHM00053463"), ("Qingdao", "CHM00054857"), ("Dalian", "CHM00054662"),
]
BASE = "https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/{}.csv"
OUT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else r"E:\数学建模\数维杯\03_实战演练\2021_B_ExtremeRainfall\03_results\ghcn")
OUT.mkdir(parents=True, exist_ok=True)

rows = []
for city, sid in CITIES:
    dst = OUT / f"{sid}.csv"
    if not dst.exists() or dst.stat().st_size < 5000:
        try:
            req = urllib.request.Request(BASE.format(sid), headers={"User-Agent": "Mozilla/5.0 research"})
            with urllib.request.urlopen(req, timeout=120) as r:
                dst.write_bytes(r.read())
        except Exception as e:
            rows.append({"city": city, "station": sid, "status": f"ERR {type(e).__name__}: {e}", "bytes": 0})
            continue
    text = dst.read_text(encoding="utf-8", errors="replace")
    rdr = csv.DictReader(io.StringIO(text))
    prcp_years, nprcp = set(), 0
    tmax_years = set()
    for rec in rdr:
        el = rec.get("ELEMENT")
        if el == "PRCP" and rec.get("DATA_VALUE") not in ("-9999", "", None):
            prcp_years.add(int(rec["DATE"][:4])); nprcp += 1
        elif el == "TMAX":
            tmax_years.add(int(rec["DATE"][:4]))
    rows.append({
        "city": city, "station": sid, "status": "OK" if prcp_years else "NO_PRCP",
        "bytes": dst.stat().st_size, "prcp_days": nprcp,
        "year_min": min(prcp_years) if prcp_years else None,
        "year_max": max(prcp_years) if prcp_years else None,
        "n_years": len(prcp_years),
        "tmax_years": len(tmax_years),
    })
    print(rows[-1], flush=True)

with open(OUT / "coverage.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
print("\nSUMMARY")
for r in rows:
    print(f"{r['city']:<14}{r['station']:<14}{r['status']:<8}{r.get('year_min')}-{r.get('year_max')} years={r.get('n_years')} days={r.get('prcp_days')}")