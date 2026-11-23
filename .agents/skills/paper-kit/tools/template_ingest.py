#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""用户上传的论文模板：认主文件、收依赖、判编译方式、试编译；写好论文后核对模板有没有被改坏。

投稿格式库 1C（2026-10-11）。后台 services/user_template.py 上传时调用 scan / choose / trial_compile，
写作步调用 materialize；编译步在技能里跑 ``python _utils/template_ingest.py verify``。只用标准库。

规则（规划 01_详细施工规划.md 的 U1–U3）：
  - 主文件：同时有 \documentclass 和 \begin{document} 的 .tex。有多个时按文件名（template、main、sample
    这类加分，doc、manual、guide、test 这类减分）、谁 \input 了谁、用没用包里自带的类文件排序；
    排不出唯一的就请用户选，不猜。
  - 编译方式：主文件和包里的类文件、宏包用了 fontspec、xeCJK、ctex、unicode-math 等用 xelatex，
    luatexja 等用 lualatex，否则 pdflatex；文件头的 ``% !TEX program = ...`` 也认。biblatex 记下后端（默认 biber）。
  - 试编译只在临时目录里做：-no-shell-escape；MiKTeX 上缺的宏包按调用方的设置联网自动装（-enable-installer，
    后台默认这样，用户 10-11 定，和内置模板一样）或不装（-disable-installer，命令行入口默认）；插图按草稿框排
    （样例里的 EPS 图在禁用外部命令时转不了，不影响版式）。缺的宏包逐个记下：临时目录里放个空壳接着往下找，
    用户的模板目录里不留任何东西。
  - 放进 paper/ 时保留原文件名和子目录，只把主文件改名为 main.tex（整条流水线都认 main.tex）；
    主文件不是 UTF-8 时转成 UTF-8（内容不变）。

用法：
  python template_ingest.py inspect <模板目录> [--main 相对路径] [--trial]   → 打印识别结果（JSON）
  python template_ingest.py verify [工作区]                                 → 编译步核对模板（有错误时退出码 1）
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path, PurePosixPath

SCHEMA_VERSION = 1
STORE_DIR = "user_template"
MANIFEST_RELATIVE = PurePosixPath(".mh") / "user_template.json"
REPORT_NAME = "模板识别报告.md"
MAIN_NAME = "main.tex"
ENGINES = ("pdflatex", "xelatex", "lualatex")
BIB_ENGINES = ("bibtex", "biber", "none")

_TEX = {".tex", ".ltx"}
_CLASS = {".cls"}
_STYLE = {".sty", ".clo", ".cfg", ".def", ".fd", ".ldf"}
_BIBSTYLE = {".bst", ".bbx", ".cbx", ".dbx", ".lbx"}
_FONT = {".otf", ".ttf", ".ttc", ".pfb", ".pfm", ".afm", ".tfm", ".vf", ".map", ".enc"}
_IMAGE = {".png", ".jpg", ".jpeg", ".pdf", ".eps", ".ps", ".gif", ".bmp", ".tif", ".tiff", ".svg", ".mps",
          ".jbig2", ".jb2"}
_SOURCE = {".dtx", ".ins"}
_WORD = {".docx", ".dotx"}
WORD_MACRO = {".docm": ".docx", ".dotm": ".dotx"}
_ARCHIVE = (".zip", ".tar", ".tgz", ".tar.gz", ".tbz2", ".tar.bz2", ".txz", ".tar.xz", ".gz", ".bz2", ".xz",
            ".rar", ".7z")
_BUILD = {".aux", ".log", ".blg", ".bbl", ".out", ".toc", ".lof", ".lot", ".fls", ".fdb_latexmk", ".bcf", ".xdv",
          ".dvi", ".nav", ".snm", ".vrb", ".idx", ".ilg", ".ind", ".glo", ".gls", ".glg", ".pag", ".spl", ".brf",
          ".thm", ".loa", ".lol", ".synctex"}
_BUILD_TAILS = (".synctex.gz", ".run.xml", "-blx.bib")
_JUNK = {".ds_store", "thumbs.db", "desktop.ini", "长文件名对照.csv", REPORT_NAME.lower()}
_DOC_TEXT = {".txt", ".md", ".html", ".htm", ".rtf"}
# 写好的论文里不许动的模板文件：类文件、宏包、参考文献样式、字体（样例图、样例 .bib、子 .tex 是样例内容，可以换）
PROTECTED = _CLASS | _STYLE | _BIBSTYLE | _FONT

_DOC_STEM_RE = re.compile(r"(?i)(doc|manual|guide|howto|readme|instruction|changelog|history|testflow|userguide)")
_TEMPLATE_STEM_RE = re.compile(
    r"(?i)(template|sample|main|paper|article|manuscript|bare|demo|example|conf|jrnl|journal|thesis|submission)")
_DOC_DIRS = {"doc", "docs", "documentation", "manual", "manuals", "guide", "guides", "testflow", "test", "tests"}
_MAC_VARIANT_RE = re.compile(r"(?i)(?:^|[-_ .])mac(?:os|osx)?(?:$|[-_ .])")
_LICENSE_RE = re.compile(r"(?i)^(license|licence|copying|lppl)")
_STANDARD_CLASSES = {
    "article", "report", "book", "letter", "slides", "proc", "minimal", "amsart", "amsbook", "amsproc",
    "scrartcl", "scrreprt", "scrbook", "memoir", "beamer", "ctexart", "ctexrep", "ctexbook", "ctexbeamer",
    "revtex4-1", "revtex4-2", "IEEEtran", "llncs", "elsarticle", "acmart", "svjour3",
}
_XE_PACKAGES = {"fontspec", "xecjk", "unicode-math", "polyglossia", "xltxtra", "xunicode", "ctex", "xecjkfntef",
                "ctexcap", "ctexheading", "ctexsize", "zhspacing"}
_LUA_PACKAGES = {"luatexja", "luatexja-fontspec", "luatexja-preset", "luacode", "luaotfload", "luatexbase"}
_XE_CLASSES = {"ctexart", "ctexrep", "ctexbook", "ctexbeamer"}
_LUA_CLASSES = {"ltjsarticle", "ltjarticle", "ltjsbook", "ltjbook", "ltjsreport", "ltjreport"}
_ACMART_TWOCOL = {"sigconf", "sigplan", "siggraph", "sigchi", "sigchi-a", "acmtog"}

_COMMENT_RE = re.compile(r"(?<!\\)%.*")
_DOCCLASS_RE = re.compile(r"\\documentclass\s*(?:\[([^\]]*)\])?\s*\{([^}]*)\}")
_BEGIN_DOC_RE = re.compile(r"\\begin\s*\{document\}")
_END_DOC_RE = re.compile(r"\\end\s*\{document\}")
_PKG_RE = re.compile(r"\\(?:usepackage|RequirePackage|RequirePackageWithOptions)\s*(?:\[([^\]]*)\])?\s*\{([^}]*)\}")
_LOADCLASS_RE = re.compile(r"\\LoadClass(?:WithOptions)?\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}")
_INPUT_RE = re.compile(r"\\(?:input|include|subfile)\s*\{([^}]*)\}")
_INPUT_BARE_RE = re.compile(r"\\input\s+([A-Za-z0-9_./-]+)")
_IMPORT_RE = re.compile(r"\\(?:sub)?import\*?\s*\{([^}]*)\}\s*\{([^}]*)\}")
_GRAPHICS_RE = re.compile(r"\\includegraphics\s*\*?\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}")
_GRAPHICSPATH_RE = re.compile(r"\\graphicspath\s*\{((?:\s*\{[^{}]*\})+)\s*\}")
_BIBSTYLE_RE = re.compile(r"\\bibliographystyle\s*\{([^}]*)\}")
_BIBDATA_RE = re.compile(r"\\bibliography\s*\{([^}]*)\}")
_ADDBIB_RE = re.compile(r"\\addbibresource\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}")
_THEBIB_RE = re.compile(r"\\begin\s*\{thebibliography\}")
_MAGIC_RE = re.compile(r"(?im)^\s*%+\s*!\s*TeX\s+(?:TS-)?program\s*=\s*([A-Za-z]+)")
_FONT_CMD_RE = re.compile(r"\\(?:setmainfont|setsansfont|setmonofont|newfontfamily|setCJKmainfont|setCJKsansfont"
                          r"|setCJKmonofont|setCJKfamilyfont|setmathfont)(?![A-Za-z@])")
_LUA_CMD_RE = re.compile(r"\\(?:directlua|luaexec|luadirect)(?![A-Za-z@])")
_BODY_TWOCOL_RE = re.compile(r"\\twocolumn(?![A-Za-z@])")

# 写好的论文里，导言区这些命令改了不算改模板：题目、作者、单位、关键词、期刊元数据、参考文献来源
_META_LINE_RE = re.compile(
    r"^\s*\\(?:title|subtitle|shorttitle|runningtitle|titlerunning|author|authors|authorrunning|address|affil"
    r"|affiliation|institute|inst|email|ead|orcid|thanks|keywords?|kwd|abstract|date|received|revised|accepted"
    r"|published|journal|journalname|volume|issue|year|pubyear|doi|corres|corresp|cortext|cormark|fntext|tnotetext"
    r"|tnoteref|articletype|subarticletype|specialissue|titlemark|authormark|markboth|copyrightyear|jvol|jnum"
    r"|paperid|editor|presentaddress|fnm|sur|orgdiv|orgname|orgaddress|street|city|postcode|state|country"
    r"|IEEEauthorblockN|IEEEauthorblockA|headers|runninghead|credit|funding|equalcont|footnote|maketitle"
    r"|addbibresource|bibliography|bibliographystyle|graphicspath)(?![A-Za-z@])")
_GENERIC_SAMPLE_MARKERS = (
    "lorem ipsum", "this is a sample", "this is an example", "insert your", "type your", "enter your",
    "your name", "author name", "first author", "second author", "third author", "given name surname",
    "paper title", "article title", "contribution title", "title of the paper", "请在此处", "在此输入",
    "此处填写", "作者姓名", "论文题目",
)
_ALWAYS_SAMPLE = ("lorem ipsum",)


# ----------------------------------------------------------------------------- 读文件
def read_text(path: Path) -> tuple[str, str]:
    """(文本, 原编码)。去 BOM，换行统一成 \\n；不是 UTF-8 时按 cp1252、再不行按 latin-1 读。"""
    data = Path(path).read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    for encoding in ("utf-8", "cp1252"):
        try:
            text = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text, encoding = data.decode("latin-1"), "latin-1"
    return text.replace("\r\n", "\n").replace("\r", "\n"), encoding


def strip_comments(text: str) -> str:
    return _COMMENT_RE.sub("", text or "")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _suffix(name: str) -> str:
    lower = name.lower()
    for tail in _BUILD_TAILS:
        if lower.endswith(tail):
            return tail
    for tail in (".tar.gz", ".tar.bz2", ".tar.xz"):
        if lower.endswith(tail):
            return tail
    return PurePosixPath(lower).suffix


def is_build_artifact(name: str) -> bool:
    sfx = _suffix(name)
    return sfx in _BUILD or sfx in _BUILD_TAILS


def is_archive(name: str) -> bool:
    return name.lower().endswith(_ARCHIVE)


def doc_like(stem: str) -> bool:
    return bool(_DOC_STEM_RE.search(stem)) and not _TEMPLATE_STEM_RE.search(stem)


def _braced(text: str, start: int) -> tuple[str, int]:
    """text[start] 是 '{'：返回配对大括号里的内容和结束位置；不配对时返回 ('', start)。"""
    if start >= len(text) or text[start] != "{":
        return "", start
    depth, i = 0, start
    while i < len(text):
        ch = text[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:i], i + 1
        i += 1
    return "", start


def _command_args(text: str, command: str, limit: int = 12) -> list[str]:
    """\\command[可选]{内容} 的内容（配对大括号），最多 limit 个。"""
    out = []
    for match in re.finditer(r"\\" + re.escape(command) + r"\*?\s*", text):
        pos = match.end()
        while pos < len(text) and text[pos] == "[":
            close = text.find("]", pos)
            if close < 0:
                break
            pos = close + 1
            while pos < len(text) and text[pos] in " \t\n":
                pos += 1
        content, end = _braced(text, pos)
        if end > pos:
            out.append(content)
            if len(out) >= limit:
                break
    return out


def _drop_command_args(text: str, names: tuple[str, ...]) -> str:
    """去掉 \\name[可选]{内容}（内容按配对大括号算，可以嵌套）。"""
    out, pos = [], 0
    pattern = re.compile(r"\\(?:" + "|".join(re.escape(n) for n in names) + r")(?![A-Za-z@])\*?\s*")
    while True:
        match = pattern.search(text, pos)
        if not match:
            out.append(text[pos:])
            return "".join(out)
        out.append(text[pos:match.start()])
        cursor = match.end()
        while cursor < len(text) and text[cursor] == "[":
            close = text.find("]", cursor)
            if close < 0:
                break
            cursor = close + 1
        _content, end = _braced(text, cursor)
        pos = end if end > cursor else match.end()


_NAME_RE = re.compile(r"^(?:[A-Z][a-z'\-]+|[A-Z]\.(?:-[A-Z]\.)?|[a-z]{1,3})(?: (?:[A-Z][a-z'\-]+|[A-Z]\.(?:-[A-Z]\.)?"
                      r"|van|von|de|der|da|di|le|la))+$")


def _sample_authors(text: str) -> list[str]:
    """样例里的作者姓名（像人名的才收：两到五个首字母大写的词，没有逗号和数字），核对时找残留用。"""
    found: list[str] = []
    args = _command_args(text, "IEEEauthorblockN")
    if not args:
        for arg in _command_args(text, "author"):
            arg = _drop_command_args(arg, ("inst", "thanks", "orcidID", "orcid", "footnote", "textsuperscript",
                                           "affil", "affiliation", "email", "ead", "corref", "fnref", "tnoteref",
                                           "IEEEauthorblockA", "IEEEmembership", "address", "institute"))
            args += [re.split(r"\\\\", part)[0] for part in re.split(r"\\(?:and|And|AND)(?![A-Za-z])", arg)]
    for arg in args:
        arg = _drop_command_args(arg, ("textsuperscript", "thanks", "footnote", "inst", "orcidID"))
        name = re.sub(r"\s+", " ", plain_text(re.split(r"\\\\", arg)[0])).strip(" ,;*")
        name = re.sub(r"^\d+\s*(?:st|nd|rd|th)?\s+", "", name)
        if _NAME_RE.match(name) and 2 <= len(name.split()) <= 5 and name not in found:
            found.append(name)
    return found[:12]


def plain_text(tex: str) -> str:
    """去掉命令、公式、表格代码后的正文文字（只用来比对样例句子，不求精确）。"""
    t = strip_comments(tex)
    t = re.sub(r"\\begin\{(equation|align|gather|multline|eqnarray|displaymath|math|tikzpicture|tabular|tabularx"
               r"|verbatim|lstlisting|algorithmic|algorithm|minted)\*?\}.*?\\end\{\1\*?\}", " ", t, flags=re.S)
    t = re.sub(r"\$\$.*?\$\$|\$[^$]*\$|\\\[.*?\\\]|\\\(.*?\\\)", " ", t, flags=re.S)
    t = re.sub(r"\\(?:cite[a-z]*|ref|eqref|autoref|cref|Cref|label|includegraphics|input|include|bibliography"
               r"|bibliographystyle|url|href|documentclass|usepackage|begin|end)\*?(?:\[[^\]]*\])*\{[^}]*\}", " ", t)
    t = re.sub(r"\\[A-Za-z@]+\*?", " ", t)
    t = re.sub(r"\\.", " ", t)
    t = re.sub(r"[{}\[\]~&^_#]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _norm_sentence(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def sample_fingerprints(body_tex: str, limit: int = 60) -> list[str]:
    """样例正文里有辨识度的句子（英文 ≥8 个词、中文 ≥14 个字），写好的论文里不该还有。
    方括号里的内容（引用编号、占位）先去掉，和 verify 的处理一致。"""
    text = plain_text(_BRACKET_RE.sub(" ", body_tex))
    seen, out = set(), []
    for sentence in re.split(r"(?<=[.!?。！？；;])\s+", text):
        sentence = sentence.strip()
        words = len(re.findall(r"[A-Za-z]{2,}", sentence))
        cjk = len(re.findall(r"[\u4e00-\u9fff]", sentence))
        if words < 8 and cjk < 14:
            continue
        key = _norm_sentence(sentence)[:90]
        if key and key not in seen:
            seen.add(key)
            out.append(key)
    out.sort(key=len, reverse=True)
    return out[:limit]


# ----------------------------------------------------------------------------- 解析 .tex
def parse_tex(raw: str) -> dict:
    magic = _MAGIC_RE.search(raw or "")
    text = strip_comments(raw)
    doc = _DOCCLASS_RE.search(text)
    begin = _BEGIN_DOC_RE.search(text)
    preamble = text[: begin.start()] if begin else text
    body = text[begin.end():] if begin else ""
    end = _END_DOC_RE.search(body)
    if end:
        body = body[: end.start()]
    packages = []
    for match in _PKG_RE.finditer(preamble):
        options = [o.strip() for o in (match.group(1) or "").split(",") if o.strip()]
        for name in match.group(2).split(","):
            if name.strip():
                packages.append({"name": name.strip(), "options": options})
    inputs = [m.group(1).strip() for m in _INPUT_RE.finditer(text)]
    inputs += [m.group(1).strip() for m in _INPUT_BARE_RE.finditer(text)]
    inputs += [(m.group(1).strip().rstrip("/") + "/" + m.group(2).strip()).lstrip("/") for m in _IMPORT_RE.finditer(text)]
    graphics_paths = []
    for match in _GRAPHICSPATH_RE.finditer(text):
        graphics_paths += [p.strip() for p in re.findall(r"\{([^{}]*)\}", match.group(1)) if p.strip()]
    biblatex = next((p for p in packages if p["name"] == "biblatex"), None)
    biblatex_options = {}
    if biblatex:
        for option in biblatex["options"]:
            key, _, value = option.partition("=")
            biblatex_options[key.strip()] = value.strip()
    return {
        "documentclass": doc.group(2).strip() if doc else "",
        "class_options": [o.strip() for o in (doc.group(1) or "").split(",") if o.strip()] if doc else [],
        "has_begin": bool(begin),
        "packages": packages,
        "inputs": [i for i in inputs if i],
        "graphics": [m.group(1).strip() for m in _GRAPHICS_RE.finditer(body)],
        "graphics_paths": graphics_paths,
        "bib_styles": [m.group(1).strip() for m in _BIBSTYLE_RE.finditer(text)],
        "bib_files": [f.strip() for m in _BIBDATA_RE.finditer(text) for f in m.group(1).split(",") if f.strip()],
        "bib_resources": [m.group(1).strip() for m in _ADDBIB_RE.finditer(text)],
        "biblatex": biblatex is not None,
        "biblatex_options": biblatex_options,
        "thebibliography": bool(_THEBIB_RE.search(body)),
        "magic_program": magic.group(1).lower() if magic else "",
        "font_commands": bool(_FONT_CMD_RE.search(text)),
        "lua_commands": bool(_LUA_CMD_RE.search(text)),
        "load_classes": [m.group(1).strip() for m in _LOADCLASS_RE.finditer(text)],
        "body_twocolumn": bool(_BODY_TWOCOL_RE.search(body)),
        "preamble": preamble,
        "body": body,
    }


def split_preamble(text: str) -> tuple[str, str]:
    """(导言区, 从 \\begin{document} 起的其余部分) —— 按原文（含注释）切在第一个不在注释里的 \\begin{document}。"""
    pos = 0
    for line in (text or "").splitlines(keepends=True):
        match = _BEGIN_DOC_RE.search(_COMMENT_RE.sub("", line))
        if match:
            return text[: pos + match.start()], text[pos + match.start():]
        pos += len(line)
    return text or "", ""


# ----------------------------------------------------------------------------- 扫描模板目录
def list_files(root: Path, *, skip_dirs: tuple[str, ...] = ()) -> list[str]:
    """root 下所有文件（posix 相对路径），跳过打包垃圾和识别报告。"""
    out = []
    root = Path(root)
    skip = {s.strip("/") for s in skip_dirs if s}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        parts = rel.split("/")
        if parts[0] in skip or any(p == "__MACOSX" or p.startswith("._") for p in parts):
            continue
        if parts[-1].lower() in _JUNK or parts[-1].startswith("."):
            continue
        out.append(rel)
    return out


def _index_by_name(files: list[str]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for rel in files:
        index.setdefault(PurePosixPath(rel).name.lower(), []).append(rel)
    return index


def _resolve_local(base_dir: PurePosixPath, ref: str, suffixes: tuple[str, ...], files: set[str],
                   index: dict[str, list[str]]) -> str | None:
    """主文件里 \\input{ref} 之类引用的包内文件；找不到返回 None。先按相对路径，再按文件名（TEXINPUTS 递归能找到）。"""
    ref = ref.strip().strip('"').replace("\\", "/")
    if not ref or ref.startswith("/") or re.match(r"^[A-Za-z]:", ref):
        return None
    names = [ref] if PurePosixPath(ref).suffix.lower() in suffixes else [ref + s for s in suffixes] + [ref]
    for name in names:
        candidate = str(PurePosixPath(os.path.normpath(str(base_dir / name)).replace("\\", "/")))
        if candidate in files:
            return candidate
    for name in names:
        hits = index.get(PurePosixPath(name).name.lower())
        if hits:
            return sorted(hits, key=lambda h: (h.count("/"), h))[0]
    return None


def scan(root: Path, *, skip_dirs: tuple[str, ...] = (), converted: dict[str, str] | None = None) -> dict:
    """扫一遍模板目录：每个 .tex 的解析结果、候选主文件（打分排序）、Word 模板。

    converted：已去宏另存的 Word 模板 {原 .docm 路径: 另存的 .docx 路径}，原文件不再当候选。
    """
    root = Path(root)
    files = list_files(root, skip_dirs=skip_dirs)
    fileset = set(files)
    index = _index_by_name(files)
    parsed: dict[str, dict] = {}
    encodings: dict[str, str] = {}
    for rel in files:
        if _suffix(rel) in _TEX:
            try:
                raw, encoding = read_text(root / rel)
            except OSError:
                continue
            parsed[rel] = parse_tex(raw)
            encodings[rel] = encoding
    included = set()
    for rel, info in parsed.items():
        base = PurePosixPath(rel).parent
        for ref in info["inputs"]:
            target = _resolve_local(base, ref, (".tex",), fileset, index)
            if target and target != rel:
                included.add(target)
    has_custom_class = any(_suffix(f) in _CLASS for f in files)
    candidates = []
    for rel, info in parsed.items():
        if not (info["documentclass"] and info["has_begin"]):
            continue
        path = PurePosixPath(rel)
        stem, parts = path.stem, path.parent.parts
        score, reasons, is_doc = 0.0, [], False
        if _TEMPLATE_STEM_RE.search(stem):
            score += 2
            reasons.append("文件名像模板主文件")
        if doc_like(stem):
            score -= 4
            is_doc = True
            reasons.append("文件名像说明文档")
        if any(p.lower() in _DOC_DIRS for p in parts):
            score -= 3
            is_doc = True
            reasons.append("放在说明文档目录里")
        cls = info["documentclass"]
        cls_local = _resolve_local(path.parent, cls, (".cls",), fileset, index)
        if cls_local:
            score += 3
            reasons.append(f"用的是包里自带的类文件 {PurePosixPath(cls_local).name}")
        elif cls in ("article", "report", "book") and has_custom_class:
            score -= 2
            reasons.append("用的是通用 article 类，包里另有专用类文件")
        if rel in included:
            score -= 5
            reasons.append("被别的文件 \\input 进来，是子文件")
        local_inputs = [r for r in (_resolve_local(path.parent, ref, (".tex",), fileset, index) for ref in info["inputs"])
                        if r and r != rel]
        if local_inputs:
            score += 1
            reasons.append("引入了包里的其他 .tex 文件")
        score -= 0.5 * len(parts)
        candidates.append({
            "path": rel, "score": round(score, 2), "reasons": reasons, "doc_like": is_doc,
            "included": rel in included, "documentclass": cls, "class_options": info["class_options"],
            "class_file": cls_local,
        })
    candidates.sort(key=lambda c: (-c["score"], c["path"].count("/"), c["path"]))
    words = []
    converted = dict(converted or {})
    for rel in files:
        sfx = _suffix(rel)
        if sfx in WORD_MACRO and rel in converted:
            continue  # 已经去宏另存成 .docx/.dotx，只认另存的那份
        if sfx in _WORD or sfx in WORD_MACRO:
            source = next((src for src, dst in converted.items() if dst == rel), None)
            words.append({"path": rel, "macro": sfx in WORD_MACRO, "converted_from": source,
                          "mac_variant": bool(_MAC_VARIANT_RE.search(PurePosixPath(source or rel).stem))})
    return {"root": str(root), "files": files, "parsed": parsed, "encodings": encodings,
            "candidates": candidates, "word_templates": words}


def choose_main(scanned: dict, *, main: str | None = None, prefer: str = "latex") -> dict:
    """选主文件。返回 {status, kind, main, reason}；status：ready / needs_choice / no_main / invalid_choice。

    明确给了 main 就只认候选里的（LaTeX 候选或 Word 模板）；没给就只在“唯一说得通”时自动选。
    """
    cands = scanned["candidates"]
    words = scanned["word_templates"]
    word_paths = {w["path"] for w in words}
    if main:
        main = main.replace("\\", "/").strip("/")
        if any(c["path"] == main for c in cands):
            return {"status": "ready", "kind": "latex", "main": main, "reason": "你选的主文件"}
        if main in word_paths:
            return {"status": "ready", "kind": "word", "main": main, "reason": "你选的 Word 模板"}
        return {"status": "invalid_choice", "kind": "none", "main": None,
                "reason": f"模板包里没有这个主文件：{main}"}
    latex_first = prefer != "word"
    order = ("latex", "word") if latex_first else ("word", "latex")
    for kind in order:
        if kind == "latex" and cands:
            viable = [c for c in cands if not c["doc_like"] and not c["included"]]
            if len(viable) == 1:
                return {"status": "ready", "kind": "latex", "main": viable[0]["path"], "reason": "包里只有这一个样例主文件"}
            if len(viable) > 1 and viable[0]["score"] - viable[1]["score"] >= 2:
                return {"status": "ready", "kind": "latex", "main": viable[0]["path"],
                        "reason": "按文件名和引用关系，它明显是主文件"}
            reason = ("包里只有说明文档里的样例，没有模板主文件" if not viable
                      else f"包里有 {len(viable)} 个都像主文件的 .tex，请选一个")
            return {"status": "needs_choice", "kind": "latex", "main": None, "reason": reason}
        if kind == "word" and words:
            plain = [w for w in words if not w["mac_variant"]]
            pick = plain if plain else words
            if len(pick) == 1:
                return {"status": "ready", "kind": "word", "main": pick[0]["path"], "reason": "包里只有这一个 Word 模板"}
            return {"status": "needs_choice", "kind": "word", "main": None,
                    "reason": f"包里有 {len(pick)} 个 Word 模板，请选一个"}
    sources = [f for f in scanned["files"] if _suffix(f) in _SOURCE]
    if sources:
        return {"status": "no_main", "kind": "none", "main": None,
                "reason": "包里只有 .dtx/.ins 源文件，没有能直接编译的样例主文件；请上传官方给的样例 .tex 和生成好的类文件"}
    return {"status": "no_main", "kind": "none", "main": None,
            "reason": "没找到主文件（需要同时有 \\documentclass 和 \\begin{document} 的 .tex，或 Word 模板）"}


# ----------------------------------------------------------------------------- 主文件细节
def _local_style_closure(root: Path, start: list[str], scanned: dict, limit: int = 40) -> list[str]:
    """从主文件用到的包内类文件、宏包出发，顺着 \\RequirePackage / \\LoadClass 收齐包内的 .cls/.sty。"""
    files = set(scanned["files"])
    index = _index_by_name(scanned["files"])
    seen, queue = [], list(start)
    while queue and len(seen) < limit:
        rel = queue.pop(0)
        if rel in seen:
            continue
        seen.append(rel)
        try:
            raw, _ = read_text(root / rel)
        except OSError:
            continue
        text = strip_comments(raw)
        base = PurePosixPath(rel).parent
        for match in _PKG_RE.finditer(text):
            for name in match.group(2).split(","):
                hit = _resolve_local(base, name, (".sty",), files, index)
                if hit and hit not in seen:
                    queue.append(hit)
        for name in _LOADCLASS_RE.findall(text):
            hit = _resolve_local(base, name, (".cls",), files, index)
            if hit and hit not in seen:
                queue.append(hit)
    return seen


def _engine_evidence(info: dict, style_texts: list[tuple[str, str]]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    xe, lua = [], []
    cls = info["documentclass"]
    if cls in _XE_CLASSES:
        xe.append(f"文档类 {cls}")
    if cls in _LUA_CLASSES:
        lua.append(f"文档类 {cls}")
    for pkg in info["packages"]:
        name = pkg["name"].lower()
        if name in _XE_PACKAGES:
            xe.append(f"宏包 {pkg['name']}")
        if name in _LUA_PACKAGES:
            lua.append(f"宏包 {pkg['name']}")
    if info["font_commands"]:
        xe.append("主文件里设置了系统字体（\\setmainfont 等）")
    if info["lua_commands"]:
        lua.append("主文件里用了 \\directlua")
    for rel, text in style_texts:
        clean = strip_comments(text)
        for match in _PKG_RE.finditer(clean):
            for name in match.group(2).split(","):
                key = name.strip().lower()
                if key in _XE_PACKAGES:
                    xe.append(f"{PurePosixPath(rel).name} 里的宏包 {name.strip()}")
                if key in _LUA_PACKAGES:
                    lua.append(f"{PurePosixPath(rel).name} 里的宏包 {name.strip()}")
        for name in _LOADCLASS_RE.findall(clean):
            if name.strip() in _XE_CLASSES:
                xe.append(f"{PurePosixPath(rel).name} 基于 {name.strip()}")
        if _FONT_CMD_RE.search(clean):
            xe.append(f"{PurePosixPath(rel).name} 里设置了系统字体")
    magic = info["magic_program"]
    if lua:
        engine = "lualatex"
        reasons.append("用了只有 LuaLaTeX 支持的内容：" + "、".join(dict.fromkeys(lua)))
    elif xe:
        engine = "xelatex"
        reasons.append("用了要 XeLaTeX 的内容：" + "、".join(dict.fromkeys(xe)))
        if magic == "lualatex":
            engine = "lualatex"
            reasons.append("文件头写明用 LuaLaTeX")
    elif magic in ENGINES:
        engine = magic
        reasons.append(f"文件头写明 % !TEX program = {magic}")
    else:
        engine = "pdflatex"
        reasons.append("没有用 fontspec、xeCJK、ctex 这类要 XeLaTeX 的宏包")
    if magic in ENGINES and magic != engine:
        reasons.append(f"文件头写的是 {magic}，但模板内容需要 {engine}，按 {engine}")
    return engine, reasons


def _columns(info: dict) -> int:
    options, cls = info["class_options"], info["documentclass"]
    if "twocolumn" in options or info["body_twocolumn"]:
        return 2
    if "onecolumn" in options:
        return 1
    if cls in ("IEEEtran", "cas-dc") or (cls == "elsarticle" and "5p" in options):
        return 2
    if cls == "acmart" and any(o in _ACMART_TWOCOL for o in options):
        return 2
    if cls.startswith("icml") or any(p["name"].startswith("icml") for p in info["packages"]):
        return 2
    return 1


def _paper_size(options: list[str]) -> str | None:
    lowered = [o.lower() for o in options]
    if any(o in ("a4paper", "a4") for o in lowered):
        return "a4"
    if any(o in ("letterpaper", "letter", "usletter") for o in lowered):
        return "letter"
    return None


def describe_main(scanned: dict, main_rel: str) -> dict:
    """主文件的文档类、编译方式、参考文献、栏数、样例内容。"""
    root = Path(scanned["root"])
    info = scanned["parsed"][main_rel]
    files = set(scanned["files"])
    index = _index_by_name(scanned["files"])
    base = PurePosixPath(main_rel).parent
    cls = info["documentclass"]
    class_file = _resolve_local(base, cls, (".cls",), files, index)
    local_packages, other_packages = [], []
    for pkg in info["packages"]:
        hit = _resolve_local(base, pkg["name"], (".sty",), files, index)
        (local_packages if hit else other_packages).append(hit or pkg["name"])
    starts = ([class_file] if class_file else []) + [p for p in local_packages if p]
    closure = _local_style_closure(root, starts, scanned)
    style_texts = []
    for rel in closure:
        try:
            style_texts.append((rel, read_text(root / rel)[0]))
        except OSError:
            continue
    engine, engine_reasons = _engine_evidence(info, style_texts)
    shipped_log = _resolve_local(base, PurePosixPath(main_rel).stem + ".log", (".log",), files, index)
    if shipped_log:
        try:
            first = read_text(root / shipped_log)[0][:200]
        except OSError:
            first = ""
        used = ("xelatex" if "XeTeX" in first else "lualatex" if "LuaHBTeX" in first or "LuaTeX" in first
                else "pdflatex" if "pdfTeX" in first else "")
        if used:
            engine_reasons.append(f"包里附带的编译日志显示出版方用的是 {used}（仅供参考）")
    if info["biblatex"]:
        backend = info["biblatex_options"].get("backend", "biber") or "biber"
        bib_engine = "biber" if backend == "biber" else "bibtex"
    elif info["bib_files"]:
        bib_engine = "bibtex"
    else:
        bib_engine = "none"
    missing_inputs = []
    for ref in info["inputs"]:
        if not _resolve_local(base, ref, (".tex",), files, index):
            missing_inputs.append(ref)
    bib_style = info["bib_styles"][0] if info["bib_styles"] else ""
    bib_style_file = _resolve_local(base, bib_style, (".bst",), files, index) if bib_style else None
    title_args = _command_args(info["body"] + info["preamble"], "title", 1)
    title = plain_text(re.split(r"\\\\", title_args[0])[0]).strip(" *") if title_args else ""
    authors = _sample_authors(info["preamble"] + info["body"])
    abstract = ""
    match = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", info["body"] + info["preamble"], re.S)
    if match:
        abstract = plain_text(match.group(1))[:200]
    elif _command_args(info["body"] + info["preamble"], "abstract", 1):
        abstract = plain_text(_command_args(info["body"] + info["preamble"], "abstract", 1)[0])[:200]
    sample_text = info["body"]
    for ref in info["inputs"]:
        hit = _resolve_local(base, ref, (".tex",), files, index)
        if hit and hit != main_rel:
            try:
                sample_text += "\n" + strip_comments(read_text(root / hit)[0])
            except OSError:
                continue
    sections = [plain_text(s) for s in _command_args(info["body"], "section", 30)]
    graphics = []
    for ref in info["graphics"]:
        hit = None
        for prefix in [""] + info["graphics_paths"]:
            hit = _resolve_local(base, prefix + ref, tuple(sorted(_IMAGE)), files, index)
            if hit:
                break
        graphics.append({"ref": ref, "file": hit})
    markers = [m for m in _GENERIC_SAMPLE_MARKERS if m in plain_text(info["preamble"] + " " + info["body"]).lower()]
    return {
        "documentclass": {"name": cls, "options": info["class_options"], "file": class_file,
                          "standard": cls in _STANDARD_CLASSES or cls.lower() in {c.lower() for c in _STANDARD_CLASSES}},
        "engine": {"tex": engine, "bib": bib_engine, "reasons": engine_reasons},
        "bibliography": {"style": bib_style, "style_file": bib_style_file, "files": info["bib_files"],
                         "resources": info["bib_resources"], "biblatex": info["biblatex"],
                         "biblatex_options": info["biblatex_options"], "thebibliography": info["thebibliography"]},
        "columns": _columns(info),
        "paper_size": _paper_size(info["class_options"]),
        "packages": [p["name"] for p in info["packages"]],
        "local_packages": [p for p in local_packages if p],
        "local_styles": closure,
        "missing_inputs": missing_inputs,
        "graphics": graphics,
        "encoding": scanned["encodings"].get(main_rel, "utf-8"),
        "sample": {
            "title": title[:200], "authors": authors[:12], "abstract": abstract,
            "sections": [s for s in sections if s][:30],
            "fingerprints": sample_fingerprints(sample_text),
            "markers": markers,
        },
    }


def copy_plan(scanned: dict, main_rel: str, *, exclude_dirs: tuple[str, ...] = ()) -> tuple[list[str], list[dict]]:
    """放进 paper/ 的文件（相对模板目录）和不放的文件及原因。模板目录 = 主文件所在目录。"""
    root = PurePosixPath(main_rel).parent
    candidates = {c["path"] for c in scanned["candidates"]}
    cand_stems = {PurePosixPath(c).stem.lower() for c in candidates}
    plan, excluded = [], []
    main_inside = [d for d in exclude_dirs if main_rel.startswith(d.rstrip("/") + "/")]
    skip_dirs = tuple(d for d in exclude_dirs if d not in main_inside)
    for rel in scanned["files"]:
        path = PurePosixPath(rel)
        if str(root) != ".":
            try:
                sub = path.relative_to(root)
            except ValueError:
                continue
        else:
            sub = path
            if any(rel.startswith(d.rstrip("/") + "/") for d in skip_dirs):
                excluded.append({"path": rel, "why": "另一个压缩包里的内容"})
                continue
        if rel == main_rel:
            continue
        name, sfx = path.name, _suffix(path.name)
        if str(sub) == MAIN_NAME:
            excluded.append({"path": rel, "why": "和主文件改名后的 main.tex 重名", "conflict": True})
            continue
        if is_build_artifact(name):
            excluded.append({"path": rel, "why": "编译产物"})
        elif is_archive(name):
            excluded.append({"path": rel, "why": "压缩包（已解开）"})
        elif sfx in _WORD or sfx in WORD_MACRO:
            excluded.append({"path": rel, "why": "Word 文件"})
        elif rel in candidates:
            excluded.append({"path": rel, "why": "另一个样例主文件"})
        elif any(p.lower() in _DOC_DIRS for p in sub.parent.parts):
            excluded.append({"path": rel, "why": "说明文档目录"})
        elif sfx == ".pdf" and (path.stem.lower() in cand_stems or doc_like(path.stem)):
            excluded.append({"path": rel, "why": "样例 PDF 或说明文档"})
        elif sfx in _DOC_TEXT and not _LICENSE_RE.match(name):
            excluded.append({"path": rel, "why": "说明文字"})
        else:
            plan.append(rel)
    return plan, excluded


def guide_documents(scanned: dict, main_rel: str) -> list[str]:
    """包里的说明文档 PDF（作者指南、类文件手册；包括模板目录以外的），只在报告和 CLAUDE.md 里列出来供参考。"""
    root = PurePosixPath(main_rel).parent
    cand_stems = {PurePosixPath(c["path"]).stem.lower() for c in scanned["candidates"]}
    out = []
    for rel in scanned["files"]:
        path = PurePosixPath(rel)
        if path.suffix.lower() != ".pdf" or path.stem.lower() in cand_stems:
            continue
        inside = str(root) == "." or str(path).startswith(str(root) + "/")
        in_doc_dir = any(p.lower() in _DOC_DIRS for p in path.parent.parts)
        if doc_like(path.stem) or in_doc_dir or not inside:
            out.append(rel)
    return out[:12]


# ----------------------------------------------------------------------------- 放进 paper/
def _utf8_main(store_root: Path, main_rel: str) -> tuple[bytes, bool]:
    raw = (store_root / main_rel).read_bytes()
    try:
        (raw[3:] if raw.startswith(b"\xef\xbb\xbf") else raw).decode("utf-8")
        return raw, False
    except UnicodeDecodeError:
        text, _ = read_text(store_root / main_rel)
        text = re.sub(r"(\\usepackage\s*\[)\s*(?:latin1|latin9|ansinew|cp1252)\s*(\]\s*\{inputenc\})", r"\1utf8\2", text)
        return text.encode("utf-8"), True


_SEARCHED = _CLASS | _STYLE | _BIBSTYLE


def materialize(store_root: Path, main_rel: str, plan: list[str], dest: Path, *, overwrite: bool = False) -> dict:
    """把模板目录按原样放进 dest（保留子目录），主文件放成 main.tex。dest 里已有的文件默认不覆盖。

    放在子目录里的类文件、宏包、bst（TeX 和 BibTeX 默认只在当前目录找）在根目录再各放一份，
    子目录里的原样保留；同名的有两份不一样的就不放，留给试编译报出来。
    返回 {copied, kept, flattened, files: {相对 dest 的路径: 模板原文件 sha256}, main_converted, main_sha, preamble}。
    """
    store_root, dest = Path(store_root), Path(dest)
    root = PurePosixPath(main_rel).parent
    copied, kept, flattened, files = [], [], [], {}
    subs = []
    for rel in plan:
        sub = PurePosixPath(rel).relative_to(root) if str(root) != "." else PurePosixPath(rel)
        subs.append((rel, sub))
    top_names = {str(sub).lower() for _rel, sub in subs if len(sub.parts) == 1} | {MAIN_NAME}
    by_name: dict[str, set[str]] = {}
    for rel, sub in subs:
        if len(sub.parts) > 1 and _suffix(sub.name) in _SEARCHED:
            by_name.setdefault(sub.name.lower(), set()).add(sha256_file(store_root / rel))
    extra = []
    for rel, sub in subs:
        key = sub.name.lower()
        if len(sub.parts) > 1 and key in by_name and len(by_name[key]) == 1 and key not in top_names:
            extra.append((rel, PurePosixPath(sub.name)))
            top_names.add(key)
            flattened.append(f"{sub} → {sub.name}")
    for rel, sub in subs + extra:
        source, target = store_root / rel, dest / sub
        files[str(sub)] = sha256_file(source)
        if target.exists() and not overwrite:
            kept.append(str(sub))
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        copied.append(str(sub))
    data, converted = _utf8_main(store_root, main_rel)
    main_target = dest / MAIN_NAME
    if main_target.exists() and not overwrite:
        kept.append(MAIN_NAME)
        text = read_text(main_target)[0]
    else:
        main_target.parent.mkdir(parents=True, exist_ok=True)
        main_target.write_bytes(data)
        copied.append(MAIN_NAME)
        text = data.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    preamble, _ = split_preamble(text.lstrip("\ufeff"))
    return {"copied": copied, "kept": kept, "flattened": flattened, "files": files, "main_converted": converted,
            "main_sha": hashlib.sha256(data).hexdigest(), "preamble": preamble}


# ----------------------------------------------------------------------------- 试编译
_LAYOUT_RE = re.compile(r"MHLAYOUT:([0-9.]+)pt;([0-9.]+)pt;([0-9.]+)pt;([0-9.]+)pt;([0-9.]+)pt;([01])")
_MISSING_RE = re.compile(r"! LaTeX Error: File `([^']+)' not found")
_CANT_FIND_RE = re.compile(r"! I can't find file `([^']+)'")
_TFM_RE = re.compile(r"! Font \\?[^=\s]*=([^\s]+)(?: at [^\s]+)? not loadable: Metric \(TFM\) file not found")
_SYSFONT_RE = re.compile(r'Package fontspec Error: The font "([^"]+)" cannot be found')
_NEEDS_XE_RE = re.compile(r"requires either XeTeX or LuaTeX|xeCJK package only supports XeTeX|Package ctex Error"
                          r"|only supports XeTeX|requires XeTeX")
_NEEDS_LUA_RE = re.compile(r"requires LuaTeX|only supports LuaTeX|LuaTeX is required")
_PAGES_RE = re.compile(r"Output written on \S+ \((\d+) pages?")
_BST_MISSING_RE = re.compile(r"I couldn't open style file (\S+?)\.bst")
_BIB_MISSING_RE = re.compile(r"I couldn't open database file (\S+?)\.bib")
_PREFIX = (r"\PassOptionsToPackage{draft}{graphicx}\makeatletter\AtBeginDocument{\typeout{MHLAYOUT:"
           r"\the\textwidth;\the\columnwidth;\the\textheight;\the\paperwidth;\the\paperheight;"
           r"\if@twocolumn 1\else 0\fi}}\makeatother\input{main.tex}")
_GENERATABLE = {".cls", ".sty", ".clo", ".cfg", ".bst", ".def", ".fd"}


def _which(name: str, tex_bin: str | None) -> str | None:
    if tex_bin:
        for candidate in (Path(tex_bin) / f"{name}.exe", Path(tex_bin) / name):
            if candidate.is_file():
                return str(candidate)
    return shutil.which(name)


_MIKTEX_CACHE: dict[str, bool] = {}


def is_miktex(exe: str) -> bool:
    """MiKTeX 才认 -enable-installer / -disable-installer（TeX Live 不认这两个参数）。"""
    if exe in _MIKTEX_CACHE:
        return _MIKTEX_CACHE[exe]
    try:
        out = subprocess.run([exe, "--version"], capture_output=True, timeout=60,
                             **({"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}))
        found = b"MiKTeX" in (out.stdout or b"") or "miktex" in exe.lower()
    except (OSError, subprocess.SubprocessError):
        found = "miktex" in exe.lower()
    _MIKTEX_CACHE[exe] = found
    return found


# 样例插图不在包里时，试编译临时目录里放的占位图（1×1 PNG、最小的 JPEG/PDF/EPS）
_STUB_PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478"
                          "9c6360000002000154a24f5d0000000049454e44ae426082")
_STUB_PDF = (b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>"
             b"endobj\n3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 72 72]>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n")
_STUB_EPS = b"%!PS-Adobe-3.0 EPSF-3.0\n%%BoundingBox: 0 0 72 72\nshowpage\n"


def _stub_image(target: Path) -> None:
    sfx = target.suffix.lower()
    target.write_bytes(_STUB_PDF if sfx == ".pdf" else _STUB_EPS if sfx in (".eps", ".ps") else _STUB_PNG)


def tex_search_env(base_env: dict | None = None, tex_bin: str | None = None) -> dict:
    """试编译的环境。⛔ 不设递归的 TEXINPUTS（.//）：MiKTeX 会把找到的文件换成绝对路径，
    路径里有 ~（Windows 短路径）、空格或中文用户名时 TeX 直接读不了。子目录里的类文件、bst
    由 materialize 在根目录各放一份解决。"""
    env = dict(base_env if base_env is not None else os.environ)
    env["max_print_line"] = "10000"
    if tex_bin:
        env["PATH"] = str(tex_bin) + os.pathsep + env.get("PATH", "")
    return env


def _run(cmd: list[str], cwd: Path, env: dict, timeout: float) -> tuple[int, str]:
    try:
        result = subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True, timeout=max(5.0, timeout),
                                **({"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}))
    except subprocess.TimeoutExpired:
        return 124, "（超时）"
    except OSError as exc:
        return 127, str(exc)
    return result.returncode, (result.stdout or b"").decode("utf-8", errors="replace")


def _safe_stub_path(work: Path, name: str) -> Path | None:
    rel = name.replace("\\", "/")
    if rel.startswith("/") or re.match(r"^[A-Za-z]:", rel) or ".." in PurePosixPath(rel).parts:
        return None
    target = (work / rel).resolve()
    try:
        target.relative_to(work.resolve())
    except ValueError:
        return None
    return target


def trial_compile(work: Path, *, engine: str, bib_engine: str = "none", tex_bin: str | None = None,
                  run_timeout: float = 90.0, budget: float = 300.0, max_rounds: int = 15,
                  generated_sink: Path | None = None, graphics: tuple[str, ...] = (),
                  auto_install: bool = False) -> dict:
    """在 work（已按 materialize 放好的临时副本，主文件叫 main.tex）里试编译模板样例。

    缺的宏包逐个记下并放空壳继续往下找；缺类文件但包里有同名 .ins 时先用它生成类文件
    （生成的文件同时复制到 generated_sink，也就是用户的模板目录，写作时也要用）。
    样例插图（graphics 里列的引用名）不在包里时放占位图，只记一条说明。
    auto_install：MiKTeX 缺宏包时联网自动装（和正式编译一样）；这时 missing 里只剩联网也没装上的。
    返回 {ran, ok, engine, missing, errors, layout, pages, generated, notes, seconds, auto_install}。
    """
    work = Path(work)
    started = time.monotonic()
    result = {"ran": False, "ok": False, "engine": engine, "bib_engine": bib_engine, "missing": [], "errors": [],
              "layout": None, "pages": None, "generated": [], "notes": [], "seconds": 0.0, "auto_install": False}
    exe = _which(engine, tex_bin)
    if not exe:
        result["notes"].append(f"本机没找到 {engine}，没法试编译；写作时会按识别出的方式编译")
        return result
    miktex = is_miktex(exe)
    # ⛔ 不加 -file-line-error：加了以后报错行变成 “./main.tex:5: LaTeX Error: …”，下面认缺包的正则就失效了
    flags = ["-interaction=nonstopmode", "-no-shell-escape"]
    installer = (["-enable-installer"] if auto_install else ["-disable-installer"]) if miktex else []
    flags += installer
    graphic_names = {g.replace("\\", "/").strip() for g in graphics if g}
    graphic_names |= {str(PurePosixPath(g).with_suffix("")) for g in list(graphic_names)}
    env = tex_search_env(tex_bin=str(Path(exe).parent))
    if miktex and auto_install:
        # 和后台给 CLI 设的一样（claude_runner：MIKTEX_ENABLEINSTALLER=yes）；第一次用到的宏包要联网下载，时间放宽
        env["MIKTEX_ENABLEINSTALLER"] = "yes"
        run_timeout, budget = max(run_timeout, 240.0), max(budget, 600.0)
    result["auto_install"] = bool(miktex and auto_install)
    result["ran"] = True
    stubs: set[str] = set()
    tried_ins: set[str] = set()
    switched = False
    log_text = ""

    def compile_once(halt: bool = False) -> tuple[int, str]:
        cmd = [exe, *flags, *(["-halt-on-error"] if halt else []), "-jobname=main", _PREFIX]
        code, _ = _run(cmd, work, env, min(run_timeout, max(5.0, budget - (time.monotonic() - started))))
        log_path = work / "main.log"
        text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
        return code, text

    for _round in range(max_rounds):
        if time.monotonic() - started > budget:
            result["notes"].append("试编译超时，后面的问题没有查完")
            break
        code, log_text = compile_once()
        if not switched and engine == "pdflatex" and _NEEDS_LUA_RE.search(log_text):
            switched, engine = True, "lualatex"
        elif not switched and engine == "pdflatex" and _NEEDS_XE_RE.search(log_text):
            switched, engine = True, "xelatex"
        if switched and result["engine"] != engine:
            new_exe = _which(engine, tex_bin)
            result["notes"].append(f"用 pdflatex 编不了（模板需要 {engine}），改用 {engine}")
            result["engine"] = engine
            if not new_exe:
                result["notes"].append(f"本机没找到 {engine}")
                break
            exe = new_exe
            continue
        miss = _MISSING_RE.search(log_text) or _CANT_FIND_RE.search(log_text)
        font = _TFM_RE.search(log_text)
        for sysfont in _SYSFONT_RE.findall(log_text):
            if not any(m["file"] == sysfont for m in result["missing"]):
                result["missing"].append({"file": sysfont, "kind": "system_font"})
        if font and not miss:
            result["missing"].append({"file": font.group(1), "kind": "font"})
            break
        if not miss:
            break
        name = miss.group(1).strip()
        if name in stubs:
            break
        sfx = PurePosixPath(name).suffix.lower()
        stem = PurePosixPath(name).stem
        is_graphic = name in graphic_names or str(PurePosixPath(name).with_suffix("")) in graphic_names
        if is_graphic:
            target = _safe_stub_path(work, name if sfx in _IMAGE else name + ".png")
            if target is None:
                result["errors"].append(f"模板引用了包外的插图：{name}")
                break
            stubs.add(name)
            target.parent.mkdir(parents=True, exist_ok=True)
            _stub_image(target)
            result["notes"].append(f"样例插图 {name} 不在包里（写作时会换成你的图，不影响）")
            continue
        target = _safe_stub_path(work, name if sfx else name + ".tex")
        if target is None:
            result["errors"].append(f"模板引用了包外的文件：{name}")
            break
        if sfx == ".cls" and stem not in tried_ins and (work / f"{stem}.ins").is_file():
            tried_ins.add(stem)
            before = {p.name for p in work.iterdir() if p.is_file()}
            _run([exe, "-interaction=nonstopmode", "-no-shell-escape", *installer,
                  f"{stem}.ins"], work, env, run_timeout)
            made = sorted(p.name for p in work.iterdir() if p.is_file() and p.name not in before
                          and p.suffix.lower() in _GENERATABLE)
            if (work / name).is_file():
                result["generated"].extend(made)
                if generated_sink is not None:
                    for item in made:
                        if not (Path(generated_sink) / item).exists():
                            shutil.copyfile(work / item, Path(generated_sink) / item)
                result["notes"].append(f"包里只有 {stem}.ins，已用它生成 {', '.join(made)}")
                continue
        kind = ("class" if sfx == ".cls" else "package" if sfx in {".sty", ".clo", ".cfg", ".def", ".fd", ".ldf"}
                else "image" if sfx in _IMAGE else "input")
        result["missing"].append({"file": name if sfx else name + ".tex", "kind": kind})
        stubs.add(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        if kind == "class":
            target.write_text("\\NeedsTeXFormat{LaTeX2e}\\ProvidesClass{%s}\\LoadClass{article}\n" % stem,
                              encoding="utf-8")
        elif kind == "package" and sfx == ".sty":
            target.write_text("\\ProvidesPackage{%s}\n" % stem, encoding="utf-8")
        elif kind == "image":
            _stub_image(target)
        else:
            target.write_text("\n", encoding="utf-8")

    if result["ran"] and not result["missing"] and time.monotonic() - started < budget:
        aux = work / "main.aux"
        if bib_engine in ("bibtex", "biber") and aux.exists():
            bib_exe = _which(bib_engine, tex_bin) or _which(bib_engine, str(Path(exe).parent))
            if not bib_exe:
                result["notes"].append(f"本机没找到 {bib_engine}，参考文献没试")
            else:
                _code, out = _run([bib_exe, "main"], work, env, run_timeout)
                for style in _BST_MISSING_RE.findall(out):
                    result["missing"].append({"file": style + ".bst", "kind": "bib_style"})
                for data in _BIB_MISSING_RE.findall(out):
                    result["notes"].append(f"样例引用的文献库 {data}.bib 不在包里（写作时换成 references.bib，不影响）")
        compile_once()
        code, log_text = compile_once(halt=True)
        result["ok"] = code == 0 and (work / "main.pdf").is_file() and not result["missing"]
    if log_text:
        layout = _LAYOUT_RE.search(log_text)
        if layout:
            pt = [float(x) for x in layout.groups()[:5]]
            result["layout"] = {"textwidth_in": round(pt[0] / 72.27, 3), "columnwidth_in": round(pt[1] / 72.27, 3),
                                "textheight_in": round(pt[2] / 72.27, 3), "paperwidth_in": round(pt[3] / 72.27, 3),
                                "paperheight_in": round(pt[4] / 72.27, 3), "twocolumn": layout.group(6) == "1"}
        pages = _PAGES_RE.search(log_text)
        if pages:
            result["pages"] = int(pages.group(1))
        if not result["ok"]:
            errors = []
            for match in re.finditer(r"^(?:\S+:\d+: |! )(.+)$", log_text, re.M):
                line = match.group(1).strip()
                if "not found" in line and any(m["file"] in line for m in result["missing"]):
                    continue
                if line not in errors:
                    errors.append(line[:200])
                if len(errors) >= 5:
                    break
            result["errors"].extend(errors)
    result["seconds"] = round(time.monotonic() - started, 1)
    return result


# ----------------------------------------------------------------------------- 写好之后的核对
def load_manifest(workspace: Path) -> dict | None:
    path = Path(workspace) / MANIFEST_RELATIVE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get("schema_version") == SCHEMA_VERSION else None


def _meaningful_lines(text: str) -> list[str]:
    out = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        stripped = line.rstrip()
        if not stripped.strip() or stripped.lstrip().startswith("%"):
            continue
        out.append(stripped)
    return out


_CODE_LINE_RE = re.compile(
    r"\\(?:documentclass|usepackage|RequirePackage|setlength|addtolength|geometry|renewcommand|newcommand"
    r"|providecommand|def|edef|gdef|let|makeatletter|makeatother|pagestyle|thispagestyle|setcounter|linespread"
    r"|DeclareMathOperator|newtheorem|theoremstyle|newenvironment|renewenvironment|hypersetup|captionsetup"
    r"|titleformat|titlespacing|fancyhf|fancyhead|fancyfoot|bibpunct|setcitestyle|input|include)(?![A-Za-z@])")


# 新加在导言区、会改模板版式的命令（页边距、版心、行距、字号）：算改坏模板
_LAYOUT_LINE_RE = re.compile(
    r"\\(?:setlength|addtolength|geometry|newgeometry|linespread|fontsize|selectfont|onehalfspacing|doublespacing)"
    r"(?![A-Za-z@])|baselinestretch|\\usepackage\s*(?:\[[^\]]*\])?\s*\{[^}]*\b(?:geometry|fullpage|a4wide|vmargin"
    r"|anysize|setspace|typearea)\b")
# 方括号占位（[Author Name]、[作者姓名]、[1] 这类）：核对样例残留时先去掉，免得把占位当成样例文字
_BRACKET_RE = re.compile(r"\[[^\[\]\n]{1,80}\]")


def _content_line(line: str) -> bool:
    """导言区里写样例内容的行（期刊元数据、样例题目之类）：有成句的文字，又不是排版代码。"""
    if _CODE_LINE_RE.search(line):
        return False
    text = plain_text(line)
    return len(re.findall(r"[A-Za-z]{2,}", text)) >= 3 or len(re.findall(r"[一-鿿]", text)) >= 4


def preamble_changes(baseline: str, current: str) -> dict:
    """导言区和放进 paper/ 时的样子比：errors（改了文档类、删了宏包、改了模板原有的排版代码）、
    warnings（新加的宏包和命令）、info（题目、作者、关键词、期刊元数据、参考文献来源这类本来就要填的）。"""
    old, new = _meaningful_lines(baseline), _meaningful_lines(current)
    errors, warnings, info = [], [], []
    matcher = difflib.SequenceMatcher(a=old, b=new, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        removed, added = old[i1:i2], new[j1:j2]
        for line in removed:
            if _META_LINE_RE.match(line) or _content_line(line):
                info.append(f"改了：{line.strip()[:120]}")
            elif "\\documentclass" in line:
                errors.append(f"文档类那一行被改了：{line.strip()[:120]}")
            elif re.search(r"\\(?:usepackage|RequirePackage)", line):
                errors.append(f"删了模板原有的宏包：{line.strip()[:120]}")
            else:
                errors.append(f"改了模板导言区原有的一行：{line.strip()[:120]}")
        for line in added:
            if _META_LINE_RE.match(line) or "\\documentclass" in line or _content_line(line):
                continue
            if _LAYOUT_LINE_RE.search(line):
                errors.append(f"导言区新加了改版式的命令：{line.strip()[:120]}")
            elif re.search(r"\\(?:usepackage|RequirePackage)", line):
                warnings.append(f"导言区新加了宏包：{line.strip()[:120]}")
            else:
                warnings.append(f"导言区新加了一行：{line.strip()[:120]}")
    return {"errors": errors, "warnings": warnings, "info": info}


def verify(workspace: Path) -> dict:
    """编译步核对：模板文件没被改、导言区没被改、没有残留的样例文字。没有生效的用户 LaTeX 模板时 active=False。

    errors 里是全部错误；template（模板文件、导言区）和 residue（样例残留）把两类分开，投稿前检查分两项报。
    """
    workspace = Path(workspace)
    manifest = load_manifest(workspace)
    report = {"active": False, "errors": [], "warnings": [], "info": [], "template": [], "residue": []}
    if not manifest or manifest.get("kind") != "latex" or not manifest.get("materialized"):
        return report
    report["active"] = True
    paper = workspace / "paper"
    mat = manifest["materialized"]
    changed, deleted = [], []
    for sub, digest in sorted((mat.get("files") or {}).items()):
        if _suffix(sub) not in PROTECTED:
            continue
        path = paper / sub
        if not path.is_file():
            deleted.append(sub)
        elif sha256_file(path) != digest:
            changed.append(sub)
    if changed:
        report["errors"].append("模板文件被改了：" + "、".join(changed[:8]))
    if deleted:
        report["errors"].append("模板文件被删了：" + "、".join(deleted[:8]))
    main = paper / MAIN_NAME
    if not main.is_file():
        report["errors"].append("paper/main.tex 不见了")
        report["template"] = list(report["errors"])
        return report
    text = read_text(main)[0]
    preamble, _ = split_preamble(text)
    diff = preamble_changes(mat.get("preamble") or "", preamble)
    report["errors"] += diff["errors"]
    report["template"] = list(report["errors"])
    report["warnings"] += diff["warnings"]
    if diff["info"]:
        report["info"].append(f"导言区按要求填了 {len(diff['info'])} 处（题目、作者、关键词、参考文献等）")
    sources = [text]
    sections = paper / "sections"
    if sections.is_dir():
        for path in sorted(sections.rglob("*.tex")):
            try:
                sources.append(read_text(path)[0])
            except OSError:
                continue
    sources = [_BRACKET_RE.sub(" ", s) for s in sources]
    body_text = plain_text("\n".join(split_preamble(s)[1] or s for s in sources)).lower()
    full_text = plain_text("\n".join(sources)).lower()
    sample = manifest.get("sample") or {}
    hits = [f for f in sample.get("fingerprints") or [] if f and f in body_text]
    if hits:
        report["errors"].append(f"还留着模板自带的样例文字 {len(hits)} 句，例如：“{hits[0][:80]}”")
    title = _norm_sentence(sample.get("title") or "")
    current_titles = [_norm_sentence(plain_text(t)) for t in _command_args(strip_comments(text), "title", 2)]
    if title and len(title) >= 6 and any(title == t or title.rstrip("*") == t.rstrip("*") for t in current_titles):
        report["errors"].append(f"题目还是模板样例的：“{sample.get('title')}”")
    for name in sample.get("authors") or []:
        key = _norm_sentence(name)
        if len(key) >= 6 and key in full_text and key not in {"[author name]", "[作者姓名]"}:
            report["errors"].append(f"还留着模板样例的作者：“{name}”")
            break
    for marker in set(sample.get("markers") or []) | set(_ALWAYS_SAMPLE):
        if marker in full_text:
            report["errors"].append(f"还留着样例占位文字：“{marker}”")
    report["residue"] = report["errors"][len(report["template"]):]
    return report


def print_verify(report: dict) -> int:
    if not report.get("active"):
        print("  (没有用上传的 LaTeX 模板，跳过模板核对)")
        return 0
    for line in report["errors"]:
        print(f"❌ {line}")
    for line in report["warnings"]:
        print(f"⚠ {line}")
    for line in report["info"]:
        print(f"  {line}")
    if not report["errors"]:
        print("✅ 用户模板完好：类文件、宏包、导言区没被改，样例文字都换掉了")
    return 1 if report["errors"] else 0


# ----------------------------------------------------------------------------- Word 模板去宏
_MACRO_PARTS = re.compile(r"(?i)^word/(?:vbaProject\.bin|vbaData\.xml|_rels/vbaProject\.bin\.rels|customizations\.xml"
                          r"|attachedToolbars\.bin|_rels/attachedToolbars\.bin\.rels)$")


def strip_word_macros(src: Path, dst: Path) -> dict:
    """.docm/.dotm 去掉宏另存为 .docx/.dotx：删 VBA 部件和它们的关系、内容类型改回普通文档。"""
    removed = []
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            name = info.filename
            if _MACRO_PARTS.match(name) or name.lower().startswith("customui/"):
                removed.append(name)
                continue
            data = zin.read(info)
            if name == "[Content_Types].xml":
                text = data.decode("utf-8")
                main_type = ("application/vnd.openxmlformats-officedocument.wordprocessingml.template.main+xml"
                             if Path(dst).suffix.lower() == ".dotx"
                             else "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml")
                # 主文档部件的内容类型改成普通文档/模板（.docm、.dotm 写的是 macroEnabled 的类型）
                text = re.sub(r'(<Override[^>]*PartName="/word/document\.xml"[^>]*ContentType=")[^"]*(")',
                              lambda m: m.group(1) + main_type + m.group(2), text)
                text = re.sub(r'<Override[^>]*PartName="/(?:word/(?:vbaProject\.bin|vbaData\.xml|customizations\.xml'
                              r'|attachedToolbars\.bin)|customUI/[^"]*)"[^>]*/>', "", text, flags=re.I)
                text = re.sub(r'<Default[^>]*ContentType="application/vnd\.ms-office\.vbaProject"[^>]*/>', "", text)
                data = text.encode("utf-8")
            elif name.endswith(".rels"):
                text = data.decode("utf-8")
                text = re.sub(r'<Relationship[^>]*Type="[^"]*(?:/vbaProject|/keyMapCustomizations|/attachedToolbars'
                              r'|/ui/extensibility)"[^>]*/>', "", text)
                data = text.encode("utf-8")
            zout.writestr(info, data)
        zout.comment = _CONVERSION_MARK
    return {"source": str(src), "converted": str(dst), "removed": removed}


_CONVERSION_MARK = b"paperkit: word macros removed"


def _our_conversion(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path) as z:
            return z.comment == _CONVERSION_MARK
    except (OSError, zipfile.BadZipFile):
        return False


def convert_macro_templates(store_root: Path) -> list[dict]:
    """.docm/.dotm 去宏另存为同名 .docx/.dotx（同名文件已存在且不是我们另存的，就另存成“-无宏”）；另存过的不重做。"""
    store_root = Path(store_root)
    out = []
    for rel in list_files(store_root):
        sfx = _suffix(rel)
        if sfx not in WORD_MACRO:
            continue
        path = PurePosixPath(rel)
        names = [str(path.with_suffix(WORD_MACRO[sfx])), str(path.with_name(path.stem + "-无宏" + WORD_MACRO[sfx]))]
        target_rel = next((n for n in names if not (store_root / n).exists() or _our_conversion(store_root / n)), None)
        if target_rel is None:
            out.append({"source": rel, "converted": None, "error": "同名的 Word 文件已经存在，没法另存"})
            continue
        target = store_root / target_rel
        if target.exists():
            out.append({"source": rel, "converted": target_rel, "removed": None})
            continue
        try:
            info = strip_word_macros(store_root / rel, target)
        except (OSError, zipfile.BadZipFile, KeyError, UnicodeDecodeError) as exc:
            target.unlink(missing_ok=True)
            out.append({"source": rel, "converted": None, "error": f"去宏失败：{exc}"})
            continue
        out.append({"source": rel, "converted": target_rel, "removed": info["removed"]})
    return out


_LAYOUT_BREAKERS = {"geometry.sty", "typearea.sty", "vmargin.sty", "fullpage.sty", "a4wide.sty", "anysize.sty"}


def final_layout(desc: dict, trial: dict | None) -> dict:
    """栏数和版心：试编译量到的为准（缺了类文件或页面设置宏包时量到的不算数），量不到按文档类判断。"""
    columns = desc["columns"]
    out = {"columns": columns, "textwidth_in": None, "textheight_in": None, "columnwidth_in": None,
           "paperwidth_in": None, "paperheight_in": None, "source": "按文档类和选项判断"}
    trial = trial or {}
    layout = trial.get("layout")
    broken = any(m["kind"] == "class" or m["file"].lower() in _LAYOUT_BREAKERS for m in trial.get("missing") or [])
    if not layout or broken:
        if layout and broken:
            out["source"] = "试编译不完整（缺类文件或页面设置宏包），版心没量准"
        return out
    if layout.get("twocolumn"):
        columns = 2
    out.update(columns=columns, textwidth_in=layout["textwidth_in"], textheight_in=layout["textheight_in"],
               paperwidth_in=layout["paperwidth_in"], paperheight_in=layout["paperheight_in"], source="试编译实测")
    if columns == 2 and layout.get("twocolumn") and 0 < layout["columnwidth_in"] < layout["textwidth_in"]:
        out["columnwidth_in"] = layout["columnwidth_in"]
    return out


def _default_trial(store_root: Path, main_rel: str, plan: list[str], desc: dict, tex_bin: str | None,
                   auto_install: bool = False) -> dict:
    import tempfile
    with tempfile.TemporaryDirectory(prefix="mh-tpl-trial-") as tmp:
        materialize(store_root, main_rel, plan, Path(tmp), overwrite=True)
        sink = Path(store_root) / str(PurePosixPath(main_rel).parent)
        return trial_compile(Path(tmp), engine=desc["engine"]["tex"], bib_engine=desc["engine"]["bib"],
                             tex_bin=tex_bin, generated_sink=sink, graphics=tuple(g["ref"] for g in desc["graphics"]),
                             auto_install=auto_install)


def inspect_store(store_root: Path, *, main: str | None = None, prefer: str = "latex",
                  exclude_dirs: tuple[str, ...] = (), trial: bool = True, tex_bin: str | None = None,
                  trial_runner=None) -> dict:
    """上传的模板目录 → 识别结果（.mh/user_template.json 的主体，materialized 段写作步再补）。

    trial_runner(store_root, main_rel, plan, desc, tex_bin) -> 试编译结果；后台用它加缓存。
    """
    store_root = Path(store_root)
    conversions = convert_macro_templates(store_root)
    converted = {c["source"]: c["converted"] for c in conversions if c.get("converted")}
    scanned = scan(store_root, converted=converted)
    choice = choose_main(scanned, main=main, prefer=prefer)
    manifest = {
        "schema_version": SCHEMA_VERSION, "store": STORE_DIR, "status": choice["status"], "kind": choice["kind"],
        "main": choice["main"], "reason": choice["reason"],
        "candidates": [{k: c[k] for k in ("path", "score", "reasons", "doc_like", "included", "documentclass",
                                          "class_options")} for c in scanned["candidates"]][:20],
        "word_templates": scanned["word_templates"][:20], "conversions": conversions,
        "file_count": len(scanned["files"]), "warnings": [],
    }
    if choice["status"] == "ready" and choice["kind"] == "latex":
        main_rel = choice["main"]
        desc = describe_main(scanned, main_rel)
        plan, excluded = copy_plan(scanned, main_rel, exclude_dirs=exclude_dirs)
        conflicts = [e["path"] for e in excluded if e.get("conflict")]
        if conflicts:
            manifest.update(status="error", reason=f"模板目录里另有一个 {conflicts[0]}，和主文件改名后的 main.tex 重名；"
                                                   "请把那个文件改个名再上传")
        for key in ("documentclass", "engine", "bibliography", "columns", "paper_size", "packages", "local_packages",
                    "missing_inputs", "graphics", "encoding", "sample"):
            manifest[key] = desc[key]
        manifest["copy"] = {"root": str(PurePosixPath(main_rel).parent), "files": plan, "excluded": excluded[:80],
                            "excluded_count": len(excluded)}
        manifest["guides"] = guide_documents(scanned, main_rel)
        result = None
        if trial and manifest["status"] == "ready":
            result = (trial_runner or _default_trial)(store_root, main_rel, plan, desc, tex_bin)
            if result.get("generated"):
                scanned = scan(store_root, converted=converted)
                plan, excluded = copy_plan(scanned, main_rel, exclude_dirs=exclude_dirs)
                manifest["copy"].update(files=plan, excluded=excluded[:80], excluded_count=len(excluded))
                manifest["documentclass"] = describe_main(scanned, main_rel)["documentclass"]
            if result.get("ran") and result.get("engine") and result["engine"] != desc["engine"]["tex"]:
                manifest["engine"] = {**desc["engine"], "tex": result["engine"],
                                      "reasons": desc["engine"]["reasons"] + [f"试编译时发现要用 {result['engine']}"]}
        manifest["trial"] = result
        manifest["layout"] = final_layout(desc, result)
        manifest["columns"] = manifest["layout"]["columns"]
    elif choice["status"] == "ready" and choice["kind"] == "word":
        word = next((w for w in scanned["word_templates"] if w["path"] == choice["main"]), {})
        manifest["word"] = {"converted_from": word.get("converted_from"),
                            "macro_removed": bool(word.get("converted_from"))}
    return manifest


def _inch(value) -> str:
    return f"{value:.2f}" if isinstance(value, (int, float)) else "?"


def render_report(manifest: dict, *, generated_at: str = "") -> str:
    """给用户看的《模板识别报告》（Markdown）。"""
    lines = ["# 模板识别报告", ""]
    if generated_at:
        lines += [f"（MH Agent 自动生成，{generated_at}）", ""]
    status, kind = manifest.get("status"), manifest.get("kind")
    lines.append("## 结论")
    if status == "ready" and kind == "latex":
        lines.append(f"- 主文件：`{manifest['main']}`（写作时放成 `paper/main.tex`）——{manifest.get('reason', '')}")
    elif status == "ready" and kind == "word":
        word = manifest.get("word") or {}
        source = word.get("converted_from")
        lines.append(f"- Word 模板：`{manifest['main']}`" + (f"（由 `{source}` 去掉宏另存，原文件没动）" if source else ""))
        lines.append("- 写完后按这个模板排版：保留原封面、页眉页脚和样式，内容填到占位处；中图分类号、基金、作者简介这类"
                     "事实由你填写，软件不编。")
    else:
        lines.append(f"- ⚠ 还不能用：{manifest.get('reason', '')}")
        cands = [c for c in manifest.get("candidates") or [] if not c.get("included")]
        if cands:
            lines.append("- 可选的主文件：" + "、".join(f"`{c['path']}`" for c in cands[:10]))
    if kind == "latex" and status in ("ready", "error"):
        doc = manifest.get("documentclass") or {}
        cls_note = ("类文件随包提供" if doc.get("file") else "用 TeX 自带的类" if doc.get("standard")
                    else "⚠ 包里没有这个类文件，试编译会告诉你缺不缺")
        opts = "、".join(doc.get("options") or []) or "无"
        lines.append(f"- 文档类：`{doc.get('name', '')}`（选项：{opts}；{cls_note}）")
        engine = manifest.get("engine") or {}
        bib = {"bibtex": "参考文献用 BibTeX", "biber": "参考文献用 Biber（biblatex）",
               "none": "样例没用 BibTeX，写作时改用 BibTeX 从 references.bib 生成"}.get(engine.get("bib"), "")
        lines.append(f"- 编译方式：{engine.get('tex', '')}；{bib}；依据：" + "；".join(engine.get("reasons") or []))
        layout = manifest.get("layout") or {}
        col = "双栏" if layout.get("columns") == 2 else "单栏"
        area = ""
        if layout.get("textwidth_in"):
            area = f"；版心 {_inch(layout['textwidth_in'])} × {_inch(layout['textheight_in'])} 英寸"
            if layout.get("columnwidth_in"):
                area += f"，栏宽 {_inch(layout['columnwidth_in'])} 英寸"
        lines.append(f"- 栏数：{col}{area}（{layout.get('source', '')}）")
        size = {"a4": "A4", "letter": "US Letter"}.get(manifest.get("paper_size") or "", "按模板默认")
        lines.append(f"- 纸张：{size}")
        bibl = manifest.get("bibliography") or {}
        parts = []
        if bibl.get("style"):
            parts.append(f"样式 `{bibl['style']}`" + ("（随包提供）" if bibl.get("style_file") else ""))
        if bibl.get("files") or bibl.get("resources"):
            parts.append("样例文献库 " + "、".join(f"`{f}`" for f in (bibl.get("files") or []) + (bibl.get("resources") or []))
                         + "（写作时换成 `references.bib`）")
        if bibl.get("thebibliography"):
            parts.append("样例里是手写的参考文献列表（写作时改成用 `references.bib` 生成）")
        lines.append("- 参考文献：" + ("；".join(parts) if parts else "模板里没有参考文献设置"))
        if manifest.get("encoding") not in (None, "utf-8"):
            lines.append(f"- 主文件原来是 {manifest['encoding']} 编码，放进 paper/ 时转成了 UTF-8（内容不变）")
        trial = manifest.get("trial")
        lines += ["", "## 试编译"]
        if not trial:
            lines.append("- 没试（模板还没定下来）")
        elif not trial.get("ran"):
            lines.append("- 没试：" + "；".join(trial.get("notes") or ["本机没有 TeX"]))
        else:
            verdict = "通过" if trial.get("ok") else "没通过"
            pages = f"，{trial['pages']} 页" if trial.get("pages") else ""
            lines.append(f"- 结果：{verdict}{pages}，用 {trial.get('engine')}，用时 {trial.get('seconds')} 秒"
                         + ("（编译时禁止调用外部命令；缺的宏包联网自动装）" if trial.get("auto_install")
                            else "（编译时禁止调用外部命令；本机的排版工具不会自动下载缺的宏包）"))
            missing = trial.get("missing") or []
            if missing:
                kinds = {"package": "宏包", "class": "类文件", "font": "字体", "system_font": "系统字体",
                         "bib_style": "参考文献样式", "input": "子文件", "image": "图片"}
                lines.append("- 缺少：")
                lines += [f"  - `{m['file']}`（{kinds.get(m['kind'], m['kind'])}）" for m in missing]
                if trial.get("auto_install"):
                    lines.append("- 已经试过联网自动安装，这些还是没装上（可能没联网，或者 MiKTeX 仓库里没有）。办法："
                                 "把缺的文件跟模板一起上传；或者改用内置的投稿格式；联网后重新上传模板会再试着安装。")
                else:
                    lines.append("- 办法：把缺的文件跟模板一起上传；或者改用内置的投稿格式。自己装了 MiKTeX 的，也可以在"
                                 " MiKTeX Console 里装上这些宏包，再重新上传模板。")
            for note in trial.get("notes") or []:
                lines.append(f"- {note}")
            if trial.get("errors") and not trial.get("ok"):
                lines.append("- 编译报错（前几条）：")
                lines += [f"  - {e}" for e in trial["errors"][:5]]
        sample = manifest.get("sample") or {}
        lines += ["", "## 要换掉的样例内容"]
        if sample.get("title"):
            lines.append(f"- 样例题目：“{sample['title']}”")
        if sample.get("authors"):
            lines.append("- 样例作者：" + "、".join(sample["authors"][:6]) + "（作者信息软件不编，留方括号占位由你填）")
        if sample.get("sections"):
            lines.append("- 样例章节：" + "、".join(sample["sections"][:10]))
        lines.append(f"- 样例正文里有辨识度的句子 {len(sample.get('fingerprints') or [])} 句：写完后逐句核对，不能留下")
        graphics = manifest.get("graphics") or []
        if graphics:
            lines.append("- 样例插图：" + "、".join(g["ref"] for g in graphics[:8]))
        copy = manifest.get("copy") or {}
        lines += ["", "## 放进 paper/ 的文件"]
        files = copy.get("files") or []
        lines.append(f"- {len(files) + 1} 个（含主文件；保留原文件名和子目录）："
                     + "、".join(f"`{f}`" for f in files[:20]) + ("……" if len(files) > 20 else ""))
        if copy.get("excluded_count"):
            reasons = sorted({e["why"] for e in copy.get("excluded") or []})
            lines.append(f"- 没放进去的 {copy['excluded_count']} 个：" + "、".join(reasons))
        if manifest.get("guides"):
            lines += ["", "## 包里的说明文档（只供参考，不当你的研究资料）"]
            lines += [f"- `{g}`" for g in manifest["guides"]]
    conversions = [c for c in manifest.get("conversions") or [] if c.get("converted") or c.get("error")]
    rejected = manifest.get("rejected") or []
    if conversions or rejected or manifest.get("warnings"):
        lines += ["", "## 其他"]
        for c in conversions:
            if c.get("converted"):
                lines.append(f"- `{c['source']}` 是带宏的 Word 文件，已去掉宏另存为 `{c['converted']}`（原文件没动）")
            else:
                lines.append(f"- `{c['source']}`：{c['error']}")
        for item in rejected:
            lines.append(f"- 拒收：`{item}`")
        lines += [f"- {w}" for w in manifest.get("warnings") or []]
    return "\n".join(lines) + "\n"


# ----------------------------------------------------------------------------- 命令行
def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_inspect = sub.add_parser("inspect")
    p_inspect.add_argument("root")
    p_inspect.add_argument("--main")
    p_inspect.add_argument("--prefer", default="latex")
    p_inspect.add_argument("--trial", action="store_true")
    p_inspect.add_argument("--auto-install", action="store_true", help="MiKTeX 缺宏包时联网自动装（默认不装）")
    p_verify = sub.add_parser("verify")
    p_verify.add_argument("workspace", nargs="?", default=".")
    args = parser.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    if args.cmd == "verify":
        return print_verify(verify(Path(args.workspace)))
    scanned = scan(Path(args.root))
    choice = choose_main(scanned, main=args.main, prefer=args.prefer)
    out = {"choice": choice, "candidates": scanned["candidates"], "word_templates": scanned["word_templates"]}
    if choice["status"] == "ready" and choice["kind"] == "latex":
        out["main"] = describe_main(scanned, choice["main"])
        plan, excluded = copy_plan(scanned, choice["main"])
        out["copy"], out["excluded"] = plan, excluded
        if args.trial:
            import tempfile
            with tempfile.TemporaryDirectory(prefix="mh-tpl-") as tmp:
                materialize(Path(args.root), choice["main"], plan, Path(tmp), overwrite=True)
                out["trial"] = trial_compile(Path(tmp), engine=out["main"]["engine"]["tex"],
                                             bib_engine=out["main"]["engine"]["bib"],
                                             graphics=tuple(g["ref"] for g in out["main"]["graphics"]),
                                             auto_install=args.auto_install)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
