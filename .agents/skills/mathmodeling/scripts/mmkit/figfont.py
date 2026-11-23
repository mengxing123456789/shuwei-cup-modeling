"""量 PDF 里"缩比之后"的文字有效字号 —— 抓"图看着清楚、印出来读不出"的那类图。

为什么要单独一个模块：2025C 的图表审读实测 Fig 1 的有效字号只有 **5.36 pt**，
而这件事在任何缩略图里都看不出来（5 pt 与 8 pt 在 800 px 宽的预览里一样"清楚"）。
唯一的客观判据是从 PDF 里读每个 span 的字号——图以矢量 PDF 插入时，matplotlib 的字号
会被页面缩放乘一次，`get_text("dict")` 给出的就是**缩放后**的磅值，正是印刷尺寸。

判据（R-V14）：
  * 任何**3 个字符以上**的 span 不得低于 6.0 pt；
  * 单个字符（面板字母 'b'、刻度 '25'、数学符号 '∗'）不判——它们在正文里也常见 4.98 pt，
    那是常规下标尺寸，不是排版事故。
  * 同时报全篇最小字号与低于 6 pt 的 span 数，便于人判断"要不要再放大一档"。

用法：
    python -m mmkit.figfont [main.pdf]
"""
from __future__ import annotations

import statistics
import sys
from pathlib import Path

MIN_PT = 6.0
MIN_CHARS = 3


def _open(pdf: Path):
    try:
        import pymupdf as fitz  # 新接口
    except ImportError:  # pragma: no cover - 老版本 pymupdf 只有 fitz
        import fitz  # type: ignore
    return fitz.open(str(pdf))


def spans(pdf: Path) -> list[tuple[float, int, str]]:
    """返回 [(字号, 页码(1-based), 文本)]，按字号升序。"""
    doc = _open(pdf)
    out: list[tuple[float, int, str]] = []
    for pno in range(len(doc)):
        for b in doc[pno].get_text("dict")["blocks"]:
            for line in b.get("lines", []):
                for s in line["spans"]:
                    t = s["text"].strip()
                    if t:
                        out.append((round(float(s["size"]), 2), pno + 1, t))
    out.sort()
    return out


def report(pdf: Path) -> dict:
    sp = spans(pdf)
    bad = [(sz, pg, tx) for sz, pg, tx in sp if sz < MIN_PT and len(tx) >= MIN_CHARS]
    small_chars = [(sz, pg, tx) for sz, pg, tx in sp if sz < MIN_PT and len(tx) < MIN_CHARS]
    return {
        "pdf": str(pdf),
        "spans": len(sp),
        "min_pt": sp[0][0] if sp else 0.0,
        "median_pt": round(statistics.median([s for s, _, _ in sp]), 2) if sp else 0.0,
        "violations": len(bad),
        "violation_examples": bad[:6],
        "single_char_below": len(small_chars),
        "ok": not bad,
    }


def main() -> int:
    pdf = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if pdf is None:
        from .paths import find_paper
        pdf = find_paper().pdf
    r = report(pdf)
    print(f"pdf: {r['pdf']}")
    print(f"spans={r['spans']}  min={r['min_pt']} pt  median={r['median_pt']} pt")
    print(f"violations (>= {MIN_CHARS} chars and < {MIN_PT} pt): {r['violations']}")
    for sz, pg, tx in r["violation_examples"]:
        print(f"   p{pg:<3} {sz:5.2f} pt  {tx!r}")
    print(f"single-character spans below {MIN_PT} pt (not judged): {r['single_char_below']}")
    print("PASS" if r["ok"] else "FAIL")
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())