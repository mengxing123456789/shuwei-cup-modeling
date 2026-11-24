#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 契约五件套脚手架（源自 Modex 3.0.2 templates/ 逆向，test_modex_reuse_patterns.py 11 PASS）。
# Drafted with DeepSeek Harness 0.2.2-rc.3 (assistant); rules fixed by the team.
# 用法: python scaffold_contracts.py <目标目录>   （在 <目标目录>/contracts/ 下写五份文件）
"""Scaffold the five contract files for a modeling-competition paper workspace.

Exit codes: 0 = written; 1 = target already has contracts/ (no overwrite); 2 = bad args.
"""
from __future__ import annotations

import sys
from pathlib import Path

TEMPLATES: dict[str, str] = {
    "RESEARCH_CONTRACT.md": (
        "# Research Contract\n"
        "<!-- 会话恢复/交接只读本文 + FINDINGS + PAPER_PLAN，不重读原始材料 -->\n\n"
        "## Selected Idea\n\n\n"
        "## Core Claims\n"
        "- C1: \n"
        "- C2: \n\n"
        "## Method Summary\n\n\n"
        "## Experiment Design\n\n\n"
        "## Baselines\n"
        "| id | method | expected |\n|---|---|---|\n| B1 | | |\n\n"
        "## Key Decisions\n"
        "<!-- 格式：YYYY-MM-DD  决定  理由（一条一行） -->\n\n"
        "## Status checklist\n"
        "- [ ] M0 sanity\n- [ ] M1 baselines\n- [ ] M2 main\n- [ ] M3 ablation\n"
        "- [ ] Decision Gate passed\n"
    ),
    "EXPERIMENT_PLAN.md": (
        "# Experiment Plan\n\n"
        "## Claim Map\n"
        "| claim | evidence | section |\n|---|---|---|\n| C1 | | |\n\n"
        "## Blocks\n"
        "- MUST-RUN: \n- NICE-TO-HAVE: \n\n"
        "## Run Order\n"
        "M0 -> M1 -> M2 -> M3 (Decision Gate after M2)\n\n"
        "## Compute Budget\n\n\n"
        "## Risks\n"
    ),
    "EXPERIMENT_LOG.md": (
        "# Experiment Log\n"
        "<!-- tracker = CONTRACT 的 checklist；本文 = 永久记录。每实验一节，Verdict 必答 -->\n\n"
        "## E1: <name>\n"
        "- Setup: \n- Results: \n- Verdict (Supports claim?): \n"
        "- Reproduction: `python code/... `\n"
    ),
    "FINDINGS.md": (
        "# Findings\n"
        "<!-- 会话恢复必读。负结果也是结果：『X 在小样本上无效』『Y 组合发散』『Z 不值额外开销』 -->\n\n"
        "## Research Findings\n\n\n"
        "## Engineering Findings\n"
    ),
    "PAPER_PLAN.md": (
        "# Paper Plan\n\n"
        "## Claims-Evidence Matrix\n"
        "<!-- 每个 C# 至少一条已存在证据；没有的标 UNSUPPORTED -->\n"
        "| claim | evidence | section | status |\n|---|---|---|---|\n| C1 | | | UNSUPPORTED |\n\n"
        "## Section Plan\n"
        "<!-- 每节页数预算 -->\n\n"
        "## Figure Plan\n"
        "<!-- Auto: illustration / matplotlib / LaTeX -->\n\n"
        "## Key References\n"
    ),
}


def scaffold(target: Path) -> int:
    cdir = target / "contracts"
    if cdir.exists():
        print(f"已存在 {cdir}，不覆盖。如需重建请先手动删除。")
        return 1
    cdir.mkdir(parents=True)
    for name, body in TEMPLATES.items():
        (cdir / name).write_text(body, encoding="utf-8", newline="\n")
        print(f"  写 {cdir / name}")
    print(f"契约五件套完成：{len(TEMPLATES)} 份 @ {cdir}")
    print("提醒：M0 sanity 之前先把 RESEARCH_CONTRACT 的 Core Claims 写实（- C1: 起头）。")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    return scaffold(Path(argv[1]).resolve())


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
