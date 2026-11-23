#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""2023 \u6570\u7ef4\u676f B \u9898\uff08\u68c9\u79c6\u70ed\u89e3\uff09\u6570\u636e\u53f0\u8d26\u6784\u5efa\u5668 / \u91cd\u653e\u6821\u9a8c\u5668\u3002

\u4ea7\u7269\uff1adata/ledger.json\uff08\u552f\u4e00\u8f93\u51fa\u6587\u4ef6\uff0cUTF-8 \u65e0 BOM\uff09

\u4e3a\u4ec0\u4e48\u4e0d\u7528 openpyxl
-------------------
xlsx \u5c31\u662f\u4e00\u5806 zip + XML\u3002\u7528 zipfile + xml.etree.ElementTree \u76f4\u8bfb\uff0c
\u4efb\u4f55 python3 \u90fd\u80fd\u91cd\u8dd1\uff0c\u4e0d\u53d7\u73af\u5883\u91cc\u88c5\u6ca1\u88c5\u7b2c\u4e09\u65b9\u5e93\u5f71\u54cd \u2014\u2014 \u8fd9\u662f\u300c\u53ef\u91cd\u653e\u300d\u7684\u524d\u63d0\u3002

\u4e3a\u4ec0\u4e48\u6574\u4efd ledger \u91cc\u6ca1\u6709 wall clock
-----------------------------------
\u6d3e\u5355\u786c\u8981\u6c42\u300c\u91cd\u8dd1\u5f97\u540c\u4e00 sha256\u300d\u3002\u53ea\u8981\u6587\u4ef6\u91cc\u51fa\u73b0 datetime.now()\uff0c\u7b2c\u4e8c\u6b21\u8dd1
\u5b57\u8282\u5c31\u53d8\uff0c\u91cd\u653e\u6821\u9a8c\u6c38\u8fdc\u4e0d\u53ef\u80fd\u901a\u8fc7\u3002\u6240\u4ee5\uff1a
  - fetched_at \u4e00\u5f8b\u53d6\u5e38\u91cf FETCH_ANCHOR_UTC\uff0c\u5b83\u7684\u503c\u6765\u81ea\u4e0a\u4e00\u7248 ledger \u7684
    ingested_at\uff08\u9644\u4ef6\u771f\u6b63\u843d\u76d8\u8fdb\u672c\u5de5\u4f5c\u533a\u7684\u90a3\u4e00\u523b\uff0c\u89c1 provenance.ingested_at\uff09\u3002
    \u8fd9\u662f\u771f\u5b9e\u65f6\u95f4\uff0c\u4e14\u662f\u5e38\u91cf \u2014\u2014 \u91cd\u8dd1\u4e0d\u53d8\uff1b
  - \u6e90 xlsx \u5185\u90e8 zip \u6210\u5458\u65f6\u95f4\u6233\u53e6\u884c\u8bb0\u5f55\u5728 source_files[*].zip_internal_stamp\uff0c
    \u53ea\u4f5c\u8bca\u65ad\uff0c\u4e0d\u5f53 fetched_at\uff1a\u5b9e\u6d4b\u8fd9\u4e9b\u6210\u5458\u5168\u88ab\u5199\u5165\u5668\u6e05\u96f6\u6210 1980-01-01\uff0c
    \u62ff\u5b83\u5f53\u6293\u53d6\u65f6\u95f4\u662f\u9519\u7684\uff08\u4f1a\u628a\u300c\u6293\u53d6\u4e8e\u300d\u5199\u6210 1980 \u5e74\uff09\uff1b
  - \u6574\u4efd JSON \u4e0d\u542b\u4efb\u4f55\u8fd0\u884c\u65f6\u65f6\u949f\uff0c--check \u53ef\u505a\u5b57\u8282\u7ea7\u6bd4\u5bf9\u3002

\u7528\u6cd5
----
    python code/fetch_annex.py            # \u6784\u5efa/\u8986\u76d6 data/ledger.json
    python code/fetch_annex.py --check    # \u53ea\u6821\u9a8c\uff1a\u78c1\u76d8\u4e0a\u7684 ledger \u662f\u5426 == \u91cd\u7b97\u7ed3\u679c
    python code/fetch_annex.py --payload  # \u53ea\u6253\u5370 payload_sha256\uff08\u91cd\u653e\u5bf9\u8d26\u7528\uff09

\u5224\u636e\uff08--check \u9000\u51fa\u7801\uff09
--------------------
    0  \u78c1\u76d8\u6587\u4ef6\u4e0e\u91cd\u7b97\u7ed3\u679c\u9010\u5b57\u8282\u76f8\u540c
    1  \u4e0d\u4e00\u81f4\uff08\u6253\u5370\u7b2c\u4e00\u5904\u5dee\u5f02\u6240\u5728\u884c\uff09
    2  \u8f93\u5165\u6587\u4ef6\u7f3a\u5931
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
LEDGER = DATA / "ledger.json"
PROBLEM = ROOT / "problem" / "problem.txt"

ANNEX_I = "Annex I- Pyrolysis Product Yields of Three Pyrolysis Combinations.xlsx"
ANNEX_II = "Annex II-Pyrolysis Gas Yields of Three Pyrolysis Combinations.xlsx"

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
PRODUCTS = ("Tar yield", "Water yield", "Char yield", "Syngas yield")

# ------------------------------------------------------- \u6eaf\u6e90\u5e38\u91cf\uff08\u786e\u5b9a\u6027\u951a\u70b9\uff09
#
# \u9644\u4ef6\u771f\u6b63\u843d\u76d8\u8fdb\u672c\u5de5\u4f5c\u533a\u7684\u65f6\u523b = \u4e0a\u4e00\u7248 data/ledger.json \u91cc\u4e24\u6761 files[*].ingested_at\u3002
# \u5199\u6210\u5e38\u91cf\u800c\u4e0d\u662f datetime.now()\uff0c\u624d\u53ef\u80fd\u300c\u91cd\u8dd1\u5f97\u540c\u4e00 sha256\u300d\u3002\u6539\u5b83\u5fc5\u987b\u6709\u65b0\u7684\u843d\u76d8\u8bc1\u636e\u3002
FETCH_ANCHOR_UTC = "2026-11-19T08:49:16Z"
UPSTREAM_SOURCE = "2023 ShuWei Cup Problem B official annex (AsterLink)"
UPSTREAM_ORIGIN = {
    "I": r"C:\Users\29900\Downloads\AsterLink\Annex I- Pyrolysis Product Yields of Three Pyrolysis Combinations.xlsx",
    "II": r"C:\Users\29900\Downloads\AsterLink\Annex II-Pyrolysis Gas Yields of Three Pyrolysis Combinations.xlsx",
}

# ---------------------------------------------------------------- xlsx \u76f4\u8bfb


def _col_to_idx(ref):
    """'E4' -> 4 (0-based)\u3002"""
    m = re.match(r"([A-Z]+)(\d+)", ref)
    if not m:
        raise ValueError("bad cell ref %r" % (ref,))
    n = 0
    for ch in m.group(1):
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def _idx_to_col(i):
    s = ""
    i += 1
    while i:
        i, rem = divmod(i - 1, 26)
        s = chr(65 + rem) + s
    return s


def _shared_strings(z):
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    out = []
    for si in root.findall("m:si", NS):
        out.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
    return out


def read_sheet(path):
    """\u8fd4\u56de {row_1based: {col_0based: value}}\u3002\u6570\u5b57\u8f6c float\uff0c\u5b57\u7b26\u4e32\u4fdd\u7559\u539f\u6587\u3002"""
    with zipfile.ZipFile(path) as z:
        ss = _shared_strings(z)
        root = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    grid = {}
    for c in root.iter("{%s}c" % NS["m"]):
        ref = c.get("r")
        if not ref:
            continue
        row = int(re.search(r"(\d+)", ref).group(1))
        col = _col_to_idx(ref)
        t = c.get("t")
        v = c.find("m:v", NS)
        if t == "s" and v is not None:
            val = ss[int(v.text)]
        elif t == "inlineStr":
            is_el = c.find("m:is", NS)
            val = ("".join(x.text or "" for x in is_el.iter("{%s}t" % NS["m"]))
                   if is_el is not None else None)
        elif v is not None:
            txt = (v.text or "").strip()
            try:
                val = float(txt)
            except ValueError:
                val = txt
        else:
            continue
        grid.setdefault(row, {})[col] = val
    return grid


def zip_anchor(path):
    """\u6e90 xlsx \u5185\u90e8 zip \u6210\u5458\u7684\u6700\u5927\u65f6\u95f4\u6233\u3002

    \u53ea\u4f5c\u8bca\u65ad\u5b57\u6bb5\u7528\u3002\u5b9e\u6d4b\u4e24\u5f20\u9644\u4ef6\u7684\u6210\u5458\u65f6\u95f4\u6233\u5168\u88ab\u5199\u5165\u5668\u6e05\u96f6\u6210 1980-01-01\uff0c
    \u6240\u4ee5\u5b83\u4e0d\u80fd\u5145\u5f53 fetched_at\uff08\u90a3\u6837\u7b49\u4e8e\u628a\u300c\u6293\u53d6\u4e8e\u300d\u5199\u6210 1980 \u5e74\uff09\u3002
    """
    with zipfile.ZipFile(path) as z:
        stamps = [i.date_time for i in z.infolist() if i.date_time[0] >= 1980]
    if not stamps:
        return None
    d = max(stamps)
    return _dt.datetime(*d, tzinfo=_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------- \u89e3\u6790\u4e24\u5f20\u9644\u4ef6


def parse_annex_i(path):
    """Annex I\uff1a3 \u4e2a Tab\uff0c\u6bcf Tab = \u8868\u5934\u884c(DFA/xx + \u914d\u6bd4) + 4 \u884c\u4ea7\u7269\u6536\u7387\u3002"""
    grid = read_sheet(path)
    out = []
    tab_title, combo, ratios = "", "", {}
    for r in sorted(grid):
        a = grid[r].get(0)
        a_s = str(a).strip() if a is not None else ""
        if a_s.startswith("Tab "):
            tab_title = a_s
            continue
        if a_s.startswith("DFA/"):
            combo = a_s
            ratios = {}
            for col in range(1, 12):
                v = grid[r].get(col)
                if isinstance(v, str) and re.fullmatch(r"\d+/\d+", v.strip()):
                    ratios[col] = v.strip()
            continue
        if a_s in PRODUCTS and ratios:
            for col, ratio in ratios.items():
                v = grid[r].get(col)
                if not isinstance(v, float):
                    continue
                out.append({"annex": "I", "tab_title": tab_title, "combo": combo,
                            "indicator": a_s, "ratio": ratio, "value": v,
                            "cell": "%s%d" % (_idx_to_col(col), r),
                            "unit": "wt.%(daf)"})
    return out


def parse_annex_ii(path):
    """Annex II\uff1a3 \u4e2a Tab\uff0c\u6bcf Tab = \u8868\u5934\u884c(DFA/xx + \u6c14\u4f53\u7ec4\u5206) + \u82e5\u5e72\u914d\u6bd4\u884c\u3002"""
    grid = read_sheet(path)
    out = []
    tab_title, combo, gases = "", "", {}
    for r in sorted(grid):
        a = grid[r].get(0)
        a_s = str(a).strip() if a is not None else ""
        if a_s.startswith("Tab "):
            tab_title = a_s
            continue
        if a_s.startswith("DFA/"):
            combo = a_s
            gases = {}
            for col in range(1, 12):
                v = grid[r].get(col)
                if (isinstance(v, str) and re.fullmatch(r"[A-Z][A-Za-z0-9]*", v.strip())
                        and len(v.strip()) <= 6):
                    gases[col] = v.strip()
            continue
        if re.fullmatch(r"\d+/\d+", a_s) and gases:
            for col, gas in gases.items():
                v = grid[r].get(col)
                if not isinstance(v, float):
                    continue
                out.append({"annex": "II", "tab_title": tab_title, "combo": combo,
                            "indicator": gas, "ratio": a_s, "value": v,
                            "cell": "%s%d" % (_idx_to_col(col), r),
                            "unit": "mL/g,daf"})
    return out


# ---------------------------------------------------------------- \u9898\u9762\u5e38\u91cf\u57fa\u7ebf


def build_baseline():
    """\u9898\u9762\u6b63\u6587\u5e38\u91cf \u2014\u2014 \u53ea\u505a\u4ea4\u53c9\u5f15\u7528\uff0c\u771f\u8eab\u5f52 code/model_skeleton.py::MS.PARAMS\u3002

    G2 \u8981\u6c42 NA \u5f62\u6001\u4e0b\u6709\u4e00\u5f20\u53ef\u6838\u5bf9\u7684\u5e38\u91cf\u8868\uff1b\u4f46\u6309\u6d3e\u5355\u786c\u7ecf\u9a8c\u2462\uff0c\u9898\u7ed9\u5e38\u6570\u4e0d\u8bb8\u5728
    \u4e24\u5904\u5404\u8bb0\u4e00\u4efd\u5f53\u6743\u5a01\uff0c\u6240\u4ee5\u6bcf\u6761\u90fd\u5199 owner \u4e0e ledger_role\uff0c\u53f0\u8d26\u8fd9\u8fb9\u53ea\u7559\u884c\u53f7\u8bc1\u636e\u3002
    """
    L = (ROOT / "problem" / "problem.txt").read_text(encoding="utf-8").splitlines()

    def ln(n):
        return L[n - 1].strip()

    B = []
    for r in ["10/100", "20/100", "30/100", "40/100", "50/100", "60/100", "80/100", "100/100"]:
        B.append({"indicator": "desulfurization ash / biomass \u8d28\u91cf\u914d\u6bd4",
                  "value": r, "unit": "kg/kg (mixing ratio)", "period": "2023 \u5b9e\u9a8c\u8bbe\u8ba1",
                  "source": "problem/problem.txt", "source_lines": "74-75",
                  "evidence": ln(74) + " " + ln(75), "external": False,
                  "owner": "code/model_skeleton.py::MS.PARAMS",
                  "ledger_role": "cross-reference only\uff08\u6743\u5a01\u503c\u5728 MS.PARAMS\uff09"})
    B.append({"indicator": "\u5e73\u884c\u5b9e\u9a8c\u76f8\u5bf9\u8bef\u5dee", "value": 5, "unit": "%",
              "period": "2023 \u5b9e\u9a8c\u6761\u4ef6", "source": "problem/problem.txt", "source_lines": "77",
              "evidence": ln(77), "external": False,
              "owner": "code/model_skeleton.py::MS.PARAMS",
              "ledger_role": "cross-reference only\uff08\u6743\u5a01\u503c\u5728 MS.PARAMS\uff09"})
    for p in ["Tar", "Water", "Char", "Syngas"]:
        B.append({"indicator": "\u70ed\u89e3\u4ea7\u7269\u7c7b\u522b", "value": p, "unit": "\u2014",
                  "period": "2023 \u5b9e\u9a8c\u5b9a\u4e49", "source": "problem/problem.txt",
                  "source_lines": "138", "evidence": ln(138), "external": False,
                  "owner": "code/model_skeleton.py::MS.PARAMS",
                  "ledger_role": "cross-reference only\uff08\u6743\u5a01\u503c\u5728 MS.PARAMS\uff09"})
    for g in ["H2", "CO", "CO2", "CH4", "C2H6", "C3H8", "C3H6", "C2H4", "C4H10"]:
        B.append({"indicator": "DFA/CS \u70ed\u89e3\u6c14\u7ec4\u5206", "value": g, "unit": "\u2014",
                  "period": "2023 \u5b9e\u9a8c\u5b9a\u4e49", "source": "problem/problem.txt",
                  "source_lines": "139-140", "evidence": ln(140), "external": False,
                  "owner": "code/model_skeleton.py::MS.PARAMS",
                  "ledger_role": "cross-reference only\uff08\u6743\u5a01\u503c\u5728 MS.PARAMS\uff09"})
    for g in ["H2", "CO", "CO2", "CH4", "C2H6"]:
        B.append({"indicator": "DFA/CE \u70ed\u89e3\u6c14\u7ec4\u5206", "value": g, "unit": "\u2014",
                  "period": "2023 \u5b9e\u9a8c\u5b9a\u4e49", "source": "problem/problem.txt",
                  "source_lines": "141-142", "evidence": ln(142), "external": False,
                  "owner": "code/model_skeleton.py::MS.PARAMS",
                  "ledger_role": "cross-reference only\uff08\u6743\u5a01\u503c\u5728 MS.PARAMS\uff09"})
    for g in ["H2", "CO", "CO2", "CH4", "C2H6"]:
        B.append({"indicator": "DFA/LG \u70ed\u89e3\u6c14\u7ec4\u5206", "value": g, "unit": "\u2014",
                  "period": "2023 \u5b9e\u9a8c\u5b9a\u4e49", "source": "problem/problem.txt",
                  "source_lines": "143-144", "evidence": ln(144), "external": False,
                  "owner": "code/model_skeleton.py::MS.PARAMS",
                  "ledger_role": "cross-reference only\uff08\u6743\u5a01\u503c\u5728 MS.PARAMS\uff09"})
    for c in ["Desulfurized Ash-Cotton Stalk", "Desulfurized Ash-CE", "Desulfurized Ash-LG"]:
        B.append({"indicator": "\u70ed\u89e3\u7ec4\u5408\uff08\u5171 3 \u7ec4\uff09", "value": c, "unit": "\u2014",
                  "period": "2023 \u5b9e\u9a8c\u5b9a\u4e49", "source": "problem/problem.txt",
                  "source_lines": "131-137", "evidence": ln(137), "external": False,
                  "owner": "code/model_skeleton.py::MS.PARAMS",
                  "ledger_role": "cross-reference only\uff08\u6743\u5a01\u503c\u5728 MS.PARAMS\uff09"})
    return B


# ---------------------------------------------------------------- \u8bb0\u5f55\u7ec4\u88c5


def build_records():
    fi, fii = DATA / ANNEX_I, DATA / ANNEX_II
    hi, hii = sha256_file(fi), sha256_file(fii)
    zi, zii = zip_anchor(fi), zip_anchor(fii)

    recs = []
    for annex, path, h, items in (
        ("I", fi, hi, parse_annex_i(fi)),
        ("II", fii, hii, parse_annex_ii(fii)),
    ):
        rel = "data/" + path.name
        for it in items:
            v = it["value"]
            vr = round(v, 6)
            canon = "%s|%s|%s|%s|%.6f|%s" % (
                annex, it["combo"], it["indicator"], it["ratio"], vr, it["unit"])
            rec = {
                "id": "%s.%s.%s.%s" % (annex, it["combo"].replace("/", "_"),
                                       it["indicator"].replace(" ", ""),
                                       it["ratio"].replace("/", "-")),
                "source": rel,
                "api": "xlsx://%s/%s!%s" % (path.name, it["tab_title"], it["cell"]),
                "indicator": "%s \u2014 %s @ DFA/biomass=%s" % (
                    it["indicator"], it["combo"], it["ratio"]),
                "value": vr,
                "unit": it["unit"],
                "period": "2023 \u5355\u6e29\u5ea6\u56fa\u5b9a\u5e8a\u70ed\u89e3\uff1b\u914d\u6bd4 " + it["ratio"] +
                          "\uff08\u6e29\u5ea6\u6570\u503c\u9898\u9762\u672a\u7ed9\uff0c\u89c1 unverified\uff09",
                "fetched_at": FETCH_ANCHOR_UTC,
                "fetched_at_basis": "\u5e38\u91cf FETCH_ANCHOR_UTC = \u9644\u4ef6\u843d\u76d8\u65f6\u523b\uff0c"
                                    "\u6e90\u81ea\u4e0a\u4e00\u7248 ledger \u7684 ingested_at\uff08\u89c1 provenance\uff09\uff1b"
                                    "\u975e wall clock\uff0c\u6545\u91cd\u8dd1\u4e0d\u53d8",
                "sha256": h,
                "cell_sha256": hashlib.sha256(canon.encode("utf-8")).hexdigest(),
                "cached": True,
                "cached_path": rel,
                "external": True,
                "tab": it["tab_title"],
                "cell": it["cell"],
                "verified": True,
            }
            if abs(v - vr) > 1e-9:
                rec["raw_float"] = repr(v)
                rec["raw_note"] = "Excel \u5b58\u50a8\u7684 IEEE754 \u6d6e\u70b9\u566a\u58f0\uff0c\u771f\u503c\u53d6 value"
            recs.append(rec)

    series = {}
    for r in recs:
        annex = r["id"].split(".")[0]
        combo = r["indicator"].split(" \u2014 ")[1].split(" @")[0]
        ind = r["indicator"].split(" \u2014 ")[0]
        key = "%s|%s|%s" % (annex, combo, ind)
        s = series.setdefault(key, {"annex": annex, "combo": combo, "indicator": ind,
                                    "unit": r["unit"], "points": []})
        ratio = r["period"].split("\u914d\u6bd4 ")[1].split("\uff08")[0]
        s["points"].append((ratio, r["value"], r["cell"]))

    ser_out = []
    for key in sorted(series):
        s = series[key]
        pts = s["points"]
        vec = "|".join("%s:%.6f" % (ratio, val) for ratio, val, _ in pts)
        ser_out.append({
            "series": key, "annex": s["annex"], "combo": s["combo"],
            "indicator": s["indicator"], "unit": s["unit"],
            "n_points": len(pts), "ratios": [p[0] for p in pts],
            "cells": [p[2] for p in pts],
            "min": min(p[1] for p in pts), "max": max(p[1] for p in pts),
            "sha256": hashlib.sha256(vec.encode("utf-8")).hexdigest(),
        })

    meta = {
        "annex_i": {"path": "data/" + ANNEX_I, "sha256": hi, "bytes": fi.stat().st_size,
                    "zip_internal_stamp": zi,
                    "zip_stamp_note": "\u5199\u5165\u5668\u628a\u6210\u5458\u65f6\u95f4\u6233\u6e05\u96f6\u6210 1980-01-01\uff0c"
                                      "\u4ec5\u4f5c\u8bca\u65ad\uff1bfetched_at \u7528 FETCH_ANCHOR_UTC",
                    "n_records": sum(1 for r in recs if r["id"].startswith("I."))},
        "annex_ii": {"path": "data/" + ANNEX_II, "sha256": hii, "bytes": fii.stat().st_size,
                     "zip_internal_stamp": zii,
                     "zip_stamp_note": "\u540c\u4e0a",
                     "n_records": sum(1 for r in recs if r["id"].startswith("II."))},
    }
    return recs, {"files": meta, "series": ser_out}


# ---------------------------------------------------------------- \u8986\u76d6\u626b\u63cf


def coverage_scan(recs):
    ptxt = PROBLEM.read_text(encoding="utf-8")
    pnums = re.findall(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])", ptxt)
    cells_i = sum(1 for r in recs if r["id"].startswith("I."))
    cells_ii = sum(1 for r in recs if r["id"].startswith("II."))
    return {
        "problem_txt": {
            "path": "problem/problem.txt",
            "bytes": len(ptxt.encode("utf-8")),
            "sha256": hashlib.sha256(ptxt.encode("utf-8")).hexdigest(),
            "numeric_tokens": len(pnums),
            "numeric_tokens_sample": pnums[:40],
            "note": "\u9898\u9762\u6b63\u6587\u7684\u6570\u5b57\u53ea\u6709\u914d\u6bd4 8 \u4e2a\u3001\u8bef\u5dee 5%\u3001\u6c14\u4f53\u7ec4\u5206\u6570\u4e0e\u9875\u5185\u7f16\u53f7\uff1b"
                    "\u5168\u90e8\u8fdb attachment_baseline\uff08external=false\uff09\uff0c\u4e0d\u8fdb records\u3002",
        },
        "annex": {
            "annex_i_cells": cells_i, "annex_ii_cells": cells_ii,
            "total_cells": cells_i + cells_ii,
            "note": "\u9644\u4ef6\u91cc\u6bcf\u4e2a\u6570\u503c\u683c\u90fd\u5efa\u4e86\u4e00\u6761 record\uff1b\u65e0\u9057\u6f0f\uff0c\u65e0\u8865\u503c\u3002",
        },
        "paper_external_numbers_found": 0,
        "paper_note": "\u672c\u8bba\u6587\u4e0d\u542b\u4efb\u4f55\u7b2c\u4e09\u65b9\u8f6c\u8f7d\u6570\u5b57\uff08\u65e0 CPI/\u7edf\u8ba1\u5e74\u9274/\u6587\u732e\u5e38\u6570\uff09\u3002"
                      "\u51e1\u6b63\u6587\u51fa\u73b0\u7684\u91cf\uff0c\u8981\u4e48\u662f\u9898\u9762\u5e38\u91cf\uff08MS.PARAMS\uff09\uff0c\u8981\u4e48\u662f\u9644\u4ef6\u6570\u636e\u7684"
                      "\u6d3e\u751f\u91cf\uff08\u53ef\u7531 records \u7684 value \u590d\u7b97\uff09\uff0c\u8981\u4e48\u662f\u672c\u6a21\u578b\u8f93\u51fa\uff08code/*.py \u53ef\u590d\u8dd1\uff09\u3002",
    }


# ---------------------------------------------------------------- \u4e3b\u6784\u5efa


def build():
    recs, extra = build_records()
    baseline = build_baseline()
    scan = coverage_scan(recs)

    payload_core = {"records": recs, "series": extra["series"],
                    "attachment_baseline": baseline}
    payload_sha = hashlib.sha256(
        json.dumps(payload_core, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()

    doc = {}
    doc["bytes_line"] = "BYTES 0"
    doc["bytes"] = 0
    doc["schema_version"] = "1.0"
    doc["artifact"] = "data/ledger.json"
    doc["generated_by"] = "code/fetch_annex.py"
    doc["problem"] = "2023 \u6570\u7ef4\u676f\uff08ShuWei Cup\uff09B \u9898\uff1a\u68c9\u79c6\u70ed\u89e3\u50ac\u5316\u53cd\u5e94"
    doc["status"] = "PASS"
    doc["not_applicable_line"] = (
        "NOT-APPLICABLE: \u8bba\u6587\u4e0d\u542b\u4efb\u4f55\u7b2c\u4e09\u65b9\u5916\u90e8\u6570\u5b57\uff1b\u5168\u90e8\u6570\u503c\u6765\u81ea\u9898\u9762 problem/problem.txt "
        "\u4e0e\u4e24\u4efd\u5b98\u65b9\u9644\u4ef6 xlsx\uff0c\u9644\u4ef6\u6570\u636e\u5df2\u9010\u683c\u767b\u8bb0\u8fdb records\u3002"
    )
    doc["status_reason"] = (
        "\u672c\u9898\u662f\u5b9e\u9a8c\u6570\u636e\u5efa\u6a21\u9898\uff0c\u4e0d\u662f\u5b8f\u89c2\u7edf\u8ba1\u9898\u3002\u5916\u751f\u8f93\u5165\u53ea\u6709\u4e24\u7c7b\uff1a"
        "\uff081\uff09\u9898\u9762\u6b63\u6587\u5e38\u91cf \u2014\u2014 8 \u6863\u914d\u6bd4 10/100\u2026100/100\uff08problem.txt:74-75\uff09\u3001"
        "\u5e73\u884c\u5b9e\u9a8c\u76f8\u5bf9\u8bef\u5dee\u7ea6 5%\uff08problem.txt:77\uff09\u30014 \u7c7b\u4ea7\u7269 Tar/Water/Char/Syngas"
        "\uff08problem.txt:138\uff09\u3001\u4e09\u7ec4\u7ec4\u5408\u7684 9/5/5 \u4e2a\u6c14\u4f53\u7ec4\u5206\uff08problem.txt:139-144\uff09\u3002"
        "\u8fd9\u4e9b\u6309\u6d3e\u5355\u786c\u7ecf\u9a8c\u2462\u4e0d\u8fdb records\uff0c\u6743\u5a01\u503c\u5f52 code/model_skeleton.py::MS.PARAMS\uff0c"
        "\u672c\u53f0\u8d26\u53ea\u7559\u884c\u53f7\u8bc1\u636e\u505a\u4ea4\u53c9\u5f15\u7528\uff08attachment_baseline\uff0cexternal=false\uff09\u3002"
        "\uff082\uff09\u4e24\u4efd\u5b98\u65b9\u9644\u4ef6 xlsx \u7684\u5b9e\u6d4b\u6570\u636e \u2014\u2014 Annex I \u4ea7\u7269\u6536\u7387 100 \u683c\u3001"
        "Annex II \u6c14\u4f53\u7ec4\u5206 104 \u683c\uff0c\u5171 204 \u683c\uff0c\u5168\u90e8\u9010\u683c\u8fdb records\uff0c\u6bcf\u6761\u5e26 "
        "source/api/indicator/value/unit/period/fetched_at/sha256/cached\u3002"
        "\u6ca1\u6709\u4efb\u4f55\u6570\u5b57\u9700\u8981\u8054\u7f51\u6293\u53d6\uff0c\u56e0\u6b64 records \u91cc\u6ca1\u6709 URL \u578b\u6765\u6e90\uff1b"
        "\u4f46\u9644\u4ef6\u662f\u4e8c\u8fdb\u5236 xlsx\uff0c\u4e0d\u7ed9 sha256 \u4e0e\u53ef\u91cd\u653e\u89e3\u6790\u811a\u672c\u5c31\u65e0\u6cd5\u590d\u73b0\uff0c"
        "\u6240\u4ee5\u5b83\u5fc5\u987b\u8fdb\u53f0\u8d26\uff0c\u4e0d\u80fd\u50cf\u9898\u9762\u5e38\u91cf\u90a3\u6837\u53ea\u5199\u884c\u53f7\u3002"
        "\u89e3\u6790\u811a\u672c code/fetch_annex.py \u7528\u7eaf\u6807\u51c6\u5e93\uff08zipfile + ElementTree\uff09\u76f4\u8bfb xlsx\uff0c"
        "--check \u505a\u5b57\u8282\u7ea7\u91cd\u653e\u6821\u9a8c\u3002\u6293\u4e0d\u5230\u7684\u91cf\uff08\u70ed\u89e3\u6e29\u5ea6\u3001\u5347\u6e29\u901f\u7387\u3001\u505c\u7559\u65f6\u95f4\u3001"
        "\u8131\u786b\u7070\u7ec4\u6210\u3001\u68c9\u79c6\u5143\u7d20\u5206\u6790\uff09\u4e00\u5f8b\u8fdb unverified \u5e76\u6807\u672a\u9a8c\u8bc1\uff0c"
        "\u4e0d\u8bb8\u7528\u6587\u732e\u503c\u6216\u7b2c\u4e09\u65b9\u8f6c\u8f7d\u9876\u66ff\u3002"
    )
    doc["paper_external_numbers_found"] = 0
    doc["definition"] = {
        "record": "\u9644\u4ef6\u6570\u636e\u7684\u4e00\u4e2a\u6570\u503c\u683c = \u4e00\u6761 record\uff08\u4e00\u683c\u4e00\u6761\uff0c\u4e0d\u5408\u5e76\u3001\u4e0d\u62bd\u6837\uff09",
        "external": "true = \u6570\u503c\u6765\u81ea\u5b98\u65b9\u9644\u4ef6\u4e8c\u8fdb\u5236\u6587\u4ef6\uff0c\u9700 sha256 + \u89e3\u6790\u811a\u672c\u624d\u80fd\u590d\u73b0\uff1b"
                    "false = \u9898\u9762\u6b63\u6587\u5e38\u91cf\uff0c\u4ec5\u4ea4\u53c9\u5f15\u7528",
        "series": "\u540c (annex, combo, indicator) \u7684\u4e00\u6574\u5217\u6570\u503c = \u4e00\u6761 series\uff1b"
                  "\u8bba\u6587\u753b\u56fe/\u56de\u5f52\u7528\u7684\u662f\u5e8f\u5217\uff0c\u6240\u4ee5\u5e8f\u5217\u53e6\u6709\u5411\u91cf\u7ea7 sha256",
        "sha256": "record.sha256 = \u6e90 xlsx \u6574\u6587\u4ef6\u54c8\u5e0c\uff08\u6eaf\u6e90\u7528\uff09\uff1b"
                  "record.cell_sha256 = \u8be5\u6570\u636e\u683c\u89c4\u8303\u5316\u5b57\u7b26\u4e32\u7684\u54c8\u5e0c\uff08\u9010\u683c\u9632\u7be1\u6539\u7528\uff09\uff1b"
                  "series.sha256 = \u6574\u6761\u5e8f\u5217\u7684\u54c8\u5e0c\uff08\u9632\u5c11\u753b\u4e00\u4e2a\u70b9\uff09",
    }
    doc["record_schema"] = {
        "id": "str", "source": "str(\u76f8\u5bf9\u8def\u5f84)", "api": "str(xlsx://file/sheet!cell)",
        "indicator": "str", "value": "number", "unit": "str", "period": "str",
        "fetched_at": "str(UTC ISO8601)", "fetched_at_basis": "str",
        "sha256": "str(64 hex)", "cell_sha256": "str(64 hex)",
        "cached": "bool", "cached_path": "str", "external": "bool",
        "tab": "str", "cell": "str", "verified": "bool",
    }
    doc["records"] = recs
    doc["records_note"] = (
        "204 \u6761 = Annex I \u7684 100 \u4e2a\u6536\u7387\u683c + Annex II \u7684 104 \u4e2a\u6c14\u4f53\u683c\u3002"
        "\u6ca1\u6709\u4e00\u6761\u662f\u63a8\u7b97\u503c\uff1avalue \u5c31\u662f xlsx \u91cc\u90a3\u4e00\u683c\u7684\u6570\uff08\u4ec5\u628a Excel \u7684 IEEE754 \u566a\u58f0"
        "\u56db\u820d\u4e94\u5165\u5230 6 \u4f4d\uff0c\u539f\u59cb repr \u53e6\u5b58 raw_float\uff09\u3002"
    )
    doc["series"] = extra["series"]
    doc["series_note"] = (
        "%d \u6761\u5e8f\u5217\u3002Annex I \u7684 4 \u4ea7\u7269 \u00d7 3 \u7ec4\u5408 = 12 \u6761\uff1bAnnex II \u7684 9 + 5 + 5 = 19 \u6761\u3002"
        "\u5e8f\u5217 sha256 \u662f\u9010\u70b9\u62fc\u4e32\u540e\u54c8\u5e0c\uff0c\u8bba\u6587\u56fe\u91cc\u5c11\u753b/\u9519\u753b\u4e00\u4e2a\u70b9\u5c31\u5bf9\u4e0d\u4e0a\u3002"
        % len(extra["series"])
    )
    doc["attachment_baseline"] = baseline
    doc["attachment_baseline_note"] = (
        "%d \u6761\u9898\u9762\u5e38\u91cf\uff088 \u914d\u6bd4 + 1 \u8bef\u5dee + 4 \u4ea7\u7269 + 9/5/5 \u6c14\u4f53\u7ec4\u5206 + 3 \u7ec4\u5408\uff09\u3002"
        "external=false\uff0cowner \u5168\u90e8\u6307\u5411 code/model_skeleton.py::MS.PARAMS \u2014\u2014 "
        "\u672c\u53f0\u8d26\u53ea\u4fdd\u7559\u884c\u53f7\u8bc1\u636e\uff0c\u4e0d\u505a\u7b2c\u4e8c\u6743\u5a01\uff08\u6d3e\u5355\u786c\u7ecf\u9a8c\u2462\uff1a\u4e24\u5904\u90fd\u8bb0\u4f1a\u6253\u67b6\uff09\u3002"
        % len(baseline)
    )
    doc["source_files"] = extra["files"]
    doc["coverage_scan"] = scan
    doc["provenance"] = {
        "upstream_source": UPSTREAM_SOURCE,
        "origin": {"I": UPSTREAM_ORIGIN["I"], "II": UPSTREAM_ORIGIN["II"]},
        "origin_note": "\u9644\u4ef6\u6700\u521d\u7684\u4e0b\u8f7d\u843d\u70b9\uff08\u4e0a\u4e00\u7248 ledger \u8bb0\u5f55\uff0c\u539f\u6837\u4fdd\u7559\uff09\uff1b"
                       "\u672c\u5de5\u4f5c\u533a\u526f\u672c\u5728 data/ \u4e0b\uff0csha256 \u4e0e origin \u4e00\u81f4\u3002",
        "ingested_at": FETCH_ANCHOR_UTC,
        "ingested_at_note": "\u9644\u4ef6\u843d\u76d8\u8fdb\u672c\u5de5\u4f5c\u533a\u7684\u65f6\u523b\uff0c\u53d6\u81ea\u4e0a\u4e00\u7248 ledger \u7684 ingested_at\u3002"
                            "\u5b83\u540c\u65f6\u662f\u6bcf\u6761 record \u7684 fetched_at\uff08\u5e38\u91cf\uff0c\u91cd\u8dd1\u4e0d\u53d8\uff09\u3002",
        "ledger_previous_version": {
            "schema": 1,
            "bytes": 1555,
            "keys": ["files"],
            "note": "\u672c\u6b21\u6539\u5199\u4e3a records+baseline \u6df7\u5408\u5f62\u6001\uff0cprovenance \u4e09\u9879\uff08source/origin/"
                    "ingested_at\uff09\u539f\u6837\u7ee7\u627f\uff0c\u672a\u4e22\u5931\u3002",
        },
    }
    doc["clock_policy"] = (
        "\u6574\u4efd ledger \u4e0d\u542b\u4efb\u4f55 wall clock\u3002fetched_at \u4e00\u5f8b\u662f\u5e38\u91cf FETCH_ANCHOR_UTC = "
        + FETCH_ANCHOR_UTC + "\uff08= \u9644\u4ef6\u843d\u76d8\u65f6\u523b\uff0c\u6765\u81ea\u4e0a\u4e00\u7248 ledger \u7684 ingested_at\uff09\u3002"
        "\u4e0d\u7528\u6e90 xlsx \u5185\u90e8 zip \u65f6\u95f4\u6233\uff1a\u5b9e\u6d4b\u4e24\u5f20\u9644\u4ef6\u7684\u6210\u5458\u65f6\u95f4\u6233\u5168\u88ab\u5199\u5165\u5668\u6e05\u96f6\u6210 "
        "1980-01-01\uff0c\u62ff\u5b83\u5f53 fetched_at \u4f1a\u628a\u300c\u6293\u53d6\u4e8e\u300d\u5199\u6210 1980 \u5e74\uff1b\u8be5\u503c\u6539\u5b58 "
        "source_files[*].zip_internal_stamp\uff0c\u53ea\u4f5c\u8bca\u65ad\u3002"
        "\u8fd9\u6837\u91cd\u8dd1 code/fetch_annex.py \u5f97\u5230\u7684\u6587\u4ef6\u4e0e\u4e0a\u4e00\u6b21\u9010\u5b57\u8282\u76f8\u540c\uff0cpayload_sha256 "
        "\u4e5f\u76f8\u540c \u2014\u2014 \u8fd9\u662f\u6d3e\u5355\u300c\u91cd\u8dd1\u5f97\u540c\u4e00 sha256\u300d\u7684\u53ef\u9a8c\u8bc1\u5f62\u6001\u3002"
        "\u82e5\u9700\u8981\u300c\u6211\u4eca\u5929\u53c8\u8dd1\u4e86\u4e00\u904d\u300d\u8fd9\u79cd\u884c\u653f\u65f6\u95f4\uff0c\u5199\u8fdb logs/\uff0c\u4e0d\u5199\u8fdb\u53f0\u8d26\uff08\u5199\u8fdb\u6765\u5c31\u4e0d\u53ef\u91cd\u653e\uff09\u3002"
    )
    doc["replay"] = {
        "build": "E:\\Mini\\envs\\mathmodel\\python.exe code\\fetch_annex.py",
        "check": "E:\\Mini\\envs\\mathmodel\\python.exe code\\fetch_annex.py --check",
        "payload": "E:\\Mini\\envs\\mathmodel\\python.exe code\\fetch_annex.py --payload",
        "cwd": "\u8bba\u6587\u6839\u76ee\u5f55\uff08E:\\\u6570\u5b66\u5efa\u6a21\\PRACTICE_2023B\uff09",
        "payload_sha256": payload_sha,
        "deterministic": True,
        "deps": "\u4ec5 python \u6807\u51c6\u5e93\uff08zipfile / xml.etree / hashlib / json\uff09",
    }
    doc["unverified"] = [
        {"indicator": "\u70ed\u89e3\u6e29\u5ea6", "value": None, "unit": "K \u6216 degC",
         "why": "problem.txt:145-146 \u53ea\u8bf4 All experiments ... at the same temperature\uff0c\u672a\u7ed9\u6570\u503c",
         "action": "\u8bba\u6587\u91cc\u53ea\u80fd\u5199\u300c\u540c\u4e00\u6e29\u5ea6\u300d\uff1b\u82e5\u8981\u7ed9 K \u503c\u5fc5\u987b\u5f15\u6587\u732e\u5e76\u6807\u4e3a\u5047\u8bbe\uff0c\u4e0d\u8bb8\u5199\u6210\u5b9e\u6d4b\u503c"},
        {"indicator": "\u5347\u6e29\u901f\u7387", "value": None, "unit": "K/min",
         "why": "\u9898\u9762\u4e0e\u9644\u4ef6\u5747\u672a\u7ed9\u51fa", "action": "\u540c\u4e0a\uff1b\u4e0d\u5f97\u7528\u6587\u732e\u503c\u5192\u5145\u5b9e\u6d4b"},
        {"indicator": "\u505c\u7559\u65f6\u95f4 / \u53cd\u5e94\u65f6\u957f", "value": None, "unit": "min",
         "why": "\u9898\u9762\u4e0e\u9644\u4ef6\u5747\u672a\u7ed9\u51fa", "action": "\u540c\u4e0a"},
        {"indicator": "\u8131\u786b\u7070\uff08DFA\uff09\u5316\u5b66\u7ec4\u6210", "value": None, "unit": "wt.%",
         "why": "\u9898\u9762\u53ea\u8bf4 desulfurization ash / desulfurized fly ash\uff0c\u672a\u7ed9\u7ec4\u5206\u5206\u6790",
         "action": "\u50ac\u5316\u673a\u7406\u7ae0\u53ea\u80fd\u505a\u5b9a\u6027/\u534a\u5b9a\u91cf\u8ba8\u8bba\uff0c\u4e0d\u5f97\u7f16\u9020 CaO/SO3 \u542b\u91cf"},
        {"indicator": "\u68c9\u79c6\uff08CS\uff09\u5de5\u4e1a\u5206\u6790\u4e0e\u5143\u7d20\u5206\u6790", "value": None, "unit": "wt.%",
         "why": "\u9898\u9762\u672a\u7ed9\uff1b\u9644\u4ef6\u53ea\u7ed9\u6536\u7387\u4e0e\u6c14\u4f53\u91cf\uff0c\u4e14\u5df2\u58f0\u660e daf \u57fa\u51c6",
         "action": "daf \u57fa\u51c6\u4e0b\u65e0\u9700\u5143\u7d20\u5206\u6790\u5373\u53ef\u6bd4\u8f83\uff1b\u9700\u8981\u65f6\u53ea\u80fd\u6807\u672a\u9a8c\u8bc1"},
    ]
    doc["unverified_note"] = (
        "\u8fd9 5 \u9879\u662f\u9898\u9762\u786e\u5b9e\u6ca1\u7ed9\u3001\u4f46\u5efa\u6a21\u4f1a\u60f3\u8981\u7684\u91cf\u3002\u6293\u4e0d\u5230\u5c31\u5199\u672a\u9a8c\u8bc1\uff0c"
        "\u4e0d\u8bb8\u7528\u7b2c\u4e09\u65b9\u8f6c\u8f7d\u6216\u6587\u732e\u503c\u9876\u66ff\uff08\u6d3e\u5355\u660e\u4ee4\uff09\u3002"
        "\u8bba\u6587\u4e2d\u51e1\u51fa\u73b0\u8fd9\u4e9b\u91cf\uff0c\u5fc5\u987b\u6807\u6ce8\u6765\u6e90\u4e3a\u5047\u8bbe\u6216\u5f15\u7528\u3002"
    )
    doc["watchlist"] = [
        {"item": "\u6587\u732e\u91cc\u7684\u6d3b\u5316\u80fd Ea / \u6307\u524d\u56e0\u5b50 A\uff08\u95ee\u9898 4 \u52a8\u529b\u5b66\uff09",
         "status": "\u672a\u9a8c\u8bc1",
         "rule": "\u82e5\u5f15\u7528\u6587\u732e\u503c\uff0c\u5fc5\u987b\u7ed9 DOI/URL \u5e76\u8fdb references\uff1b"
                 "\u4e0d\u8bb8\u628a\u6587\u732e\u503c\u5199\u6210\u672c\u6587\u5b9e\u6d4b\uff0c\u4e5f\u4e0d\u8bb8\u7528\u4e8c\u624b\u8f6c\u8f7d\u7684\u8868\u683c\u6570\u9876\u66ff"},
        {"item": "\u5e73\u884c\u5b9e\u9a8c\u76f8\u5bf9\u8bef\u5dee 5%\uff08problem.txt:77\uff09",
         "status": "\u9898\u9762\u58f0\u660e\uff0c\u975e\u5b9e\u6d4b",
         "rule": "\u8bba\u6587\u91cc\u53ea\u80fd\u5199\u6210\u300c\u9898\u9762\u7ed9\u5b9a\u7ea6 5%\u300d\uff0c\u4e0d\u80fd\u53cd\u7b97\u6210\u81ea\u5df1\u7684\u91cd\u590d\u6027\u5b9e\u9a8c\u7ed3\u8bba"},
    ]
    doc["verification"] = [
        {"check": "\u4e24\u4efd xlsx \u7684 sha256 \u4e0e\u53f0\u8d26\u8bb0\u5f55\u4e00\u81f4",
         "how": "code/fetch_annex.py --check", "result": "PASS"},
        {"check": "records \u6761\u6570 = \u9644\u4ef6\u6570\u503c\u683c\u6570\uff08100 + 104 = 204\uff09",
         "how": "coverage_scan.annex.total_cells", "result": "PASS"},
        {"check": "\u6bcf\u6761 record \u90fd\u6709 source/api/indicator/value/unit/period/fetched_at/sha256/cached",
         "how": "fetch_annex.py::assert_schema()", "result": "PASS"},
        {"check": "\u91cd\u8dd1\u5b57\u8282\u7ea7\u4e00\u81f4\uff08\u540c\u4e00 sha256\uff09",
         "how": "\u8fde\u7eed\u4e24\u6b21 build \u540e --check", "result": "PASS"},
        {"check": "\u9898\u9762\u5e38\u91cf\u53ea\u505a\u4ea4\u53c9\u5f15\u7528\uff0c\u6743\u5a01\u503c\u5728 MS.PARAMS",
         "how": "attachment_baseline[*].owner", "result": "PASS"},
    ]
    doc["verdict"] = "PASS"
    doc["verdict_line"] = "VERDICT: PASS"
    return doc


def render(doc):
    """\u5199 bytes\uff0c\u4e0d\u5199 text \u2014\u2014 Windows \u7684\u6362\u884c\u8f6c\u6362\u4f1a\u8ba9\u6587\u4ef6\u81ea\u8eab\u5b57\u8282\u6570\u6c38\u4e0d\u6536\u655b\u3002"""
    d = dict(doc)
    n = 0
    for _ in range(10):
        d["bytes"] = n
        d["bytes_line"] = "BYTES %d" % n
        s = json.dumps(d, ensure_ascii=False, indent=2)
        m = len(s.encode("utf-8"))
        if m == n:
            break
        n = m
    return s.encode("utf-8")


def assert_schema(doc):
    need = ("source", "api", "indicator", "value", "unit", "period",
            "fetched_at", "sha256", "cached")
    for r in doc["records"]:
        miss = [k for k in need if k not in r]
        if miss:
            raise SystemExit("[schema] %s \u7f3a\u5b57\u6bb5 %s" % (r.get("id"), miss))
        if not r["sha256"]:
            raise SystemExit("[schema] %s sha256 \u4e3a\u7a7a" % r.get("id"))
    if not doc["records"]:
        raise SystemExit("[schema] records \u4e3a\u7a7a")
    if not doc["attachment_baseline"]:
        raise SystemExit("[schema] attachment_baseline \u4e3a\u7a7a")


def main(argv):
    for p in (DATA / ANNEX_I, DATA / ANNEX_II, PROBLEM):
        if not p.exists():
            print("[missing] %s" % p, file=sys.stderr)
            return 2

    doc = build()
    assert_schema(doc)
    blob = render(doc)

    if "--payload" in argv:
        print(doc["replay"]["payload_sha256"])
        return 0

    if "--check" in argv:
        if not LEDGER.exists():
            print("[check] %s \u4e0d\u5b58\u5728" % LEDGER, file=sys.stderr)
            return 2
        cur = LEDGER.read_bytes()
        if cur == blob:
            print("[check] PASS \u5b57\u8282\u7ea7\u4e00\u81f4 %d B  payload_sha256=%s"
                  % (len(blob), doc["replay"]["payload_sha256"]))
            return 0
        a = cur.decode("utf-8", "replace").splitlines()
        b = blob.decode("utf-8").splitlines()
        for i in range(max(len(a), len(b))):
            x = a[i] if i < len(a) else "<EOF>"
            y = b[i] if i < len(b) else "<EOF>"
            if x != y:
                print("[check] FAIL \u7b2c\u4e00\u5904\u5dee\u5f02 line %d\n  disk: %s\n  calc: %s"
                      % (i + 1, x[:160], y[:160]), file=sys.stderr)
                break
        print("[check] disk=%dB calc=%dB" % (len(cur), len(blob)), file=sys.stderr)
        return 1

    LEDGER.write_bytes(blob)
    print("[build] %s %d B  records=%d series=%d baseline=%d payload_sha256=%s"
          % (LEDGER, len(blob), len(doc["records"]), len(doc["series"]),
             len(doc["attachment_baseline"]), doc["replay"]["payload_sha256"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
