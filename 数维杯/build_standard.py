"""用数维杯自己的优秀论文重建奖级基准（不再拿亚太杯 16 篇当尺子）。

数据源：C:\\Users\\29900\\Downloads\\AsterLink 根目录下的 A/B/C/D<队号>.pdf
（各年份「数维杯优秀论文」）。每篇都走与主稿完全相同的 measure()，两边可比。

产物：E:\\数学建模\\数维杯\\refs\\official_standard.json
      E:\\数学建模\\数维杯\\refs\\official_standard_report.txt

注意：奖级只到「目录名为优秀论文」这一层，没逐队核官网获奖名单，
所以 n_first_prize_verified 写 0，prize_evidence 里写清楚证据强度。
"""
from __future__ import annotations

import io
import json
import pathlib
import re
import statistics as st
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"E:\数学建模\.agents\skills\mathmodeling\scripts")
from mmkit import award_standard as A  # noqa: E402

try:
    import pymupdf as fitz
except ImportError:  # noqa: PLC0415
    import fitz  # type: ignore  # noqa: PLC0415

ROOT = pathlib.Path(r"C:\Users\29900\Downloads\AsterLink")
OUT = pathlib.Path(r"E:\数学建模\数维杯\refs")
KEYS = ["words", "abstract_words", "abstract_numbers", "abstract_density",
        "distinct_numbers", "pct_mentions", "density_per_100w", "sections",
        "subsections", "figures", "tables", "equations", "references"]
FLAGS = ["has_monte_carlo", "has_sensitivity", "has_backtest", "has_limitation",
         "has_provenance", "has_gpu", "has_epoch", "has_loss", "has_hyperparam",
         "has_crossval", "has_neural", "has_sklearn", "has_ci", "has_robust",
         "has_assumption", "has_error_metric", "has_software"]


def main() -> None:
    rows, skipped = [], []
    pat = re.compile(r"^([ABCD])(\d{9,})\s*\.pdf$")
    for f in sorted(ROOT.iterdir()):
        m = pat.match(f.name)
        if not m:
            continue
        prob, team = m.group(1), m.group(2)
        try:
            doc = fitz.open(str(f))
            text = "\n".join(p.get_text() for p in doc)
            pages = doc.page_count
            doc.close()
        except Exception as exc:                                   # noqa: BLE001
            skipped.append(f"{f.name}: {type(exc).__name__}")
            continue
        if len(text) < 800:
            skipped.append(f"{f.name}: text only {len(text)} chars（扫不出来）")
            continue
        year = int(team[:4]) if team.startswith("20") else 0
        r = A.measure(f.stem, team, prob, year, ["优秀论文（目录收录，未逐队核奖级）"], text=text)
        r["pages"] = pages
        r["file"] = f.name
        rows.append(r)
        print(f"  {f.name:26s} {pages:3d}p  words={r['words']:6d}  sec={r['sections']:3d} "
              f"fig={r['figures']:3d} tab={r['tables']:3d} ref={r['references']:3d}")

    if len(rows) < 8:
        raise SystemExit(f"只有 {len(rows)} 篇，基准不够")
    OUT.mkdir(parents=True, exist_ok=True)
    summary = {k: A.agg(rows, k) for k in KEYS}
    presence = {k: sum(1 for r in rows if r[k] > 0) for k in FLAGS}
    out = {
        "n_first_prize_verified": 0,
        "n_papers": len(rows),
        "prize_evidence": "目录/文件名为『数维杯优秀论文』，未逐队核官网获奖名单；"
                          "分布形态可用，奖级强度请按这个口径理解。",
        "source_root": str(ROOT),
        "built_at": __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
        "skipped": skipped,
        "per_paper": rows,
        "summary": summary,
        "presence": presence,
        "presence_pct": {k: round(v / len(rows) * 100, 1) for k, v in presence.items()},
    }
    (OUT / "official_standard.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    L = ["SHUWEI CUP BENCHMARK（数维杯优秀论文，非亚太杯）", "=" * 70,
         f"papers: {len(rows)}   source: {ROOT}", ""]
    L.append(f"{'metric':22s} {'min':>8s} {'p25':>8s} {'median':>8s} {'p75':>8s} {'max':>8s} {'mean':>8s}")
    for k in KEYS:
        s = summary[k]
        L.append(f"{k:22s} {s['min']:8.2f} {s['p25']:8.2f} {s['median']:8.2f} "
                 f"{s['p75']:8.2f} {s['max']:8.2f} {s['mean']:8.2f}")
    L.append("")
    L.append("EVIDENCE TYPES PRESENT")
    for k in FLAGS:
        L.append(f"  {k:20s} {presence[k]:3d}  ({out['presence_pct'][k]:5.1f}%)")
    (OUT / "official_standard_report.txt").write_text("\n".join(L), encoding="utf-8")
    print("\n" + "\n".join(L))
    print(f"\nwrote {OUT / 'official_standard.json'}  ({(OUT / 'official_standard.json').stat().st_size:,} B)")


if __name__ == "__main__":
    main()
