# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# AI 辅助：DeepSeek Harness 助手生成的盘点脚本（逐文件读 schema，不读全内容）。
# -*- coding: utf-8 -*-
"""Build a per-file inventory of the released package.

For every file under the package root we record: relative path, dataset, record,
camera (when the path encodes one), extension, bytes, and -- for tables -- the
column list and row count.  Files that share an identical column list are folded
into one "schema family" so the document stays readable: there are 593 CSVs but
far fewer distinct table layouts.

Output:
  data/data_manifest.json   full per-file records + schema families
  ../23-数据包逐文件清单.md  human-readable summary
"""
from __future__ import annotations

import os

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(r"Restocking_Problem_and_Data_EN")
OUT = Path(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"))
DOC = Path(r"23-数据包逐文件清单.md")

CAM_RE = re.compile(r"(head_?stereo|head|left_wrist|right_wrist|wrist_left|wrist_right|"
                    r"left|right|top|front|hand_left|hand_right)", re.I)


def dataset_and_record(rel: str):
    parts = rel.split("/")
    ds = rec = ""
    cam = ""
    for p in parts:
        if p in ("EgoDemo", "EgoPro", "EgoStandard"):
            ds = p
        elif re.fullmatch(r"E\d{3}", p):
            rec = p
        elif re.fullmatch(r"[0-9a-f]{8}-[0-9a-f-]{27,}", p, re.I):
            rec = p[:8]
    for p in parts[-2:]:
        m = CAM_RE.search(Path(p).stem)
        if m:
            cam = m.group(1).lower()
            break
    return ds, rec, cam


def csv_schema(path: Path):
    try:
        with path.open("r", encoding="utf-8", newline="") as fh:
            r = csv.reader(fh)
            head = next(r)
            n = sum(1 for _ in r)
        return head, n
    except Exception as exc:  # noqa: BLE001
        return [f"<unreadable: {exc}>"], -1


def parquet_schema(path: Path):
    try:
        import pyarrow.parquet as pq

        f = pq.ParquetFile(str(path))
        return [f"{k}: {v}" for k, v in zip(f.schema_arrow.names, f.schema_arrow.types)], f.metadata.num_rows
    except Exception as exc:  # noqa: BLE001
        return [f"<unreadable: {exc}>"], -1


def json_keys(path: Path):
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(d, dict):
            return sorted(d.keys())[:24], len(d)
        return [f"<{type(d).__name__} of {len(d)}>"], len(d)
    except Exception as exc:  # noqa: BLE001
        return [f"<unreadable: {exc}>"], -1


def main():
    files = sorted(p for p in ROOT.rglob("*") if p.is_file())
    records = []
    families = defaultdict(lambda: {"files": 0, "rows": 0, "ext": "", "examples": []})
    per_ds = defaultdict(lambda: {"files": 0, "bytes": 0})
    per_ext = defaultdict(lambda: {"files": 0, "bytes": 0})

    for p in files:
        rel = p.relative_to(ROOT).as_posix()
        ds, rec, cam = dataset_and_record(rel)
        ext = p.suffix.lower().lstrip(".")
        size = p.stat().st_size
        entry = {
            "rel": rel,
            "dataset": ds,
            "record": rec,
            "camera": cam,
            "ext": ext,
            "bytes": size,
        }
        if ext == "csv":
            cols, n = csv_schema(p)
            entry["columns"] = cols
            entry["rows"] = n
        elif ext == "parquet":
            cols, n = parquet_schema(p)
            entry["columns"] = cols
            entry["rows"] = n
        elif ext == "json":
            cols, n = json_keys(p)
            entry["keys"] = cols
            entry["n_keys"] = n
        records.append(entry)
        per_ds[ds or "(root)"]["files"] += 1
        per_ds[ds or "(root)"]["bytes"] += size
        per_ext[ext]["files"] += 1
        per_ext[ext]["bytes"] += size
        if ext in ("csv", "parquet", "json"):
            key = (ext, tuple(entry.get("columns") or entry.get("keys") or []))
            fam = families[key]
            fam["files"] += 1
            fam["rows"] += max(entry.get("rows") or 0, 0)
            fam["ext"] = ext
            if len(fam["examples"]) < 3:
                fam["examples"].append(rel)

    payload = {
        "_meta": {
            "root": str(ROOT),
            "n_files": len(records),
            "bytes": sum(r["bytes"] for r in records),
            "by_dataset": {k: v for k, v in per_ds.items()},
            "by_ext": {k: v for k, v in per_ext.items()},
        },
        "schema_families": [
            {
                "ext": k[0],
                "n_files": v["files"],
                "total_rows": v["rows"],
                "columns": list(k[1]),
                "examples": v["examples"],
            }
            for k, v in sorted(families.items(), key=lambda kv: -kv[1]["files"])
        ],
        "files": records,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "data_manifest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n"
    )

    L = []
    A = L.append
    A("# 数据包逐文件清单（自动生成，勿手改）")
    A("")
    A(f"- 根目录：`{ROOT}`")
    A(f"- 文件数：**{len(records)}**，合计 **{payload['_meta']['bytes']/2**20:.1f} MiB**")
    A("")
    A("## 1. 按扩展名")
    A("")
    A("| ext | 文件数 | 体积 |")
    A("|---|---|---|")
    for k, v in sorted(per_ext.items(), key=lambda kv: -kv[1]["bytes"]):
        A(f"| `{k}` | {v['files']} | {v['bytes']/2**20:.1f} MiB |")
    A("")
    A("## 2. 按数据集")
    A("")
    A("| 数据集 | 文件数 | 体积 |")
    A("|---|---|---|")
    for k, v in sorted(per_ds.items(), key=lambda kv: -kv[1]["bytes"]):
        A(f"| {k} | {v['files']} | {v['bytes']/2**20:.1f} MiB |")
    A("")
    A("## 3. 表结构族（相同列名折叠为一族）")
    A("")
    A(f"共 **{len(families)}** 族。逐族列出列名与文件数，**这就是包里全部的表布局**。")
    A("")
    for i, fam in enumerate(
        sorted(families.items(), key=lambda kv: -kv[1]["files"]), 1
    ):
        cols = list(fam[0][1])
        A(f"### 族 {i}｜`{fam[0][0]}`｜{fam[1]['files']} 个文件｜累计 {fam[1]['rows']:,} 行")
        A("")
        A(f"列（{len(cols)}）：`" + "`, `".join(cols) + "`")
        A("")
        A("例：" + "；".join(f"`{e}`" for e in fam[1]["examples"]))
        A("")
    DOC.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")

    print(f"files={len(records)} bytes={payload['_meta']['bytes']}")
    print(f"schema families={len(families)}")
    for k, v in sorted(families.items(), key=lambda kv: -kv[1]["files"]):
        print(f"  {k[0]:8s} n={v['files']:4d} rows={v['rows']:>10,} cols={len(k[1]):3d}"
              f"  {', '.join(list(k[1])[:8])}{' ...' if len(k[1]) > 8 else ''}")


main()