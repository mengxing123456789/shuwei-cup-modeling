"""语料索引：把历年真题与获奖论文建成一份可查询的本地索引。

为什么需要它
    2026-11-19 之前，这条流水线的手上都只有"当前这道题"。历年真题与获奖论文散落在
    `C:\\Users\\29900\\Downloads\\AsterLink`（9 个 zip + 1 个 rar + 49 份散装 PDF）里，
    能读，但不能查：给一道新题，没人能三十秒内说出"这题型 2022 C 做过、那篇一等用 ARIMA"。
    语料索引就是补这一块——它把「附件包」变成「可检索的先验」。

索引里存什么（每条记录）
    id / source(zip|rar|pdf|md) / kind(problem|paper) / year / problem(A–E) / contest /
    file(虚拟路径：`zip://<压缩包>!/<包内名>`) / pages / chars / title / head(前 1200 字)

不存什么
    不存全文、不存向量。全文要重读时按 file 回原处取；固定的压缩包路径比一份 50 MB
    的可再生副本更可靠。grams 在查询时现算（大 gram 集合进 JSON 会让文件膨胀十倍）。

用法
    建索引：  python <skill>\\scripts\\corpus_index.py --build
    查近邻：  python ... --query "主动减振 离心作动器" --top 5
    按题筛：  python ... --query "热解 催化" --year 2023 --problem B
    看统计：  python ... --stats
    接口：    from mmkit.corpus import load, build, query, snippet
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_ROOT = Path(r"C:\Users\29900\Downloads\AsterLink")  # 旧的本地语料根，仅作最后兜底
CACHE_DIRNAME = ".asterlink-cache"
OUT_REL = Path(".mh") / "corpus.json"

YEAR_RE = re.compile(r"(20\d\d)")
PAPER_RE = re.compile(r"^([A-Ea-e])[\s_]*20\d\d\d+")
# 题号出现在文件名里的三种写法（2019–2025 全都出现过，只认第一种会把 2019/2020/2021 全漏掉）：
#   `A_Problem` / `A202111107503`        —— 字母在前
#   `Problem_A` / `Problem A：…`          —— 字母在后（2019 全系列、2025 秋季赛）
#   `problemC-Optimal snow removal…`      —— 小写 problem + 字母 + 连字符（2020）
PROBLEM_IN_NAME = re.compile(r"([A-E])[\s_]*(?:Problem|problem)|"
                            r"[Pp]roblem[\s_\-：:]*([A-E])(?![A-Za-z])|"
                            r"(?i:prob\w{0,3}([A-E])(?![A-Za-z]))")
PROBLEM_IN_LABEL = re.compile(r"([A-E])_Problem|[Pp]roblem[\s_\-：:]*([A-E])(?![A-Za-z])|"
                             r"(?i:prob\w{0,3}([A-E])(?![A-Za-z]))")
PROBLEM_IN_TEXT = re.compile(r"[Pp]roblem\s*([A-E])(?![A-Za-z])")


def _problem_of(m: re.Match | None) -> str:
    """三组捕获（字母在前 / 字母在后 / 拼错的 problem）统一成一个字母。"""
    if not m:
        return ""
    for g in m.groups():
        if g:
            return g.upper()
    return ""
SURROGATE = re.compile(r"[\ud800-\udfff]")
WS_RE = re.compile(r"\s+")
CJK_RE = re.compile(r"[\u4e00-\u9fff]+")
WORD_RE = re.compile(r"[a-z][a-z0-9_\-]{1,}")
SEVEN_ZIP = [
    Path(r"C:\Program Files\7-Zip\7z.exe"),
    Path(r"C:\Program Files (x86)\7-Zip\7z.exe"),
    Path.home() / "AppData" / "Local" / "Microsoft" / "WindowsApps" / "7z.exe",
]

PAGE_LIMIT = 2          # 只抽前两页：题面与论文标题/摘要都在这一带，抽多了纯浪费时间
CHAR_LIMIT = 6000       # 每条记录正文上限，head 再截到 1200
HEAD_CHARS = 1200


def workspace_root() -> Path:
    """从本文件向上找带 .agents/skills 的那一级——工作区根，不写死 E:\\。"""
    for probe in Path(__file__).resolve().parents:
        if (probe / ".agents" / "skills").is_dir():
            return probe
    return Path(__file__).resolve().parents[3]


def corpus_path() -> Path:
    env = os.environ.get("MM_CORPUS")
    if env:
        return Path(env)
    return workspace_root() / OUT_REL


def corpus_root() -> Path:
    """语料根：MM_CORPUS_ROOT > 仓库内 corpus/ > 旧的 AsterLink 兜底。"""
    env = os.environ.get("MM_CORPUS_ROOT")
    if env:
        return Path(env)
    local = workspace_root() / "corpus"
    if local.is_dir():
        return local
    return DEFAULT_ROOT


# ---------------------------------------------------------------- 文本抽取

def _norm(t: str) -> str:
    t = SURROGATE.sub("", t or "")
    t = t.replace("\x00", " ")
    return WS_RE.sub(" ", t).strip()


def _clean_keep_lines(t: str) -> str:
    """保换行的清洗：标题识别要看行，整段压成一行会让「最长的行」变成全文。"""
    t = SURROGATE.sub("", t or "").replace("\x00", " ")
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    lines = [WS_RE.sub(" ", l).strip() for l in t.split("\n")]
    return "\n".join(l for l in lines if l)


def pdf_text(blob: bytes, pages: int = PAGE_LIMIT, limit: int = CHAR_LIMIT) -> tuple[str, int]:
    """返回 (正文, 总页数)。pymupdf 不可用时抛 ImportError，由调用方降级。"""
    import pymupdf  # 别用 fitz：它每次 import 都往 stderr 打 FutureWarning

    with pymupdf.open(stream=blob, filetype="pdf") as doc:
        n = doc.page_count
        chunks = []
        for i in range(min(pages, n)):
            chunks.append(doc.load_page(i).get_text("text"))
        return _clean_keep_lines("\n".join(chunks))[:limit], n


_HEADING_RE = re.compile(r"^(Abstract|Summary|摘\s*要|关键词|Keywords|Contents|目\s*录|问题重述)\b", re.I)
_NOISE_RE = re.compile(r"^(Team|Page|Problem|参赛|第\s*\d+\s*页|Page\s*\d+|ShuWei Cup Summary"
                      r"|Your team|Type a summary)", re.I)
_SENT_START_RE = re.compile(r"^(For|With|In|Based|The|This|We|It|As|To|By|Our|A|An|Since|"
                            r"Given|According|Due|Now|At|On|From|There|These|Those)\b")
_TAIL_FUNC = re.compile(r"\b(and|of|the|to|in|for|with|on|at|by|a|an)$", re.I)
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def _tidy_title(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"[\s\.。，,;；:：]+$", "", s)
    return s[:120]


def _join_wrap(lines: list[str], i: int, first: str) -> str:
    """标题被排版折行时把它接回来。

    2023/2024 的官方题面标题多跨两行："Modeling and Optimization Control Issues of" 后面
    另起一行 "a Compound Helicopter"。只取首行会留下半句（截图给人看时像被截断）。
    判据：首行以 and/of/the/for/in/on/with 之类虚词结尾，且次行短、不像正文段落。
    """
    out = first
    j = i + 1
    while j < len(lines) and j <= i + 2:
        if not _TAIL_FUNC.search(out.rstrip()):
            break
        nxt = lines[j].strip()
        if not nxt or len(nxt) > 60 or _NOISE_RE.match(nxt) or _HEADING_RE.match(nxt):
            break
        out = out.rstrip() + " " + nxt
        j += 1
    return out


_ABSTRACT_OPEN = re.compile(
    r"^(this paper|in this paper|this article|this study|we |our |here we|the results|results show|"
    r"based on the|according to|it is |there are|as shown|by using|firstly|secondly|thirdly|"
    r"for question|in order to|due to the|with the development|in recent years|nowadays)", re.I)
_ABSTRACT_BODY = re.compile(
    r"\b(this paper|this article|this study|we (can|could|will|have|use|propose|find)|"
    r"it (can|could|should) be|will be|have been|has been|are (shown|given|listed)|"
    r"is (shown|given|listed|proposed)|as (follows|shown))\b", re.I)


def _plausible_title(s: str) -> bool:
    """否定器：不像论文标题的候选一律否决（宁可退回文件名）。

    只在「规则一 / 规则零点五 / 规则二 / 打分制」这几条启发式上用；
    规则零（官方题面 `Problem A：<标题>`）与 `_title_from_name` 不走这里——
    那两个来源本身可信，标题是句首大写式（"Demand forecast of rebar in China"）。
    """
    s = (s or "").strip()
    if not (8 <= len(s) <= 130):
        return False
    if _ABSTRACT_OPEN.match(s):
        return False
    if re.fullmatch(r"(January|February|March|April|May|June|July|August|September|October|"
                    r"November|December)\s+\d{1,2},\s*20\d\d", s, re.I):
        return False
    if _CONT_HEAD.match(s) and len(re.findall(r"[A-Za-z]+", s)) <= 6:
        return False
    if _ABSTRACT_BODY.search(s):
        return False
    if len(re.findall(r"[A-Za-z][A-Za-z'\-]+", s)) > 18:
        return False
    return True


def _title_case_ratio(s: str) -> float:
    words = re.findall(r"[A-Za-z][A-Za-z'\-]+", s)
    if not words:
        return 0.0
    return sum(1 for w in words if w[:1].isupper()) / len(words)



_CONT_HEAD = re.compile(
    r"^(and|or|based|through|for|on|of|with|using|under|via|by|to|in|from|toward|towards|"
    r"machines|models|model|method|methods|algorithm|algorithms|analysis|approach|system|"
    r"systems|research|study|optimization|assessment|evaluation|design|control)\b", re.I)
_CAP_HEAD = re.compile(r"^[A-Z][a-z]+\b")


def _join_back(lines: list[str], i: int, first: str) -> str:
    """标题被换行切成几段时，把前面的段接回来（最多 3 段）。

    判据：当前候选以接续词开头（and/based/through/for/on/of/…）或首词小写，
    才认为「这句是从中间开始的」，于是往前找。往前找的那一行必须像标题的一部分：
    <= 90 字符、不是页眉/小标题（Abstract…）、不是整句开头（This/For/We…）。
    这已经是第五轮：前四轮的共同毛病是只接一行，而标题常被抽成 3 行。
    """
    head = first.strip()
    j = i - 1
    steps = 0
    while j >= 0 and steps < 3:
        if not (_CONT_HEAD.match(head) or head[:1].islower()):
            break
        prev = lines[j].strip()
        if not prev or len(prev) > 90:
            break
        if _NOISE_RE.match(prev) or _HEADING_RE.match(prev):
            break
        if prev.endswith((".", "。", "?", "？", ":", "：")) and not _TAIL_FUNC.search(prev):
            break
        if _SENT_START_RE.match(prev):
            break
        head = _tidy_title(prev.rstrip() + " " + head)
        j -= 1
        steps += 1
    return head


def _guess_title(text: str, fallback: str) -> str:
    """从首页前若干行里猜标题。取不到就用文件名。

    四轮踩坑史（每一轮都是被真实语料打回来的）：
      1) 取「第一句像标题的」→ 2023 那批首页第一行是 Team/Page，跳过之后没有候选，
         标题全变成文件名（B2023081819323）。
      2) 「前 10 行里最长的一行」→ 常拿到摘要里被换行截断的长句
         （"For question 1: Firstly, the data were pre-processed…"）。摘要句子比标题长。
      3) 打分制（长度 − 句首词 − 冒号）→ 能扫读，但仍常拿到摘要第一句。
      4) 现在加了最硬的一条规则：**Abstract/摘要 标题行前面那一行就是论文标题**。
         官方题面没有这一段，所以对题面仍然走打分制。
    打分制里新增「实词首字母大写比例」——标题式写法（Title Case）与正文句子在这一点上差得最明显。
    """
    lines = [l.strip() for l in text[:1800].split("\n") if l.strip()]

    # 规则零：官方题面的固定写法「Problem A：<标题>」/「Problem A」换行再给标题。
    # 2019–2022 的英文原件都是这个版式；因为 _NOISE_RE 把 Problem 开头的行当噪声过滤，
    # 前几版规则全部跳过它，标题才一路退化到摘要首句。这条必须放在最前面。
    for i, line in enumerate(lines[:6]):
        m = re.match(r"^\s*Problem\s*[A-E]\s*[：:]\s*(.+)$", line, re.I)
        if m:
            return _tidy_title(_join_wrap(lines, i, m.group(1)))
        if re.match(r"^\s*Problem\s*[A-E]\s*$", line, re.I):
            for nxt in lines[i + 1: i + 4]:
                if len(nxt) >= 8 and not _HEADING_RE.match(nxt) and not re.match(r"^\s*Problem\s*[A-E]", nxt, re.I):
                    return _tidy_title(nxt)

    # 规则一：摘要小标题的上一行
    for i, line in enumerate(lines[:25]):
        if _HEADING_RE.match(line) and i > 0:
            for j in range(i - 1, max(-1, i - 4), -1):
                cand = lines[j]
                if _NOISE_RE.match(cand) or len(cand) < 12 or _HEADING_RE.match(cand):
                    continue
                if not _plausible_title(cand):
                    continue
                _cand = _tidy_title(_join_back(lines, j, cand))
                if _plausible_title(_cand) and _title_case_ratio(_cand) >= 0.45:
                    return _cand

    # 规则零点五：2020/2021 那批原件是「首行标题 + 次行长正文」的版式，标题是
    # 句首大写式（"Demand forecast of rebar in China"），大写比例只有 2/7，
    # 过不了下面的 Title Case 卡；但「短行 + 紧跟长段落」这个版式信号足够硬。
    for i, line in enumerate(lines[:4]):
        if i + 1 >= len(lines):
            break
        if _NOISE_RE.match(line) or _HEADING_RE.match(line):
            continue
        words = re.findall(r"[A-Za-z][A-Za-z'\-]+", line)
        if not (2 <= len(words) <= 10) or line.endswith((".", "。", "?", "？", ":")):
            continue
        if len(line) <= 70 and len(lines[i + 1]) >= 80:
            _cand = _tidy_title(_join_back(lines, i, _join_wrap(lines, i, line)))
            if _plausible_title(_cand) and _title_case_ratio(_cand) >= 0.45:
                return _cand

    best, best_score = "", -1e9

    # 规则二（严格）：Title Case。标题式写法里实词几乎全大写开头，正文句子不会。
    # 先走这条，命中就返回——比打分制稳，因为标题通常在页面最上方。
    for line in lines[:8]:
        if len(line) < 12 or len(line) > 120 or _NOISE_RE.match(line) or _HEADING_RE.match(line):
            continue
        words = re.findall(r"[A-Za-z][A-Za-z'\-]+", line)
        if not (3 <= len(words) <= 18):
            continue
        cap = sum(1 for w in words if w[:1].isupper()) / len(words)
        if cap >= 0.6 and not re.search(r"[,;，；]$", line.rstrip(".")):
            # 不要以句号结尾的整句；但允许 "…Using a" 这种被换行截断的写法
            if line.endswith(".") and cap < 0.85:
                continue
            _cand = _tidy_title(_join_back(lines, i, _join_wrap(lines, i, line)))
            if _plausible_title(_cand) and _title_case_ratio(_cand) >= 0.45:
                return _cand

    for line in lines[:14]:
        if len(line) < 12 or len(line) > 160:
            continue
        if _NOISE_RE.match(line) or _HEADING_RE.match(line):
            continue
        if re.fullmatch(r"[\d\s\.\-–—#:]+", line):
            continue
        s = float(len(line)) if len(line) <= 110 else 110.0 - 0.3 * (len(line) - 110)
        words = re.findall(r"[A-Za-z][A-Za-z'\-]+", line)
        if words:
            cap = sum(1 for w in words if w[:1].isupper()) / len(words)
            s += 40.0 * cap                            # Title Case 加分，句子不加
            if len(words) < 3:
                s -= 20.0                              # 两三个词的多半是页眉
        if _SENT_START_RE.match(line):
            s -= 35
        if ":" in line or "，" in line:
            s -= 25
        if _TAIL_FUNC.search(line):
            s -= 20
        if _CJK_RE.search(line):
            s += 10                                    # 中文题名本身短，别被长度项压掉
        if s > best_score:
            best, best_score = line, s
    best = _tidy_title(best) if best else ""
    # 打分制的最后一道闸：既要不「像摘要句」，也要「像 Title Case」。
    # 2023 B 出现的 "efficient feed ratio" 就是正文小写片段——3 个词，靠长度能赢，
    # 大写比例只有 0.33，这一条把它挡掉，让它退回队号。
    if best and _plausible_title(best) and _title_case_ratio(best) >= 0.5:
        return best
    if best:
        _cand = _tidy_title(_join_back(lines, lines.index(best) if best in lines else 0, best))
        if _plausible_title(_cand) and _title_case_ratio(_cand) >= 0.45:
            return _cand
    return fallback[:120]


def _title_from_name(stem: str) -> str:
    """官方题面文件名里自带标题：`Problem A：Active Vibration Suppression Design …`。

    网盘给的这四份（2025 秋季赛）正文首页没有 Title Case 标题行，全是 Background 段落，
    只靠正文猜必然拿到摘要句；文件名反而是最可靠的来源。
    """
    m = re.search(r"Problem\s*[A-E]\s*[：:]\s*(.+)$", stem, re.I)
    if m:
        return _tidy_title(m.group(1))
    m = re.search(r"^[A-E]_?[Pp]roblem[\s_]*[：:]\s*(.+)$", stem)
    if m:
        return _tidy_title(m.group(1))
    return ""


def _meta_from_name(name: str) -> tuple[str, str]:
    """从文件名推 (年份, 题号)。`A202111107503.pdf` → ('2021','A')。"""
    stem = Path(name).stem
    m = YEAR_RE.search(stem)
    year = m.group(1) if m else ""
    pm = PAPER_RE.match(stem.strip()) or PROBLEM_IN_NAME.search(stem)
    if pm and pm.re is PAPER_RE:
        problem = pm.group(1).upper()
    else:
        problem = _problem_of(pm)
    return year, problem


def _meta_from_dir(path: Path, stop: Path | None = None) -> tuple[str, str]:
    """文件名里没年份时，从祖先目录名推：`2023第九届数维杯国际赛题目（整理版）` → 2023。

    为什么要这一层：整理版的题面文件名是 `A_Problem（题面整理）.md`，年份只出现在目录名上。
    不往上找，这四份就会全部掉进「未知」年份，查询时 `--year 2023` 一条都查不到。
    """
    for parent in path.parents:
        m = YEAR_RE.search(parent.name)
        if m:
            return m.group(1), ""
        if stop is not None and parent == stop:
            break
    return "", ""


def _zip_name(info: zipfile.ZipInfo) -> str:
    """中文包名在 Windows 上被 zipfile 按 cp437 解，转回 utf-8/gbk 还原。"""
    raw = info.filename
    if info.flag_bits & 0x800:
        return raw
    for enc in ("utf-8", "gbk", "cp936"):
        try:
            return raw.encode("cp437").decode(enc)
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
    return raw


def _record(rec_id: str, *, source: str, kind: str, year: str, problem: str,
            file: str, text: str, pages: int, title: str) -> dict:
    text = _norm(text)
    return {
        "id": rec_id,
        "source": source,
        "kind": kind,
        "year": year,
        "problem": problem,
        "contest": "数维杯",
        "file": file,
        "pages": pages,
        "chars": len(text),
        "title": title,
        "head": text[:HEAD_CHARS],
    }


def _rid(label: str) -> str:
    return hashlib.sha1(label.encode("utf-8")).hexdigest()[:10]


# ---------------------------------------------------------------- 各类源

def scan_zip(path: Path, depth: int = 0) -> list[dict]:
    out: list[dict] = []
    kind = "paper" if re.search(r"论文|paper", path.name, re.I) else "problem"
    year_arch, _ = _meta_from_name(path.name)
    try:
        with zipfile.ZipFile(path) as zf:
            for info in zf.infolist():
                name = _zip_name(info)
                if info.is_dir():
                    continue
                # 2024 的题目包是「zip 里再套一层 zip」：不递归就只剩一封说明信，
                # 四道真题全丢（实测 2024 只扫到 2 条题面就是这个原因）。
                if name.lower().endswith(".zip") and depth < 2 and info.file_size < 60 * 1024 * 1024:
                    try:
                        with zipfile.ZipFile(io.BytesIO(zf.read(info))) as inner:
                            for r in _zip_members(inner, f"{path}!/{name}", kind,
                                                  year_arch, depth + 1):
                                out.append(r)
                    except (zipfile.BadZipFile, OSError):
                        pass
                    continue
                if not name.lower().endswith(".pdf"):
                    continue
                if info.file_size > 40 * 1024 * 1024:      # 单份 >40MB 的整册跳过：抽两页不值当
                    continue
                out.append(_one_from_blob(zf.read(info), f"{path}!/{name}", kind, year_arch, Path(name).stem))
    except (zipfile.BadZipFile, OSError) as exc:          # noqa: BLE001
        out.append(_record(_rid(str(path)), source="zip", kind=kind, year=year_arch, problem="",
                           file=str(path), text=f"<压缩包打不开：{type(exc).__name__}>",
                           pages=0, title=path.name))
    return out


def _zip_members(zf: zipfile.ZipFile, label: str, kind: str, year_arch: str, depth: int) -> list[dict]:
    out: list[dict] = []
    for info in zf.infolist():
        name = _zip_name(info)
        if info.is_dir():
            continue
        if name.lower().endswith(".zip") and depth < 2 and info.file_size < 60 * 1024 * 1024:
            try:
                with zipfile.ZipFile(io.BytesIO(zf.read(info))) as inner:
                    out.extend(_zip_members(inner, f"{label}!/{name}", kind, year_arch, depth + 1))
            except (zipfile.BadZipFile, OSError):
                pass
            continue
        if not name.lower().endswith(".pdf") or info.file_size > 40 * 1024 * 1024:
            continue
        out.append(_one_from_blob(zf.read(info), f"{label}!/{name}", kind, year_arch, Path(name).stem))
    return out


def _one_from_blob(blob: bytes, label: str, kind: str, year_arch: str, stem: str) -> dict:
    """把一份 PDF 字节变成一条记录。抽不出文本也留记录（标 <无法抽取>），免得静默丢件。"""
    try:
        text, pages = pdf_text(blob)
    except Exception as exc:                              # noqa: BLE001
        return _record(_rid(label), source="zip", kind=kind, year=year_arch, problem="",
                       file=label if label.startswith(("zip://", "rar://")) else f"zip://{label}",
                       text=f"<无法抽取：{type(exc).__name__}>", pages=0, title=stem)
    y, p = _meta_from_name(stem)
    if not p:
        # 包内 PDF 的题号常常只在父目录上（`…/2021_“ShuWei Cup”B_Problem/B_Analysis…pdf`），
        # 文件名只有字母+下划线；再退一步读首页的 `Problem B`。
        p = _problem_of(PROBLEM_IN_LABEL.search(label))
    if not p:
        m = PROBLEM_IN_TEXT.search(text[:2000])
        p = m.group(1).upper() if m else ""
    return _record(_rid(label), source="zip", kind=kind, year=y or year_arch, problem=p,
                   file=label if label.startswith(("zip://", "rar://")) else f"zip://{label}",
                   text=text, pages=pages, title=(_title_from_name(stem) or _guess_title(text, stem)))


def _seven_zip() -> Path | None:
    return next((p for p in SEVEN_ZIP if p.exists()), None)


def scan_rar(path: Path) -> list[dict]:
    """rar 只有三条路：7z 解出 PDF、七牛/网盘重下、或跳过。这里只走第一条。"""
    exe = _seven_zip()
    if exe is None:
        return [_record(_rid(str(path)), source="rar", kind="problem", year=_meta_from_name(path.name)[0],
                        problem="", file=str(path), text="<无 7z，未索引>", pages=0, title=path.name)]
    cache = path.parent / CACHE_DIRNAME / (path.stem + "-pdf")
    cache.mkdir(parents=True, exist_ok=True)
    if not any(cache.rglob("*.pdf")):
        subprocess.run([str(exe), "x", "-y", f"-o{cache}", str(path), "-ir!*.pdf", "-r"],
                       capture_output=True, timeout=600)
    out: list[dict] = []
    for pdf in sorted(cache.rglob("*.pdf")):
        try:
            text, pages = pdf_text(pdf.read_bytes())
        except Exception as exc:                          # noqa: BLE001
            continue
        y, p = _meta_from_name(pdf.name)
        if not p:
            p = _problem_of(PROBLEM_IN_LABEL.search(str(pdf.relative_to(cache))))
        if not p:
            m = PROBLEM_IN_TEXT.search(text[:2000])
            p = m.group(1).upper() if m else ""
        out.append(_record(_rid(f"{path.name}!/{pdf.relative_to(cache)}"), source="rar", kind="problem",
                           year=y or _meta_from_name(path.name)[0], problem=p,
                           file=f"rar://{path}!/{pdf.relative_to(cache)}", text=text, pages=pages,
                           title=(_title_from_name(pdf.stem) or _guess_title(text, pdf.stem))))
    return out


def scan_pdf(path: Path) -> list[dict]:
    year, problem = _meta_from_name(path.name)
    if not year:
        year = _meta_from_dir(path)[0]
    # 只有「A202111107503.pdf」这种队号式文件名才是论文；`2025_ShuWei Cup A_Problem（官方原件）.pdf`
    # 里也有 A，之前被当成论文，于是 --kind paper 会把官方题面一起列出来。
    kind = "paper" if PAPER_RE.match(path.stem.strip()) else "problem"
    try:
        text, pages = pdf_text(path.read_bytes())
    except Exception as exc:                              # noqa: BLE001
        text, pages = f"<无法抽取：{type(exc).__name__}: {exc}>", 0
    if not problem and kind == "problem":
        m = PROBLEM_IN_TEXT.search(text[:2000])
        problem = m.group(1).upper() if m else ""
    if not year:
        # 2025 秋季赛那批散装题面叫 `Problem B：Research on Crop Leaf Disease.pdf`，
        # 年份既不在文件名也不在目录名，只在抬头 `2025_“ShuWei Cup”` 里。
        m = re.search(r"(20[12]\d)\s*[“\"']?\s*ShuWei", text[:800])
        if m:
            year = m.group(1)
    return [_record(_rid(str(path)), source="pdf", kind=kind, year=year, problem=problem,
                    file=str(path), text=text, pages=pages,
                    title=(_title_from_name(path.stem) or _guess_title(text, path.stem)))]


def scan_md(path: Path) -> list[dict]:
    text = _norm(path.read_text(encoding="utf-8", errors="replace"))
    year, problem = _meta_from_name(path.name)
    if not problem:
        m = re.search(r"([A-E])[_\- ]?Problem", path.name)
        problem = m.group(1) if m else ""
    if not year:
        year = _meta_from_dir(path)[0]
    return [_record(_rid(str(path)), source="md", kind="problem", year=year, problem=problem,
                    file=str(path), text=text, pages=0, title=path.stem)]


def scan_xlsx(path: Path) -> list[dict]:
    """附录数据表：索引工作表的表名、行列与首行表头。

    为什么附录也要进索引：2023 A/B/D 与 2025 A 的题面都写明"数据见附件 xlsx"，
    但索引里只有题面，就会出现「题面说要建模型、手上却查不到那份表」的空档。
    这里只存表名与表头，不存数据本体——查询要的是"这份表长什么样"，不是数值。
    """
    year, problem = _meta_from_name(path.name)
    if not year:
        year = _meta_from_dir(path)[0]
    if not problem:
        problem = _problem_of(PROBLEM_IN_NAME.search(path.name))
    lines: list[str] = [f"附录数据表：{path.name}"]
    try:
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        for ws in wb.worksheets:
            header: list[str] = []
            for row in ws.iter_rows(min_row=1, max_row=1, values_only=True):
                header = [str(c).strip() for c in row if c is not None][:8]
                break
            lines.append(f"工作表 {ws.title}：{ws.max_row} 行 × {ws.max_column} 列；表头 {header}")
            # 第二行给一条样例，用于判断是参数表还是原始观测
            for row in ws.iter_rows(min_row=2, max_row=2, values_only=True):
                sample = [str(c) for c in row if c is not None][:6]
                if sample:
                    lines.append(f"  首行样例 {sample}")
                break
        wb.close()
    except Exception as exc:                              # noqa: BLE001
        lines.append(f"<无法读取：{type(exc).__name__}: {exc}>")
    text = "\n".join(lines)
    return [_record(_rid(str(path)), source="xlsx", kind="data", year=year, problem=problem,
                    file=str(path), text=text, pages=0, title=path.stem)]


def scan_docx(path: Path) -> list[dict]:
    """附录文档（如 C 题的四份 docx）：索引前若干段，供按内容查。"""
    year, problem = _meta_from_name(path.name)
    if not year:
        year = _meta_from_dir(path)[0]
    if not problem:
        problem = _problem_of(PROBLEM_IN_NAME.search(path.name))
    try:
        import docx
        d = docx.Document(str(path))
        paras = [p.text.strip() for p in d.paragraphs if p.text and p.text.strip()][:40]
        text = "\n".join(paras)
        text = f"{path.name}\n段落 {len(d.paragraphs)}，表格 {len(d.tables)}\n{text}"
    except Exception as exc:                              # noqa: BLE001
        text = f"<无法读取：{type(exc).__name__}: {exc}>"
    return [_record(_rid(str(path)), source="docx", kind="appendix", year=year, problem=problem,
                    file=str(path), text=text, pages=0, title=path.stem)]


# ---------------------------------------------------------------- 建 / 查

def _skip_name(path: Path) -> bool:
    """台账/说明类文件不进语料：不提供题面也不提供论文，进索引只会稀释检索。"""
    name = path.name
    return name.startswith("_") or name.lower().startswith("readme")


def build(roots: list[Path] | None = None, verbose: bool = False) -> dict:
    roots = roots or [corpus_root()]
    records: list[dict] = []
    seen: set[str] = set()
    content: set[str] = set()
    dup = 0
    for root in roots:
        if not root.exists():
            continue
        for dirpath, _dirnames, filenames in os.walk(root):
            for fn in sorted(filenames):
                p = Path(dirpath) / fn
                low = fn.lower()
                if _skip_name(p):
                    # 台账（_PROVENANCE.md）与说明（README…）不进语料：不提供题面也不提供论文，
                    # 进了索引只会让「未知年份 题面」凭空多几条，检索时还得人工跳过。
                    continue
                if low.endswith(".zip"):
                    recs = scan_zip(p)
                elif low.endswith(".rar"):
                    recs = scan_rar(p)
                elif low.endswith(".pdf"):
                    recs = scan_pdf(p)
                elif low.endswith(".xlsx"):
                    recs = scan_xlsx(p)
                elif low.endswith(".docx"):
                    recs = scan_docx(p)
                elif low.endswith(".md") and "README" not in fn:
                    recs = scan_md(p)
                else:
                    continue
                for r in recs:
                    if r["id"] in seen:
                        continue
                    seen.add(r["id"])
                    # 内容级去重：AsterLink 里 `2023…优秀论文.zip` 与 `… (1).zip` 是同一包，
                    # 按路径去重会留下 36 条同题论文（实测），查询结果里前十条全是双份。
                    # 键里**不含 title**：title 由启发式推断，启发式一改，同一份文件就会被
                    # 判成两份（182→183→185 条就是这么漂的）。
                    ck = hashlib.sha1(
                        f"{r['kind']}|{r['year']}|{r['problem']}|{r['head'][:300]}".encode("utf-8")
                    ).hexdigest()
                    if ck in content:
                        dup += 1
                        continue
                    content.add(ck)
                    records.append(r)
                if verbose:
                    print(f"  {len(records):4d}  {p.name}", flush=True)
    records.sort(key=lambda r: (r["year"] or "0000", r["kind"], r["problem"], r["title"]))
    return {
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "roots": [str(r) for r in roots],
        "count": len(records),
        "deduped": dup,
        "records": records,
    }


def save(corpus: dict, path: Path | None = None) -> Path:
    path = path or corpus_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # ensure_ascii=False：中文标题要能在编辑器里直接看；\n 归一由 write_text 的 newline 处理
    path.write_text(json.dumps(corpus, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def _rebase(rec: dict, root: Path) -> dict:
    """把记录里的 file 从「建索引时的绝对路径」改成「相对语料根的路径」。

    索引可能是在另一台机器、另一个盘符下建的；`file` 里存绝对路径会让索引
    一换位置就失效。这里统一成相对路径，取用时拼 root。
    `zip://` / `rar://` 前缀的虚拟路径原样保留（它们指向包内成员，包已解开时无效）。
    """
    f = rec.get("file") or ""
    if f.startswith(("zip://", "rar://")):
        return rec
    try:
        rel = Path(f).resolve().relative_to(root.resolve())
    except (ValueError, OSError):
        # 不在当前语料根下（旧索引、跨盘），保留原值让调用方能看出问题
        return rec
    return {**rec, "file": str(rel), "abs": f}


def load(path: Path | None = None) -> dict:
    p = path or corpus_path()
    if not p.exists():
        raise FileNotFoundError(f"语料索引不存在：{p}（先跑 corpus_index.py --build）")
    data = json.loads(p.read_text(encoding="utf-8"))
    root = corpus_root()
    if data.get("records"):
        data["records"] = [_rebase(r, root) for r in data["records"]]
    return data


def grams(text: str) -> set[str]:
    """中文按 2-gram、英文按词。不用 jieba：多一个依赖，而 2-gram 在短查询上够用。"""
    text = text.lower()
    g: set[str] = set()
    for run in CJK_RE.findall(text):
        g.update(run[i:i + 2] for i in range(len(run) - 1))
        if len(run) == 1:
            g.add(run)
    g.update(WORD_RE.findall(text))
    return g


def query(corpus: dict, text: str, *, year: str | None = None, problem: str | None = None,
          kind: str | None = None, top: int = 8) -> list[dict]:
    """返回按相关度排序的命中。打分 = 2-gram 命中率 + 题号/年份完全命中加分。"""
    q = grams(text)
    if not q:
        return []
    hits = []
    for r in corpus.get("records", []):
        if year and r["year"] != year:
            continue
        if problem and r["problem"].upper() != problem.upper():
            continue
        if kind and r["kind"] != kind:
            continue
        body = r["title"] + " " + r["head"]
        g = grams(body)
        inter = len(q & g)
        if not inter:
            continue
        score = inter / (len(q) ** 0.5)                 # 长查询不因为 gram 多而虚高
        if r["problem"] and r["problem"].lower() in text.lower():
            score += 1.5
        if r["year"] and r["year"] in text:
            score += 1.0
        hits.append({**r, "score": round(score, 3), "hits": inter})
    hits.sort(key=lambda h: (-h["score"], h["year"], h["title"]))
    return hits[:top]


def snippet(rec: dict, text: str, width: int = 90) -> str:
    """在 head 里找命中词最密的那一段，给报告引用时有据可依。"""
    body = rec.get("head", "")
    q = [w for w in grams(text) if len(w) >= 2]
    best, best_at = 0, 0
    for i in range(0, max(1, len(body) - width), max(1, width // 3)):
        win = body[i:i + width]
        score = sum(1 for w in q if w in win)
        if score > best:
            best, best_at = score, i
    return body[best_at:best_at + width].strip()


def stats(corpus: dict) -> str:
    recs = corpus.get("records", [])
    by_year: dict[str, dict[str, int]] = {}
    for r in recs:
        d = by_year.setdefault(r["year"] or "未知", {"problem": 0, "paper": 0, "chars": 0})
        d[r["kind"]] = d.get(r["kind"], 0) + 1
        d["chars"] += r["chars"]
    lines = [f"共 {len(recs)} 条，建于 {corpus.get('built_at')}", "年份  题面  论文  字符数"]
    for y in sorted(by_year):
        d = by_year[y]
        lines.append(f"{y}  {d.get('problem', 0):4d}  {d.get('paper', 0):4d}  {d['chars']:7d}")
    return "\n".join(lines)