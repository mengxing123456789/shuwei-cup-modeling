#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""一条命令从「只有题目」跑到「可交件」。

## 为什么要有它

赛时不该让人记七八条命令与正确的参数顺序。这个入口只做三件事：
    1. 目录没起骨架 → 调 `new_paper.py` 起；
    2. 有题面 → 写进 `problem/problem.txt`；
    3. 跑 `pipeline.py`（八步二十门），完了把 `main.pdf` 复制成 `题号+队号.pdf`
       并打印三闸终检数字。

**它不做决策**：任何门不过就停，把是哪道门、哪一行、什么理由打出来——
这是有意的。2026-11-18 那轮 42 项审阅里，最后能不能进一等奖带，靠的正是
「红门一条条修掉」，而不是「一口气渲完」。

## 用法

    python run_all.py <paper_dir> [--type A] [--problem path|text] [--problem-file path]
                      [--skip-dispatch] [--no-review-each] [--no-compile]
                      [--timeout 2400]

`--type` 决定骨架（A/B/C/D/E）。题面可以是文件路径，也可以直接给一段文字；
从 PDF 提取文本请先自己转成 txt（`pymupdf` 一行即可，见 BUILD.md）。

## 交件命名

`C3` 要求交付件名是「题号+队号」。队号从 `main.tex` 的 `\\baominghao{...}` 读，
读不到就跳过复制并在最后提示手工改名——不猜。
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from mmkit.pyexe import resolve_py  # noqa: E402

# 解释器不再写死盘符：MM_PY → 当前解释器 → 工作区内常见 venv → PATH。
PY, _PY_OK = resolve_py()
PY = Path(PY)


def _run(argv: list[str], cwd: Path | None = None, timeout: int = 7200) -> tuple[int, str]:
    env = {**__import__("os").environ, "PYTHONIOENCODING": "utf-8"}
    env["PYTHONPATH"] = str(SCRIPTS) + (";" + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    t0 = time.time()
    try:
        r = subprocess.run([str(a) for a in argv], cwd=str(cwd or SCRIPTS),
                           capture_output=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return 3, f"<超时 {timeout}s>"
    out = (r.stdout or b"").decode("utf-8", "replace") + (r.stderr or b"").decode("utf-8", "replace")
    print(out.rstrip()[-6000:])
    print(f"  （{time.time() - t0:.1f}s, rc={r.returncode}）")
    return r.returncode, out


def team_number(paper: Path) -> str:
    tex = paper / "main.tex"
    if not tex.exists():
        return ""
    m = re.search(r"\\baominghao\{([^}]*)\}", tex.read_text(encoding="utf-8", errors="replace"))
    if not m:
        return ""
    v = m.group(1).strip()
    if not v or "X" * 4 in v or "placeholder" in v.lower():
        return ""
    return v


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="一条命令：骨架 → 八步二十门 → 交件")
    ap.add_argument("paper", help="论文目录")
    ap.add_argument("--type", default="C", help="题号 A/B/C/D/E（建骨架时用）")
    ap.add_argument("--cls", default="apmcm", choices=("apmcm", "swmcm"),
                    help="模板：apmcm（亚太/美赛）或 swmcm（数维杯官方 swmcmthesis）")
    ap.add_argument("--problem", default="", help="题面文本或 txt 路径")
    ap.add_argument("--problem-file", default="", help="题面 txt 路径（优先于 --problem）")
    ap.add_argument("--skip-dispatch", action="store_true")
    ap.add_argument("--no-review-each", action="store_true")
    ap.add_argument("--timeout", type=int, default=2400)
    a = ap.parse_args(argv)

    if not PY.exists():
        print(f"找不到解释器 {PY}——设 MM_PY 指向一个带 numpy/pandas/matplotlib 的 Python")
        return 2
    if not _PY_OK:
        print(f"警告：{PY} 无法 import numpy/pandas/matplotlib，后续步骤可能失败")

    paper = Path(a.paper).resolve()
    print(f"\n=== 目标 {paper}")

    # 1. 骨架
    if not (paper / "main.tex").exists():
        print("\n--- 起骨架")
        rc, _ = _run([PY, SCRIPTS / "new_paper.py", paper, "--type", a.type,
                      "--cls", a.cls], timeout=600)
        if rc != 0:
            print("骨架没起来，停。")
            return rc
    else:
        print("  main.tex 已在，跳过骨架")

    # 2. 题面
    src = a.problem_file or a.problem
    if src:
        dst = paper / "problem" / "problem.txt"
        dst.parent.mkdir(parents=True, exist_ok=True)
        p = Path(src)
        if p.exists() and p.is_file():
            shutil.copyfile(p, dst)
            print(f"\n--- 题面已复制 {p.name} → problem/problem.txt（{dst.stat().st_size:,} B）")
        else:
            dst.write_text(src, encoding="utf-8", newline="\n")
            print(f"\n--- 题面已写入 problem/problem.txt（{dst.stat().st_size:,} B）")
    elif not (paper / "problem" / "problem.txt").exists():
        print("\nWARN: 没有 problem/problem.txt，s1 的侦察手会没题面可读")

    # 3. 流水线
    print("\n--- 八步二十门")
    args = [PY, SCRIPTS / "pipeline.py", paper, "--timeout", str(a.timeout)]
    if a.skip_dispatch:
        args.append("--skip-dispatch")
    if a.no_review_each:
        args.append("--no-review-each")
    rc, out = _run(args, timeout=8 * 3600)
    if rc != 0:
        print("\nSTOP：门没过。修完重跑同一条命令即可（已过的步骤不会重派）。")
        print("     只想看交接单：python pipeline.py <paper> --status")
        return rc

    # 4. 交件
    print("\n--- 交件")
    pdf = paper / "main.pdf"
    if not pdf.exists():
        print("  main.pdf 不存在，跳过复制")
        return 1
    tn = team_number(paper)
    if not tn:
        print("  main.tex 里的 \\baominghao 还是占位，跳过复制（填真队号后再跑一次）")
    else:
        dst = paper / f"{a.type.lower()}apmcm{tn.replace('apmcm', '')}.pdf"
        if dst.name.lower() != f"{a.type.lower()}{tn}.pdf".lower():
            dst = paper / f"{a.type}{tn}.pdf"
        shutil.copyfile(pdf, dst)
        print(f"  已复制 → {dst.name}  ({dst.stat().st_size:,} B)")

    # 5. 三闸终检摘要
    print("\n--- 终检")
    _run([PY, SCRIPTS / "gauntlet_check.py", paper], timeout=1800)
    _run([PY, SCRIPTS / "submission_gate.py", paper, "--only", "venue"], timeout=1800)
    code_dir = paper / "code" / "verify_numbers.py"
    if code_dir.exists():
        _run([PY, code_dir], cwd=paper, timeout=900)
    print("\n以上三条全绿才算可交件。")
    return 0


if __name__ == "__main__":
    sys.exit(main())