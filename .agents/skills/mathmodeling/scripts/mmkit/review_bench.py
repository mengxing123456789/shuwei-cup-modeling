"""官方语料的唯一入口：任何"评审判据"都必须从这里取，不许在别处手抄。

设计原则（三条，都是为了"客观、真实、可核"）：
1. 每条判据都指向 `_official_criteria.json` 里的 id（C1..C12），该文件每条都带原文出处
   （普通 PDF 是 file:line，扫描件是页号+转录）。本模块只做"把证据搬进代码"，
   不新增任何没有出处的判据。
2. 每条判据都对应一个**可机器核**的函数，返回 (ok, observed, why)。判不出时返回
   ok=None（"无法判定"），不许默认当通过。
3. 阈值只从官方文本或一等奖论文实测里来；每个常数旁边写它从哪来。

用法：
    from mmkit import review_bench as RB
    RB.criteria()                 # 12 条判据 + 出处
    RB.check_paper(paper_dir)     # 对一篇论文跑全部可机器核项
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
from dataclasses import dataclass, field

# ---------------------------------------------------------------- 语料根
PROB = pathlib.Path(r"E:\数学建模\APMCM-PROBLEMS")
CRIT = PROB / "_official_criteria.json"
AWARD_INDEX = PROB / "_award_pdfs.json"
AWARD_TEXT = PROB / "_award_text"
RULES2026 = pathlib.Path(r"E:\数学建模\APMCM2026\refs\apmcm2026_rules.pdf")
MKTEX = pathlib.Path(r"E:\MIKTEX\miktex\miktex\bin\x64")

# 页眉判据（唯一来源；探针与测试都 import 它，避免"探针测的是另一份正则"这类假结论）
# 覆盖 22 篇一等奖里实测出现的全部写法：
#   "Team # apmcm2400001   Page 10 of 66"（官方范例）
#   "Team E apmcm2213503"                （没有页码，by design）
#   "Team # apmcm24207218   P2 of 101"   （Page 缩成 P + 数字）
#   队号本身区分大小写无关：一等奖全小写 apmcm，本项目稿写 APMCM25XXXXX（占位符）。
#   2026-11-11 实测：本稿 108 页里 105 页有 "Team # APMCM25XXXXX ... Page N of 105"，
#   而旧式只认小写 apmcm，导致 C5 报 "header lines matched=0" 假 FAIL。系数 I 修正。
# 语义占位：正文自称"队号无效/不是真队号/占位"，正则查字形查不到（见 C11 第二条）
SEM_PLACEHOLDER = re.compile(
    r"(?i)(?:not\s+(?:a\s+)?(?:valid|real|actual)\s+(?:team\s+)?(?:number|identifier|id)"
    r"|(?:team\s+)?(?:number|identifier|id)\s+is\s+(?:deliberately\s+)?(?:a\s+)?placeholder"
    r"|placeholder\s+(?:team\s+)?(?:number|identifier)"
    r"|队号\s*(?:无效|不真实|占位|待填))"
)
# 页眉有两种排版，判据必须都认：
#   (a) 一行式 —— apmcmthesis: "Team # apmcm2699001  Page 12 of 96"
#   (b) 两行式 —— swmcmthesis: 第一行 "Team # SWBMCM2634892"，第二行 "Page 1 of 14"
# 只写 (a) 时，数维杯合规稿的 C5 实测 0 命中（2026-11-19 用官方模板编出的 16 页稿验的）。
HEADER_RE = (r"(?i)(?:^\s*team\s*[01#]?\s*[a-z]?\s*(?:apmcm|swbmcm|cumcm|mcm|icm)[0-9x]{5,}"
             r"[^\S\n]*(?:page|[a-z]\d)[^\n]{0,12}"
             r"|^\s*team\s*[01#]?\s*[a-z]?\s*(?:apmcm|swbmcm|cumcm|mcm|icm)[0-9x]{5,}[^\S\n]*\n"
             r"[^\n]{0,24}(?:page|[a-z]\d)[^\n]{0,12})")


# ---------------------------------------------------------------- 判据表
@dataclass(frozen=True)
class Criterion:
    id: str
    name: str
    why: str
    n_hits: int
    files: tuple
    evidence: tuple  # ((file, line, quote), ...)
    status: str
    note: str | None = None


def criteria() -> list[Criterion]:
    """12 条官方判据（原样读盘，不缓存，改了 JSON 立刻生效）。"""
    d = json.loads(CRIT.read_text(encoding="utf-8"))
    out = []
    for c in d["criteria"]:
        ev = tuple((e["file"], e["line"], e["quote"]) for e in c.get("evidence", []))
        if c.get("evidence_2026_scanned"):
            ev += tuple((f"apmcm2026_rules.pdf:{e['page']}", 0, e["transcription"])
                        for e in c["evidence_2026_scanned"])
        out.append(Criterion(c["id"], c["name"], c["why"], c.get("n_hits", 0),
                             tuple(c.get("files", [])), ev, c.get("status", ""), c.get("note")))
    return out


def criterion(cid: str) -> Criterion:
    for c in criteria():
        if c.id == cid:
            return c
    raise KeyError(cid)


# ---------------------------------------------------------------- 论文侧体检
def _pdf_text(pdf: pathlib.Path) -> list[str]:
    """按页返回文本（pdftotext 以 \\f 分页）。"""
    r = subprocess.run([str(MKTEX / "pdftotext.exe"), "-enc", "UTF-8", "-layout",
                        str(pdf), "-"], capture_output=True)
    return r.stdout.decode("utf-8", "replace").split("\f")


def _pdf_pages(pdf: pathlib.Path) -> int:
    r = subprocess.run([str(MKTEX / "pdfinfo.exe"), str(pdf)], capture_output=True)
    for line in r.stdout.decode("utf-8", "replace").splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":")[1])
    return 0


@dataclass
class Finding:
    cid: str                     # C1..C12 或 'X-*'（论文自身的可核项）
    ok: bool | None              # None = 无法判定
    observed: str
    why: str = ""
    fix: str = ""                # 给申请人的下一步动作


def _pick_pdf(p: pathlib.Path) -> pathlib.Path | None:
    """选对"要被检的那一篇"。

    **这个函数存在的原因**：初版写 `next(iter(sorted(p.glob("*.pdf"))))`，取的是字典序第一个
    —— 在真稿目录里 `ai_usage.pdf` 排在 `main.pdf` 前面，于是 review_check 拿 3 页的 AI 声明
    去核论文合规，报出 7 条假 FAIL（没有摘要页/没有目录/没有附录/没有参考文献……）。
    判据：**被检对象必须是你要交付的那一篇**，不是目录里碰巧排第一的那一篇。
    """
    if p.suffix.lower() == ".pdf":
        return p
    for name in ("main.pdf", f"{p.name}.pdf"):
        q = p / name
        if q.exists():
            return q
    cands = sorted(p.glob("*.pdf"), key=lambda q: (-q.stat().st_size, q.name))
    return cands[0] if cands else None


@dataclass
class Report:
    paper: pathlib.Path
    pdf: pathlib.Path | None = None
    pages: int = 0
    findings: list[Finding] = field(default_factory=list)

    def add(self, cid, ok, observed, why="", fix=""):
        self.findings.append(Finding(cid, ok, observed, why, fix))

    @property
    def fail(self):
        return [f for f in self.findings if f.ok is False]

    @property
    def unknown(self):
        return [f for f in self.findings if f.ok is None]

    def verdict(self) -> str:
        return "FAIL" if self.fail else ("PARTIAL" if self.unknown else "PASS")


def check_paper(paper: pathlib.Path | str) -> Report:
    """对一篇论文（目录或 PDF）跑全部**可机器核**的官方判据。

    只覆盖能"数得清"的项；判断类（创新性、模型是否有效）不在本函数能力内，
    交给评审小队的人工成员，但他们的结论必须引用这里的数字。
    """
    p = pathlib.Path(paper)
    pdf = _pick_pdf(p)
    rep = Report(paper=p if p.is_dir() else p.parent)
    if pdf is None or not pdf.exists():
        rep.add("X-pdf", False, "找不到 PDF", fix="把论文目录或 main.pdf 路径传进来")
        return rep
    rep.pdf = pdf
    pages = _pdf_text(pdf)
    rep.pages = len(pages) - 1 if pages and pages[-1].strip() == "" else len(pages)
    total = _pdf_pages(pdf)
    full = "\n".join(pages)
    first = pages[0] if pages else ""

    # C4 第一页摘要页、第二页目录（官方 2023 规范原文；2026 p3/p4 同义）
    p1 = (pages[0] if len(pages) > 0 else "").lower()
    p2 = (pages[1] if len(pages) > 1 else "").lower()
    rep.add("C4", "summary" in p1 or "abstract" in p1,
            f"p1 has summary/abstract={'summary' in p1 or 'abstract' in p1}",
            "第一页必须是摘要页",
            "把 \\maketitle 的 summary sheet 放在第 1 页；Control Sheet 不许占第 1 页")
    rep.add("C4", "content" in p2 or "contents" in p2 or "directory" in p2,
            f"p2 has contents/directory={'contents' in p2 or 'directory' in p2}",
            "第二页必须是目录页", "第 2 页放 \\tableofcontents")

    # C5 页眉只有队号 + 页码
    # 官方例子是 "Team#apmcm2600001Page10of20"，但 22 篇一等奖里有 7 种写法：
    # "Team # apmcm2208815 Page 10 of 66" / "Team Dapmcm2201058 ..." / "Team E apmcm2213503 ..."
    # （无 "#"、题号粘在 Team 后面、页眉里没有 "of N"）。所以判据必须放宽到
    # "Team + 可选题号字母 + 队号 + 任意位置出现 Page N"，否则会把正规论文判红。
    # re.S 会让 ".{0,40}" 跨页吞掉整篇再去配 Page，反过来把同页的页眉配没；
    # 页眉里队号与页码是同行的，用 [^\n]{0,60} 限制在本行内。
    # 注意：[01] 而不是 [A-Z#]?——"Team#apmcm…" 里 # 后面没有空格，[A-Z#]?\s* 的
    # \s* 只吃一个可选空白，遇到 "Team # apmcm" 中 # 与 apmcm 之间的空格就配不上；
    # 这一处让 16 篇里 7 篇被误判成"无页眉"，是必须留 [01] 的原因。
    # 页码写法的三种真实变体（2022E 甚至没有 Page 字样，只有队号）：
    #   "Team # apmcm2400001   Page 10 of 66"  ← 官方范例
    #   "Team # apmcm24207218  P1 of 101"      ← 2024D 用 P 而不是 Page
    #   "Team # apmcm25301412  Page 1"          ← 2025C 没有 of N
    # 所以判据是"每页顶部有队号行"，页码范围放宽到可选，不许把变体判成违规。
    # 还有个坑：2025C/2025D 的页码被 pdftotext 在右边界处**截断成 "Page" 或 "P"**，
    # 后面根本没有数字。所以数字部分也必须可选，否则又把两篇正规论文判红。
    # 代价：这一项只能证明"页眉存在且是队号"，证明不了"每页都编了号"——
    # 后者交给 mmkit.gauntlet.body_pages() 的连续编号检查。
    # 第二个坑：_pdf_text() 用 -layout 出文本，页眉右端到 "Page" 之间的空白可能远超 60 字符
    # （2025C 实测 76 字符、2024D 142 行），所以中间段不能设上限，只能排除换行。
    # 但 "[^\n]*?" 会连"其他字"一起吃掉，于是 2022E 那种**没有页码的页眉**也能配上后面的任意 Page。
    # 正解：中间只允许空白 —— "Team E apmcm2213503" 后面是行尾，所以它正确地判为"无页码页眉"。
    # 但 2024D 又有 "P2 of 101" 这种把 "Page" 缩成 "P" + 数字的写法，所以 P 后面要允许数字。
    heads = re.findall(HEADER_RE, full, re.M)
    rep.add("C5", len(heads) > 0, f"header lines matched={len(heads)}",
            "页眉必须形如 Team#apmcm2600001 Page 10 of 20", "用 \\pagestyle{mainmatterstyle}")
    # 页眉越界检查要在"整行"上做，不能只看匹配片段：学校名通常跟在队号后面
    head_lines = [l for l in full.splitlines()
                  if re.match(r"\s*[Tt]eam\s*[01#]?\s*[A-Za-z]?apmcm", l)]
    bad_head = [l for l in head_lines if re.search(r"universit|college|advis|professor|school of", l, re.I)]
    rep.add("C5", not bad_head, f"headers leaking identity={len(bad_head)}",
            "页眉里不许出现学校/指导教师", "页眉只保留 \\team 与页码")

    # C7 正文不得有中文。
    # 官方原文（2017-2023 每年 Essay format，p.67 起）是 "no Chinese word should be found in the
    # **main body** of the solution paper, the chart, etc." —— 口径是**正文**，不是整本 PDF。
    # 旧版对整个 full 计数，于是附录里带中文注释的源码被当成正文违规：本机实测 2018A 练习稿
    # 正文 0 个汉字、附录代码 3207 个汉字，被判 FAIL —— 是判据口径错，不是论文错。
    # 现在：正文 = 前两页之后、第一个 "Appendix A" 行首锚点之前；附录里的汉字单独报数（不判定），
    # 因为"附录代码用母语写注释"这件事官方没有禁止，但读者/评委可能不喜欢，值得让人自己决定。
    body_pages = []
    if pages:
        start = min(2, len(pages))
        app_at = next((i for i, t in enumerate(pages)
                       if re.search(r"^[ \t]*(?:[A-Z]{1,4}\.|[0-9]+\.)?[ \t]*Appendix[ \t]+A\b", t, re.M)), None)
        body_pages = pages[start:app_at] if app_at is not None else pages[start:]
    body_cjk = re.findall(r"[\u4e00-\u9fff]", "\n".join(body_pages))
    app_cjk = re.findall(r"[\u4e00-\u9fff]", "\n".join(pages[len(body_pages) + min(2, len(pages)):]))
    rep.add("C7", not body_cjk,
            f"chinese chars in body={len(body_cjk)} (appendix, not judged={len(app_cjk)})",
            "正文与图表不得出现中文（官方口径是 main body，附录代码不在其内）",
            "把正文/图里的中文换成英文；附录里的中文注释可以选择保留或翻译")

    # C6 页数与字号（官方 2023：正文 within 25 pages；2026 p4：字号 11 或 12）
    # 2026 版扫描件没有给出正文页数上限，只有中文字项模板写"原则上不超过 20 页"，
    # 所以这里两个数都报，不擅自判定。
    rep.add("C6", None if total == 0 else True, f"total pages={total}",
            "正文页数上限按年份不同（2023 规范 25 页 / 中文赛项模板 20 页）；2026 英文规则未给页数上限",
            "报数即可，判定留给按赛事年份选的规则卡")

    # C9 附录必须列软件名 + 全部源码
    has_app = re.search(r"Appendix\s+[A-Z]", full) is not None
    has_code = bool(re.search(r"\\begin\{(lstlisting|verbatim)\}|def\s+\w+\(|import\s+\w+|function\s+\w+\(", full))
    rep.add("C9", has_app and has_code, f"appendix={has_app} code={has_code}",
            "附录须给软件名与全部源代码", "把 code/*.py 用 \\lstinputlisting 进附录")

    # C11 违规风险：队号占位符 / 缺 References
    ph = re.findall(r"apmcm2\dXXXXX|APMCM2\dXXXXX|XXXXX", full)
    rep.add("C11", not ph, f"placeholder team number hits={len(ph)}",
            "占位队号=提交前必须替换，否则违规", "填 \\baominghao{...}")
    # 字形占位只是第一层。2018A 定稿时正文印着 "the identifier ... is deliberately not a
    # valid team number"：上面那行 0 命中，而评委读到字面就成立（C11 语义占位）。
    sem = [(i + 1, m.group(0)[:70]) for i, pg in enumerate(body_pages)
           for m in SEM_PLACEHOLDER.finditer(pg)]
    rep.add("C11", not sem, f"self-declared invalid identifier in body={len(sem)}",
            "正文自称队号无效，与印 XXXXX 同等致命，而字形正则查不到",
            "删掉该句，全篇只留一个真队号")
    rep.add("C11", "Reference" in full, f"has References section={'Reference' in full}",
            "参考文献是官方要求的部分之一", "加参考文献章")

    # C8 参考文献格式
    typed = re.findall(r"\[(?:M|J|R|DB/OL|EB/OL|C|D|S|P)\]", full)
    rep.add("C8", len(typed) > 0, f"reference type markers={len(typed)}",
            "官方给了 [M]/[J] 的形式，应照着写", "每条书目补类型标记")

    return rep


# ---------------------------------------------------------------- 一等奖基准
BENCH_KEYS = ("pages", "front_pages_words", "abstract_numbers", "sections", "figures", "tables")


def award_bench() -> dict:
    """22 篇官方一等奖/优秀论文的实测分布（分位数），供"我比获奖论文差在哪"对照。"""
    recs = json.loads(AWARD_INDEX.read_text(encoding="utf-8"))["records"]
    pages = sorted(int(r["pages"]) for r in recs if str(r["pages"]).isdigit())
    return {"n": len(recs), "pages_p25": _q(pages, .25), "pages_median": _q(pages, .5),
            "pages_p75": _q(pages, .75), "pages_min": pages[0], "pages_max": pages[-1],
            "source": str(AWARD_INDEX)}


def _q(v: list, q: float) -> float:
    if not v:
        return 0.0
    k = (len(v) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(v) - 1)
    return round(v[lo] + (v[hi] - v[lo]) * (k - lo), 1)


# ---------------------------------------------------------------- 摘要基准（16 篇英文一等奖实测）
ABSTRACT_BENCH = {
    "n": 16,
    "words_median": 363.5, "words_p25": 327.0, "words_p75": 449.0,
    "numbers_median": 11.5, "numbers_min": 2, "numbers_max": 66,
    "zero_number_papers": 0,
    "source": r"E:\数学建模\APMCM2026\refs\allpapers\... 16 篇英文一等奖，摘要页 = summary sheet 与 Contents 之间",
}


def abstract_text(pdf: pathlib.Path) -> str:
    """取摘要页正文：从 summary sheet / abstract 之后到 Contents 之前。"""
    pages = _pdf_text(pdf)
    if not pages:
        return ""
    p1 = pages[0]
    m = re.search(r"(?is)(?:summary\s*sheet|abstract)(.*?)(?:\n\s*contents|\Z)", p1)
    return " ".join((m.group(1) if m else p1).split())


def abstract_stats(pdf: pathlib.Path) -> dict:
    """摘要的四件可核事实：词数、数字个数、数字密度、是否逐问。"""
    t = abstract_text(pdf)
    words = re.findall(r"[A-Za-z][A-Za-z\-']+", t)
    nums = re.findall(r"\b\d+(?:\.\d+)?\b", t)
    qs = len(set(re.findall(r"(?i)\b(?:question|problem|task)\s*(\d|one|two|three|four)\b", t)))
    return {"words": len(words), "numbers": len(nums),
            "density": round(len(nums) / max(1, len(words)) * 100, 2),
            "question_refs": qs,
            "verdict_words": "inside" if 327 <= len(words) <= 449 else ("below" if len(words) < 327 else "above"),
            "verdict_numbers": "zero" if not nums else ("thin" if len(nums) < 2 else "ok")}


if __name__ == "__main__":
    for c in criteria():
        print(f"{c.id:16} {c.status:12} hits={c.n_hits:>3} files={len(c.files)}")
    print("bench:", award_bench())

