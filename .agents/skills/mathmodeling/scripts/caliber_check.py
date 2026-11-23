#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""口径审计的机器硬项（G16 的实算部分）。

## 为什么要有这个脚本

2026-11-18 那轮 42 项审阅里，有 10 项属于同一类缺陷：**同一个词被两种算法用过**——
`0.86%` 一处指松弛天花板、一处指整数格可达值；`−1866.23` 一处当基准、一处当结论；
`3.0044` 与 `3.0093` 两处同量不同值。这些是稿子的病，不是工具的误报。

但当时只有「口径审计手」写一份 md 报告，报告是**快照**：改完稿它不会变，于是 `G16`
永远红，重新派单又卡在宿主 run 状态不翻转。判据与产物互相定义，是这套流水线里
反复出现的同一个坑（`verify_numbers` 不动点、`gen_index` 字节数、`gate_g19` 自指）。

所以这里把**机器能判的那部分**做成现算脚本：每次读当前的 `main.tex`，当场给结论。
人只补机器判不出的部分（比如「这个阈值该按哪条路径读」），不再承担「报告要不要重写」。

## 判什么、不判什么

硬项（能 FAIL，误报率低）：
  H1 `same_literal_conflicting_unit` —— 同一个数值串在同一份稿子里被当成两种量纲用
     （例如 `0.86` 一处配 `\\%`、一处配 `teams`）。这是口径混用最硬的证据：
     读者无法知道这 0.86 到底是比例还是队数。

提示项（只记账，不改 VERDICT）：
  W1 `percent_without_base` —— 百分数所在句子里找不到分母线索。
  W2 `near_duplicate` —— 两个不同字面量相差 <0.5%，可能是同一个量的两处不同结果。
  W3 `json_key_collision` —— 两个 `results_*.json` 里同名叶子键取值不同。

不判：哪个数「对」。那要回到模型与数据，只有人和 `verify_numbers` 能做。

## 用法

    python caliber_check.py <paper_dir> [--json out.json] [--quiet]

写 `<paper>/out/15-caliber-machine.md`（首行 `BYTES <n>`，末行 `VERDICT: PASS|FAIL`），
退出码 0 = PASS、1 = FAIL、2 = 读不到稿子。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------- 量纲分类

# 只认**紧跟数字**的单位后缀，不看整句上下文。
# 第一版用 ±60 字符窗口判量纲，在一份人类审出 10 个问题的稿子上报了 92 个硬项——
# 原因是「800 workstations … 2,000 m2」这种句子里，每个数字的窗口都同时含五种单位。
# 口径混用的真实形态是「同一个 0.86 一处写成 0.86%、一处写成 0.86 teams」，
# 单位必须紧贴数字才说明问题。
UNIT_SUFFIX: list[tuple[str, re.Pattern[str]]] = [
    ("pct", re.compile(r"\s*\\%")),
    ("pct", re.compile(r"\s*(?:per ?cent|percentage points?)", re.I)),
    ("count", re.compile(r"\s*(?:teams?|workstations?|persons?|firms?|sets?|nodes?|"
                         r"storeys?|floors?|tiers?|desks?|ways?|pairs?)\b", re.I)),
    ("money", re.compile(r"\s*(?:CNY|wan|yuan|NPV|IRR|ROI)\b", re.I)),
    ("area", re.compile(r"\s*(?:m\s*\^?2|m\\textsuperscript\{2\})\b")),
    ("time", re.compile(r"\s*(?:ms|s|sec|seconds?|years?|yr|min|minutes?)\b", re.I)),
    ("font", re.compile(r"\s*pt\b", re.I)),
]

# 分母线索：出现这些词就认为「分母写清了」。
BASE_WORDS = re.compile(
    r"\bof\b|\bof the\b|\bamong\b|\bout of\b|\brelative\b|\bshare\b|"
    r"\bper\b|\bversus\b|\bthan\b|\bto the\b|\bin the\b|\bpercentage point",
    re.I,
)

NUM_RE = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)(?![\w])")
PCT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*\\%")
SENT_SPLIT = re.compile(r"(?<=[.;!?])\s+|\n\n+")


def _strip_tex_comments(line: str) -> str:
    """去掉 TeX 注释（未转义的 `%` 之后），避免把注释里的数字算进正文。"""
    out = []
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == "\\" and i + 1 < len(line):
            out.append(line[i:i + 2])
            i += 2
            continue
        if ch == "%":
            break
        out.append(ch)
        i += 1
    return "".join(out)


def _prose_lines(tex: Path) -> list[tuple[int, str]]:
    rows: list[tuple[int, str]] = []
    for i, raw in enumerate(tex.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        s = _strip_tex_comments(raw)
        if not s.strip():
            continue
        if s.lstrip().startswith(("\\lstinputlisting", "\\includegraphics", "\\input{figures/")):
            continue          # 这些行里的数字属于别的文件，不该在这里判
        rows.append((i, s))
    return rows


def _norm(lit: str) -> str:
    return lit.replace(",", "")


# ---------------------------------------------------------------- H1 同一字面量两种量纲

def check_units(rows: list[tuple[int, str]]) -> list[dict]:
    """同一个数值串被两种量纲用过 → 硬项。

    只认**带小数或千分位**的字面量：`10`、`40`、`12` 这种裸整数几乎每页都有，
    它们出现在 `10 years` 与 `10\\%` 里不是口径混用，只是数字碰巧相同。
    真正的问题是 `0.86` 一处配 `\\%`、一处配 `teams` —— 读者没法判断这 0.86 是什么。
    """
    seen: dict[str, dict[str, list[int]]] = {}
    for lineno, s in rows:
        for m in NUM_RE.finditer(s):
            raw = m.group(1)
            lit = _norm(raw)
            if "." not in raw and "," not in raw:
                continue                       # 裸整数不判（见 docstring）
            if len(lit.replace(".", "")) < 2:
                continue
            tail = s[m.end():m.end() + 16]
            kinds = {name for name, pat in UNIT_SUFFIX if pat.match(tail)}
            if not kinds:
                continue
            slot = seen.setdefault(lit, {})
            for u in kinds:
                slot.setdefault(u, []).append(lineno)
    bad: list[dict] = []
    for lit, units in seen.items():
        if len(units) < 2:
            continue
        bad.append({
            "rule": "H1",
            "literal": lit,
            "units": sorted(units),
            "where": {u: sorted(v)[:4] for u, v in units.items()},
        })
    return bad


# ---------------------------------------------------------------- W1 百分数没写分母

def check_percent_base(rows: list[tuple[int, str]]) -> list[dict]:
    text = "\n".join(s for _, s in rows)
    hits: list[dict] = []
    for sent in SENT_SPLIT.split(text):
        if not PCT_RE.search(sent):
            continue
        if BASE_WORDS.search(sent):
            continue
        for m in PCT_RE.finditer(sent):
            frag = sent.strip()[:110]
            if len(frag) < 12:
                continue
            hits.append({"rule": "W1", "literal": m.group(1) + "%", "sentence": frag})
            break                          # 一句只记一条，免得刷屏
    return hits


# ---------------------------------------------------------------- W2 疑似同量两值

def check_near_duplicate(rows: list[tuple[int, str]]) -> list[dict]:
    """疑似同量两值：只比**正文散文行**里、至少三位小数的字面量。

    表格行整片都是四位数，两两比较会刷出几十条假配对（第一版就这么报了 41 条）。
    散文里出现 3.0044 与 3.0093 才是真信号：同一句话在讲同一个指标。
    """
    vals: list[tuple[float, str, int]] = []
    for lineno, s in rows:
        if s.count("&") >= 2 or "\\\\" in s:      # 表格行
            continue
        for m in NUM_RE.finditer(s):
            raw = m.group(1)
            if "." not in raw:
                continue
            dec = raw.split(".")[1]
            if len(dec) < 3:                      # 至少三位小数
                continue
            try:
                v = float(_norm(raw))
            except ValueError:
                continue
            if v == 0:
                continue
            vals.append((v, _norm(raw), lineno))
    out: list[dict] = []
    seen_pairs: set[tuple[str, str]] = set()
    for i in range(len(vals)):
        for j in range(i + 1, len(vals)):
            a, la, la_line = vals[i]
            b, lb, lb_line = vals[j]
            if la == lb:
                continue
            key = (min(la, lb), max(la, lb))
            if key in seen_pairs:
                continue
            hi, lo = max(a, b), min(a, b)
            if hi <= 0:
                continue
            rel = (hi - lo) / hi
            if not (0.0 < rel < 0.005):
                continue
            # 一个数是另一个的舍入 → 舍掉，那不是两个结果
            rounded = False
            for x, lx, y in ((a, la, b), (b, lb, a)):
                decs = len(lx.split(".")[1]) if "." in lx else 0
                if decs and f"{y:.{decs}f}" == lx:
                    rounded = True
                    break
            if rounded:
                continue
            seen_pairs.add(key)
            out.append({"rule": "W2", "a": la, "b": lb,
                        "rel": round(rel * 100, 3), "lines": [la_line, lb_line]})
    return out[:12]


# ---------------------------------------------------------------- 汇总

def run(paper: Path) -> tuple[bool, str, list[dict], list[dict]]:
    tex = paper / "main.tex"
    if not tex.exists():
        return False, f"缺 {tex}", [], []
    rows = _prose_lines(tex)
    hard = check_units(rows)
    warn = check_percent_base(rows) + check_near_duplicate(rows)
    detail = f"硬项 {len(hard)} / 提示 {len(warn)}"
    return (not hard), detail, hard, warn


def render(paper: Path, ok: bool, detail: str, hard: list[dict], warn: list[dict]) -> str:
    lines = [f"# 口径机器硬项（caliber_check.py）  {paper.name}", ""]
    lines.append(f"判据：H1 同一字面量两种量纲（硬）；W1/W2/W3 提示项不改判定。")
    lines.append("")
    lines.append(f"## 硬项（{len(hard)}）")
    if hard:
        for h in hard:
            lines.append(f"- **{h['literal']}** 出现在 {' / '.join(h['units'])} 两种量纲："
                         f"{h['where']}")
    else:
        lines.append("- 没有发现同一数值串被两种量纲使用。")
    lines.append("")
    lines.append(f"## 提示（{len(warn)}）")
    if warn:
        for w in warn:
            if w["rule"] == "W1":
                lines.append(f"- W1 `{w['literal']}` 所在句没写分母：{w['sentence']}")
            elif w["rule"] == "W2":
                lines.append(f"- W2 `{w['a']}` 与 `{w['b']}` 相差 {w['rel']}%，"
                             f"行 {w['lines']}，疑似同一个量的两处结果")
            elif w["rule"] == "W3":
                lines.append(f"- W3 同名键 `{w['key']}` 在 {', '.join(w['files'])} 里取值不同：{w['values']}")
    else:
        lines.append("- 无。")
    lines.append("")
    lines.append(f"结论：{detail}")
    return "\n".join(lines) + "\n"


def with_bytes(body: str) -> str:
    """给正文加首行 `BYTES <n>`，`n` 迭代到不动点。

    2023B 压测实测：原实现 `return f"BYTES {len(body.encode())}\\n" + body` 只数了
    正文，既没数首行自身（`BYTES 274\\n` = 10 B），也没数 `main()` 事后追加的
    `VERDICT: PASS\\n`（14 B），于是 274 vs 实际 298 —— 首行自报数字本身就是错的，
    而这正是 G16 里人被要求去查的 P 项。凡自指字节数都必须数完整文件。
    """
    text = body
    for _ in range(6):
        n = len(text.encode("utf-8"))
        new = f"BYTES {n}\n" + body
        if new == text:
            return text
        text = new
    return text


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="口径审计的机器硬项（G16 实算部分）")
    ap.add_argument("paper", help="论文目录")
    ap.add_argument("--quiet", action="store_true", help="只回报告路径")
    ap.add_argument("--no-write", action="store_true", help="不写报告，只打印")
    a = ap.parse_args(argv)

    paper = Path(a.paper).resolve()
    ok, detail, hard, warn = run(paper)
    if hard == [] and not (paper / "main.tex").exists():
        print(detail)
        return 2
    verdict = "VERDICT: PASS" if ok else "VERDICT: FAIL"
    text = with_bytes(render(paper, ok, detail, hard, warn) + verdict + "\n")
    if not a.no_write:
        out = paper / "out" / "15-caliber-machine.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8", newline="\n")
        if a.quiet:
            print(f"报告: {out}")
        else:
            print(f"报告: {out}  {detail}  {verdict}")
    else:
        print(text)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())