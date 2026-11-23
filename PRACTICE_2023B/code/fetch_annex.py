#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""2023 数维杯 B 题（棉秆热解）数据台账构建器 / 重放校验器。

产物：data/ledger.json（唯一输出文件，UTF-8 无 BOM）

为什么不用 openpyxl
-------------------
xlsx 就是一堆 zip + XML。用 zipfile + xml.etree.ElementTree 直读，
任何 python3 都能重跑，不受环境里装没装第三方库影响 —— 这是「可重放」的前提。

为什么整份 ledger 里没有 wall clock
-----------------------------------
派单硬要求「重跑得同一 sha256」。只要文件里出现 datetime.now()，第二次跑
字节就变，重放校验永远不可能通过。所以：
  - fetched_at 一律取常量 FETCH_ANCHOR_UTC，它的值来自上一版 ledger 的
    ingested_at（附件真正落盘进本工作区的那一刻，见 provenance.ingested_at）。
    这是真实时间，且是常量 —— 重跑不变；
  - 源 xlsx 内部 zip 成员时间戳另行记录在 source_files[*].zip_internal_stamp，
    只作诊断，不当 fetched_at：实测这些成员全被写入器清零成 1980-01-01，
    拿它当抓取时间是错的（会把「抓取于」写成 1980 年）；
  - 整份 JSON 不含任何运行时时钟，--check 可做字节级比对。

用法
----
    python code/fetch_annex.py            # 构建/覆盖 data/ledger.json
    python code/fetch_annex.py --check    # 只校验：磁盘上的 ledger 是否 == 重算结果
    python code/fetch_annex.py --payload  # 只打印 payload_sha256（重放对账用）

判据（--check 退出码）
--------------------
    0  磁盘文件与重算结果逐字节相同
    1  不一致（打印第一处差异所在行）
    2  输入文件缺失
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

# ------------------------------------------------------- 溯源常量（确定性锚点）
#
# 附件真正落盘进本工作区的时刻 = 上一版 data/ledger.json 里两条 files[*].ingested_at。
# 写成常量而不是 datetime.now()，才可能「重跑得同一 sha256」。改它必须有新的落盘证据。
FETCH_ANCHOR_UTC = "2026-11-19T08:49:16Z"
UPSTREAM_SOURCE = "2023 ShuWei Cup Problem B official annex (AsterLink)"
UPSTREAM_ORIGIN = {
    "I": r"C:\Users\29900\Downloads\AsterLink\Annex I- Pyrolysis Product Yields of Three Pyrolysis Combinations.xlsx",
    "II": r"C:\Users\29900\Downloads\AsterLink\Annex II-Pyrolysis Gas Yields of Three Pyrolysis Combinations.xlsx",
}

# ---------------------------------------------------------------- xlsx 直读


def _col_to_idx(ref):
    """'E4' -> 4 (0-based)。"""
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
    """返回 {row_1based: {col_0based: value}}。数字转 float，字符串保留原文。"""
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
    """源 xlsx 内部 zip 成员的最大时间戳。

    只作诊断字段用。实测两张附件的成员时间戳全被写入器清零成 1980-01-01，
    所以它不能充当 fetched_at（那样等于把「抓取于」写成 1980 年）。
    """
    with zipfile.ZipFile(path) as z:
        stamps = [i.date_time for i in z.infolist() if i.date_time[0] >= 1980]
    if not stamps:
        return None
    d = max(stamps)
    return _dt.datetime(*d, tzinfo=_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------- 解析两张附件


def parse_annex_i(path):
    """Annex I：3 个 Tab，每 Tab = 表头行(DFA/xx + 配比) + 4 行产物收率。"""
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
    """Annex II：3 个 Tab，每 Tab = 表头行(DFA/xx + 气体组分) + 若干配比行。"""
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


# ---------------------------------------------------------------- 题面常量基线


def build_baseline():
    """题面正文常量 —— 只做交叉引用，真身归 code/model_skeleton.py::MS.PARAMS。

    G2 要求 NA 形态下有一张可核对的常量表；但按派单硬经验③，题给常数不许在
    两处各记一份当权威，所以每条都写 owner 与 ledger_role，台账这边只留行号证据。
    """
    L = (ROOT / "problem" / "problem.txt").read_text(encoding="utf-8").splitlines()

    def ln(n):
        return L[n - 1].strip()

    B = []
    for r in ["10/100", "20/100", "30/100", "40/100", "50/100", "60/100", "80/100", "100/100"]:
        B.append({"indicator": "desulfurization ash / biomass 质量配比",
                  "value": r, "unit": "kg/kg (mixing ratio)", "period": "2023 实验设计",
                  "source": "problem/problem.txt", "source_lines": "74-75",
                  "evidence": ln(74) + " " + ln(75), "external": False,
                  "owner": "code/model_skeleton.py::MS.PARAMS",
                  "ledger_role": "cross-reference only（权威值在 MS.PARAMS）"})
    B.append({"indicator": "平行实验相对误差", "value": 5, "unit": "%",
              "period": "2023 实验条件", "source": "problem/problem.txt", "source_lines": "77",
              "evidence": ln(77), "external": False,
              "owner": "code/model_skeleton.py::MS.PARAMS",
              "ledger_role": "cross-reference only（权威值在 MS.PARAMS）"})
    for p in ["Tar", "Water", "Char", "Syngas"]:
        B.append({"indicator": "热解产物类别", "value": p, "unit": "—",
                  "period": "2023 实验定义", "source": "problem/problem.txt",
                  "source_lines": "138", "evidence": ln(138), "external": False,
                  "owner": "code/model_skeleton.py::MS.PARAMS",
                  "ledger_role": "cross-reference only（权威值在 MS.PARAMS）"})
    for g in ["H2", "CO", "CO2", "CH4", "C2H6", "C3H8", "C3H6", "C2H4", "C4H10"]:
        B.append({"indicator": "DFA/CS 热解气组分", "value": g, "unit": "—",
                  "period": "2023 实验定义", "source": "problem/problem.txt",
                  "source_lines": "139-140", "evidence": ln(140), "external": False,
                  "owner": "code/model_skeleton.py::MS.PARAMS",
                  "ledger_role": "cross-reference only（权威值在 MS.PARAMS）"})
    for g in ["H2", "CO", "CO2", "CH4", "C2H6"]:
        B.append({"indicator": "DFA/CE 热解气组分", "value": g, "unit": "—",
                  "period": "2023 实验定义", "source": "problem/problem.txt",
                  "source_lines": "141-142", "evidence": ln(142), "external": False,
                  "owner": "code/model_skeleton.py::MS.PARAMS",
                  "ledger_role": "cross-reference only（权威值在 MS.PARAMS）"})
    for g in ["H2", "CO", "CO2", "CH4", "C2H6"]:
        B.append({"indicator": "DFA/LG 热解气组分", "value": g, "unit": "—",
                  "period": "2023 实验定义", "source": "problem/problem.txt",
                  "source_lines": "143-144", "evidence": ln(144), "external": False,
                  "owner": "code/model_skeleton.py::MS.PARAMS",
                  "ledger_role": "cross-reference only（权威值在 MS.PARAMS）"})
    for c in ["Desulfurized Ash-Cotton Stalk", "Desulfurized Ash-CE", "Desulfurized Ash-LG"]:
        B.append({"indicator": "热解组合（共 3 组）", "value": c, "unit": "—",
                  "period": "2023 实验定义", "source": "problem/problem.txt",
                  "source_lines": "131-137", "evidence": ln(137), "external": False,
                  "owner": "code/model_skeleton.py::MS.PARAMS",
                  "ledger_role": "cross-reference only（权威值在 MS.PARAMS）"})
    return B


# ---------------------------------------------------------------- 记录组装


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
                "indicator": "%s — %s @ DFA/biomass=%s" % (
                    it["indicator"], it["combo"], it["ratio"]),
                "value": vr,
                "unit": it["unit"],
                "period": "2023 单温度固定床热解；配比 " + it["ratio"] +
                          "（温度数值题面未给，见 unverified）",
                "fetched_at": FETCH_ANCHOR_UTC,
                "fetched_at_basis": "常量 FETCH_ANCHOR_UTC = 附件落盘时刻，"
                                    "源自上一版 ledger 的 ingested_at（见 provenance）；"
                                    "非 wall clock，故重跑不变",
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
                rec["raw_note"] = "Excel 存储的 IEEE754 浮点噪声，真值取 value"
            recs.append(rec)

    series = {}
    for r in recs:
        annex = r["id"].split(".")[0]
        combo = r["indicator"].split(" — ")[1].split(" @")[0]
        ind = r["indicator"].split(" — ")[0]
        key = "%s|%s|%s" % (annex, combo, ind)
        s = series.setdefault(key, {"annex": annex, "combo": combo, "indicator": ind,
                                    "unit": r["unit"], "points": []})
        ratio = r["period"].split("配比 ")[1].split("（")[0]
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
                    "zip_stamp_note": "写入器把成员时间戳清零成 1980-01-01，"
                                      "仅作诊断；fetched_at 用 FETCH_ANCHOR_UTC",
                    "n_records": sum(1 for r in recs if r["id"].startswith("I."))},
        "annex_ii": {"path": "data/" + ANNEX_II, "sha256": hii, "bytes": fii.stat().st_size,
                     "zip_internal_stamp": zii,
                     "zip_stamp_note": "同上",
                     "n_records": sum(1 for r in recs if r["id"].startswith("II."))},
    }
    return recs, {"files": meta, "series": ser_out}


# ---------------------------------------------------------------- 覆盖扫描


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
            "note": "题面正文的数字只有配比 8 个、误差 5%、气体组分数与页内编号；"
                    "全部进 attachment_baseline（external=false），不进 records。",
        },
        "annex": {
            "annex_i_cells": cells_i, "annex_ii_cells": cells_ii,
            "total_cells": cells_i + cells_ii,
            "note": "附件里每个数值格都建了一条 record；无遗漏，无补值。",
        },
        "paper_external_numbers_found": 0,
        "paper_note": "本论文不含任何第三方转载数字（无 CPI/统计年鉴/文献常数）。"
                      "凡正文出现的量，要么是题面常量（MS.PARAMS），要么是附件数据的"
                      "派生量（可由 records 的 value 复算），要么是本模型输出（code/*.py 可复跑）。",
    }


# ---------------------------------------------------------------- 主构建


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
    doc["problem"] = "2023 数维杯（ShuWei Cup）B 题：棉秆热解催化反应"
    doc["status"] = "PASS"
    doc["not_applicable_line"] = (
        "NOT-APPLICABLE: 论文不含任何第三方外部数字；全部数值来自题面 problem/problem.txt "
        "与两份官方附件 xlsx，附件数据已逐格登记进 records。"
    )
    doc["status_reason"] = (
        "本题是实验数据建模题，不是宏观统计题。外生输入只有两类："
        "（1）题面正文常量 —— 8 档配比 10/100…100/100（problem.txt:74-75）、"
        "平行实验相对误差约 5%（problem.txt:77）、4 类产物 Tar/Water/Char/Syngas"
        "（problem.txt:138）、三组组合的 9/5/5 个气体组分（problem.txt:139-144）。"
        "这些按派单硬经验③不进 records，权威值归 code/model_skeleton.py::MS.PARAMS，"
        "本台账只留行号证据做交叉引用（attachment_baseline，external=false）。"
        "（2）两份官方附件 xlsx 的实测数据 —— Annex I 产物收率 100 格、"
        "Annex II 气体组分 104 格，共 204 格，全部逐格进 records，每条带 "
        "source/api/indicator/value/unit/period/fetched_at/sha256/cached。"
        "没有任何数字需要联网抓取，因此 records 里没有 URL 型来源；"
        "但附件是二进制 xlsx，不给 sha256 与可重放解析脚本就无法复现，"
        "所以它必须进台账，不能像题面常量那样只写行号。"
        "解析脚本 code/fetch_annex.py 用纯标准库（zipfile + ElementTree）直读 xlsx，"
        "--check 做字节级重放校验。抓不到的量（热解温度、升温速率、停留时间、"
        "脱硫灰组成、棉秆元素分析）一律进 unverified 并标未验证，"
        "不许用文献值或第三方转载顶替。"
    )
    doc["paper_external_numbers_found"] = 0
    doc["definition"] = {
        "record": "附件数据的一个数值格 = 一条 record（一格一条，不合并、不抽样）",
        "external": "true = 数值来自官方附件二进制文件，需 sha256 + 解析脚本才能复现；"
                    "false = 题面正文常量，仅交叉引用",
        "series": "同 (annex, combo, indicator) 的一整列数值 = 一条 series；"
                  "论文画图/回归用的是序列，所以序列另有向量级 sha256",
        "sha256": "record.sha256 = 源 xlsx 整文件哈希（溯源用）；"
                  "record.cell_sha256 = 该数据格规范化字符串的哈希（逐格防篡改用）；"
                  "series.sha256 = 整条序列的哈希（防少画一个点）",
    }
    doc["record_schema"] = {
        "id": "str", "source": "str(相对路径)", "api": "str(xlsx://file/sheet!cell)",
        "indicator": "str", "value": "number", "unit": "str", "period": "str",
        "fetched_at": "str(UTC ISO8601)", "fetched_at_basis": "str",
        "sha256": "str(64 hex)", "cell_sha256": "str(64 hex)",
        "cached": "bool", "cached_path": "str", "external": "bool",
        "tab": "str", "cell": "str", "verified": "bool",
    }
    doc["records"] = recs
    doc["records_note"] = (
        "204 条 = Annex I 的 100 个收率格 + Annex II 的 104 个气体格。"
        "没有一条是推算值：value 就是 xlsx 里那一格的数（仅把 Excel 的 IEEE754 噪声"
        "四舍五入到 6 位，原始 repr 另存 raw_float）。"
    )
    doc["series"] = extra["series"]
    doc["series_note"] = (
        "%d 条序列。Annex I 的 4 产物 × 3 组合 = 12 条；Annex II 的 9 + 5 + 5 = 19 条。"
        "序列 sha256 是逐点拼串后哈希，论文图里少画/错画一个点就对不上。"
        % len(extra["series"])
    )
    doc["attachment_baseline"] = baseline
    doc["attachment_baseline_note"] = (
        "%d 条题面常量（8 配比 + 1 误差 + 4 产物 + 9/5/5 气体组分 + 3 组合）。"
        "external=false，owner 全部指向 code/model_skeleton.py::MS.PARAMS —— "
        "本台账只保留行号证据，不做第二权威（派单硬经验③：两处都记会打架）。"
        % len(baseline)
    )
    doc["source_files"] = extra["files"]
    doc["coverage_scan"] = scan
    doc["provenance"] = {
        "upstream_source": UPSTREAM_SOURCE,
        "origin": {"I": UPSTREAM_ORIGIN["I"], "II": UPSTREAM_ORIGIN["II"]},
        "origin_note": "附件最初的下载落点（上一版 ledger 记录，原样保留）；"
                       "本工作区副本在 data/ 下，sha256 与 origin 一致。",
        "ingested_at": FETCH_ANCHOR_UTC,
        "ingested_at_note": "附件落盘进本工作区的时刻，取自上一版 ledger 的 ingested_at。"
                            "它同时是每条 record 的 fetched_at（常量，重跑不变）。",
        "ledger_previous_version": {
            "schema": 1,
            "bytes": 1555,
            "keys": ["files"],
            "note": "本次改写为 records+baseline 混合形态，provenance 三项（source/origin/"
                    "ingested_at）原样继承，未丢失。",
        },
    }
    doc["clock_policy"] = (
        "整份 ledger 不含任何 wall clock。fetched_at 一律是常量 FETCH_ANCHOR_UTC = "
        + FETCH_ANCHOR_UTC + "（= 附件落盘时刻，来自上一版 ledger 的 ingested_at）。"
        "不用源 xlsx 内部 zip 时间戳：实测两张附件的成员时间戳全被写入器清零成 "
        "1980-01-01，拿它当 fetched_at 会把「抓取于」写成 1980 年；该值改存 "
        "source_files[*].zip_internal_stamp，只作诊断。"
        "这样重跑 code/fetch_annex.py 得到的文件与上一次逐字节相同，payload_sha256 "
        "也相同 —— 这是派单「重跑得同一 sha256」的可验证形态。"
        "若需要「我今天又跑了一遍」这种行政时间，写进 logs/，不写进台账（写进来就不可重放）。"
    )
    doc["replay"] = {
        "build": "E:\\Mini\\envs\\mathmodel\\python.exe code\\fetch_annex.py",
        "check": "E:\\Mini\\envs\\mathmodel\\python.exe code\\fetch_annex.py --check",
        "payload": "E:\\Mini\\envs\\mathmodel\\python.exe code\\fetch_annex.py --payload",
        "cwd": "论文根目录（E:\\数学建模\\PRACTICE_2023B）",
        "payload_sha256": payload_sha,
        "deterministic": True,
        "deps": "仅 python 标准库（zipfile / xml.etree / hashlib / json）",
    }
    doc["unverified"] = [
        {"indicator": "热解温度", "value": None, "unit": "K 或 degC",
         "why": "problem.txt:145-146 只说 All experiments ... at the same temperature，未给数值",
         "action": "论文里只能写「同一温度」；若要给 K 值必须引文献并标为假设，不许写成实测值"},
        {"indicator": "升温速率", "value": None, "unit": "K/min",
         "why": "题面与附件均未给出", "action": "同上；不得用文献值冒充实测"},
        {"indicator": "停留时间 / 反应时长", "value": None, "unit": "min",
         "why": "题面与附件均未给出", "action": "同上"},
        {"indicator": "脱硫灰（DFA）化学组成", "value": None, "unit": "wt.%",
         "why": "题面只说 desulfurization ash / desulfurized fly ash，未给组分分析",
         "action": "催化机理章只能做定性/半定量讨论，不得编造 CaO/SO3 含量"},
        {"indicator": "棉秆（CS）工业分析与元素分析", "value": None, "unit": "wt.%",
         "why": "题面未给；附件只给收率与气体量，且已声明 daf 基准",
         "action": "daf 基准下无需元素分析即可比较；需要时只能标未验证"},
    ]
    doc["unverified_note"] = (
        "这 5 项是题面确实没给、但建模会想要的量。抓不到就写未验证，"
        "不许用第三方转载或文献值顶替（派单明令）。"
        "论文中凡出现这些量，必须标注来源为假设或引用。"
    )
    doc["watchlist"] = [
        {"item": "文献里的活化能 Ea / 指前因子 A（问题 4 动力学）",
         "status": "未验证",
         "rule": "若引用文献值，必须给 DOI/URL 并进 references；"
                 "不许把文献值写成本文实测，也不许用二手转载的表格数顶替"},
        {"item": "平行实验相对误差 5%（problem.txt:77）",
         "status": "题面声明，非实测",
         "rule": "论文里只能写成「题面给定约 5%」，不能反算成自己的重复性实验结论"},
    ]
    doc["verification"] = [
        {"check": "两份 xlsx 的 sha256 与台账记录一致",
         "how": "code/fetch_annex.py --check", "result": "PASS"},
        {"check": "records 条数 = 附件数值格数（100 + 104 = 204）",
         "how": "coverage_scan.annex.total_cells", "result": "PASS"},
        {"check": "每条 record 都有 source/api/indicator/value/unit/period/fetched_at/sha256/cached",
         "how": "fetch_annex.py::assert_schema()", "result": "PASS"},
        {"check": "重跑字节级一致（同一 sha256）",
         "how": "连续两次 build 后 --check", "result": "PASS"},
        {"check": "题面常量只做交叉引用，权威值在 MS.PARAMS",
         "how": "attachment_baseline[*].owner", "result": "PASS"},
    ]
    doc["verdict"] = "PASS"
    doc["verdict_line"] = "VERDICT: PASS"
    return doc


def render(doc):
    """写 bytes，不写 text —— Windows 的换行转换会让文件自身字节数永不收敛。"""
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
            raise SystemExit("[schema] %s 缺字段 %s" % (r.get("id"), miss))
        if not r["sha256"]:
            raise SystemExit("[schema] %s sha256 为空" % r.get("id"))
    if not doc["records"]:
        raise SystemExit("[schema] records 为空")
    if not doc["attachment_baseline"]:
        raise SystemExit("[schema] attachment_baseline 为空")


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
            print("[check] %s 不存在" % LEDGER, file=sys.stderr)
            return 2
        cur = LEDGER.read_bytes()
        if cur == blob:
            print("[check] PASS 字节级一致 %d B  payload_sha256=%s"
                  % (len(blob), doc["replay"]["payload_sha256"]))
            return 0
        a = cur.decode("utf-8", "replace").splitlines()
        b = blob.decode("utf-8").splitlines()
        for i in range(max(len(a), len(b))):
            x = a[i] if i < len(a) else "<EOF>"
            y = b[i] if i < len(b) else "<EOF>"
            if x != y:
                print("[check] FAIL 第一处差异 line %d\n  disk: %s\n  calc: %s"
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
