#!/usr/bin/env python

# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""扫本目录，禁止出现指向获奖论文/优秀论文的路径或行为（练习赛用）。

用法：
    python code/check_no_peek.py [目录]        # 默认本文件的上一级
负对照（必须先做一次）：
    在本目录随便写一个 .py，里面放一行 src = r"...\\_award_text\\x.txt"
    -> 必须 FAIL 并指出行号；删掉后必须 PASS。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# 路径词：出现即说明引用了禁区语料
PATH_WORDS = ["_award_text", "award_pdfs", "_award_outline", "APMCM2025_C",
              "allpapers", "excellent", "prize_lists", "优秀论文", "一等奖论文"]
# 行为词：出现即说明在描述"抄哪篇"
# 行为词只收"指向某个获奖答案"的短语。裸的"照抄"会命中"别照抄键名"这类正常句子（P11 实测）。
ACT_WORDS = ["获奖论文怎么", "参考一等奖", "照抄一等奖", "照抄获奖", "仿写一等奖", "copy the award"]
EXT = {".py", ".md", ".tex", ".json", ".txt", ".log", ".csv", ".m"}
SKIP = {"problem", "data", "refs", "annex_A", "review", ".git", "__pycache__"}
# 目录级禁区：refs/award_text 是一等奖正文，练习赛里出现就等于把答案放在了旁边。
# 只在文件级扫会漏掉它（refs 本身要跳过，因为 official_standard.json 就在那儿）。
DIR_BAN = ["refs/award_text", "award_text"]
# 这些文件**本来就要写出禁区路径**（否则没法告诉人哪些不能碰）。判据若扫自己必然 FAIL，
# 规则文档与判据本身必须豁免，否则负对照永远做不出来（P11 实测：豁免前 8 命中）。
EXEMPT = {"NO_PEEK.md", "code/check_no_peek.py"}

PAT = re.compile("|".join(map(re.escape, PATH_WORDS)), re.I)
ACT = re.compile("|".join(map(re.escape, ACT_WORDS)), re.I)


def scan(root: Path) -> list[str]:
    hits: list[str] = []
    for bad in DIR_BAN:
        d = root / bad
        if d.exists() and d.is_dir():
            hits.append(f"{bad}/ (directory: 一等奖正文在这里，练习赛必须删除)")
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in EXT:
            continue
        rel = p.relative_to(root).as_posix()
        if set(p.relative_to(root).parts) & SKIP or rel in EXEMPT:
            continue
        try:
            for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if PAT.search(line) or ACT.search(line):
                    hits.append(f"{p.relative_to(root)}:{i}")
        except OSError:
            continue
    return hits


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    hits = scan(root)
    for h in hits:
        print("FAIL", h)
    print(f"scanned {root}  forbidden hits {len(hits)}")
    print("VERDICT:", "PASS" if not hits else "FAIL")
    return 0 if not hits else 1


if __name__ == "__main__":
    raise SystemExit(main())
