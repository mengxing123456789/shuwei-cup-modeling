#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 引文回查 + 结论降档（源自 Modex simulated_review.pyd 逆向，test_modex_reuse_patterns.py 已验证核心逻辑）。
# Drafted with DeepSeek Harness 0.2.2-rc.3 (assistant); rules fixed by the team.
# 用法:
#   python citation_audit.py report.json paper.txt -o audit.json
#   report.json = 审稿模型输出（issues: [{quote, severity, ...}], verdict: "A"|"B"|...）
#   paper.txt   = 被审稿件的纯文本（\input 展开后、去注释；Word 模式给 Markdown 源稿）
#   audit.json  = 逐条回查结果 + 归一化 verdict
"""Citation back-audit and verdict downgrade (Modex simulated_review rules).

Rules implemented (see RE-MODEX-FULL-REPORT.md §5):
- normalized substring match; exact hit -> (page, True)
- ellipsis split needs >=2 segments found in order with adjacency (gap <= 200 chars)
- <8 normalized chars -> skip (-1, False)
- verdict normalization: 22+ known verdict phrasings; located major forbids top verdict
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ADJacency_GAP = 200      # 省略号两段在原文里的最大间隔（字符）
MIN_QUOTE_CHARS = 8      # 规范化后少于 8 字符不查（Modex 规则）

# 结论短语归一表：长的先认（Modex：22 种写法读错 16 种，因为短匹配先命中）
VERDICT_PATTERNS: list[tuple[str, str]] = [
    ("接受并建议评奖", "accept_award"),
    ("建议接受", "accept"),
    ("同意答辩", "accept_defense"),
    ("修改后答辩", "revise_defense"),
    ("修后可投", "revise_accept"),
    ("修改后录用", "revise_accept"),
    ("修改后重审", "revise_rereview"),
    ("需补实验", "needs_experiments"),
    ("建议拒稿", "reject"),
    ("不建议录用", "reject"),
    ("大修", "major_revision"),
    ("小修", "minor_revision"),
    ("minor revision", "minor_revision"),
    ("major revision", "major_revision"),
    ("accept", "accept"),
    ("reject", "reject"),
]


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def locate_quote(quote: str, pages: dict[int, str]) -> tuple[int, bool]:
    """返回 (page, exact)。镜像 Modex：双边规范化；逐字命中最好；
    省略号切分需 >=2 段按序命中且相邻（间距 <= ADJacency_GAP）。
    找不到给 (-1, False)；<8 规范化字符跳过。"""
    q = normalize(quote)
    if len(q) < MIN_QUOTE_CHARS:
        return -1, False
    parts = [p for p in re.split(r"\.{3,}|……|…", quote) if normalize(p)]
    for page in sorted(pages):
        t = normalize(pages[page])
        if q in t:
            return page, True
        if len(parts) >= 2:
            pos = -1
            ok = True
            for seg in parts:
                s = normalize(seg)
                hit = t.find(s)
                if hit < 0 or (pos >= 0 and hit - pos > ADJacency_GAP):
                    ok = False
                    break
                pos = hit
            if ok:
                return page, False  # 找到了但不是逐字（省略号拼接）
    return -1, False


def normalize_verdict(raw: str) -> str:
    v = normalize(raw)
    for pat, tag in VERDICT_PATTERNS:  # 长的在前
        if normalize(pat) in v:
            return tag
    return "unknown"


TOP_VERDICTS = {"accept", "accept_award", "accept_defense"}
DOWNGRADED = {
    "accept_award": "accept",
    "accept": "revise_accept",
    "accept_defense": "revise_defense",
}


def audit(report: dict, paper_text: str) -> dict:
    """report: {"issues":[{quote, severity,...}], "verdict": str}
    返回逐条定位 + 归一化 verdict + 降档说明。"""
    # 按 \input 展开是调用方的事；这里按空页策略分页：整篇为 1 页也可
    pages: dict[int, str] = {1: paper_text}
    if "\f" in paper_text:  # 若已按页分好
        pages = {i + 1: t for i, t in enumerate(paper_text.split("\f"))}

    out_issues = []
    located_major = False
    for i, iss in enumerate(report.get("issues", [])):
        quote = iss.get("quote", "")
        page, exact = locate_quote(quote, pages)
        sev = normalize(iss.get("severity", ""))
        if sev not in ("major", "minor", "nit"):
            sev = "minor"  # Modex：认不出的当一般问题
        if sev == "major" and page > 0:
            located_major = True
        out_issues.append({
            "idx": i,
            "severity": sev,
            "page": page,
            "verbatim": exact,
            "status": ("located" if page > 0 else "NOT-FOUND-IN-TEXT"),
        })

    verdict = normalize_verdict(str(report.get("verdict", "")))
    note = ""
    if located_major and verdict in TOP_VERDICTS:
        down = DOWNGRADED.get(verdict, "revise_accept")
        note = f"downgraded {verdict} -> {down}: located major issues exist"
        verdict = down
    return {"issues": out_issues, "verdict": verdict, "note": note,
            "located_major": located_major}


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    report = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    paper = Path(argv[2]).read_text(encoding="utf-8", errors="replace")
    out = audit(report, paper)
    dst = Path(argv[4]) if len(argv) > 4 and argv[3] == "-o" else Path("audit.json")
    dst.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(f"verdict={out['verdict']}  located_major={out['located_major']}  note={out['note']}")
    for it in out["issues"]:
        print(f"  #{it['idx']} {it['severity']:5s} page={it['page']:>3} "
              f"{'verbatim' if it['verbatim'] else 'non-verbatim' if it['page']>0 else 'NOT-FOUND'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
