"""产物过期检验。

评审队在第一轮实跑里抓到一个真问题：`code/q1_sobol.py` 的 mtime 比它应该产出的
`data/q1_sobol.json` 新 17 小时 —— 脚本改过、改完没重跑。于是论文印的 3.1% 来自旧产物，
重跑后是 3.0591，偏差 1.95e-04 恰是标准误 3.64e-05 的 **5.4 倍**（不是 GPU 抖动：
同一脚本连跑两次 431 个叶子 0 差）。

这件事只能机器查：人眼不会去比 mtime。判据是**同名 token 配对 + mtime 比较**：
    script  data/q1_sobol.py   tokens {q1, sobol}
    artifact data/q1_sobol.json / tables/tab_sobol.tex / figures/fig18_sobol.pdf
  → artifact 的 tokens 与 script 的 tokens 有交集，且 artifact 更旧 → 报告。

限制（必须写在报告里）：token 配对是启发式，**不是依赖图**。一条 `stale` 记录只说明
"可能过期"，要靠人的一句解释消掉；而 `verify_numbers.py` 全绿**不能**证明不过期
—— 旧产物撑住断言时它也全绿（这就是本次的现场）。
"""

from __future__ import annotations

import re
from pathlib import Path

from .paths import Paper

#: 名字里这些词太常见，不参与配对（否则每个产物都会和每个脚本配在一起）
STOP = {"q1", "q2", "q3", "q4", "q5", "data", "make", "tab", "fig", "code", "py",
        "json", "tex", "pdf", "png", "final", "check", "run"}

ARTIFACT_GLOBS = ("data/*.json", "data/*.csv", "tables/*.tex", "figures/*.pdf")


def _tokens(name: str) -> set[str]:
    stem = re.sub(r"\.[A-Za-z0-9]+$", "", name)
    parts = re.split(r"[^A-Za-z0-9]+", stem.lower())
    out: set[str] = set()
    for p in parts:
        if not p or p in STOP:
            continue
        # fig18_sobol / fig12 -> 去掉序号再入集合
        out.add(re.sub(r"^\d+", "", p) or p)
    return out


def stale_artifacts(paper: Paper) -> list[dict]:
    """每个"脚本比产物新且名字相关"的配对，一条记录。"""
    scripts = sorted(paper.code.glob("*.py"))
    if not scripts:
        return []
    arts: list[Path] = []
    for g in ARTIFACT_GLOBS:
        arts.extend(sorted(paper.root.glob(g)))
    rows: list[dict] = []
    for a in arts:
        at = _tokens(a.name)
        if not at:
            continue
        am = a.stat().st_mtime
        for s in scripts:
            st = _tokens(s.name)
            # 只认"一方 token 是另一方的子集"的配对：交集打配会把
            # q1_surrogate_meta.json 配给 q1_surrogate_train.py（前者是后者的输入，
            # 旧是应该的），噪声会把真问题埋掉。
            if not (at <= st or st <= at):
                continue
            if s.stat().st_mtime > am + 1:
                rows.append({
                    "artifact": str(a.relative_to(paper.root)),
                    "script": str(s.relative_to(paper.root)),
                    "artifact_mtime": am,
                    "script_mtime": s.stat().st_mtime,
                    "lag_hours": round((s.stat().st_mtime - am) / 3600.0, 2),
                })
    rows.sort(key=lambda r: -r["lag_hours"])
    return rows


def report(paper: Paper | None = None) -> str:
    from .paths import find_paper
    p = paper or find_paper()
    rows = stale_artifacts(p)
    if not rows:
        return "PASS  no script is newer than a name-matched artefact"
    lines = [f"WARN  {len(rows)} artefact(s) older than a name-matched script:"]
    for r in rows[:20]:
        lines.append(f"  {r['artifact']:34s} older than {r['script']:28s} by {r['lag_hours']:6.2f} h")
    lines.append("  -> each line needs one sentence: either re-run the script, or say why "
                 "the artefact is still valid. A green verify_numbers.py does NOT clear this "
                 "(a stale artefact is exactly what makes it green).")
    return "\n".join(lines)


def main() -> int:
    print(report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())