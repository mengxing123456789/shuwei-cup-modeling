"""把论文的体检口径固定下来：页数、合规、数值对账、基准带。

为什么要有这一层：这些口径在本项目里各自被踩过一次，每次都是"命令能跑、
结论是错的"。把它们写进一个可被 unittest 直接断言的对象，改口径就得改测试。
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .paths import Paper, find_paper

MIKTEX_BIN = Path(r"E:\MIKTEX\miktex\miktex\bin\x64")
PDFTOTEXT = MIKTEX_BIN / "pdftotext.exe"
XELATEX = MIKTEX_BIN / "xelatex.exe"
PDFINFO = MIKTEX_BIN / "pdfinfo.exe"

FRONT_PAGES = 3  # summary sheet + contents x2


def _run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(a) for a in args], cwd=str(cwd) if cwd else None,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def extract_text(pdf: Path, out: Path | None = None) -> str:
    """pdftotext -layout。stderr 里的 "security risk" 不等于失败，只看退出码之外的产物。"""
    if out is None:
        r = _run([PDFTOTEXT, "-layout", "-enc", "UTF-8", pdf, "-"])
        return r.stdout
    _run([PDFTOTEXT, "-layout", "-enc", "UTF-8", pdf, out])
    return out.read_text(encoding="utf-8", errors="replace")


def pages(text: str) -> list[str]:
    return text.split("\f")


def body_pages(text: str) -> int:
    """正文页数。

    口径（三次踩坑后定下来的唯一口径）：
      - 按 \\f 分页；
      - 从「最后一个匹配 Appendix\\s+A 的页」往前找到第一个带 'Page N of M' 的页；
      - N 就是正文页数。
    为什么不再「跳过前 4 页」：官方格式是 第 1 页 Control Sheet + 第 2 页 Summary
    Sheet + 第 3 页目录，正文从第 4 页开始；一旦有人少一个 \\newpage 或加了封面，
    固定跳 4 页就会错位（小队测验里 03 与 06 两个成员用不同跳页口径得出了不同结论）。
    为什么取「最后一个」Appendix A 命中页：目录页自己也会列出 "Appendix A"，先命中它
    会读到空页眉并抛 'no header marker'。

    第五次修正（2026-11-12）：附录 E 现在列出 `code/` 全部 31 个脚本，其中若干脚本的
    源码里出现字面量 "Appendix A"（它们本来就是查附录的探针）。于是"最后一个命中页"
    落到附录深处，body 从 30 变成 112 —— 正是本函数第三次踩的同一个坑（锚点字符串
    出现在被测文本里）。同时官方模板会把附录标题编号成 `I. Appendix A: Code`。
    现在的口径：
      - 锚点 = 行首形态 `^[ \t]*(?:[A-Z]{1,4}\.|[0-9]+\.)?[ \t]*Appendix[ \t]+[A-Z]`；
      - 只在**目录之后**（index >= 3）找，且取**第一个**命中页 —— 目录页本身列着
        "Appendix A" 且带点引，但它在前 3 页；
      - 从该页往前找第一个带 'Page N of M' 的页，N 即正文页数。
    取第一个而不是最后一个的理由：代码清单会一直往下复制粘贴这类字符串，取最后一个
    必然被后文的代码带走；而附录 A 在文档里只会出现一次（在代码之前）。
    """
    ps = pages(text)
    # 前缀两种写法都要认：apmcm 是 "I. Appendix A"（罗马数字 + 点），
    # 数维杯 swmcmthesis 是 "A       Appendix A"（字母 + 空格，无点；实测 pdftotext -layout 输出）。
    anchor = re.compile(r"^[ \t]*(?:[A-Z]{1,4}\.|[0-9]+\.|[A-Z]{1,3}[ \t]{2,})?[ \t]*Appendix[ \t]+[A-Z]\b", re.M)
    hits = [i for i in range(3, len(ps)) if anchor.search(ps[i])]
    if not hits:
        raise ValueError("Appendix heading page not found")
    for i in range(hits[0], -1, -1):
        m = re.search(r"Page\s+(\d+)\s+of\s+(\d+)", ps[i])
        if m:
            return int(m.group(1))
    raise ValueError(f"page {hits[0] + 1} has the Appendix heading but no header marker")


FRONT_PAGE_PREFIXES = (r"\makecontrolsheet", r"\maketitle", r"\tableofcontents")


def _page_roles(ps: list[str]) -> list[str]:
    """给每页贴一个角色标签，用于判「前三页顺序」。

    判据来自实测（不是官方文档，官方 PDF 被加密了）：
      - 'control'：页首 3 行内出现 control sheet / team member must sign；
      - 'summary'：有 "summary sheet"，或页首 8 行内出现 ABSTRACT；
      - 'contents'：页首 3 行内有 Contents；
      - 'body'：其余。
    """
    roles = []
    for p in ps:
        lines = [l.strip() for l in p.split("\n") if l.strip()]
        head3 = " ".join(lines[:3]).lower()
        head8 = " ".join(lines[:8]).lower()
        if "control sheet" in head3 or "must sign" in head3:
            roles.append("control")
        # 摘要页的三种标记：模板写 "Team Number: / Problem Chosen: / 20xx APMCM summary sheet"，
        # 别的模板写 "ABSTRACT"。实测 2025 主稿的 summary sheet 落在第 4 行（页眉占 1 行、队号页眉占 2 行），
        # 所以判据取前 8 行，不能取前 3 行 —— 我第一版取 3 行，把真稿判成了空。
        elif "summary sheet" in head8 or "abstract" in head8:
            roles.append("summary")
        # 数维杯模板的目录标题是单数 "Content"（实测 demo 与骨架都如此），
        # 只写 "contents" 会让 R-W11 的前置顺序变成 ['summary'] 而判红。
        elif any(l.lower().startswith(("content", "contents")) for l in lines[:4]):
            roles.append("contents")
        else:
            roles.append("body")
    return roles


def front_matter_from_pdf(paper: Paper) -> list[str]:
    """从前三页的实际内容判顺序，返回例如 ['summary', 'contents'] 或
    ['control', 'summary', 'contents']。

    为什么不从源码判 \\makecontrolsheet：真正在用的主稿 `APMCM2025_C` 根本没写那条命令，
    它是靠 `mainmatter`/`frontmatterstyle` 自己排出来的；只认源码命令会把它判成空。
    """
    ps = pages(extract_text(paper.pdf))
    return [r for r in _page_roles(ps[:3]) if r != "body"]


def front_matter_order(paper: Paper) -> list[str]:
    """按源码里 \\begin{document} 之后的出现顺序，判前三页是否 Control Sheet → 摘要页 → 目录。

    官方格式硬项：第 1 页是 Control Sheet（承诺书），第 2 页是 Summary Sheet（摘要页），
    第 3 页起目录。模板默认写 \\maketitle，编出来第 1 页就是摘要页 —— 这是小队测验里
    R-W11 唯一一条「规则没拦住的真实违规」，所以把它自动化。
    """
    tex = paper.tex.read_text(encoding="utf-8", errors="replace")
    i = tex.find(r"\begin{document}")
    head = tex[i:] if i >= 0 else tex
    j = head.find(r"\begin{abstract}")
    front = head[:j] if j >= 0 else head
    order: list[str] = []
    for m in re.finditer(r"\\(makecontrolsheet|maketitle|tableofcontents)\b", front):
        name = m.group(1)
        if not order or order[-1] != name:
            order.append(name)
    return order


@dataclass
class Compliance:
    total_pages: int = 0
    body_pages: int = 0
    header_markers: int = 0
    distinct_of: int = 0
    cjk_chars: int = 0
    university_hits: int = 0
    placeholder_team: bool = False
    # 数维杯口径：正文 = 前置页 + body_pages（附录不计）。apmcm 口径不看它。
    submitted_pages: int = 0
    page_limit: int = 30
    template: str = "apmcm"
    findings: list[str] = field(default_factory=list)
    _numbers_are_contiguous: bool = True
    # 诊断用：页眉里出现过的分子与分母。失败时打印它，才知道是跳号还是缺页眉，
    # 而不是只看到一个 False。（测试里曾因拿不到诊断信息多跑了一轮。）
    _header_numbers: list[int] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return (
            self.cjk_chars == 0
            and self.university_hits == 0
            and 0 < self.body_pages
            and (
                (self.template == "swmcm" and 0 < self.submitted_pages <= self.page_limit)
                or (self.template != "swmcm" and self.body_pages <= self.page_limit)
            )
            # 不再要求 header_markers == total_pages：前端 3 页与未编号附录页本来就不带页眉。
            # 这条曾在 R-V02 里把任何正常论文判成不合格。
            and self.distinct_of == 1
            and self._numbers_are_contiguous
            and not self.placeholder_team
        )


def check_compliance(paper: Paper | None = None) -> Compliance:
    P = paper or find_paper()
    text = extract_text(P.pdf)
    ps = pages(text)
    c = Compliance(total_pages=len(ps) - 1 if ps and ps[-1].strip() == "" else len(ps))
    try:
        c.body_pages = body_pages(text)
    except ValueError as e:
        c.findings.append(str(e))
    marks = re.findall(r"Page\s+(\d+)\s+of\s+(\d+)", text)
    c.header_markers = len(marks)
    # 分母才是总页数（同一份 PDF 全篇一致）；分子去重后应等于分母，
    # 否则说明有页重复或跳号。第一次实现取了分子，distinct_of 恒为 1。
    totals = {m[1] for m in marks}
    numbers = {m[0] for m in marks}
    c.distinct_of = len(totals)
    # 「全篇一致」= 只有一个分母，且分子覆盖 1..分母 中的每一页。
    # 前端 3 页不编号、未编号的附录页也不带页眉，所以分子数通常 < 分母数，
    # 判定的是「有没有跳号或重复」，不是「两数相等」。第一次写成相等，
    # 于是任何正常论文都会被判不合格。
    # 「位置诚实」判据：前置页（摘要页、目录页）按官方模板本来就不带页眉，所以
    # 分子不必从 1 开始；但凡带页眉的页，Page n 的 n 必须等于它的物理页号 —— 既不跳号、
    # 也不重号。旧判据要求分子 == 1..n 连续，于是「摘要+目录占 2 页、正文首页写
    # Page 3 of 25」这种完全合规的版式被判 FAIL（2026-11-22 本机实测，swmcm 模板）。
    # 拿不到逐页映射时（合成夹具、单页文本）退回旧判据。
    _pos_marks = []
    for _i, _pg in enumerate(ps):
        for _m in re.finditer(r"Page\s+(\d+)\s+of\s+(\d+)", _pg):
            _pos_marks.append((_i + 1, int(_m.group(1))))
    _phys = {num for _phys_i, num in _pos_marks}
    if _pos_marks and len(_phys) == len(_pos_marks):
        c._numbers_are_contiguous = len(totals) == 1 and all(
            num == phys_i for phys_i, num in _pos_marks
        )
    else:
        c._numbers_are_contiguous = (
            len(totals) == 1
            and sorted(map(int, numbers)) == list(range(1, len(numbers) + 1))
        )
    c._header_numbers = sorted(map(int, numbers))
    # R-V03 的口径是**正文**，不是整本 PDF：官方 2017-2023 每年 Essay format 写的是
    # "no Chinese word should be found in the main body of the solution paper"。
    # 旧实现数整个 text，于是附录里带中文注释的源码被算成违规（本机 2018A 练习稿实测
    # 正文 0 字、附录 3207 字被判 FAIL）—— 判据错，不是论文错。
    # 附录里的汉字仍然统计（cjk_chars_appendix），但单独报数、不参与 ok。
    roles = _page_roles(ps)
    # 前缀两种写法都要认：apmcm 是 "I. Appendix A"（罗马数字 + 点），
    # 数维杯 swmcmthesis 是 "A       Appendix A"（字母 + 空格，无点；实测 pdftotext -layout 输出）。
    anchor = re.compile(r"^[ \t]*(?:[A-Z]{1,4}\.|[0-9]+\.|[A-Z]{1,3}[ \t]{2,})?[ \t]*Appendix[ \t]+[A-Z]\b", re.M)
    app_at = next((i for i in range(2, len(ps)) if anchor.search(ps[i])), len(ps))
    body_txt = "\n".join(ps[i] for i in range(app_at) if roles[i] == "body")
    c.cjk_chars = len(re.findall(r"[\u4e00-\u9fff]", body_txt))
    c.cjk_chars_appendix = len(re.findall(r"[\u4e00-\u9fff]", "\n".join(ps[app_at:])))
    c.university_hits = len(re.findall(r"(?i)university", text))
    tex = P.tex.read_text(encoding="utf-8", errors="replace")
    c.placeholder_team = bool(re.search(r"\\baominghao\{[^}]*X{3,}", tex))
    c.template = "swmcm" if "swmcmthesis" in tex else "apmcm"
    if c.template == "swmcm":
        # 正文第一页 = 第一个出现 "Page 1 of N" 的物理页；它前面的都是前置页。
        first_body = next(
            (i for i, pg in enumerate(ps) if re.search(r"Page\s+1\s+of\s+\d+", pg)), 0
        )
        c.page_limit = 25
        c.submitted_pages = first_body + c.body_pages
        if c.submitted_pages > c.page_limit:
            c.findings.append(
                f"submitted {c.submitted_pages} pages (front {first_body} + body {c.body_pages})"
                f" > {c.page_limit} limit"
            )
    elif c.body_pages > 30:
        c.page_limit = 30
        c.submitted_pages = c.body_pages
        c.findings.append(f"body {c.body_pages} pages > 30 limit")
    if c.placeholder_team:
        c.findings.append(r"\baominghao still a placeholder (XXXXX)")
    if len(totals) != 1:
        c.findings.append(f"{len(totals)} distinct page totals in the headers")
    if not c._numbers_are_contiguous and numbers:
        c.findings.append("header page numbers are not a contiguous run from 1")
    return c


def build(paper: Paper | None = None, passes: int = 2) -> list[int]:
    """两次 xelatex。latexmk 在本机不可用（MiKTeX 找不到 perl 引擎）。"""
    P = paper or find_paper()
    codes = []
    for _ in range(passes):
        r = _run([XELATEX, "-interaction=nonstopmode", "-halt-on-error", "main.tex"], cwd=P.root)
        codes.append(r.returncode)
    return codes


def latex_errors(log: Path) -> list[str]:
    """取 xelatex 日志里的 ! 错误行。

    两件事要分开（这是本机实测过的口径，别把旧结论当事实）：
      - MiKTeX 自己写的 <job>.log 是**普通 UTF-8/ASCII**，首字节常见 "This"，
        实测 main.log 54328 字节全 ASCII/UTF-8。旧笔记说"日志是 UTF-16"是错的。
      - 真正带 FF FE BOM 的 UTF-16 文件，是 PowerShell 用 `*>` / `>` 重定向
        把 stdout 落盘时生成的产物。
    所以判据只能是 BOM，不能是"它在 logs 目录里"。原实现已经按 BOM 判，这里把注释改成真实口径。
    """
    if not log.exists():
        return []
    raw = log.read_bytes()
    s = raw.decode("utf-16", errors="replace") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8", "replace")
    return [ln for ln in s.splitlines() if ln.startswith("!")]


@dataclass
class BandRow:
    metric: str
    project: float
    median: float
    pct: float
    verdict: str

    @property
    def inside_band(self) -> bool:
        return "inside" in self.verdict or "within" in self.verdict


METRICS = (
    "words", "abstract_words", "abstract_numbers", "abstract_density",
    "distinct_numbers", "pct_mentions", "density_per_100w", "sections",
    "subsections", "figures", "tables", "equations", "references",
)

def _benchmark_dir(paper: "Paper") -> "Paper":
    """The directory that owns the award benchmark.

    2026-11-12（R-V15）：基准曾经有**两份**——donor 的重算过，练习稿目录里的还是
    11-10 的旧副本，而 `band()` 恰好读到旧的那份，于是 `sections median` 报 1.0。
    现在不猜「最新含 main.tex 的目录」，而是把所有候选基准按 mtime 列出、取最新
    的一份并**打印路径**；同时 `band()` 会对「median sections <= 2」直接报错
    （那是旧章节正则的指纹，不是某篇论文的属性）。
    """
    from .paths import Paper as _Paper

    roots = {paper.root, paper.root.parent}
    cands: list[Path] = []
    for r in roots:
        if r.is_dir():
            cands += list(r.glob("*/refs/official_standard.json"))
            cands += list(r.glob("refs/official_standard.json"))
    cands = sorted(set(cands), key=lambda p: p.stat().st_mtime, reverse=True)
    if not cands:
        raise FileNotFoundError(
            "no refs/official_standard.json found near %s; run "
            "award_standard.main() in a directory that holds refs/award_text/"
            % paper.root)
    return _Paper(cands[0].parents[1])


def band(paper: Paper | None = None) -> list[BandRow]:
    """项目 vs 一等奖论文的百分位带。

    两侧必须走同一个 measure()，否则就是把 LaTeX 源码和 PDF 文本相比 ——
    那样任何论文都会"图表数为 0"。基准来自 refs/official_standard.json 的
    per_paper（已逐一核验过一等奖队号）。
    """
    import json
    import numpy as np
    from . import award_standard as A
    from .compare_to_awards import project_metrics
    P = paper or find_paper()
    # 「主稿」可能不在 P.root 下：P 是工作区里最新一个含 main.tex 的目录，而 refs/
    # 与 code/compare_to_awards.py 可能属于另一个目录（本项目就是 APMCM2025_C）。
    # project_metrics(P) 默认走 donor（有 official_standard.json 的那个），band 必须跟它同源。
    donor = P if (P.refs / "official_standard.json").exists() else find_paper()
    if not (donor.refs / "official_standard.json").exists():
        donor = _benchmark_dir(P)
    std_path = donor.refs / "official_standard.json"
    std = json.loads(std_path.read_text(encoding="utf-8"))
    papers = std["per_paper"]
    # 2026-11-12（R-V15）：练习稿目录里躺着一份 11-10 的官方基准副本，而 donor 里的
    # 已在 11-01 用修好的章节尺子重算过 —— band 于是拿着旧尺子量新稿，报
    # `sections median 1.0`（30 页论文只有 1 个章节）。基准必须是**唯一**的一份，且
    # 用了哪份要打出来。sections 中位数 <= 2 是旧正则的指纹（它把 "4 . 3 . 1" 和
    # 罗马数字整类漏掉），出现即报错而不是静默继续。
    med_sec = float(np.median([float(p["sections"]) for p in papers]))
    if med_sec <= 2.0:
        raise RuntimeError(
            f"benchmark at {std_path} looks stale: median sections={med_sec} "
            f"(a first-prize paper has >10 sections; the old heading regex missed "
            f"'4 . 3 . 1 Foo' and 'XII. References'). Regenerate with "
            f"award_standard.main() and delete stray copies.")
    print(f"[band] benchmark: {std_path}  n={len(papers)}  "
          f"median sections={med_sec:.1f}")
    proj = project_metrics(P)
    out = []
    for m in METRICS:
        d = np.array([float(p[m]) for p in papers], dtype=float)
        v = float(proj[m])
        pct = float((d < v).mean() * 100.0)
        lo, hi = float(np.percentile(d, 25)), float(np.percentile(d, 75))
        verdict = "inside IQR" if lo <= v <= hi else ("ABOVE band" if v > hi else "BELOW band")
        out.append(BandRow(m, round(v, 3), round(float(np.median(d)), 3), round(pct, 1), verdict))
    return out


def out_of_band(paper: Paper | None = None) -> list[str]:
    return [r.metric for r in band(paper) if not r.inside_band]

