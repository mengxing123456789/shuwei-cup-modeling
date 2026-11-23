#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把「一份下载来的数据」变成「论文里可以引用的数据」——中间必须过真实性闸。

为什么需要这一步：数维杯/国赛/美赛的附件常常是网盘断点、转发件、别人改过的版本。
数字一旦来自不可信文件，正文再漂亮也是废稿（G2 数据台账 + G12 论文数字都会红）。

做法（只有一条路）：check_file → verdict 必须是 OK → 复制进 <paper>/data/ → 写 ledger.json。
SUSPECT / BROKEN 一律拒收，理由原样打印；确实要收的（比如整个题目的附件只有一个来源）
用 --force，但 ledger 里会留 verdict 与 forced=true，评审一眼看得见，不会被当成干净数据。

用法：
    python ingest_data.py <论文目录> <文件>... [--source "赛方网盘 Problem A：Data.xlsx"]
                                          [--note "2025 秋季赛 A 题官方附件"]
                                          [--dry] [--force]
退出码：0 全部收下；1 有文件被拒（含 SUSPECT/BROKEN）。
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from mmkit import authenticity as A  # noqa: E402

LEDGER = "ledger.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_ledger(p: Path) -> dict:
    if p.is_file():
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(obj, dict) and "files" in obj:
                return obj
        except (ValueError, OSError):
            pass
    return {"schema": 1, "updated_at": "", "files": []}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="收数据：先核真实性，再进 data/")
    ap.add_argument("paper", help="论文目录（产物只进这里的 data/）")
    ap.add_argument("files", nargs="+", help="要收进来的文件")
    ap.add_argument("--source", default="", help="来源一句话（网盘/官网/GitHub/队友转发）")
    ap.add_argument("--note", default="", help="备注（题号、届次、附件号）")
    ap.add_argument("--dest", default="data", help="目标子目录，默认 data")
    ap.add_argument("--dry", action="store_true", help="只核不复制")
    ap.add_argument("--force", action="store_true", help="非 OK 也收（ledger 里会标 forced）")
    args = ap.parse_args(argv)

    paper = Path(args.paper)
    dest = paper / args.dest
    ledger_path = dest / LEDGER
    ledger = _load_ledger(ledger_path)
    root = A.corpus.corpus_root()

    refused, kept = [], []
    for f in args.files:
        src = Path(f)
        if not src.is_file():
            print(f"[缺] {f}")
            refused.append((f, "文件不存在"))
            continue
        # check_file 要求 path 在 root 下（它算 rel 与来源状态）；语料根之外的散件
        # 用文件自身所在目录当 root，等价于「相对它自己」，来源状态会落「官方原件」以外的推断
        base = root if src.is_relative_to(root) else src.parent
        e = A.check_file(src, base)
        line = f"[{e.verdict}] {src.name}  {A._fmt_size(e.size)}  {e.year}{e.problem}  {e.reason}"
        print(line)
        if e.verdict != "OK" and not args.force:
            refused.append((src.name, f"{e.verdict}: {e.reason}"))
            continue
        if args.dry:
            kept.append(src.name)
            continue
        dest.mkdir(parents=True, exist_ok=True)
        dst = dest / src.name
        if dst.exists() and A.sha256_file(dst) != e.sha256:
            print(f"  [注意] {dst.name} 已存在且内容不同，覆盖前请确认（本次已覆盖）")
        shutil.copy2(src, dst)
        row = {
            "name": src.name,
            "path": str(dst),
            "sha256": e.sha256,
            "size": e.size,
            "ext": e.ext,
            "year": e.year,
            "problem": e.problem,
            "verdict": e.verdict,
            "reason": e.reason,
            "forced": bool(e.verdict != "OK"),
            "source": args.source,
            "note": args.note,
            "ingested_at": _now(),
            "origin": str(src),
        }
        ledger["files"] = [r for r in ledger["files"] if r.get("name") != src.name] + [row]
        kept.append(src.name)

    if not args.dry:
        ledger["updated_at"] = _now()
        dest.mkdir(parents=True, exist_ok=True)
        ledger_path.write_text(
            json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8", newline="\n")
        print(f"\n台账 {ledger_path}  共 {len(ledger['files'])} 份")
    print(f"收下 {len(kept)}｜拒收 {len(refused)}")
    for name, why in refused:
        print(f"  拒收 {name}：{why}")
    return 0 if not refused else 1


if __name__ == "__main__":
    raise SystemExit(main())