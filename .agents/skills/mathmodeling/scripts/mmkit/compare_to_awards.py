"""Compare the project against the verified First-Prize distribution.

Three errors in the earlier verdict are fixed here, and all three mattered:

1. ONE paper was used as the baseline.  The benchmark is now 16 papers whose
   First-Prize level is verified against the official APMCM prize lists.

2. The benchmark numbers came from a looser extraction that reported "median
   441 words / 12 distinct numbers / density 3.3".  The verified medians are
   374.5 abstract words, 2.5 distinct DECIMAL numbers and 0.73 per 100 words.

3. The project was measured from main.tex while the benchmark was measured
   from PDF text.  That is not a comparison: \\ref, \\includegraphics and
   \\bibitem are stripped by any LaTeX-to-text pass, so the source-side count
   reports zero figures, zero numbered equations and zero references for a
   paper that has 16, 14 and 18 of them.  Both sides are now measured by the
   SAME function on pdftotext output.

A metric is called an improvement only if it moves the project TOWARDS the
median.  Being far above the median on numeric density is a deviation to be
explained, not a strength to be claimed.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from .paths import find_paper

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from . import provenance as C  # noqa: E402
from . import award_standard as A  # noqa: E402

ROOT = find_paper().root
PDFTOTEXT = Path(r"E:\MIKTEX\miktex\miktex\bin\x64\pdftotext.exe")


def project_text(paper=None) -> str:
    """Extract main.pdf with the same tool and flags used on the award PDFs."""
    P = paper or find_paper()
    pdf = P.pdf
    out = P.refs / "project_text.txt"
    out.parent.mkdir(exist_ok=True)
    subprocess.run([str(PDFTOTEXT), "-layout", "-enc", "UTF-8",
                    str(pdf), str(out)], check=True)
    return out.read_text(encoding="utf-8", errors="replace")


def _body_end_page(pages) -> int:
    """正文最后一页的下标（不含）。

    口径：从第 4 页往后，取**第一个**把 "Appendix A" 当**标题行**打开的页。
    别改成「最后一个 Appendix A 命中页」：目录页里也会列出 "Appendix A"，
    取最后一个是把附录也算进正文。这里与 gauntlet.body_pages() 的口径不同是有意为之——
    那边要的是"Appendix A 出现在第几编号页"，方向相反。

    2026-11-12 修正（第六次同族故障）：原来用的是"页内任意位置出现 Appendix\\s+A"，
    于是正文里一句交叉引用（"…all code is in Appendix A"）就把正文切成前 4 页。
    实测 2018A 练习稿：`Appendix A` 在全文第 7592 个字符处第一次出现，而它在
    目录页与正文交叉引用里都出现；band 因此报 `words=4595 / sections=0 / references=0`
    ——三个数全是切片过短的产物，不是论文的体量。现在要求**行首**形态，
    与 `gauntlet.body_pages()` 用同一条正则。
    """
    anchor = re.compile(r"^[ \t]*(?:[A-Z]{1,4}\.|[0-9]+\.)?[ \t]*Appendix[ \t]+A\b", re.M)
    for i, p in enumerate(pages):
        if i < 4:                      # pages 1-4 are front matter / contents
            continue
        if anchor.search(p):
            return i
    return len(pages)


def project_metrics(paper=None) -> dict:
    """Measure the project with award_standard.measure(), on PDF text.

    Passing `measure()` directly means the regexes, the abstract slicer and the
    figure/table/equation/reference counters are literally the same code that
    produced the benchmark -- there is no second implementation to drift.

    Two views are produced:

    body   text before the first "Appendix" heading.  This is the comparable
           unit: all award papers were measured on a PDF that ends at the end
           of their argument, whereas this project carries ~30 pages of source
           listings.  Counting the listings inflates `words` and makes the
           code line numbers ("1  import json") look like numbered section
           headings, which is exactly how the first version of this script
           reported 68 sections against a median of 1.
    full   the whole PDF, reported alongside so nothing is hidden.
    """
    t = project_text(paper)
    # Body boundary is found by PAGE, not by character offset.  Both earlier
    # attempts failed: the first `re.search` landed on the table of contents
    # (which lists all five appendices) and reported a 546-word body; taking
    # the second match landed on a cross-reference inside the body.  Splitting
    # on form feeds and choosing the first page past the contents that opens an
    # appendix is unambiguous -- measured, that is PDF page 28 of 59.
    pages = t.split("\f")
    body_end = _body_end_page(pages)
    # 2026-11-12 修正（第七次同族故障）：边界是**页级**的，而参考文献列表常常
    # 跨页续排——练习稿 p17 只排到 `[2]`，`[3]`–`[11]` 在 p18 上半页，p18 行首
    # 才是 `Appendix A`。只取 pages[:body_end] 会让 references 从 11 掉到 2，
    # 然后 band 报 "references 2 (pct 6.2 BELOW)" —— 纯粹的切片产物，不是缺陷。
    # 现在把附录起始页里**锚点之前**的那一段也算进正文（锚点之后仍排除）。
    tail = pages[body_end] if body_end < len(pages) else ""
    anchor = re.compile(r"^[ \t]*(?:[A-Z]{1,4}\.|[0-9]+\.)?[ \t]*Appendix[ \t]+A\b", re.M)
    m = anchor.search(tail)
    head = tail[:m.start()] if m else ""
    keep = pages[:body_end] + ([head] if head.strip() else [])
    body = "\f".join(keep)
    r = A.measure("__project__", "project", "-", 2025, ["project"], text=body)
    full = A.measure("__project_full__", "project", "-", 2025, ["project"], text=t)
    r["bytes"] = len(t.encode("utf-8"))
    r["full_words"] = full["words"]
    r["full_sections"] = full["sections"]
    r["full_tables"] = full["tables"]
    r["full_equations"] = full["equations"]
    r["full_figures"] = full["figures"]
    r["full_references"] = full["references"]
    return r


def pct_rank(value: float, dist: np.ndarray) -> float:
    return float(100.0 * (dist <= value).mean())


def main() -> None:
    std = json.loads((ROOT / "refs" / "official_standard.json")
                     .read_text(encoding="utf-8"))
    # `has_*` fields in per_paper are MENTION COUNTS, not flags.  Presence is
    # count > 0; reading the count as a flag overstates coverage for a paper
    # that mentions "neural" 41 times.
    papers = std["per_paper"]
    bench = pd.DataFrame(papers)
    proj = project_metrics()

    metrics = ["words", "abstract_words", "abstract_numbers", "abstract_density",
               "distinct_numbers", "pct_mentions", "density_per_100w",
               "sections", "subsections", "figures", "tables", "equations",
               "references"]
    rows = []
    for m in metrics:
        d = bench[m].to_numpy(float)
        v = float(proj[m])
        rows.append({
            "metric": m,
            "project": round(v, 2),
            "median": round(float(np.median(d)), 2),
            "p25": round(float(np.percentile(d, 25)), 2),
            "p75": round(float(np.percentile(d, 75)), 2),
            "max": round(float(d.max()), 2),
            "pct_rank": round(pct_rank(v, d), 1),
            "inside_p25_p75": bool(np.percentile(d, 25) <= v <= np.percentile(d, 75)),
        })
    tbl = pd.DataFrame(rows)

    ev_rows = []
    for k in proj:
        if not k.startswith("has_"):
            continue
        n = int(sum(1 for p in papers if p.get(k, 0) > 0))
        ev_rows.append({"flag": k, "award_papers": n,
                        "award_pct": round(100.0 * n / len(papers), 1),
                        "project": 1 if proj[k] > 0 else 0})
    ev = pd.DataFrame(ev_rows).sort_values("award_papers", ascending=False)

    out = {"benchmark_n": len(papers), "project": proj,
           "percentiles": rows, "evidence": ev_rows}
    C.save_json(ROOT / "refs" / "project_vs_awards.json", out)

    print(f"PROJECT vs {len(papers)} FIRST-PRIZE PAPERS "
          f"(prize level verified; both sides measured by the same function "
          f"on pdftotext output)\n")
    print(f"{'metric':18s} {'project':>9s} {'p25':>8s} {'median':>8s} "
          f"{'p75':>8s} {'max':>8s} {'pct':>6s}  verdict")
    for r in rows:
        if r["pct_rank"] > 90:
            v = "ABOVE the band"
        elif r["pct_rank"] < 10:
            v = "BELOW the band"
        elif r["inside_p25_p75"]:
            v = "inside IQR"
        else:
            v = "within range"
        print(f"{r['metric']:18s} {r['project']:9.2f} {r['p25']:8.2f} "
              f"{r['median']:8.2f} {r['p75']:8.2f} {r['max']:8.2f} "
              f"{r['pct_rank']:5.1f}%  {v}")

    print("\nEVIDENCE TYPES\n")
    print(f"{'flag':20s} {'award papers':>14s} {'project':>8s}")
    for r in ev_rows:
        mark = ""
        if r["award_papers"] == 0 and r["project"]:
            mark = "  <- no award paper has this"
        elif r["award_papers"] == 0:
            mark = "  <- absent from both"
        print(f"{r['flag']:20s} {r['award_papers']:5d} / {len(papers):<2d} "
              f"({r['award_pct']:4.1f}%) {r['project']:8d}{mark}")

    dev = [r for r in rows if r["pct_rank"] > 90 or r["pct_rank"] < 10]
    print(f"\n{len(dev)} metrics sit outside the 10th-90th percentile band:")
    for r in dev:
        side = "above" if r["pct_rank"] > 90 else "below"
        print(f"  {r['metric']}: project {r['project']} vs median {r['median']} "
              f"({side}, p{r['pct_rank']:.0f})")


if __name__ == "__main__":
    main()

