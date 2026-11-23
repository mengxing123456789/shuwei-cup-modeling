"""Measure the official standard from prize-verified First Prize papers.

Every paper in refs/award_text is matched to its team number, and that team
number is looked up in the official APMCM prize lists downloaded from
apmcm.org.  Only papers whose prize level is VERIFIED as First Prize enter the
benchmark.  Anything unverified is reported separately and excluded, because a
standard built on an unverified sample is exactly the mistake this script
exists to avoid.

Output: refs/official_standard.json and a human-readable report.
"""
from __future__ import annotations

import json
import re
import statistics as st
from pathlib import Path

from .paths import find_paper

ROOT = find_paper().root
TEXT = ROOT / "refs" / "award_text"
OUT = ROOT / "refs"

# paper -> (team id, problem letter, year)
PAPERS = {
    "2022年A题优秀论文": ("2208815", "A", 2022),
    "2022年B题优秀论文": ("2205838", "B", 2022),
    "2022年C题优秀论文": ("2203180", "C", 2022),
    "2022年D题优秀论文": ("2201058", "D", 2022),
    "2022年E题优秀论文": ("2213503", "E", 2022),
    "2023年A题优秀论文": ("2309364", "A", 2023),
    "2023年B题优秀论文": ("2307379", "B", 2023),
    "2023年C题优秀论文": ("2303763", "C", 2023),
    "2024年A题优秀论文": ("24200438", "A", 2024),
    "2024年B题优秀论文": ("24200636", "B", 2024),
    "2024年C题优秀论文": ("24200658", "C", 2024),
    "2024年D题优秀论文": ("24207218", "D", 2024),
    "2025年A题优秀论文": ("25302425", "A", 2025),
    "2025年B题优秀论文": ("25304268", "B", 2025),
    "2025年C题优秀论文": ("25301412", "C", 2025),
    "2025年D题优秀论文": ("25310840", "D", 2025),
}

# Chinese-track papers: a different competition stream, prize list separate.
CHINESE_TRACK = {
    "2024A题02838": ("24102838", "A", 2024),
    "2024A题03112": ("24103112", "A", 2024),
    "2024B题00536": ("24100536", "B", 2024),
    "2024B题02462": ("24102462", "B", 2024),
    "2024C题00023": ("24100023", "C", 2024),
    "2024C题02422": ("24102422", "C", 2024),
}


def load_prize_map() -> dict[str, list[str]]:
    p = ROOT / "refs" / "prize_lists" / "team_prize_map.json"
    return json.load(open(p, encoding="utf-8"))


def norm(t: str) -> str:
    t = t.replace("\u00a0", " ")
    t = re.sub(r"[ \t]+", " ", t)
    return t


def count_words(t: str) -> int:
    return len(re.findall(r"[A-Za-z][A-Za-z'-]*", t))


def abstract_block(t: str) -> str:
    """Slice the abstract.

    The heading varies by template: 'Abstract:', a bare 'summary' after the
    summary-sheet banner, 'summarysheet', or Chinese 摘要.  Two earlier attempts
    got this wrong and corrupted the aggregate, so the rule is now explicit:
    among every heading-shaped candidate that ENDS inside the first 1500
    characters, take the LAST one.  Taking the first hit 'summary sheet' lands
    on the page banner and starts the slice before the body; taking 'summary'
    without a word boundary lands inside 'summarysheet'.  Both are avoided.
    """
    low = t.lower()
    pats = (r"abstract\s*:?", r"summary\s*sheet", r"summary", r"摘要")
    cands = []
    for pat in pats:
        for m in re.finditer(pat, low):
            if m.end() <= 1500:
                cands.append(m.end())
    if not cands:
        return ""
    s = max(cands)
    tail = t[s:]
    # end markers, earliest wins
    ends = []
    for pat in ("keywords", "key words", "关键词", "1 introduction",
                "1. introduction", "introduction", "一、问题重述", "1 问题重述"):
        j = tail.lower().find(pat)
        if j > 200:
            ends.append(j)
    e = min(ends) if ends else min(len(tail), 4000)
    return norm(tail[:e])


def section_titles(t: str) -> list[tuple[int, str]]:
    """Numbered headings, returned as [(level, title)].

    Three shapes occur in these papers: '1 Introduction', '2.1 Assumptions'
    and Chinese '一、问题重述'.  A heading must be on its own line, short, and
    must not end in a period -- otherwise ordinary numbered sentences are
    counted, which is what inflated the first pass.

    2026-11-12 修正（第七次同族故障）：apmcmthesis 排版出来的标题是
    **`4 . 3 . 1 Foo`**（点两侧有空格），以及**罗马数字**的 `XII. References`。
    旧正则 `^\\d{1,2}(\\.\\d{1,2}){0,2}\\s+` 两种都配不上，于是 16 篇一等奖里
    **7 篇量到 sections=0**、中位数 = 1 —— 一个 30 页论文只有 1 个章节显然荒谬。
    这不是论文的问题，是尺子的问题：`sections` 的"在带内"判定一直是假的。
    现在接受：点两侧任意空格、1~3 层编号、罗马数字编号；level = 编号层数
    （罗马数字算 1 层）。混排时以出现次数最多的形态为准，不做两套并存。
    """
    out: list[tuple[int, str]] = []
    arabic = re.compile(
        r"^(\d{1,2})(?:\s*\.\s*(\d{1,2}))?(?:\s*\.\s*(\d{1,2}))?\s*\.?\s+[A-Z\u4e00-\u9fff]")
    roman = re.compile(r"^([IVXLC]{1,5})\s*\.\s+[A-Z\u4e00-\u9fff]")
    chinese = re.compile(r"^[一二三四五六七八九十]{1,3}[、.]\s*\S")
    for line in t.splitlines():
        s = line.strip()
        if len(s) < 4 or len(s) > 90 or s.endswith("."):
            continue
        # 目录行带点线（"1. Introduction . . . 1"），不是标题本体；留着会把
        # 每个标题数两遍（目录一遍、正文一遍）。判据：行内出现 4 个以上连续点。
        if s.count(" . ") >= 3 or s.count(". .") >= 2 or "...." in s:
            continue
        m = arabic.match(s)
        if m:
            level = 3 if m.group(3) else (2 if m.group(2) else 1)
            out.append((level, s))
            continue
        if roman.match(s):
            out.append((1, s))
            continue
        if chinese.match(s):
            out.append((1, s))
    return out


def measure(name: str, team: str, prob: str, year: int, prize: list[str],
            text: str | None = None) -> dict:
    """Measure one paper.

    `text` lets a caller supply already-extracted text instead of reading
    refs/award_text/<name>.txt.  The project comparison needs exactly that:
    measuring main.tex with one set of regexes and the award PDFs with another
    is not a comparison, so both sides go through THIS function.
    """
    if text is None:
        f = TEXT / f"{name}.txt"
        t = f.read_text(encoding="utf-8", errors="replace")
    else:
        t = text
    ab = abstract_block(t)
    words = count_words(t)
    nums = set(re.findall(r"\d+\.\d+", t))
    pcts = re.findall(r"\d+(?:\.\d+)?\s*%", t)
    secs = section_titles(t)
    top = [s for lvl, s in secs if lvl == 1]
    sub = [s for lvl, s in secs if lvl >= 2]

    def has(pat: str) -> int:
        return len(re.findall(pat, t, re.I))

    return {
        "paper": name, "team": team, "problem": prob, "year": year,
        "prize": prize[0] if prize else "UNVERIFIED",
        "bytes": len(t.encode("utf-8")),
        "words": words,
        "abstract_words": count_words(ab),
        "abstract_numbers": len(set(re.findall(r"\d+\.\d+", ab))),
        "abstract_density": round(len(set(re.findall(r"\d+\.\d+", ab)))
                                  / max(count_words(ab), 1) * 100, 2),
        "distinct_numbers": len(nums),
        "pct_mentions": len(pcts),
        "density_per_100w": round(len(nums) / max(words, 1) * 100, 2),
        "sections": len(top),
        "subsections": len(sub),
        "figures": len(set(re.findall(r"(?:Figure|Fig\.?)\s*(\d{1,2})", t, re.I))),
        "tables": len(set(re.findall(r"Table\s*(\d{1,2})", t, re.I))),
        "equations": len(re.findall(r"\(\d{1,2}\)\s*$", t, re.M)),
        "references": len(re.findall(r"^\s*\[\d{1,2}\]", t, re.M)),
        "has_monte_carlo": has(r"monte\s*carlo"),
        "has_sensitivity": has(r"sensitivit"),
        "has_backtest": has(r"back[\s-]*test|out[\s-]*of[\s-]*sample|hold[\s-]*out"),
        "has_limitation": has(r"limitation|weakness|shortcoming"),
        "has_provenance": has(r"sha[\s-]*256|provenance|data\s*availability"),
        "has_gpu": has(r"\bGPU\b|\bCUDA\b"),
        "has_epoch": has(r"\bepochs?\b"),
        "has_loss": has(r"loss\s*curve|validation\s*loss|training\s*loss"),
        "has_hyperparam": has(r"hyper[\s-]*parameter"),
        "has_crossval": has(r"cross[\s-]*validation"),
        "has_neural": has(r"neural\s*network|LSTM|GRU|CNN|transformer"),
        "has_training": has(r"\btrain(?:ing|ed)?\b"),
        "has_sklearn": has(r"scikit[\s-]*learn|sklearn"),
        "has_ci": has(r"confidence\s*interval|\bCI\b|credible\s*interval"),
        "has_robust": has(r"robustness"),
        "has_assumption": has(r"assumption"),
        "has_error_metric": has(r"\bMAPE\b|\bRMSE\b|\bMAE\b|\bR\s*2\b|R-squared"),
        "has_software": has(r"MATLAB|Python|pandas|numpy|LINGO|SPSS|R\s+software"),
    }


def agg(rows: list[dict], key: str) -> dict:
    vals = [r[key] for r in rows]
    return {
        "min": min(vals), "p25": round(st.quantiles(vals, n=4)[0], 2),
        "median": round(st.median(vals), 2),
        "p75": round(st.quantiles(vals, n=4)[2], 2),
        "max": max(vals),
        "mean": round(st.mean(vals), 2),
    }


def main() -> None:
    pmap = load_prize_map()
    rows, excluded = [], []
    for name, (team, prob, year) in PAPERS.items():
        prize = pmap.get(team, [])
        if "First Prize" not in prize:
            excluded.append({"paper": name, "team": team, "prize": prize or ["NOT_IN_LIST"]})
            continue
        rows.append(measure(name, team, prob, year, prize))

    ct = []
    for name, (team, prob, year) in CHINESE_TRACK.items():
        prize = pmap.get(team, [])
        ct.append({"paper": name, "team": team,
                   "prize": prize[0] if prize else "UNVERIFIED"})

    keys = ["words", "abstract_words", "abstract_numbers", "abstract_density",
            "distinct_numbers", "pct_mentions", "density_per_100w", "sections",
            "subsections", "figures", "tables", "equations", "references"]
    summary = {k: agg(rows, k) for k in keys}

    flags = ["has_monte_carlo", "has_sensitivity", "has_backtest",
             "has_limitation", "has_provenance", "has_gpu", "has_epoch",
             "has_loss", "has_hyperparam", "has_crossval", "has_neural",
             "has_sklearn", "has_ci", "has_robust", "has_assumption",
             "has_error_metric", "has_software"]
    presence = {k: sum(1 for r in rows if r[k] > 0) for k in flags}

    out = {
        "n_first_prize_verified": len(rows),
        "n_excluded": len(excluded),
        "excluded": excluded,
        "chinese_track": ct,
        "per_paper": rows,
        "summary": summary,
        "presence": presence,
        "presence_pct": {k: round(v / len(rows) * 100, 1) for k, v in presence.items()},
    }
    json.dump(out, open(OUT / "official_standard.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    L = []
    L.append("OFFICIAL STANDARD, MEASURED FROM FIRST-PRIZE-VERIFIED PAPERS")
    L.append("=" * 74)
    L.append(f"papers in benchmark: {len(rows)} (prize level verified against the")
    L.append("  official APMCM prize lists downloaded from apmcm.org)")
    L.append(f"excluded (prize not verifiable): {len(excluded)}")
    for e in excluded:
        L.append(f"  - {e['paper']} team {e['team']} -> {e['prize']}")
    L.append("")
    L.append("PER-PAPER")
    L.append(f"{'paper':22s} {'prob':5s} {'words':>6s} {'absW':>5s} {'absN':>5s} "
             f"{'dens':>6s} {'sec':>4s} {'fig':>4s} {'tab':>4s} {'ref':>4s} {'MC':>3s} {'BT':>3s}")
    for r in rows:
        L.append(f"{r['paper']:22s} {r['problem']:5s} {r['words']:6d} "
                 f"{r['abstract_words']:5d} {r['abstract_numbers']:5d} "
                 f"{r['density_per_100w']:6.2f} {r['sections']:4d} {r['figures']:4d} "
                 f"{r['tables']:4d} {r['references']:4d} "
                 f"{'Y' if r['has_monte_carlo'] else '.':>3s} "
                 f"{'Y' if r['has_backtest'] else '.':>3s}")
    L.append("")
    L.append("DISTRIBUTION ACROSS FIRST-PRIZE PAPERS")
    L.append(f"{'metric':22s} {'min':>8s} {'p25':>8s} {'median':>8s} {'p75':>8s} {'max':>8s} {'mean':>8s}")
    for k in keys:
        s = summary[k]
        L.append(f"{k:22s} {s['min']:8.2f} {s['p25']:8.2f} {s['median']:8.2f} "
                 f"{s['p75']:8.2f} {s['max']:8.2f} {s['mean']:8.2f}")
    L.append("")
    L.append("EVIDENCE TYPES PRESENT (count out of %d)" % len(rows))
    for k in flags:
        L.append(f"  {k:20s} {presence[k]:2d}  ({out['presence_pct'][k]:5.1f}%)")
    L.append("")
    L.append("CHINESE-TRACK PAPERS (separate competition stream, excluded)")
    for c in ct:
        L.append(f"  {c['paper']:20s} team {c['team']} -> {c['prize']}")
    (OUT / "official_standard_report.txt").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
