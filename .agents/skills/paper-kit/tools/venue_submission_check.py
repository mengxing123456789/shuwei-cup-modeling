# -*- coding: utf-8 -*-
"""投稿前检查（投稿格式库 1E，规划 F9，2026-10-11）。

论文编译步完成后由后台调用（web/backend/services/submission_review.py），也能单独跑：

    python venue_submission_check.py <工作区> [--json]

（不叫 submission_check.py：skills/shared-scripts/ 里早有一个同名模块，是 MathorCup 大数据的结果文件核对。）

读工作区里的 paper/main.pdf、paper/main.log、从 paper/main.tex 起 \\input 进来的 .tex，以及后台写的
.mh/writing_spec.json（投稿格式规格）、.mh/user_template.json（上传的模板）、.mh/ai_usage_statement.md
（AI 使用声明留底），逐项核对，写 SUBMISSION_CHECK.md（给人看）和 .mh/quality/submission_check.json
（给程序看，步骤卡读它）。

⛔ 第一版只报告：不拦、不自动返修（规划第十节第 6 项）。每一项自己出错只记“检查未完成”，不影响别的项，
也不影响编译结果。页数只作参考：超出只提醒，不叫删内容（用户 10-09、10-10 定）。
只用标准库；读 PDF 用 PyMuPDF（打包的运行时里有），没有时 PDF 相关的项记“没法检查”。
"""
from __future__ import annotations

import hashlib
import ast
import json
import re
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

SCHEMA_VERSION = 1
REPORT_NAME = "SUBMISSION_CHECK.md"
JSON_RELATIVE = Path(".mh") / "quality" / "submission_check.json"
SPEC_RELATIVE = Path(".mh") / "writing_spec.json"
USER_TEMPLATE_RELATIVE = Path(".mh") / "user_template.json"
AI_SUMMARY_RELATIVE = Path(".mh") / "ai_usage_statement.md"
AI_RECORD_RELATIVE = Path(".mh") / "ai_statement_written.json"
REFERENCE_CHECK_RELATIVE = Path(".mh") / "quality" / "reference_verification.json"
STATEMENT_REL = "sections/ai_statement.tex"
FOOTNOTE_REL = "sections/ai_footnote.tex"
ALT_TEXT_NAME = "ALT_TEXT.md"
MAX_DETAILS = 12
MAX_SOURCES = 300

STATUSES = ("issue", "error", "info", "skipped", "ok")
STATUS_ZH = {"issue": "要你处理", "error": "检查未完成", "info": "提醒", "skipped": "不适用或没法查", "ok": "通过"}

# 自动核对过的注册表规则；其余规则列在“要你对照官网核的规则”里
_AUTO_RULES = {"pdf_fonts_embedded", "pdf_no_bookmarks_links", "pdf_version", "pdf_not_encrypted",
               "language_english", "ai_not_author", "alt_text", "disclosure_of_interests", "review_modes",
               "front_matter"}

_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3000-\u303f\uff01-\uff60\uffe0-\uffe6]")
_CJK_CHAR_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
_REF_HEADING_RE = re.compile(r"(?m)^\s*(?:[0-9IVX]+\.?\s*)?(?:references|bibliography|参考文献)\s*$", re.I)
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
_ORCID_RE = re.compile(r"\b\d{4}-\d{4}-\d{4}-\d{3}[\dX]\b")
_INPUT_RE = re.compile(r"\\(?:input|include|subfile)\s*\{([^{}]+)\}")
_HEADING_RE = re.compile(r"\\(?:chapter|section|subsection|subsubsection|paragraph)\*?\s*(?:\[[^\]]*\])?\s*\{([^{}]*)\}"
                         r"|\\begin\{(acks|acknowledgments?|appendix|appendices|credits)\}|\\(appendix)\b")
_BRACKET_RE = re.compile(r"\[([^\[\]\n]{2,80})\]")
_REF_TYPE_RE = re.compile(r"^(?:[A-Z]{1,2}(?:/OL)?|EB/OL|DB/OL|CP/OL|J/OL|M/OL)$")
_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
_SELF_CITE_RE = re.compile(
    r"\b(?:our|my)\s+(?:own\s+)?(?:previous|prior|earlier|recent|preliminary)\s+(?:work|paper|study|studies|research|"
    r"publication|results?|method|approach)s?\b"
    r"|\bin\s+our\s+(?:previous|prior|earlier)\b"
    r"|\bwe\s+(?:have\s+)?(?:previously|earlier|recently)\s+(?:proposed|showed|shown|presented|introduced|reported|"
    r"developed|studied)\b"
    r"|(?:我们|笔者|作者|本课题组|本团队|课题组)(?:之前|此前|先前|前期|以前|早先|曾经)(?:的)?(?:工作|研究|论文|成果|提出)",
    re.I)
_AI_NAME_RE = re.compile(
    r"chat\s*gpt|\bgpt-?[345](?:\.\d)?o?\b|\bopenai\b|\bclaude[\s-]+(?:\d|opus|sonnet|haiku|instant)|\banthropic\b"
    r"|\bgemini\b|\bgoogle\s+bard\b|\bcopilot\b|\bdeepseek\b|\bkimi\s*(?:chat|ai)\b|\bmoonshot\s*ai\b|\bqwen\b"
    r"|\bernie\s*bot\b|\bdoubao\b|\bchatglm\b|\bglm-?4\b|\bllama\s*-?\d|\bgrok\b|\bnotebooklm\b|\bperplexity\b"
    r"|\b(?:ai|artificial intelligence)\s+(?:assistant|model|tool|system)\b|\blarge language model\b"
    r"|通义|千问|文心一言|豆包|智谱清言|讯飞星火|混元|腾讯元宝|月之暗面|生成式人工智能|大语言模型|人工智能助手",
    re.I)
_SAMPLE_MARKERS = ("lorem ipsum", "this is a sample", "this document is a model", "insert your", "use style:",
                   "author name here", "your name here", "type title here", "replace this text")
_PERSONAL_HINT_RE = re.compile(r"author|name|affiliation|e-?mail|orcid|address|department|university|grant|fund"
                               r"|作者|姓名|单位|地址|邮箱|基金|编号|学校|学院|职称", re.I)
_UNESCAPE = {r"\textbackslash{}": "\\", r"\textasciicircum{}": "^", r"\textasciitilde{}": "~", r"\{": "{",
             r"\}": "}", r"\$": "$", r"\&": "&", r"\#": "#", r"\_": "_", r"\%": "%"}
_AI_WORD_RE = re.compile(r"\bai\b|artificial intelligence|generative|machine|large language|人工智能|生成式|大模型", re.I)
_LOCATION_ZH = {
    "acknowledgment": "致谢里", "separate_section": "单独一节（参考文献之前）", "footnote_and_end": "首页脚注 + 文末",
    "methods_or_appendix": "研究方法或附录里", "methods_or_alternative": "方法部分或出版方指定的位置",
    "methods_or_acknowledgment": "方法部分或致谢里", "unspecified": "出版方没规定位置",
}


# ----------------------------------------------------------------------------- 读文件
def _load_json(path: Path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _read(path: Path) -> str:
    try:
        data = Path(path).read_bytes()
    except OSError:
        return ""
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    return data.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")


def _strip_comments(text: str) -> str:
    out = []
    for line in text.split("\n"):
        match = re.search(r"(?<!\\)%", line)
        out.append(line[:match.start()] if match else line)
    return "\n".join(out)


def _file_hash(path: Path) -> str:
    """和投稿格式注册表的指纹算法一致：CRLF 先统一成 LF 再算 SHA-256。"""
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _tex_sources(paper: Path) -> list[dict]:
    """从 main.tex 起顺着 \\input/\\include 找进 PDF 的 .tex（只认 paper/ 里的文件）。"""
    out: list[dict] = []
    seen: set[str] = set()
    root = paper.resolve() if paper.exists() else paper

    def visit(rel: str) -> None:
        rel = rel.strip().replace("\\", "/")
        if not rel.lower().endswith(".tex"):
            rel += ".tex"
        key = rel.lower()
        if key in seen or len(seen) >= MAX_SOURCES:
            return
        path = paper / rel
        try:
            path.resolve().relative_to(root)
        except (OSError, ValueError):
            return
        if not path.is_file():
            return
        seen.add(key)
        raw = _read(path)
        text = _strip_comments(raw)
        out.append({"rel": rel, "raw": raw, "text": text})
        for match in _INPUT_RE.finditer(text):
            visit(match.group(1))

    visit("main.tex")
    return out


def _plain(tex: str) -> str:
    """LaTeX → 大致的纯文字（找中文、自引写法用，不追求精确）。"""
    text = re.sub(r"\\(?:cite|ref|label|eqref|url|href|input|include|includegraphics|bibliography"
                  r"|bibliographystyle|usepackage|documentclass)\*?(?:\[[^\]]*\])*\{[^{}]*\}", " ", tex)
    text = re.sub(r"\\[A-Za-z@]+\*?", " ", text)
    text = re.sub(r"[{}$&^_~\\]", " ", text)
    return re.sub(r"[ \t]+", " ", text)


def _unescape(tex: str) -> str:
    for code, char in _UNESCAPE.items():
        tex = tex.replace(code, char)
    return tex


def _compact(text: str) -> str:
    """比对 PDF 文字用：去掉空白和断行连字符，忽略大小写。"""
    return re.sub(r"[\s\u00ad\-‐‑]+", "", text).lower()


def _snippet(text: str, start: int, end: int, pad: int = 14) -> str:
    return re.sub(r"\s+", " ", text[max(0, start - pad):end + pad]).strip()


# ----------------------------------------------------------------------------- 检查对象
class Paper:
    """一次检查要读的东西；PDF 用到才打开。"""

    def __init__(self, workspace: Path):
        self.ws = Path(workspace)
        self.paper = self.ws / "paper"
        spec_doc = _load_json(self.ws / SPEC_RELATIVE)
        venue = spec_doc.get("venue") if isinstance(spec_doc, dict) else None
        self.venue = venue if isinstance(venue, dict) and venue.get("family") else None
        manifest = _load_json(self.ws / USER_TEMPLATE_RELATIVE)
        self.user_tpl = manifest if isinstance(manifest, dict) else None
        self.user_latex = bool(self.user_tpl and self.user_tpl.get("kind") == "latex"
                               and self.user_tpl.get("status") == "ready" and self.user_tpl.get("materialized"))
        self.rules = {r.get("key"): r for r in (self.venue or {}).get("rules") or [] if isinstance(r, dict)}
        self.sources = _tex_sources(self.paper)
        self.main_text = self.sources[0]["text"] if self.sources and self.sources[0]["rel"] == "main.tex" else ""
        self.pdf_path = self.paper / "main.pdf"
        self.log_text = _read(self.paper / "main.log")
        self._doc = None
        self._pdf_problem: str | None = None
        self._pages: list[str] | None = None

    # PDF ---------------------------------------------------------------------
    @property
    def doc(self):
        if self._doc is None and self._pdf_problem is None:
            if not self.pdf_path.is_file():
                self._pdf_problem = "没有 paper/main.pdf（编译没出 PDF），PDF 相关的项没法查"
            else:
                try:
                    import fitz  # PyMuPDF
                except ImportError:
                    self._pdf_problem = "本机没有 PyMuPDF，PDF 相关的项没法查"
                else:
                    try:
                        self._doc = fitz.open(str(self.pdf_path))
                    except Exception as exc:  # noqa: BLE001 — 坏 PDF 也只记一句
                        self._pdf_problem = f"PDF 打不开：{exc}"
        return self._doc

    @property
    def pdf_problem(self) -> str:
        return self._pdf_problem or ""

    def page_texts(self) -> list[str]:
        if self._pages is None:
            doc = self.doc
            self._pages = [page.get_text("text") for page in doc] if doc is not None else []
        return self._pages

    def close(self) -> None:
        if self._doc is not None:
            try:
                self._doc.close()
            except Exception:  # noqa: BLE001
                pass

    # 规格 ---------------------------------------------------------------------
    @property
    def family(self) -> str:
        return str((self.venue or {}).get("family") or "")

    @property
    def review_mode(self) -> str:
        return str((self.venue or {}).get("review_mode") or "")

    @property
    def language(self) -> str:
        lang = (self.venue or {}).get("language")
        if lang in ("zh", "en"):
            return lang
        body = "".join(_plain(_body(s["text"])) for s in self.sources)
        cjk = len(_CJK_CHAR_RE.findall(body))
        letters = len(re.findall(r"[A-Za-z]", body))
        return "zh" if cjk and cjk * 2 >= letters * 0.3 else "en"

    @property
    def columns(self) -> int:
        cols = (self.venue or {}).get("columns")
        if cols in (1, 2):
            return cols
        layout = (self.user_tpl or {}).get("layout") or {}
        return 2 if layout.get("columns") == 2 else 1

    def rule(self, key: str) -> dict | None:
        rule = self.rules.get(key)
        if not rule:
            return None
        return {k: rule.get(k) for k in ("text_zh", "source_url", "locator_zh", "accessed") if rule.get(k)}

    def body_sources(self) -> list[tuple[str, str]]:
        """（文件，正文文字）：main.tex 只取 \\begin{document} 之后。"""
        return [(s["rel"], _body(s["text"]) if s["rel"] == "main.tex" else s["text"]) for s in self.sources]


def _body(text: str) -> str:
    match = re.search(r"\\begin\{document\}", text)
    return text[match.end():] if match else text


def _item(key: str, title: str, status: str, summary: str, details=None, rule=None) -> dict:
    return {"key": key, "title": title, "status": status, "summary": summary,
            "details": [str(d)[:400] for d in (details or [])][:MAX_DETAILS], "rule": rule}


def _no_pdf(key: str, title: str, p: Paper, rule=None) -> dict:
    return _item(key, title, "skipped", p.pdf_problem or "PDF 没法读", rule=rule)


# ----------------------------------------------------------------------------- 1. 页数（只作参考）
def check_pages(p: Paper) -> dict:
    title = "页数（只作参考）"
    if p.doc is None:
        return _no_pdf("pages", title, p)
    total = p.doc.page_count
    ref_page = next((i + 1 for i, text in enumerate(p.page_texts()) if i > 0 and _REF_HEADING_RE.search(text)), None)
    parts = [f"共 {total} 页"]
    if ref_page:
        parts.append(f"正文到第 {ref_page} 页（参考文献从这一页开始）")
    venue = p.venue or {}
    target = venue.get("page_target") or (venue.get("page_reference") or {}).get("typical_pages")
    details = []
    if isinstance(target, int) and target > 0:
        parts.append(f"参考篇幅 {target} 页")
        compare = (ref_page or total)
        if compare > target:
            details.append(f"比参考篇幅多 {compare - target} 页：只作参考，不用为此删内容；以会议或期刊官网的要求为准。")
    note = (venue.get("page_reference") or {}).get("note_zh")
    if note:
        details.append(f"出版方的说法：{note}")
    return _item("pages", title, "info", "，".join(parts) + "。", details)


# ----------------------------------------------------------------------------- 2. 字体全嵌入
def check_fonts(p: Paper) -> dict | None:
    rule = p.rule("pdf_fonts_embedded")
    if rule is None:
        return None
    title = "字体全嵌入"
    if p.doc is None:
        return _no_pdf("fonts_embedded", title, p, rule)
    missing, type3, seen = set(), set(), set()
    for page in p.doc:
        for font in page.get_fonts(full=True):
            _xref, ext, ftype, basefont, name = font[:5]
            label = (basefont or name or "?").split("+")[-1]
            seen.add(label)
            if ftype == "Type3":
                type3.add(label)
            elif not ext or ext == "n/a":
                missing.add(label)
    if not missing and not type3:
        return _item("fonts_embedded", title, "ok", f"{len(seen)} 种字体都嵌入了（含子集嵌入）。", rule=rule)
    details = []
    if missing:
        details.append("没嵌入的字体：" + "、".join(sorted(missing)[:10])
                       + "。多半来自插图 PDF（作图软件导出时没嵌字体）：重新导出那几张图（matplotlib 设 "
                         "pdf.fonttype=42），或用 IEEE PDF eXpress 转换。")
    if type3:
        details.append("Type 3 字体：" + "、".join(sorted(type3)[:10])
                       + "。多半来自 matplotlib 默认设置（pdf.fonttype=3）或缺 Type 1 版的位图字体，IEEE 不收。")
    return _item("fonts_embedded", title, "issue", f"{len(missing) + len(type3)} 种字体不合要求。", details, rule)


# ----------------------------------------------------------------------------- 3. 书签和链接；PDF 版本与安全设置
def check_bookmarks_links(p: Paper) -> dict | None:
    rule = p.rule("pdf_no_bookmarks_links")
    if rule is None:
        return None
    title = "书签和链接"
    if p.doc is None:
        return _no_pdf("bookmarks_links", title, p, rule)
    toc = p.doc.get_toc(simple=True)
    links = []
    for pno, page in enumerate(p.doc, 1):
        for link in page.get_links():
            links.append((pno, link.get("uri") or (f"跳到第 {link.get('page', -1) + 1} 页" if "page" in link else "")))
    if not toc and not links:
        return _item("bookmarks_links", title, "ok", "没有书签，也没有链接。", rule=rule)
    details = []
    if toc:
        details.append(f"书签 {len(toc)} 个（一般是 hyperref 生成的），例如：" + "；".join(str(t[1]) for t in toc[:3]))
    if links:
        details.append(f"链接 {len(links)} 个，例如：" + "；".join(f"第 {pno} 页 {target}" for pno, target in links[:3]))
    details.append("IEEE 模板本身不加载 hyperref：看看正文或附加的宏包里是不是加了 \\usepackage{hyperref}，去掉后重新编译。")
    return _item("bookmarks_links", title, "issue", f"PDF 里有 {len(toc)} 个书签、{len(links)} 个链接。", details, rule)


def check_pdf_properties(p: Paper) -> dict | None:
    rules = [p.rule("pdf_version"), p.rule("pdf_not_encrypted")]
    rule = next((r for r in rules if r), None)
    if rule is None:
        return None
    title = "PDF 版本与安全设置"
    if p.doc is None:
        return _no_pdf("pdf_properties", title, p, rule)
    doc = p.doc
    problems = []
    version = str((doc.metadata or {}).get("format") or "")
    match = re.search(r"(\d+)\.(\d+)", version)
    if match and (int(match.group(1)), int(match.group(2))) < (1, 4):
        problems.append(f"PDF 版本是 {version}，低于 1.4")
    try:
        extensions = doc.xref_get_key(doc.pdf_catalog(), "Extensions")
        if extensions and extensions[0] != "null" and re.search(r"/ExtensionLevel\s+(?:[3-9]|1\d)", str(extensions[1])):
            problems.append("PDF 带 Adobe 扩展级别（Acrobat 9 及以上的格式），IEEE 不收")
    except Exception:  # noqa: BLE001 — 读不到扩展字典就当没有
        pass
    if doc.is_encrypted or doc.needs_pass:
        problems.append("PDF 设了密码或安全设置")
    try:
        if doc.embfile_count():
            problems.append(f"PDF 带了 {doc.embfile_count()} 个附件")
    except Exception:  # noqa: BLE001
        pass
    if problems:
        return _item("pdf_properties", title, "issue", "；".join(problems) + "。", rule=rule)
    return _item("pdf_properties", title, "ok", f"{version or 'PDF'}，没加密，没带附件。", rule=rule)


# ----------------------------------------------------------------------------- 4. 英文稿里的中文
def check_chinese(p: Paper) -> dict | None:
    if p.language != "en":
        return None
    title = "英文稿里的中文"
    rule = p.rule("language_english")
    hits = []
    for pno, text in enumerate(p.page_texts(), 1):
        for match in _CJK_RE.finditer(text):
            hits.append(f"PDF 第 {pno} 页：“{_snippet(text, match.start(), match.end())}”")
            break
    for rel, body in p.body_sources():
        for lineno, line in enumerate(body.split("\n"), 1):
            if _CJK_RE.search(line):
                hits.append(f"{rel} 第 {lineno} 行附近：{line.strip()[:80]}")
                break
    if not hits:
        extra = "" if p.doc is not None else "（PDF 没法读，只查了 .tex）"
        return _item("chinese_in_english", title, "ok", "正文和 PDF 里都没有中文字符或全角标点。" + extra, rule=rule)
    return _item("chinese_in_english", title, "issue", f"有 {len(hits)} 处中文字符或全角标点。",
                 hits + ["图片里的文字查不到：图里要是有中文，也要换成英文。"], rule)


# ----------------------------------------------------------------------------- 5. 匿名（双盲）
def check_anonymity(p: Paper) -> dict | None:
    if p.review_mode != "double_blind":
        return None
    title = "匿名（双盲送审）"
    problems, notes = [], []
    if "\\newif\\ifmhanonymous" in p.main_text and re.search(r"(?m)^\s*\\mhanonymousfalse\b", p.main_text):
        problems.append("main.tex 里的匿名开关还是 \\mhanonymousfalse：双盲送审要改成 \\mhanonymoustrue，才会隐去作者、单位和个人致谢")
    if p.doc is not None:
        author = str((p.doc.metadata or {}).get("author") or "").strip()
        if author:
            problems.append(f"PDF 属性里写着作者“{author[:60]}”（在 \\hypersetup 或 \\pdfinfo 里删掉）")
        first = p.page_texts()[0] if p.page_texts() else ""
        emails = sorted(set(_EMAIL_RE.findall(first)))
        if emails:
            problems.append("首页有邮箱：" + "、".join(emails[:4]))
        if _ORCID_RE.search(first):
            problems.append("首页有 ORCID 号")
    for rel, body in p.body_sources():
        plain = _plain(body)
        for match in _SELF_CITE_RE.finditer(plain):
            problems.append(f"{rel}：“{_snippet(plain, match.start(), match.end(), 24)}”——双盲稿里自引要用第三人称"
                            "（如 “Smith et al. [3] showed”），不说“我们之前的工作”")
            break
    if p.user_latex:
        ack = _section_text(p, re.compile(r"acknowledg|致谢|鸣谢", re.I))
        if ack and len(_plain(ack).strip()) > 20:
            notes.append("致谢里有内容：双盲送审时确认里面没有能认出你们的信息（基金号、课题组、合作者名字），"
                         "或者送审稿里先删掉致谢")
    if problems:
        return _item("anonymity", title, "issue", f"有 {len(problems)} 处可能暴露作者身份。", problems + notes,
                     p.rule("review_modes"))
    if notes:
        return _item("anonymity", title, "info", "没发现作者信息，有一处要你确认。", notes, p.rule("review_modes"))
    return _item("anonymity", title, "ok", "作者信息已隐去，没发现邮箱、PDF 作者属性或“我们之前的工作”一类写法。",
                 rule=p.rule("review_modes"))


def _section_text(p: Paper, title_re: re.Pattern) -> str:
    """标题匹配 title_re 的那一节的正文（到下一个标题或参考文献为止）。"""
    for _rel, body in p.body_sources():
        matches = list(_HEADING_RE.finditer(body))
        for i, match in enumerate(matches):
            name = match.group(1) or match.group(2) or match.group(3) or ""
            if title_re.search(name):
                end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
                chunk = body[match.end():end]
                chunk = re.split(r"\\bibliography\b|\\begin\{thebibliography\}|\\printbibliography", chunk)[0]
                return re.sub(r"\\IfFileExists\{[^{}]*ai_statement[^{}]*\}\{[^{}]*\}\{\}|\\input\{sections/ai_statement\}",
                              " ", chunk)
    return ""


# ----------------------------------------------------------------------------- 6. 模板没被改
def check_template_intact(p: Paper, ingest=None) -> dict:
    title = "模板没被改"
    template = (p.venue or {}).get("template") or {}
    files = template.get("files") or {}
    if files:
        changed, missing = [], []
        for name, digest in sorted(files.items()):
            path = p.paper / name
            if not path.is_file():
                missing.append(name)
            elif _file_hash(path) != digest:
                changed.append(name)
        if changed or missing:
            details = []
            if changed:
                details.append("和出版方原版不一样：" + "、".join(changed))
            if missing:
                details.append("paper/ 里没有：" + "、".join(missing))
            details.append(f"这些文件要和 {template.get('class') or '出版方'} 原版一字不差，投稿系统会用原版重新编译。")
            return _item("template_intact", title, "issue", "出版方的类文件或参考文献样式被改了。", details)
        return _item("template_intact", title, "ok",
                     f"{'、'.join(sorted(files))} 和出版方原版一致（{template.get('class_version') or '注册版本'}）。")
    if p.user_latex:
        if ingest is None:
            return _item("template_intact", title, "error", "检查未完成：找不到模板核对工具 template_ingest.py")
        report = ingest.verify(p.ws)
        errors = report.get("template", report.get("errors") or [])
        warnings = report.get("warnings") or []
        if errors:
            return _item("template_intact", title, "issue", "上传的模板被改了。", errors + warnings)
        if warnings:
            return _item("template_intact", title, "info", "模板文件没被改；导言区有新加的内容，请确认。", warnings)
        return _item("template_intact", title, "ok", "上传模板的类文件、宏包和导言区都没被改。",
                     report.get("info") or [])
    return _item("template_intact", title, "skipped", "没有用内置投稿模板或上传的 LaTeX 模板。")


# ----------------------------------------------------------------------------- 7. 样例文字残留与没填的占位
_CODE_PUNCT_RE = re.compile(r"[_{}()\[\]*/\\=<>+|~^%&@#$;]")
_WORD_RE = re.compile(r"[A-Za-z]{2,}")


def _is_code_fragment(inner: str) -> bool:
    """方括号里的内容若是代码，就别当成没填的占位。

    源码附录把 `\lstinputlisting` 的每一行原样印出来，于是列表推导式
    `[(v - lo) / rng for v in vals]`、正则字符类 `[A-Za-z0-9_]`、切片
    `[l * nf:(l + 1) * nf]` 全被 `_BRACKET_RE` 当成散文占位。
    判据：含代码标点（下划线/括号/星号/斜杠等）→ 代码；不含但连两个
    英文词都凑不出（`[None, :]`、`[ηmin, ηmax]`）→ 也不是散文占位。
    真正该报的是 `[problem statement in one clause]` 这种整句英文。
    """
    if " for " in inner and " in " in inner:
        return True
    # An all-caps token is a placeholder marker, not an identifier: [TODO],
    # [XXX], [TBD], [FIXME] are exactly what this check exists to catch. This
    # test has to come before the ast check, because "TODO" parses as a valid
    # Python identifier expression and would otherwise be waved through.
    if re.fullmatch(r"[A-Z]{2,}", inner.strip()):
        return False
    try:
        ast.parse(inner, mode="eval")
        return True
    except SyntaxError:
        pass
    if _CODE_PUNCT_RE.search(inner):
        return True
    # A bare comma-separated list of single identifiers is code too: PDF text
    # extraction turns `["dataset", "split"]` into `” dataset ”, ” split ”`, and
    # the quotes alone are not in _CODE_PUNCT_RE because they are also ordinary
    # prose punctuation. Every comma-separated token being one word is the
    # giveaway; a real placeholder such as `[problem statement in one clause]`
    # has multi-word tokens.
    tokens = [t.strip().strip("\"'`\u2018\u2019\u201c\u201d ") for t in inner.split(",")]
    if len(tokens) >= 2 and all(t and " " not in t for t in tokens):
        return True
    return len(_WORD_RE.findall(inner)) < 2


def _placeholders(text: str) -> list[str]:
    found = []
    for match in _BRACKET_RE.finditer(text):
        inner = match.group(1).strip()
        if not inner or _REF_TYPE_RE.match(inner) or _YEAR_RE.search(inner) or inner.lower() in ("online", "in press"):
            continue
        if _is_code_fragment(inner):
            continue
        if inner.lower().startswith("disclosure of interests"):
            continue  # Springer 会议录的利益冲突占位，“利益冲突声明”那一项单独报
        if re.fullmatch(r"[\d\s,.;:–—~\-]+", inner):
            continue
        weight = len(re.findall(r"[A-Za-z]", inner)) + 2 * len(_CJK_CHAR_RE.findall(inner))
        if weight < 3:
            continue
        if not (" " in inner or _CJK_CHAR_RE.search(inner) or re.search(r"[a-z][A-Z]|\d", inner)):
            continue
        found.append(inner)
    return found


_FRONT_MATTER_PREFIXES = ("中图分类号", "文献标识码", "文章编号", "收稿日期", "基金项目", "作者简介")


def check_sample_residue(p: Paper, ingest=None) -> dict:
    title = "样例文字与没填的占位"
    problems = []
    if p.user_latex and ingest is not None:
        report = ingest.verify(p.ws)
        problems += report.get("residue", [])
    body = "\n".join(_plain(body) for _rel, body in p.body_sources()).lower()
    for marker in _SAMPLE_MARKERS:
        if marker in body:
            problems.append(f"还留着样例文字“{marker}”")
    holes: list[str] = []
    for text in p.page_texts():
        for inner in _placeholders(text):
            line_start = text.rfind("\n", 0, text.find("[" + inner))
            context = text[line_start + 1:text.find("[" + inner)]
            if any(context.rstrip().endswith(prefix + "：") or prefix in context[-12:] for prefix in _FRONT_MATTER_PREFIXES):
                continue  # 中文期刊要素单列一项
            if inner not in holes:
                holes.append(inner)
    if holes:
        personal = [h for h in holes if _PERSONAL_HINT_RE.search(h)]
        other = [h for h in holes if h not in personal]
        if other:
            problems.append("PDF 里还有没替换的占位：" + "、".join(f"[{h}]" for h in other[:8]))
        if personal:
            problems.append("作者、单位、基金这类要你自己填的占位还没填（软件不编）：" + "、".join(f"[{h}]" for h in personal[:8]))
    if problems:
        return _item("sample_residue", title, "issue", f"有 {len(problems)} 类没换掉的样例文字或占位。", problems)
    if p.doc is None:
        return _item("sample_residue", title, "ok", "源文件里没有样例文字（PDF 没法读，占位没查）。")
    return _item("sample_residue", title, "ok", "没有样例文字，也没有没填的方括号占位。")


# ----------------------------------------------------------------------------- 8. 中文期刊要素
def check_cn_front_matter(p: Paper) -> dict | None:
    if p.family != "cn_journal":
        return None
    title = "中文期刊要素"
    if p.doc is None:
        return _no_pdf("cn_front_matter", title, p, p.rule("front_matter"))
    first = "\n".join(p.page_texts()[:2])
    wanted = list(_FRONT_MATTER_PREFIXES)
    if p.review_mode == "double_blind":
        wanted = [w for w in wanted if w not in ("收稿日期", "基金项目", "作者简介")]
    unfilled = []
    for prefix in wanted:
        match = re.search(re.escape(prefix) + r"\s*[：:]\s*(\[[^\]\n]*\])", first)
        if match:
            unfilled.append(f"{prefix}：{match.group(1)}")
    if unfilled:
        return _item("cn_front_matter", title, "issue", f"{len(unfilled)} 项还是占位，要你自己填。",
                     unfilled + ["分类号、文献标识码、基金编号、作者简介软件不替你填；目标期刊不要的项，整行删掉。"],
                     p.rule("front_matter"))
    return _item("cn_front_matter", title, "ok", "首页的分类号、文献标识码、基金、作者简介等都填了（或按期刊要求删了）。",
                 rule=p.rule("front_matter"))


# ----------------------------------------------------------------------------- 9. AI 使用声明
def _ai_models(summary_md: str) -> list[str]:
    match = re.search(r"(?m)^- 模型：(.+)$", summary_md)
    if not match or "没有记录" in match.group(1):
        return []
    return [m.strip() for m in match.group(1).split("、") if m.strip()]


def _statement_context(p: Paper) -> tuple[str, int, str] | None:
    """(所在文件, 位置, 前面最近的标题)：\\input{sections/ai_statement} 在哪。"""
    for rel, body in p.body_sources():
        match = re.search(r"\\(?:input|include)\s*\{sections/ai_statement(?:\.tex)?\}", body)
        if not match:
            continue
        heading = ""
        for head in _HEADING_RE.finditer(body[:match.start()]):
            heading = head.group(1) or head.group(2) or head.group(3) or ""
        return rel, match.start(), heading
    return None


def check_ai_statement(p: Paper) -> dict:
    title = "AI 使用声明"
    location = ((p.venue or {}).get("ai_statement") or {}).get("location") or ("unspecified" if p.venue else "")
    summary_md = _read(p.ws / AI_SUMMARY_RELATIVE)
    statement = p.paper / STATEMENT_REL
    if not statement.is_file():
        if not summary_md:
            return _item("ai_statement", title, "info",
                         "没有运行记录，软件没生成 AI 使用声明；你另外用过 AI 工具的话，按投稿要求自己写。")
        return _item("ai_statement", title, "issue", f"声明文件 paper/{STATEMENT_REL} 不见了（软件写过，后来被删了）。")
    problems, notes = [], []
    context = _statement_context(p)
    raw = _read(statement)
    plain = _unescape(re.sub(r"(?m)^\s*%.*$", "", raw)).strip()
    if context is None:
        problems.append(f"写好了 paper/{STATEMENT_REL}，但论文里没有 \\input{{sections/ai_statement}}，PDF 里没有这段声明")
    else:
        rel, _pos, heading = context
        want = _LOCATION_ZH.get(location, "")
        ok_place = {
            "acknowledgment": bool(re.search(r"acknowledg|致谢|鸣谢", heading, re.I)),
            "separate_section": bool(_AI_WORD_RE.search(heading)) or bool(re.search(r"\\section", raw)),
            "footnote_and_end": bool(_AI_WORD_RE.search(heading)) or "credits" in heading,
            "methods_or_appendix": bool(re.search(r"method|appendix|方法|附录", heading, re.I) or heading == "appendix"),
            "methods_or_alternative": True, "methods_or_acknowledgment": True, "unspecified": True, "": True,
        }.get(location, True)
        if not ok_place:
            problems.append(f"声明放在“{heading or '正文开头'}”下面（{rel}），出版方要求放在{want}")
        if location == "footnote_and_end" and (p.paper / FOOTNOTE_REL).is_file():
            if not any(re.search(r"sections/ai_footnote", body) for _r, body in p.body_sources()):
                problems.append(f"首页脚注 paper/{FOOTNOTE_REL} 写好了，但论文里没引用它")
    models = _ai_models(summary_md)
    missing = [m for m in models if m not in plain]
    if missing:
        problems.append("运行记录里用过、声明里没写的模型：" + "、".join(missing))
    if p.doc is not None and context is not None and plain:
        pdf_text = _compact("\n".join(p.page_texts()))
        probe = _compact(plain)[:40]
        if probe and probe not in pdf_text:
            problems.append("PDF 里找不到这段声明（看看编译时是不是被条件开关跳过了）")
    record = _load_json(p.ws / AI_RECORD_RELATIVE) or {}
    digest = hashlib.sha256(statement.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if isinstance(record, dict) and record.get(STATEMENT_REL) and record.get(STATEMENT_REL) != digest:
        notes.append("你改过这段声明（软件不会覆盖）；只核对了位置和有没有漏掉运行记录里的模型。")
    notes.append("声明只写了本软件的使用；你自己另外用过的 AI 工具（翻译、润色、检索等）请补上。")
    rule = {k: ((p.venue or {}).get("ai_statement") or {}).get(k)
            for k in ("text_zh", "source_url", "locator_zh", "accessed")
            if ((p.venue or {}).get("ai_statement") or {}).get(k)} or None
    if problems:
        return _item("ai_statement", title, "issue", f"有 {len(problems)} 处要处理。", problems + notes, rule)
    where = _LOCATION_ZH.get(location, "")
    return _item("ai_statement", title, "ok",
                 f"声明写了{('，放在' + where) if where and location != 'unspecified' else ''}，运行记录里的模型都写到了。",
                 notes, rule)


# ----------------------------------------------------------------------------- 10. 图表出栏
def _near(counter: Counter, value: int) -> int:
    return counter[value - 1] + counter[value] + counter[value + 1]


def _left_edge(counter: Counter) -> float | None:
    """至少一成的长行从这里起的最左值。"""
    total = sum(counter.values())
    if total < 5:
        return None
    ok = [v for v in counter if _near(counter, v) >= 0.1 * total]
    return float(min(ok)) - 1.0 if ok else None


def _right_edge(counter: Counter) -> float | None:
    """至少一成的长行到这里止的最右值。"""
    total = sum(counter.values())
    if total < 5:
        return None
    ok = [v for v in counter if _near(counter, v) >= 0.1 * total]
    return float(max(ok)) + 1.0 if ok else None


def _layout(doc, textwidth: float | None = None, columns: int = 1) -> dict | None:
    """版心：{"pages": [(左, 右), …], "right_col": 右栏起点或 None}。

    左右边界从正文长行推（奇偶页分开：双面排版左右页边不一样）；知道确切的版心宽（textwidth，PDF 点）时右边界 = 左 + 宽；
    双栏而右栏空着（短稿）时，正文行只推得出左栏，才拿“左右页边对称”兜底。
    """
    pages_lefts: list[Counter] = []
    parity = {0: Counter(), 1: Counter()}
    parity_right = {0: Counter(), 1: Counter()}
    every = Counter()
    every_right = Counter()
    starts = Counter()
    for pno, page in enumerate(doc):
        lefts = Counter()
        min_width = 0.3 * page.rect.width  # 按行宽筛：中文双栏一行只有二十来个字，按字数会漏掉
        for block in page.get_text("dict").get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                x0, _y0, x1, _y1 = line["bbox"]
                if x1 - x0 >= min_width:  # 页眉页码、行号、公式编号、段落末行这类短行不算
                    lefts[round(x0)] += 1
                    starts[round(x0)] += 1
                    parity_right[pno % 2][round(x1)] += 1
                    every_right[round(x1)] += 1
        pages_lefts.append(lefts)
        parity[pno % 2].update(lefts)
        every.update(lefts)
    overall, overall_right = _left_edge(every), _right_edge(every_right)
    if overall is None or overall_right is None:
        return None
    total = sum(starts.values())
    centre = (overall + overall_right) / 2
    second = [v for v in starts if v > centre and _near(starts, v) >= 0.1 * total]
    right_col = float(min(second)) if second else None
    bounds = []
    for pno, page in enumerate(doc):
        left = _left_edge(parity[pno % 2]) or overall
        if textwidth and textwidth > 100:
            right = left + textwidth + 2.0
        else:
            right = _right_edge(parity_right[pno % 2]) or overall_right
            if columns == 2 and right_col is None:
                right = max(right, page.rect.width - left)  # 右栏空着：正文行只推得出左栏
        if right - left <= 100:
            return None
        bounds.append((left, right))
    return {"pages": bounds, "right_col": right_col}


def _text_area(doc, textwidth: float | None = None, columns: int = 1) -> tuple[float, float] | None:
    layout = _layout(doc, textwidth, columns)
    return None if layout is None else layout["pages"][0]


def _known_textwidth(p: "Paper") -> float | None:
    """确切的版心宽（PDF 点）：编译日志里内置模板写的 \\textwidth，或上传模板试编译量到的。"""
    match = re.search(r"(?m)^\* \\textwidth=([0-9.]+)pt", p.log_text)
    if match:
        return float(match.group(1)) * 72 / 72.27
    layout = (p.user_tpl or {}).get("layout") or {}
    if p.user_latex and isinstance(layout.get("textwidth_in"), (int, float)):
        return float(layout["textwidth_in"]) * 72
    return None


def _body_lines(page, min_width: float) -> list[tuple[float, float, float, float]]:
    out = []
    for block in page.get_text("dict").get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            x0, y0, x1, y1 = line["bbox"]
            if x1 - x0 >= min_width:
                out.append((x0, y0, x1, y1))
    return out


_OVERFULL_RE = re.compile(r"Overfull \\hbox \(([0-9.]+)pt too wide\) (?:in paragraph|in alignment|detected) at lines? (\d+)(?:--(\d+))?")


def check_overflow(p: Paper) -> dict:
    title = "图表出栏"
    details, issue = [], False
    if p.doc is not None:
        layout = _layout(p.doc, _known_textwidth(p), p.columns)
        if layout is None:
            details.append("正文行太少，推不出版心，PDF 里没量")
        else:
            right_col = layout["right_col"]
            tol = 1.5
            for pno, page in enumerate(p.doc, 1):
                left, right = layout["pages"][pno - 1]
                mid = (left + right) / 2
                colw = (right - left) / 2
                out, worst, cross = 0, 0.0, 0
                ops = [(kind, rect) for kind, rect in page.get_bboxlog()
                       if kind.startswith(("fill-", "stroke-")) and rect[2] - rect[0] >= 1.0]
                two_col = p.columns == 2 and right_col is not None
                lines = _body_lines(page, 0.6 * colw) if two_col else []

                def beside(y0: float, y1: float) -> bool:
                    # 同一高度、从右栏起点开始的一整行正文：说明这个元素压进了右栏的正文
                    return any(abs(lx0 - right_col) <= 3 and ly0 < y1 - 2 and ly1 > y0 + 2
                               for lx0, ly0, _lx1, ly1 in lines)

                bands = []  # 真通栏元素（figure*、table*，旁边没有正文）占的高度：里面的线段再窄也不算压栏
                for kind, rect in ops:
                    x0, y0, x1, y1 = rect
                    if two_col and "text" not in kind and x1 - x0 > 1.2 * colw and not beside(y0, y1):
                        bands.append((y0 - 2, y1 + 2))
                for kind, rect in ops:
                    x0, y0, x1, y1 = rect
                    over = max(x1 - right, left - x0)
                    is_text = "text" in kind
                    if over > tol and (not is_text or x1 - x0 > 15):  # 窄的文字是行号、页边标记，不算
                        out += 1
                        worst = max(worst, over)
                    elif (two_col and not is_text and x0 < mid - 3 and x1 > mid + 3 and min(mid - x0, x1 - mid) > 6
                          and not any(b0 <= y0 and y1 <= b1 for b0, b1 in bands)
                          and (x1 - x0 < 1.2 * colw or beside(y0, y1))):
                        cross += 1
                if out:
                    issue = True
                    details.append(f"第 {pno} 页有 {out} 个元素冲出版心，最多超出 {worst:.1f}pt")
                if cross:
                    issue = True
                    details.append(f"第 {pno} 页有 {cross} 个栏内元素压到另一栏")
    else:
        details.append(p.pdf_problem)
    overfull = []
    for match in _OVERFULL_RE.finditer(p.log_text):
        width = float(match.group(1))
        if width > 1.0:
            overfull.append((width, match.group(2), match.group(3) or match.group(2)))
    if overfull:
        overfull.sort(reverse=True)
        details.append(f"编译日志里有 {len(overfull)} 处行宽超出 1pt 以上（Overfull \\hbox），最大的："
                       + "；".join(f"{w:.1f}pt（第 {a}–{b} 行）" for w, a, b in overfull[:3]))
        issue = issue or overfull[0][0] > 10.0
    if issue:
        details.append("栏内的图写 width=\\linewidth（双栏里就是栏宽），通栏图（figure*）写 width=\\textwidth；"
                       "宽表放 table* 通栏或缩小字号。")
        return _item("overflow", title, "issue", "有元素超出栏宽或版心。", details)
    if overfull:
        return _item("overflow", title, "info", "图表没出栏；有几行文字略宽（10pt 以内）。", details)
    if p.doc is None:
        return _item("overflow", title, "skipped", p.pdf_problem)
    return _item("overflow", title, "ok", "图表和文字都在版心里，没有压到另一栏。", details)


# ----------------------------------------------------------------------------- 11. 参考文献可核验
def check_references(p: Paper) -> dict:
    title = "参考文献核验"
    data = _load_json(p.ws / REFERENCE_CHECK_RELATIVE)
    if isinstance(data, dict) and isinstance(data.get("entries"), list):
        bad = [e for e in data["entries"] if isinstance(e, dict) and e.get("status") not in ("verified", "ok")]
        if bad:
            return _item("references", title, "issue", f"{len(bad)} 条文献没核验通过。",
                         [str(e.get("key") or e.get("title") or "?") for e in bad[:MAX_DETAILS]])
        return _item("references", title, "ok", f"{len(data['entries'])} 条文献都核验过。")
    return _item("references", title, "info", "文献核验还没上线：参考文献未核验（这里不算通过）。",
                 ["投稿前请自己核对每条文献都查得到，作者、年份、卷期、页码和 DOI 对得上。"])


# ----------------------------------------------------------------------------- 12. 替代文本
def check_alt_text(p: Paper) -> dict | None:
    rule = p.rule("alt_text")
    if rule is None:
        return None
    title = "图的替代文本"
    figures = sum(len(re.findall(r"\\begin\{figure\*?\}", body)) for _rel, body in p.body_sources())
    if not figures:
        return _item("alt_text", title, "skipped", "论文里没有插图。", rule=rule)
    path = p.paper / ALT_TEXT_NAME
    if not path.is_file():
        return _item("alt_text", title, "issue", f"有 {figures} 张图，但没有 paper/{ALT_TEXT_NAME}。",
                     ["每张图按图号写一句客观的替代文本（只描述图里画了什么，不写结论）。"], rule)
    numbers = {int(n) for n in re.findall(r"(?mi)^\s*(?:[-*]\s*)?(?:\*\*)?(?:fig(?:ure)?\.?\s*|图\s*)(\d+)", _read(path))}
    missing = [n for n in range(1, figures + 1) if n not in numbers]
    if missing:
        return _item("alt_text", title, "issue", f"{len(missing)} 张图没写替代文本。",
                     ["缺：" + "、".join(f"图 {n}" for n in missing[:20])], rule)
    return _item("alt_text", title, "ok", f"{figures} 张图都写了替代文本。", rule=rule)


# ----------------------------------------------------------------------------- 13. 作者栏里没有 AI
_AUTHOR_MACROS = ("author", "IEEEauthorblockN", "IEEEauthorblockA", "affiliation", "address", "institute", "email")


def _author_text(p: Paper) -> str:
    text = p.main_text
    chunks = []
    for macro in _AUTHOR_MACROS:
        for match in re.finditer(r"\\" + macro + r"\*?\s*(?:\[[^\]]*\])?\s*\{", text):
            depth, i = 1, match.end()
            while i < len(text) and depth:
                depth += {"{": 1, "}": -1}.get(text[i], 0)
                i += 1
            chunks.append(text[match.end():i - 1])
    if p.doc is not None and p.page_texts():
        first = p.page_texts()[0]
        cut = re.search(r"(?im)^\s*(?:abstract|摘\s*要)", first)
        head = first[:cut.start()] if cut else first[:600]
        chunks.append(head)
    return "\n".join(chunks)


def check_ai_not_author(p: Paper) -> dict:
    title = "作者栏里没有 AI"
    rule = p.rule("ai_not_author")
    text = _author_text(p)
    hits = sorted({m.group(0).strip() for m in _AI_NAME_RE.finditer(text)})
    if hits:
        return _item("ai_not_author", title, "issue", "作者或单位里出现了 AI 工具或模型：" + "、".join(hits[:6]) + "。",
                     ["AI 不能当作者，也不能写进单位或通讯信息；用到 AI 的情况写在 AI 使用声明里。"], rule)
    return _item("ai_not_author", title, "ok", "作者和单位里没有 AI 工具或模型的名字。", rule=rule)


# ----------------------------------------------------------------------------- 利益冲突声明（Springer 会议录）
def check_disclosure(p: Paper) -> dict | None:
    rule = p.rule("disclosure_of_interests")
    if rule is None:
        return None
    title = "利益冲突声明"
    placeholder = "Disclosure of interests: state any competing interests"
    text = "\n".join(p.page_texts())
    path = p.paper / "sections" / "disclosure.tex"
    if (p.doc is not None and placeholder.lower() in text.lower()) or not path.is_file():
        return _item("disclosure", title, "issue", "还没写利益冲突声明（PDF 里印着占位）。",
                     ["写进 paper/sections/disclosure.tex：没有利益冲突也要写明（例如 “The authors have no competing "
                      "interests to declare that are relevant to the content of this article.”）。软件不替作者做这项声明。"], rule)
    return _item("disclosure", title, "ok", "写了利益冲突声明。", rule=rule)


# ----------------------------------------------------------------------------- 14. 作者指南与其他规则
_GUIDE_ITEMS = ("正文和摘要的字数上限", "图、表、参考文献的数量上限", "关键词个数", "投稿系统要的文件格式（PDF / 源文件 / Word）",
                "投稿信（cover letter）", "Highlights、图文摘要（graphical abstract）", "数据与代码可得性声明",
                "作者贡献（CRediT）、基金和利益冲突声明的写法", "补充材料的格式和大小", "版面费、开放获取等费用")


def check_author_guide(p: Paper) -> dict | None:
    guides = sorted(p.ws.glob("user_data/GUIDE.*"))
    cfp = (p.ws / "VENUE_CFP.md").is_file()
    if not guides and not cfp:
        return None
    where = "、".join([g.relative_to(p.ws).as_posix() for g in guides] + (["VENUE_CFP.md"] if cfp else []))
    return _item("author_guide", "要你对照作者指南核的项", "info",
                 f"你上传了作者指南或征稿通知（{where}），下面这些软件没法自动核，请对照着检查。",
                 list(_GUIDE_ITEMS))


def check_other_rules(p: Paper) -> dict | None:
    left = [r for key, r in p.rules.items() if key not in _AUTO_RULES]
    if not left:
        return None
    details = []
    for rule in left:
        source = f"（出处：{rule.get('source_url')}，{rule.get('locator_zh') or ''}）" if rule.get("source_url") else ""
        details.append(f"{rule.get('text_zh')}{source}")
    return _item("other_rules", "要你对照官网核的规则", "info",
                 f"{(p.venue or {}).get('label_zh') or '这个投稿格式'}还有 {len(left)} 条要求软件没法自动核。", details)


# ----------------------------------------------------------------------------- 汇总
def _checks(ingest):
    return [
        ("pages", check_pages), ("fonts_embedded", check_fonts), ("bookmarks_links", check_bookmarks_links),
        ("pdf_properties", check_pdf_properties), ("chinese_in_english", check_chinese),
        ("anonymity", check_anonymity), ("template_intact", lambda p: check_template_intact(p, ingest)),
        ("sample_residue", lambda p: check_sample_residue(p, ingest)), ("cn_front_matter", check_cn_front_matter),
        ("ai_statement", check_ai_statement), ("overflow", check_overflow), ("references", check_references),
        ("alt_text", check_alt_text), ("ai_not_author", check_ai_not_author), ("disclosure", check_disclosure),
        ("author_guide", check_author_guide), ("other_rules", check_other_rules),
    ]


def _ingest_module():
    here = Path(__file__).resolve().parent
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))  # 嵌入版运行时不把脚本目录加进 sys.path
    try:
        import template_ingest  # noqa: PLC0415
    except ImportError:
        return None
    return template_ingest


def applies(workspace: Path) -> bool:
    """有投稿格式规格或生效的上传 LaTeX 模板才查。"""
    paper = Paper(workspace)
    return bool(paper.venue) or paper.user_latex


def run(workspace: Path, *, now: str | None = None) -> dict:
    p = Paper(workspace)
    ingest = _ingest_module()
    items = []
    try:
        for key, check in _checks(ingest):
            try:
                item = check(p)
            except Exception as exc:  # noqa: BLE001 — 一项出错不连累别的项
                item = _item(key, key, "error", f"检查未完成：{exc.__class__.__name__}: {str(exc)[:200]}")
            if item:
                items.append(item)
        pages = p.doc.page_count if p.doc is not None else None
    finally:
        p.close()
    counts = Counter(item["status"] for item in items)
    venue = p.venue or {}
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now or datetime.now().strftime("%Y-%m-%d %H:%M"),
        "generated_epoch": time.time(),
        "venue": {"family": venue.get("family") or "", "label_zh": venue.get("label_zh") or "",
                  "review_mode": venue.get("review_mode") or "", "language": p.language,
                  "user_template": p.user_latex},
        "pdf": "paper/main.pdf" if p.pdf_path.is_file() else None,
        "pages": pages,
        "counts": {status: counts.get(status, 0) for status in STATUSES},
        "items": items,
    }


def render_markdown(result: dict) -> str:
    venue = result.get("venue") or {}
    counts = result.get("counts") or {}
    label = venue.get("label_zh") or ("上传的 LaTeX 模板" if venue.get("user_template") else "（没选投稿格式）")
    mode = {"double_blind": "双盲", "single_blind": "单盲", "open": "公开评审"}.get(venue.get("review_mode"), "")
    lines = [
        "# 投稿前检查（软件自动核对，只报告、不改稿）",
        "",
        f"- 时间：{result.get('generated_at')}",
        f"- 投稿格式：{label}{('（' + mode + '）') if mode else ''}",
        f"- 稿件：{result.get('pdf') or '没有 PDF'}" + (f"，{result['pages']} 页" if result.get("pages") else ""),
        f"- 结论：**{counts.get('issue', 0)} 项要你处理**，{counts.get('info', 0)} 项提醒，"
        f"{counts.get('ok', 0)} 项通过，{counts.get('skipped', 0)} 项不适用或没法查"
        + (f"，{counts['error']} 项检查未完成" if counts.get("error") else "") + "。",
        "",
        "> 软件不会自动改稿；改完重新编译，会再查一遍。页数只作参考，超出不用删内容。",
        "",
    ]
    for status in STATUSES:
        group = [item for item in result.get("items") or [] if item["status"] == status]
        if not group:
            continue
        lines += [f"## {STATUS_ZH[status]}（{len(group)}）", ""]
        for item in group:
            lines.append(f"### {item['title']}")
            lines.append("")
            lines.append(item["summary"])
            for detail in item.get("details") or []:
                lines.append(f"- {detail}")
            rule = item.get("rule") or {}
            if rule.get("source_url"):
                lines.append(f"- 依据：{rule.get('text_zh') or ''}（{rule.get('source_url')}"
                             f"{'，' + rule['locator_zh'] if rule.get('locator_zh') else ''}"
                             f"{'，访问于 ' + rule['accessed'] if rule.get('accessed') else ''}）")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_reports(workspace: Path, result: dict) -> None:
    workspace = Path(workspace)
    target = workspace / JSON_RELATIVE
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(target)
    (workspace / REPORT_NAME).write_text(render_markdown(result), encoding="utf-8")


def _main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    workspace = Path(argv[0])
    result = run(workspace)
    if "--json" in argv:
        print(json.dumps(result, ensure_ascii=False, indent=1))
    else:
        write_reports(workspace, result)
        print(render_markdown(result))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(_main(sys.argv[1:]))
