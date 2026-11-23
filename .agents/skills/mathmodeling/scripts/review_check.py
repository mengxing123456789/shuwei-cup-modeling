"""官方口径体检：把 `_official_criteria.json` 里能数清的项，逐条对一篇论文跑一遍。

这不是"评分"，是**先数硬项** —— 任何一条 FAIL 都足以让论文在评审第一步就掉档，
所以必须先确认这些项干净，再谈创新性和写作质量。

用法：
    review_check.py <论文目录或 main.pdf>            # 全部 12 条里可机器核的部分
    review_check.py <论文> --json out.json          # 同时落 JSON
    review_check.py --criteria                      # 只看 12 条判据与原文出处

退出码：0 = 无 FAIL；1 = 有 FAIL；2 = 连 PDF 都没找到。
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from mmkit import review_bench as RB  # noqa: E402


MARK = {True: "[ OK ]", False: "[FAIL]", None: "[ ?? ]"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paper", nargs="?")
    ap.add_argument("--criteria", action="store_true", help="列出 12 条官方判据与出处")
    ap.add_argument("--json", dest="json_out")
    a = ap.parse_args()

    if a.criteria:
        for c in RB.criteria():
            print(f"{c.id:16} {c.status:12} hits={c.n_hits:>3} files={len(c.files):>2}  {c.name}")
            if c.evidence:
                f, ln, q = c.evidence[0]
                loc = f"{f}:{ln}" if ln else f
                print(f"                 依据: {loc}  {q[:90]}")
        print("\nbench (22 篇一等奖):", RB.award_bench())
        return 0

    if not a.paper:
        ap.error("either give a paper path or --criteria")
    rep = RB.check_paper(a.paper)
    print(f"paper: {rep.paper}")
    print(f"pdf: {rep.pdf.name if rep.pdf else None}   pages: {rep.pages}")
    for f in rep.findings:
        print(f"{MARK[f.ok]} {f.cid:5} {f.observed}")
        if f.ok is False:
            print(f"        判据: {f.why}")
            if f.fix:
                print(f"        下一步: {f.fix}")
    print(f"\nVERDICT: {rep.verdict()}  (fail={len(rep.fail)} unknown={len(rep.unknown)})")
    if a.json_out:
        pathlib.Path(a.json_out).write_text(json.dumps(
            {"paper": str(rep.paper), "pdf": str(rep.pdf), "pages": rep.pages, "verdict": rep.verdict(),
             "findings": [{"cid": f.cid, "ok": f.ok, "observed": f.observed,
                           "why": f.why, "fix": f.fix} for f in rep.findings]},
            ensure_ascii=False, indent=1), encoding="utf-8")
    return 0 if not rep.fail else 1


if __name__ == "__main__":
    raise SystemExit(main())