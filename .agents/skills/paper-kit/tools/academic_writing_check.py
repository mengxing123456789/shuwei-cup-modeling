# -*- coding: utf-8 -*-
"""学术写作检查（论证逻辑与文理分型，2026-10-11 起；规则见规划附录 B）。

后台调用（web/backend/services/writing_review.py），也能单独跑：

    python academic_writing_check.py <工作区> --stage plan  --skill paper-plan-zh [--json]
    python academic_writing_check.py <工作区> --stage draft --skill paper-write-zh [--json]
    python academic_writing_check.py <工作区> --stage final --skill docx-export [--source COURSE_PAPER.md]

- 规划阶段（plan，规划步完成后）：P 组，核对大纲的论证主线（P1–P4）。不写给人看的报告文件
  （工作区根目录的 .md 会被别的检查当成稿件扫），没补上的需修项由后台记进 OPEN_QUESTIONS.md。
- 稿件阶段（draft 写作步完成后；final 编译或导出步完成后，终稿复查）：S 结构、I 引言、R 综述、D 讨论、C 结论、
  N 话说过头、K 口吻、T 按研究类型、H 人文、Q 开题报告的交付核对（必备部分、篇幅、文献篇数与构成、进度、计划语气）。LaTeX 从 paper/main.tex 起跟着 \\input 读，Word 稿读 Markdown 成稿。
  公式、代码、表格、命令参数、参考文献节先等长屏蔽（照语言原型 asc_proto.py），摘要、结论、贡献段从严。
  写 WRITING_CHECK.md（给人看）。开题、综述一步写规划和成稿，写作步之后两组一起查。

读 .mh/writing_spec.json 的写作档案，写 .mh/quality/writing_check.json（步骤卡读它）。只读不改稿。
竞赛、市调、软著专利、开发类工作流没有写作档案，一律不适用。

每项的 status：
- fix 需修：误报率低的硬伤。后台让本步照清单补一轮，补完再查；还有就只在步骤卡上显示，不阻断、不判失败。
- hint 提示：倾向性问题，只显示。
- ok / skipped（不适用）/ error（这一项没查成，不影响别的项）。

稿件阶段的结论和稿件版本绑定（sources、fingerprint）：稿件之后再改过，is_current() 就返回 False。

退出码：0 没有需修项；1 有需修项；2 不适用；3 检查没跑成。只用标准库（LaTeX 展开用同目录的 paper_source_scope.py）。
"""
from __future__ import annotations

import argparse
import bisect
import difflib
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path

SCHEMA_VERSION = 1
JSON_RELATIVE = Path(".mh") / "quality" / "writing_check.json"
SPEC_RELATIVE = Path(".mh") / "writing_spec.json"
OPEN_QUESTIONS = "OPEN_QUESTIONS.md"
STATUSES = ("fix", "error", "hint", "skipped", "ok")
STATUS_ZH = {"fix": "需修", "error": "检查未完成", "hint": "提示", "skipped": "不适用", "ok": "通过"}
STAGES = ("plan", "draft", "final")
EXIT_OK, EXIT_FIX, EXIT_NOT_APPLICABLE, EXIT_UNAVAILABLE = 0, 1, 2, 3
MAX_READ = 400_000

# 规划产物在哪个文件（论证主线写在这里）
PLAN_FILE_BY_SKILL = {
    "paper-plan": "PAPER_PLAN.md",
    "paper-plan-zh": "PAPER_PLAN.md",
    "humanities-plan": "OUTLINE.md",
    "course-plan": "OUTLINE.md",
    "course-report-plan": "OUTLINE.md",
    "thesis-proposal": "PROPOSAL_PLAN.md",
    "literature-review": "REVIEW_PLAN.md",
}
PLAN_SKILLS = frozenset(PLAN_FILE_BY_SKILL)

# ---------- 研究类型、报告类型、课程学科的判断行（与 web/backend/services/writing_profile.py 同一套，测试核对两边一致） ----------
RESEARCH_TYPES = {
    "experimental": "实验研究", "computational": "计算与算法", "simulation": "工程仿真",
    "clinical": "医学临床", "econometric": "计量实证", "survey": "问卷调查",
    "qualitative": "质性研究", "theoretical": "思辨与文本", "mixed": "混合方法",
}
RESEARCH_TYPE_ALIASES = {
    "实验": "experimental", "实验类": "experimental", "计算": "computational", "算法": "computational",
    "仿真": "simulation", "数值模拟": "simulation", "临床": "clinical", "医学": "clinical",
    "计量": "econometric", "实证": "econometric", "问卷": "survey", "质性": "qualitative",
    "访谈": "qualitative", "案例": "qualitative", "思辨": "theoretical", "理论": "theoretical",
    "文本": "theoretical", "混合": "mixed",
    "experiment": "experimental", "experiments": "experimental", "algorithmic": "computational",
    "engineering": "simulation", "numerical": "simulation", "medical": "clinical", "empirical": "econometric",
    "conceptual": "theoretical", "textual": "theoretical", "interpretive": "theoretical",
    "questionnaire": "survey", "interview": "qualitative", "interviews": "qualitative",
}
REPORT_KINDS = {"project": "项目或设计类", "experiment": "实验类", "survey": "调研类", "reading": "读书或文献报告类"}
REPORT_KIND_ALIASES = {
    "项目": "project", "设计": "project", "项目或设计": "project", "项目类": "project", "设计类": "project",
    "实验": "experiment", "调研": "survey", "调查": "survey", "读书": "reading", "读书报告": "reading",
    "文献报告": "reading", "读书或文献报告": "reading",
}
COURSE_SUBJECTS = {"cs": "计算机", "humanities": "人文社科", "economics": "经管", "engineering": "工程"}
COURSE_SUBJECT_ALIASES = {
    "计算机类": "cs", "计算机科学": "cs", "人文": "humanities", "社科": "humanities", "人文社会科学": "humanities",
    "经济": "economics", "管理": "economics", "经济管理": "economics", "经管类": "economics",
    "工程类": "engineering", "工学": "engineering",
}


def _decision_re(labels: str) -> re.Pattern:
    """一行"标签：取值（理由：……）"；标签可加粗，行首可以是引用号或列表符。"""
    return re.compile(
        r"^[ \t　>*\-]*(?:\*\*)?[ \t]*(?:" + labels + r")[ \t]*(?:\*\*)?[ \t]*[:：][ \t]*(?:\*\*)?[ \t]*([^\s（(*|，,；;]+)"
        r"[^（(\n]*(?:[（(]\s*(?:理由|依据|reason)\s*[:：]?\s*([^）)\n]{0,200})[）)])?",
        re.IGNORECASE | re.MULTILINE,
    )


_RESEARCH_TYPE_RE = _decision_re(r"研究类型|research\s*type")
_REPORT_KIND_RE = _decision_re(r"报告类型")
_COURSE_SUBJECT_RE = _decision_re(r"课程学科")


def _match_label(raw: str, keys: dict, aliases: dict) -> str | None:
    raw = raw.strip().strip("`*")
    low = raw.lower()
    if low in keys:
        return low
    for key, label in keys.items():
        if raw == label:
            return key
    if raw in aliases or low in aliases:
        return aliases.get(raw) or aliases.get(low)
    for label, key in [(v, k) for k, v in keys.items()] + [(k, k) for k in keys] + list(aliases.items()):
        if raw.startswith(label) or low.startswith(label):
            return key
    return None


def _first_decision(text: str, pattern: re.Pattern, keys: dict, aliases: dict) -> tuple[str | None, str, int, str] | None:
    """第一处判断行：(键或 None, 理由, 行号, 原行)；没有这一行返回 None。"""
    for m in pattern.finditer(text or ""):
        line_no = text.count("\n", 0, m.start()) + 1
        end = text.find("\n", m.start())
        line = text[m.start():end if end != -1 else len(text)]
        return _match_label(m.group(1), keys, aliases), (m.group(2) or "").strip(), line_no, line.strip()
    return None


def parse_research_type(text: str) -> tuple[str, str] | None:
    """与 writing_profile.parse_research_type 同一口径：读出 (研究类型键, 理由)；读不出返回 None。"""
    found = _first_decision(text, _RESEARCH_TYPE_RE, RESEARCH_TYPES, RESEARCH_TYPE_ALIASES)
    if not found or not found[0]:
        return None
    return found[0], found[1]


def parse_report_kind(text: str) -> tuple[str, str] | None:
    found = _first_decision(text, _REPORT_KIND_RE, REPORT_KINDS, REPORT_KIND_ALIASES)
    if not found or not found[0]:
        return None
    return found[0], found[1]


def parse_course_subject(text: str) -> tuple[str, str] | None:
    found = _first_decision(text, _COURSE_SUBJECT_RE, COURSE_SUBJECTS, COURSE_SUBJECT_ALIASES)
    if not found or not found[0]:
        return None
    return found[0], found[1]


# ---------- 读文件 ----------
def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:MAX_READ]
    except OSError:
        return ""


def load_profile(workspace: Path) -> dict | None:
    try:
        data = json.loads((Path(workspace) / SPEC_RELATIVE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    prof = data.get("profile") if isinstance(data, dict) else None
    return prof if isinstance(prof, dict) and prof.get("genre") else None


def applies(workspace: Path, stage: str, skill: str, *, source: str | None = None) -> bool:
    """学术写作工作区（有写作档案）、这一阶段有对应规则时才查；竞赛、市调、软著等没有写作档案，一律不查。
    稿件阶段还要找得到成稿（写作步没写出来，由步骤自己的检查管）。"""
    profile = load_profile(workspace)
    if profile is None:
        return False
    if stage == "plan":
        return skill in PLAN_SKILLS
    if stage == "draft" and skill not in DRAFT_SKILLS:
        return False
    if stage == "final" and skill not in FINAL_SKILLS:
        return False
    if stage not in ("draft", "final"):
        return False
    if source:
        return (Path(workspace) / source).is_file()
    return manuscript_rel(workspace, stage, skill, profile) is not None


# ---------- Markdown 表格 ----------
class Table:
    def __init__(self, start_line: int, rows: list[list[str]], heading: str):
        self.start_line = start_line      # 表头所在行（从 1 起）
        self.header = rows[0] if rows else []
        self.rows = rows[1:] if rows else []  # 数据行（已去掉分隔行）
        self.heading = heading            # 表格上方最近的标题

    def column(self, pattern: re.Pattern, default: int | None = None) -> int | None:
        for index, cell in enumerate(self.header):
            if pattern.search(_clean(cell)):
                return index
        return default


_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(?:\|\s*:?-{2,}:?\s*)*\|?\s*$")
_HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")


def _split_row(line: str) -> list[str]:
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    cells = re.split(r"(?<!\\)\|", body)
    return [cell.replace("\\|", "|").strip() for cell in cells]


def tables(text: str) -> list[Table]:
    out: list[Table] = []
    lines = text.splitlines()
    heading = ""
    i = 0
    while i < len(lines):
        m = _HEADING_RE.match(lines[i])
        if m:
            heading = m.group(2)
            i += 1
            continue
        if lines[i].lstrip().startswith("|") and i + 1 < len(lines) and _SEPARATOR_RE.match(lines[i + 1]):
            start = i
            rows = [_split_row(lines[i])]
            i += 2
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append(_split_row(lines[i]))
                i += 1
            out.append(Table(start + 1, rows, heading))
            continue
        i += 1
    return out


def _clean(cell: str) -> str:
    text = re.sub(r"<br\s*/?>", " ", cell or "", flags=re.I)
    text = text.replace("**", "").replace("`", "")
    return re.sub(r"\s+", " ", text).strip()


# ---------- 占位与"待确认" ----------
_DEFER_RE = re.compile(
    r"待作者确认|请作者确认|需作者确认|待确认|待核实|pending|to\s+be\s+confirmed|\btbc\b|"
    r"[（(]?\s*(?:见|see)?\s*open_questions(?:\.md)?\s*(?:第?\s*\d+\s*条|#\s*\d+|\d+)?\s*[）)]?",
    re.I,
)
_PLACEHOLDER_RE = re.compile(
    r"待填写?|待定|待补充?|待完善|待判断|todo|tbd|x{3,}|to\s+fill|to\s+be\s+filled|fill\s+in|"
    r"\[\s*\]|\[[^\]\n]{0,24}\]|…+|\.{3,}|［[^］\n]{0,24}］|"
    r"§\s*[XxＸ](?:\.[XxＸ])*|第\s*[XxＸNn]\s*[章节条]|\b[Xx]\.[Xx]\b",
    re.I,
)
_CJK_RE = re.compile(r"[㐀-䶿一-鿿豈-﫿]")
_WORD_RE = re.compile(r"[A-Za-z]{2,}")
_EMPTY_WORDS = {"无", "略", "空", "none", "n/a", "na", "nil", "—", "-", "/"}


def _meaningful(text: str) -> bool:
    rest = _DEFER_RE.sub(" ", text)
    rest = _PLACEHOLDER_RE.sub(" ", rest)
    rest = re.sub(r"[\s，,。.;；:：、/（）()\[\]【】\-—–_#*`'\"“”‘’]+", " ", rest).strip()
    if rest.lower() in _EMPTY_WORDS or not rest:
        return False
    return len(_CJK_RE.findall(rest)) >= 4 or len(_WORD_RE.findall(rest)) >= 3


def classify_cell(text: str, others: list[str] = ()) -> str:
    """filled（有内容）/ deferred（写明待作者确认）/ missing（空、占位、照抄了"怎么写"列）。"""
    cell = _clean(text)
    if cell and any(cell == _clean(other) for other in others if _clean(other)):
        return "missing"
    deferred = bool(_DEFER_RE.search(cell))
    if _meaningful(cell):
        return "filled_deferred" if deferred else "filled"
    return "deferred" if deferred else "missing"


def open_question_items(workspace: Path) -> list[str]:
    """OPEN_QUESTIONS.md 里的条目（去掉标题、空行和"无"）。"""
    items = []
    for raw in _read(Path(workspace) / OPEN_QUESTIONS).splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("<!--") or line.startswith(">"):
            continue
        body = re.sub(r"^(?:[-*+]|\d+[.、)）])\s*", "", line).strip()
        if body.lower().strip("。. ") in _EMPTY_WORDS or not body:
            continue
        items.append(body)
    return items


# ---------- 论证主线 ----------
ELEMENTS = (
    ("problem", "问题", ("问题", "研究问题", "problem", "question", "research question")),
    ("gap", "缺口", ("缺口", "研究缺口", "gap")),
    ("contribution", "贡献", ("贡献", "创新", "拟创新点", "contribution")),
    ("evidence", "证据", ("证据", "evidence")),
    ("scope", "边界", ("边界", "范围", "scope", "boundary", "boundaries", "limits")),
)
_SPINE_HEADING_RE = re.compile(r"论证主线|argument\s+spine", re.I)
_SELF_COLUMN_RE = re.compile(r"本文|本研究|本课题|本综述|本报告|this\s+(?:paper|study|review|work|report|thesis)", re.I)


def _element_of(first_cell: str) -> str | None:
    cell = _clean(first_cell).lower()
    for key, _label, aliases in ELEMENTS:
        if any(cell.startswith(alias) for alias in aliases):
            return key
    return None


def find_spine(text: str) -> Table | None:
    """论证主线五栏表：优先取"论证主线"标题下的表；没有就取第一列能认出 3 个以上要素的表。"""
    candidates = tables(text)
    for table in candidates:
        if _SPINE_HEADING_RE.search(table.heading or "") and sum(1 for row in table.rows if row and _element_of(row[0])) >= 2:
            return table
    for table in candidates:
        found = {_element_of(row[0]) for row in table.rows if row}
        found.discard(None)
        if len(found) >= 3:
            return table
    return None


def spine_cells(table: Table) -> dict[str, tuple[str, int, list[str]]]:
    """{要素: (本文列的内容, 行号, 同一行其他列)}"""
    col = table.column(_SELF_COLUMN_RE)
    out: dict[str, tuple[str, int, list[str]]] = {}
    for offset, row in enumerate(table.rows):
        if not row:
            continue
        key = _element_of(row[0])
        if not key or key in out:
            continue
        index = col if col is not None and col < len(row) else len(row) - 1
        others = [cell for i, cell in enumerate(row) if i not in (0, index)]
        out[key] = (row[index] if index > 0 else "", table.start_line + 2 + offset, others)
    return out


def _label(key: str) -> str:
    return next(label for k, label, _aliases in ELEMENTS if k == key)


def _item(item_id: str, title: str, status: str, message: str, locations=None) -> dict:
    return {"id": item_id, "title": title, "status": status, "message": message, "locations": list(locations or [])[:8]}


def _loc(plan_file: str, line: int, excerpt: str) -> dict:
    return {"file": plan_file, "line": line, "excerpt": _clean(excerpt)[:120]}


def check_spine(workspace: Path, plan_file: str, text: str) -> dict:
    """P1：五栏齐全、不是占位；写了"待确认"的要在 OPEN_QUESTIONS.md 里有条目。"""
    title = "论证主线五栏"
    if not text:
        return _item("P1", title, "fix", f"没有找到 {plan_file}：先写规划文件，开头放论证主线、论点—证据表、待确认问题三块"
                     "（照 _guide/OUTLINE_SKELETON.md 原样复制后填写）")
    table = find_spine(text)
    if table is None:
        return _item("P1", title, "fix",
                     f"{plan_file} 里没有\"论证主线\"五栏表（问题、缺口、贡献、证据、边界）：把 _guide/OUTLINE_SKELETON.md 里的"
                     "论证主线块原样复制到开头，再逐栏填写\"本文\"列")
    cells = spine_cells(table)
    missing, deferred, locations = [], [], []
    for key, label, _aliases in ELEMENTS:
        if key not in cells:
            missing.append(label)
            continue
        value, line, others = cells[key]
        state = classify_cell(value, others)
        if state == "missing":
            missing.append(label)
            locations.append(_loc(plan_file, line, value or label))
        elif state in ("deferred", "filled_deferred"):
            deferred.append(label)
    if missing:
        return _item("P1", title, "fix",
                     f"{plan_file} 论证主线的\"{'、'.join(missing)}\"还是空的或占位：按用户需求和材料补写；"
                     "材料里没有、又不能编的，写\"待确认（见 OPEN_QUESTIONS.md 第 N 条）\"并在 OPEN_QUESTIONS.md 列出", locations)
    if deferred and not open_question_items(workspace):
        return _item("P1", title, "fix",
                     f"论证主线的\"{'、'.join(deferred)}\"写了待确认，但 OPEN_QUESTIONS.md 里没有对应条目：逐条写清需要作者确认什么")
    if deferred:
        extra = "；主线大部分要等作者确认，正文会先用保守说法" if len(deferred) >= 3 else ""
        return _item("P1", title, "hint", f"论证主线的\"{'、'.join(deferred)}\"待作者确认（见 OPEN_QUESTIONS.md）{extra}")
    return _item("P1", title, "ok", "论证主线五栏齐全")


_RELATIVE_RE = re.compile(
    r"相对于|相对|相比|相较|较之|比起|不同于|区别于|有别于|优于|改进|弥补|补充了|拓展了|扩展了|"
    r"(?:现有|已有|以往|既有|前人|传统|主流)[^。；;]{0,30}(?:未|没有|尚未|缺少|缺乏|忽视|局限|不足|只|仅)|"
    r"\bthan\b|compared\s+(?:with|to)|relative\s+to|\bunlike\b|in\s+contrast|\bwhereas\b|prior\s+work|"
    r"existing\s+(?:work|methods?|studies|approaches)|previous\s+(?:work|methods?|studies)|outperform|improv",
    re.I,
)
_POINTER_RE = re.compile(
    # 章节可以写成区间："第 3–4 章""第三至四章"（小白实测 10-12：写了"第 3–4 章报告"仍报"没写证据指向"）
    r"[图表]\s*\d|§\s*\d|第\s*[一二三四五六七八九十\d]+(?:\s*[–—\-~～至到、,，]\s*[一二三四五六七八九十\d]+)*\s*[章节部分]|"
    r"[一二三四五六七八九十\d]+(?:\.\d+)+\s*节?|"
    r"\b(?:table|fig(?:ure)?\.?|section|sec\.|chapter|appendix)\s*(?:[A-Z]?\d|[IVX]+\b)|\b(?:fig|tab|tbl)[_:][A-Za-z\d]|"
    r"\[\d+(?:\s*[,，\-–]\s*\d+)*\]|"
    r"[\w\-]+\.(?:json|csv|xlsx?|md|py|tex|txt)\b|结果文件|实验\s*\d|访谈\s*[A-Z\d]|判决书|档案|史料|"
    r"见\s*[^\s，。；]{1,12}(?:章|节|表|图)|文献\s*\[?\d",
    re.I,
)
# 贡献逐条切开。有成序列的编号——（1）（2）、(i)(ii)、①②、1. 2.——就只按编号切，条内的分号不切；没有编号才按分号切。
# 编号只认一两位数字和罗马数字，同一种、从 1 起依次出现、至少两个才算：英文稿 "Akay (2009)" 的年份括号、
# 条末的 "Section 4." 都不是编号（第 8 期英文会议样稿曾把 3 条写全了的贡献切成 6 段、报了假提示）。
# 编号前可以是空白或标点：中文常写 "。（2）""（见表3）（2）"，前面没有空格；①② 不会有歧义，前面是什么都算。
_ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8, "ix": 9, "x": 10}
_CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"
_ITEM_MARK_RE = re.compile(
    r"(?P<circled>[①②③④⑤⑥⑦⑧⑨⑩])|"
    r"(?:^|(?<=[\s。；;：:，,）)]))(?:[（(]\s*(?P<num>\d{1,2})\s*[）)]|[（(]\s*(?P<roman>viii|vii|vi|iv|ix|iii|ii|i|v|x)\s*[）)]"
    r"|(?P<dot>\d{1,2})[.、](?!\d))", re.I)
_ITEM_SEP_RE = re.compile(r"[；;]")


def _item_cuts(line: str) -> list[int]:
    """一行里成序列的编号起点（同一种编号、从 1 起依次加 1、至少两个）；没有返回空列表。"""
    seqs: dict[str, list[int]] = {}
    want: dict[str, int] = {}
    for m in _ITEM_MARK_RE.finditer(line):
        kind = m.lastgroup
        raw = m.group(kind)
        n = int(raw) if kind in ("num", "dot") else _ROMAN[raw.lower()] if kind == "roman" else _CIRCLED.index(raw) + 1
        if n == want.get(kind, 1):
            seqs.setdefault(kind, []).append(m.start())
            want[kind] = n + 1
    best = max(seqs.values(), key=len, default=[])
    return best if len(best) >= 2 else []


def contribution_parts(value: str) -> list[str]:
    """贡献栏切成一条一条（太短的碎片不算一条）；切不出来就整栏算一条。"""
    raw = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
    parts: list[str] = []
    for line in raw.split("\n"):
        cuts = _item_cuts(line)
        if cuts:
            # 编号前的引导语不算一条：不管是"贡献有三："还是"本科论文写主要工作，不把换样本叫作理论创新。"
            # （小白实测 10-12：后一种没以冒号结尾，被当成第 1 条，报"第 1 条没写相对谁、没写证据指向"）
            pieces = [line[a:b] for a, b in zip(cuts, cuts[1:] + [len(line)])]
        else:
            pieces = _ITEM_SEP_RE.split(line)
        parts += [p.strip() for p in pieces if p.strip()]
    parts = [p for p in parts if len(_CJK_RE.findall(p)) >= 6 or len(_WORD_RE.findall(p)) >= 4]
    return parts or [_clean(value)]


def check_contributions(plan_file: str, text: str) -> dict | None:
    """P2：贡献每条有没有相对对象和证据指向（提示）。"""
    title = "贡献的相对对象与证据"
    table = find_spine(text) if text else None
    if table is None:
        return None
    cells = spine_cells(table)
    if "contribution" not in cells:
        return None
    value, line, others = cells["contribution"]
    if classify_cell(value, others) not in ("filled", "filled_deferred"):
        return _item("P2", title, "skipped", "贡献栏还没写或待作者确认，先不核对")
    parts = contribution_parts(value)
    no_relative = [str(i) for i, p in enumerate(parts, 1) if not _RELATIVE_RE.search(p)]
    no_pointer = [str(i) for i, p in enumerate(parts, 1) if not _POINTER_RE.search(p)]
    if not no_relative and not no_pointer:
        return _item("P2", title, "ok", f"贡献 {len(parts)} 条都写了相对对象和证据指向")
    bits = []
    if no_relative:
        bits.append(f"第 {'、'.join(no_relative)} 条没写相对谁（例如\"相对于某类方法\"\"现有研究在某条件下未……\"）")
    if no_pointer:
        bits.append(f"第 {'、'.join(no_pointer)} 条没写证据指向（章节、图表编号、结果文件或文献）")
    return _item("P2", title, "hint", "贡献" + "；".join(bits), [_loc(plan_file, line, value)])


def check_decisions(workspace: Path, profile: dict, plan_file: str, text: str) -> list[dict]:
    """P3：研究类型（以及课程报告的报告类型、课程论文的学科）已经确定。"""
    items = []
    rt = profile.get("research_type")
    found = _first_decision(text, _RESEARCH_TYPE_RE, RESEARCH_TYPES, RESEARCH_TYPE_ALIASES) if text else None
    if not rt:
        items.append(_item("P3", "研究类型", "skipped", "本文体不分研究类型（如文献综述）"))
    elif rt == "auto":
        if not found or not found[0]:
            where = [_loc(plan_file, found[2], found[3])] if found else []
            english = ("（英文大纲写 `Research type: computational (reason: ...)`，类型用 experimental、computational、"
                       "simulation、clinical、econometric、survey、qualitative、theoretical、mixed 之一）"
                       if profile.get("language") == "en" else "")
            items.append(_item("P3", "研究类型", "fix",
                               f"研究类型还没定：在 {plan_file} 论证主线第一行写 `研究类型：××（理由：……）`，"
                               "×× 用实验研究、计算与算法、工程仿真、医学临床、计量实证、问卷调查、质性研究、思辨与文本、混合方法之一"
                               f"{english}；拿不准就写最可能的一类，另一个候选写进 OPEN_QUESTIONS.md", where))
        elif not found[1]:
            items.append(_item("P3", "研究类型", "hint",
                               f"研究类型定为{RESEARCH_TYPES[found[0]]}，但没写理由", [_loc(plan_file, found[2], found[3])]))
        else:
            items.append(_item("P3", "研究类型", "ok", f"研究类型：{RESEARCH_TYPES[found[0]]}（AI 判断，理由：{found[1][:60]}）"))
    else:
        label = RESEARCH_TYPES.get(rt, rt)
        source = profile.get("research_type_source")
        if source == "ai":
            # AI 的判断以大纲为准（后台每步都从大纲读回）；大纲里那一行被删了才提示
            if found and found[0]:
                items.append(_item("P3", "研究类型", "ok", f"研究类型：{RESEARCH_TYPES[found[0]]}（AI 判断）"))
            else:
                items.append(_item("P3", "研究类型", "hint",
                                   f"研究类型沿用之前 AI 的判断（{label}），大纲里那一行没有了：建议在论证主线第一行写回"))
        elif found and found[0] and found[0] != rt:
            items.append(_item("P3", "研究类型", "hint",
                               f"大纲写的研究类型（{RESEARCH_TYPES[found[0]]}）和写作档案（{label}，"
                               f"{'你选的' if source == 'user' else '按学科默认'}）不一致，以写作档案为准",
                               [_loc(plan_file, found[2], found[3])]))
        else:
            items.append(_item("P3", "研究类型", "ok",
                               f"研究类型：{label}（{'你选的' if source == 'user' else '按学科默认'}）"))
    template = profile.get("template")
    if template == "course_report" and (profile.get("report_kind") in (None, "", "auto")
                                        or profile.get("report_kind_source") == "ai"):
        kind = _first_decision(text, _REPORT_KIND_RE, REPORT_KINDS, REPORT_KIND_ALIASES) if text else None
        if kind and kind[0]:
            items.append(_item("P3", "报告类型", "ok", f"报告类型：{REPORT_KINDS[kind[0]]}（AI 判断）"))
        elif profile.get("report_kind_source") == "ai":
            items.append(_item("P3", "报告类型", "hint", "报告类型沿用之前 AI 的判断，大纲里那一行没有了：建议在大纲开头写回"))
        else:
            where = [_loc(plan_file, kind[2], kind[3])] if kind else []
            items.append(_item("P3", "报告类型", "fix",
                               f"报告类型还没定：在 {plan_file} 开头写 `报告类型：××（理由：……）`，"
                               "×× 用项目或设计类、实验类、调研类、读书或文献报告类之一", where))
    if template in ("course_paper", "course_report") and (not profile.get("course_subject")
                                                          or profile.get("course_subject_source") == "ai"):
        subject = _first_decision(text, _COURSE_SUBJECT_RE, COURSE_SUBJECTS, COURSE_SUBJECT_ALIASES) if text else None
        if subject and subject[0]:
            items.append(_item("P3", "课程学科", "ok", f"课程学科：{COURSE_SUBJECTS[subject[0]]}（AI 判断）"))
        elif template == "course_paper" and not profile.get("course_subject"):
            items.append(_item("P3", "课程学科", "hint",
                               f"课程学科没写：建议在 {plan_file} 开头写 `课程学科：××（理由：……）`（计算机、人文社科、经管、工程之一），"
                               "后面几步的写作指南会按它取学科要求"))
    return items


_CLAIM_COL_RE = re.compile(r"论点|claim", re.I)
_EVIDENCE_COL_RE = re.compile(r"证据|evidence", re.I)
_SECTION_COL_RE = re.compile(r"章节|所在|落点|section", re.I)


def check_matrix(plan_file: str, text: str) -> dict:
    """P4：论点—证据表每个论点都有证据和所在章节（提示）。"""
    title = "论点—证据表"
    table = None
    for candidate in tables(text or ""):
        if candidate.column(_CLAIM_COL_RE) is not None and candidate.column(_EVIDENCE_COL_RE) is not None:
            table = candidate
            break
    if table is None:
        return _item("P4", title, "hint", f"{plan_file} 里没找到论点—证据表（表头含\"论点\"和\"证据\"）")
    claim_col = table.column(_CLAIM_COL_RE)
    evidence_col = table.column(_EVIDENCE_COL_RE)
    section_col = table.column(_SECTION_COL_RE)
    rows = []
    for offset, row in enumerate(table.rows):
        claim = row[claim_col] if claim_col < len(row) else ""
        if classify_cell(claim) == "missing":
            continue
        rows.append((offset, row))
    if not rows:
        return _item("P4", title, "hint", "论点—证据表还没填（只有表头或占位行）", [_loc(plan_file, table.start_line, " | ".join(table.header))])
    no_evidence, no_section, locations = [], [], []
    for offset, row in rows:
        line = table.start_line + 2 + offset
        evidence = row[evidence_col] if evidence_col < len(row) else ""
        if classify_cell(evidence) == "missing":
            no_evidence.append(line)
            locations.append(_loc(plan_file, line, row[claim_col]))
        if section_col is not None:
            section = row[section_col] if section_col < len(row) else ""
            if not _clean(section) or _PLACEHOLDER_RE.fullmatch(_clean(section) or "x"):
                no_section.append(line)
    if not no_evidence and not no_section:
        return _item("P4", title, "ok", f"论点—证据表 {len(rows)} 条论点都有证据和所在章节")
    bits = []
    if no_evidence:
        bits.append(f"{len(no_evidence)} 条论点没写证据（没有就写\"待补\"并说明缺什么）")
    if no_section:
        bits.append(f"{len(no_section)} 条论点没写所在章节")
    return _item("P4", title, "hint", "论点—证据表有 " + "、".join(bits), locations)


# ======================================================================
# 稿件阶段：写作步完成后（draft）、编译或导出步完成后（final），规划附录 B 的 S/I/R/D/C/N/K/T/H 组
# ======================================================================
REPORT_NAME = "WRITING_CHECK.md"
# 写作步 → 成稿（LaTeX 从 main.tex 起跟着 \input 读；Word 稿是单个 Markdown）
DRAFT_TARGET_BY_SKILL = {
    "paper-write": "paper/main.tex", "paper-write-zh": "paper/main.tex", "paper-write-nature": "paper/main.tex",
    "humanities-write-latex": "paper/main.tex",
    "paper-write-docx": "paper/main.md", "paper-write-zh-docx": "paper/main.md",
    "paper-write-nature-docx": "paper/main.md",
    "humanities-write": "HUMANITIES_PAPER.md", "course-paper": "COURSE_PAPER.md", "course-report": "COURSE_REPORT.md",
    "thesis-proposal": "PROPOSAL.md", "literature-review": "LITERATURE_REVIEW.md",
}
DRAFT_SKILLS = frozenset(DRAFT_TARGET_BY_SKILL)
COMPILE_SKILLS = frozenset({"paper-compile", "paper-compile-zh"})
FINAL_SKILLS = COMPILE_SKILLS | {"docx-export"}
# Word 导出步按模板找源稿（与 workflow_engine 的 docx-export、routers/editor._resolve_main_md 同一顺序）
WORD_SOURCE_BY_TEMPLATE = {
    "thesis_proposal": ("PROPOSAL.md",), "literature_review": ("LITERATURE_REVIEW.md",),
    "course_paper": ("COURSE_PAPER.md",), "course_report": ("COURSE_REPORT.md",),
    "humanities_paper": ("HUMANITIES_PAPER.md",),
}
PLAN_FILE_BY_TEMPLATE = {
    "humanities_paper": "OUTLINE.md", "course_paper": "OUTLINE.md", "course_report": "OUTLINE.md",
    "thesis_proposal": "PROPOSAL_PLAN.md", "literature_review": "REVIEW_PLAN.md",
}
MAX_MANUSCRIPT = 1_500_000
MAX_LOCATIONS = 8

JOURNALS = frozenset({"journal_cn", "journal_en", "humanities_journal", "nature"})
DISCUSSION_JOURNALS = frozenset({"journal_cn", "journal_en", "nature"})
CONFERENCES = frozenset({"ml_conf", "conf_en"})
STEM_THESES = frozenset({"bachelor", "master", "doctor"})
THESES = STEM_THESES | {"humanities_thesis"}
HUMANITIES = frozenset({"humanities_course", "humanities_thesis", "humanities_journal"})


def manuscript_rel(workspace: Path, stage: str, skill: str, profile: dict) -> str | None:
    """本阶段要查的成稿（工作区相对路径）；没有返回 None。"""
    ws = Path(workspace)
    if stage == "draft":
        rel = DRAFT_TARGET_BY_SKILL.get(skill)
        return rel if rel and (ws / rel).is_file() else None
    if stage != "final":
        return None
    if skill in COMPILE_SKILLS:
        return "paper/main.tex" if (ws / "paper" / "main.tex").is_file() else None
    if skill == "docx-export":
        template = str(profile.get("template") or "")
        if template == "paper_from_assets" and profile.get("genre") == "course_paper":
            candidates = ("COURSE_PAPER.md", "paper/main.md")
        else:
            candidates = WORD_SOURCE_BY_TEMPLATE.get(template, ("paper/main.md",))
        for rel in candidates:
            if (ws / rel).is_file():
                return rel
    return None


def plan_rel_for(profile: dict) -> str:
    return PLAN_FILE_BY_TEMPLATE.get(str(profile.get("template") or ""), "PAPER_PLAN.md")


# ---------- 读稿与等长屏蔽（移植自语言原型 asc_proto.py，2026-10-09 在真实稿上实测过误报） ----------
CJK = "\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"
_CJK_CHAR = re.compile(f"[{CJK}]")


def _scope_module():
    """tools/paper_source_scope.py：LaTeX 实际生效的源文件和 \\input 展开（与 services/、shared-scripts/ 同一份）。"""
    here = Path(__file__).resolve().parent
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))  # 嵌入版运行时不把脚本目录加进 sys.path
    import paper_source_scope  # noqa: PLC0415
    return paper_source_scope


class Doc:
    """raw：成稿原文（LaTeX 已展开 \\input、去掉注释）；prose：只剩读者看得到的正文，其余等长换成空格。"""

    def __init__(self, label: str, raw: str, fmt: str, locate=None, files: dict | None = None):
        self.label, self.fmt = label, fmt
        self.raw = raw
        self.prose = raw
        self.math_ctx: list[tuple[int, int]] = []
        self.quote_ctx: list[tuple[int, int]] = []
        self.math_spans: list[tuple[int, int]] = []
        self.ref_span: tuple[int, int] | None = None
        self.line_starts = [0] + [m.end() for m in re.finditer("\n", raw)]
        self._locate = locate
        self.files = files or {}           # 读到的源文件 → sha256（结论与稿件版本绑定）
        self._sections = None
        self._regions = None
        self._sents = None
        self._sent_starts: list[int] = []

    def blank_spans(self, spans):
        if not spans:
            return
        chars = list(self.prose)
        for a, b in spans:
            for i in range(max(0, a), min(b, len(chars))):
                if chars[i] != "\n":
                    chars[i] = " "
        self.prose = "".join(chars)

    def location(self, off: int) -> tuple[str, int]:
        off = max(0, min(off, len(self.raw)))
        if self._locate is not None:
            try:
                return self._locate(off)
            except Exception:  # noqa: BLE001 — 定位失败就退回主文件行号
                pass
        return self.label, bisect.bisect_right(self.line_starts, off)

    def excerpt(self, start: int, end: int | None = None, width: int = 26) -> str:
        """命中处的前后文（读者看得到的文字），命中部分用 ⟦⟧ 标出。"""
        end = start + 2 if end is None else max(end, start + 1)
        ls = self.prose.rfind("\n", 0, start) + 1
        le = self.prose.find("\n", end)
        le = len(self.prose) if le < 0 else le
        seg_a = self.prose[max(ls, start - width):start]
        seg_m = self.prose[start:min(end, le)]
        seg_b = self.prose[min(end, le):min(le, end + width)]
        text = re.sub(r"\s+", " ", seg_a + "⟦" + seg_m + "⟧" + seg_b).strip()
        if text.replace("⟦", "").replace("⟧", "").strip() == "":
            raw = re.sub(r"\s+", " ", self.raw[start:min(len(self.raw), start + 60)]).strip()
            return raw[:120]
        return text[:160]

    def sentences(self) -> list[tuple[int, int]]:
        if self._sents is None:
            self._sents = _sentences(self.prose)
            self._sent_starts = [a for a, _ in self._sents]
        return self._sents

    def sections(self) -> list["Section"]:
        if self._sections is None:
            self._sections = _sections(self)
        return self._sections

    def regions(self) -> list[tuple[int, int, str]]:
        if self._regions is None:
            self._regions = _regions(self)
        return self._regions


def _blank(s: str) -> str:
    return re.sub(r"[^\n]", " ", s)


def _spans(pattern, text, flags=0, group=0):
    return [(m.start(group), m.end(group)) for m in re.finditer(pattern, text, flags)]


TEX_BLANK_ENVS = ("verbatim", "lstlisting", "minted", "comment", "equation", "align", "gather", "multline",
                  "eqnarray", "displaymath", "math", "tabular", "tabularx", "tabulary", "longtable", "array",
                  "tikzpicture", "algorithmic", "algorithm", "thebibliography")
TEX_MATH_ENVS = ("theorem", "lemma", "proof", "proposition", "corollary", "definition")
TEX_DROP_CMDS = (r"cite[tp]?|citep|citet|citealp|citeauthor|citeyear|parencite|textcite|autocite|footcite|upcite|"
                 r"supercite|ref|eqref|autoref|cref|Cref|pageref|label|url|input|include|includegraphics|bibliography|"
                 r"bibliographystyle|usepackage|documentclass|hypersetup|setlength|vspace|hspace|addcontentsline|"
                 r"newcommand|renewcommand|pagestyle|thispagestyle|zihao|fontsize|setcounter|addtocounter|graphicspath|"
                 r"nocite|SI|si|qty|num|unit|ang|setmainfont|setCJKmainfont|geometry|title|author|date|maketitle|"
                 r"tableofcontents|listoffigures|listoftables|printbibliography|addbibresource")
# 参考文献节的标题：学校开题表、学位论文模板常写"八、主要参考文献""参考文献（不少于 25 篇）""参考书目""征引文献"。
# 以前只认"参考文献"四个字：开题实测 10-12 里"八、主要参考文献"一节被当成正文，文献算成 0 篇、字数把文献表也算进去
_REF_TITLE = (r"(?:主要)?(?:参考文献|参考书目|参考资料|征引文献|征引书目|引用文献|所引文献|书目)"
              r"(?:[ \t]*[（(][^）)\n]{0,40}[）)])?[ \t]*[:：]?"
              r"|(?:References?|Bibliography|Works[ \t]+Cited|Literature[ \t]+Cited|References[ \t]+and[ \t]+Notes)[ \t]*[:：]?")
_TEX_REF_HEADING = re.compile(r"\\(?:section|chapter)\*?\s*(?:\[[^\]\n]*\])?\s*\{\s*(?:" + _REF_TITLE + r")\s*\}", re.I)
_MD_REF_HEADING = re.compile(
    r"(?m)^#{1,6}[ \t]*(?:\*\*)?[ \t]*(?:第?[一二三四五六七八九十百\d]+(?:部分|[章节、.．])?|[（(][一二三四五六七八九十\d]+[）)])?[ \t]*"
    r"(?:" + _REF_TITLE + r")[ \t]*(?:\*\*)?[ \t]*$", re.I)


def mask_tex(doc: Doc) -> None:
    raw = re.sub(r"(?<!\\)%[^\n]*", lambda m: _blank(m.group()), doc.raw)
    doc.raw = raw
    doc.prose = raw
    m = re.search(r"\\begin\{document\}", raw)
    if m:
        doc.blank_spans([(0, m.end())])
    doc.blank_spans(_spans(r"\\begin\{(" + "|".join(TEX_BLANK_ENVS) + r")\*?\}.*?\\end\{\1\*?\}", raw, re.S))
    doc.math_ctx += _spans(r"\\begin\{(" + "|".join(TEX_MATH_ENVS) + r")\*?\}.*?\\end\{\1\*?\}", raw, re.S)
    math = (_spans(r"\$\$.*?\$\$", raw, re.S) + _spans(r"(?<!\\)\$(?:\\.|[^$\\\n])+?(?<!\\)\$", raw)
            + _spans(r"\\\(.*?\\\)", raw, re.S) + _spans(r"\\\[.*?\\\]", raw, re.S))
    doc.blank_spans(math)
    doc.math_spans += math
    doc.blank_spans(_spans(r"\\verb\*?(.).*?\1", raw))
    doc.blank_spans(_spans(r"\\(?:" + TEX_DROP_CMDS + r")\*?(?:\s*\[[^\]\n]*\])*(?:\s*\{[^{}\n]*\})*", raw))
    doc.blank_spans(_spans(r"\\href\s*\{[^{}]*\}", raw))
    doc.blank_spans(_spans(r"\\(?:begin|end)\s*\{[^{}]*\}(?:\s*\[[^\]\n]*\])?", raw))
    doc.blank_spans(_spans(r"\\[A-Za-z@]+\*?", doc.prose))
    chars = list(doc.prose)
    for i, ch in enumerate(chars):
        if ch in "{}~":
            chars[i] = " "
        elif ch == "\\" and i + 1 < len(chars) and chars[i + 1] in "%&_#$":
            chars[i] = " "
    doc.prose = "".join(chars)
    m = _TEX_REF_HEADING.search(raw)
    bib = re.search(r"\\begin\{thebibliography\}", raw)
    if m:
        end = re.search(r"\\(?:section|chapter|appendix)\b", raw[m.end():])
        doc.ref_span = (m.start(), m.end() + end.start() if end else len(raw))
        doc.blank_spans([doc.ref_span])
    elif bib:
        end = raw.find("\\end{thebibliography}", bib.end())
        doc.ref_span = (bib.start(), end + len("\\end{thebibliography}") if end >= 0 else len(raw))


def mask_md(doc: Doc) -> None:
    raw = doc.raw
    spans = []
    fm = re.match(r"---\n.*?\n---\n", raw, re.S)
    if fm:
        spans.append(fm.span())
    for n in range(6, 2, -1):
        for fence in ("`" * n, "~" * n):
            spans += _spans(re.escape(fence) + r".*?" + re.escape(fence), raw, re.S)
    spans += _spans(r"<!--.*?-->", raw, re.S)
    math = _spans(r"\$\$.*?\$\$", raw, re.S) + _spans(r"(?<![\\$])\$(?!\s)(?:\\.|[^$\\\n])+?(?<![\\\s])\$", raw)
    spans += math
    doc.math_spans += math
    spans += _spans(r"`[^`\n]+`", raw)
    spans += _spans(r"(?m)^\s*\|.*$", raw)                       # 表格
    spans += _spans(r"https?://\S+", raw)
    spans += _spans(r"<[A-Za-z/][^>\n]*>", raw)                 # html 标签
    doc.blank_spans(spans)
    doc.blank_spans(_spans(r"!?\[[^\]\n]*\]\(([^)\n]*)\)", raw, 0, 1))
    doc.blank_spans(_spans(r"!\[|\]\((?=[^)\n]*\))", raw))
    doc.blank_spans(_spans(r"\*\*|__|^#{1,6}\s|^>\s?|\[\^[^\]\s]+\]:?", raw, re.M))
    doc.quote_ctx += _spans(r"(?m)^>.*$", raw)
    doc.blank_spans(_spans(r"\^?\[\d+(?:\s*[,，、\-–—]\s*\d+)*\]\^?", raw))
    m = _MD_REF_HEADING.search(raw)
    if m:
        # 到附录、致谢或下一个同级（及以上）标题为止：学校表格里参考文献不一定在最后（"五、参考文献"后面还有"六、进度安排"），
        # 以前一直算到文末，后面的部分被当成文献表；"### 中文文献"这类下级标题仍在文献区里
        level = len(m.group()) - len(m.group().lstrip("#"))
        rest = raw[m.end():]
        ends = [x.start() for x in (re.search(r"(?m)^#{1,6}[ \t]*(?:附录|Appendix|致谢|致\s谢|Acknowledg)", rest),
                                     re.search(r"(?m)^#{1,%d}[ \t]+\S" % level, rest)) if x]
        doc.ref_span = (m.start(), m.end() + min(ends) if ends else len(raw))
        doc.blank_spans([doc.ref_span])


_DIGESTS: dict[tuple[str, int, int], str] = {}


def _sha256(path: Path) -> str:
    """文件摘要；同一路径、同样大小和修改时间的不重算（后台每次读步骤卡都要判断稿件改没改过）。"""
    stat = path.stat()
    key = (str(path.resolve()), stat.st_size, stat.st_mtime_ns)
    cached = _DIGESTS.get(key)
    if cached:
        return cached
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    if len(_DIGESTS) > 2000:
        _DIGESTS.clear()
    _DIGESTS[key] = h.hexdigest()
    return _DIGESTS[key]


def manuscript_files(workspace: Path, rel: str) -> dict[str, str]:
    """成稿实际用到的源文件 → sha256（LaTeX 含 \\input 的文件）。结论与稿件版本绑定用它。"""
    ws = Path(workspace)
    path = ws / rel
    if not path.is_file():
        return {}
    if path.suffix.lower() != ".tex":
        return {rel: _sha256(path)}
    out = {}
    for src in _scope_module().active_sources(path.parent):
        try:
            out[src.resolve().relative_to(ws.resolve()).as_posix()] = _sha256(src)
        except (OSError, ValueError):
            continue
    return out


def load_manuscript(workspace: Path, rel: str) -> Doc | None:
    """读成稿。LaTeX 从 main.tex 起展开 \\input（只读工作区内实际生效的文件），位置回到原文件和行号。"""
    ws = Path(workspace)
    path = ws / rel
    if not path.is_file():
        return None
    files = manuscript_files(ws, rel)
    if path.suffix.lower() == ".tex":
        paper_dir = path.parent
        expanded = _scope_module().expanded_documents(paper_dir)
        if not expanded:
            return None
        ex = expanded[0]
        text = ex.text.replace("\r\n", "\n").replace("\r", "\n")[:MAX_MANUSCRIPT]
        prefix = Path(rel).parent.as_posix()

        def locate(off: int) -> tuple[str, int]:
            name, line = ex.location(off, paper_dir).rsplit(":", 1)
            joined = f"{prefix}/{name}" if prefix not in ("", ".") else name
            parts: list[str] = []
            for part in joined.split("/"):
                if part == ".." and parts:
                    parts.pop()
                elif part not in ("", "."):
                    parts.append(part)
            return "/".join(parts), int(line)

        doc = Doc(rel, text, "tex", locate=locate, files=files)
        mask_tex(doc)
        return doc
    try:
        text = path.read_bytes().decode("utf-8", errors="replace")
    except OSError:
        return None
    text = text.replace("\r\n", "\n").replace("\r", "\n")[:MAX_MANUSCRIPT]
    if text.startswith("\ufeff"):
        text = " " + text[1:]
    doc = Doc(rel, text, "md", files=files)
    mask_md(doc)
    return doc


# ---------- 分句、分段 ----------
_ABBR_EN = r"(?:et al|e\.g|i\.e|Fig|Figs|Eq|Eqs|Tab|Sec|No|vs|cf|Ref|Refs|approx|Dr|Prof|Inc|Ltd|Co|Jr|St|pp|p)\."


def _sentences(prose: str) -> list[tuple[int, int]]:
    out, start = [], 0
    for m in re.finditer(r"[。！？!?；;]+[”’」』）)]?|(?<![0-9])\.(?=\s|$)|\n\s*\n", prose):
        end = m.end()
        # 缩写前面要是词边界："help." 结尾的 p. 不是页码缩写（第 5 期语料实测）
        if m.group().strip() == "." and re.search(r"(?<![A-Za-z])" + _ABBR_EN + r"$", prose[max(0, end - 10):end]):
            continue
        if prose[start:end].strip():
            out.append((start, end))
        start = end
    if prose[start:].strip():
        out.append((start, len(prose)))
    return out


def _paragraphs(prose: str, lo: int = 0, hi: int | None = None) -> list[tuple[int, int]]:
    hi = len(prose) if hi is None else hi
    out, pos = [], lo
    for m in re.finditer(r"\n[ \t]*\n", prose[lo:hi]):
        a, b = lo + m.start(), lo + m.end()
        if prose[pos:a].strip():
            out.append((pos, a))
        pos = b
    if prose[pos:hi].strip():
        out.append((pos, hi))
    return out


def _paragraph_span(prose: str, a: int, b: int) -> tuple[int, int]:
    """包住 [a, b) 的整段（到上下两个空行为止）。"""
    m = None
    for m in re.finditer(r"\n[ \t]*\n", prose[:a]):
        pass
    lo = m.end() if m else 0
    nxt = re.search(r"\n[ \t]*\n", prose[b:])
    hi = b + nxt.start() if nxt else len(prose)
    return lo, hi


def lang_of(text: str) -> str:
    cjk = len(_CJK_CHAR.findall(text))
    lat = len(re.findall(r"[A-Za-z]", text))
    return "zh" if cjk >= max(2, 0.3 * (cjk + lat)) else "en"


# ---------- 章节 ----------
_TEX_HEADING = re.compile(
    r"\\(part|chapter|section|subsection|subsubsection|paragraph)\*?\s*(?:\[[^\]\n]*\])?\s*\{((?:[^{}\n]|\{[^{}\n]*\})*)\}")
_MD_HEADING = re.compile(r"(?m)^(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$")
_TEX_LEVEL = {"part": -1, "chapter": 0, "section": 1, "subsection": 2, "subsubsection": 3, "paragraph": 4}
_NUMBERING = re.compile(
    r"^(?:第\s*[一二三四五六七八九十百零〇\d]+\s*(?:部分|[章节部篇])|[一二三四五六七八九十]+\s*[、.．]|"
    r"[（(]\s*[一二三四五六七八九十\d]+\s*[）)]|\d+(?:\.\d+)*\s*[、.．]?|[A-Z](?:\.\d+)*\s*[、.．]|[IVX]+\s*[、.．])\s*")
_KIND_PATTERNS = (
    ("abstract", r"^(?:摘\s*要|中文摘要|英文摘要|abstract)$"),
    ("keywords", r"^(?:关键词|关键字|key\s*words?)$"),
    ("intro", r"引\s*言|绪\s*论|前\s*言|导\s*论|导\s*言|引论|问题的提出|introduction"),
    ("review", r"文献综述|研究综述|相关(?:工作|研究)|研究现状|国内外(?:研究)?现状|文献回顾|学术史|研究回顾|研究述评|"
               r"文献述评|related\s+work|literature\s+review|prior\s+work|background\s+and\s+related"),
    ("method", r"方法|研究设计|实验设计|材料与|数据与|数据来源|研究思路|技术路线|模型构建|模型设计|系统设计|"
               r"\bmethods?\b|methodology|materials|study\s+design|\bapproach\b|proposed"),
    ("results", r"结果|实验(?!设计)|实证分析|实证检验|研究发现|性能评估|\bresults?\b|\bexperiments?\b|evaluation|"
                r"findings|empirical"),
    ("discussion", r"讨论|discussion"),
    # 结论、局限：关键词前最多 6 个字且不隔标点，后面是结尾、空格或"与/和/及/、/："（"研究结论与政策启示""第六章 总结与展望"
    # "结 语"）；"稳健性检验：控制人口特征后结论不变""供给不足的原因"这种句中出现不算
    ("conclusion", r"^[^，,：:；;。！？!?]{0,6}?(?:结\s*论|结\s*语|结\s*束\s*语|总\s*结|余\s*论)(?=$|\s|[与和及、，,：:；;（(—\-])|"
                   r"^conclu(?:sions?|ding)\b|\bconclusions?$"),
    ("limitations", r"^[^，,：:；;。！？!?]{0,6}?局限(?:性|之处)?(?=$|\s|[与和及、，,：:；;（(—\-])|"
                    r"^(?:(?:研究|本文|本研究|论文|本论文|工作|方法|模型|实验|系统)的?|(?:存在的)?问题[与和及])?不足(?:之处)?"
                    r"(?=$|\s|[与和及、，,：:；;（(—\-])|limitations?|threats\s+to\s+validity"),
    ("outlook", r"展望|未来(?:工作|研究)|今后|future\s+(?:work|research|directions)|outlook"),
    ("references", r"^(?:" + _REF_TITLE + r")$"),
    ("appendix", r"^(?:附录|appendix|appendices)"),
    ("ack", r"^(?:致谢|致\s*谢|acknowledge?ments?)$"),
    ("contribution", r"创新点|主要贡献|研究贡献|本文贡献|创新之处|特色与创新|\bcontributions?\b"),
    ("summary_review", r"述评|评述|小结"),
)


def clean_title(title: str) -> str:
    text = re.sub(r"\\[A-Za-z@]+\*?", " ", title or "")
    text = re.sub(r"[{}*`#\\]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return _NUMBERING.sub("", text).strip()


def section_kinds(title: str) -> frozenset:
    t = clean_title(title).lower()
    found = {kind for kind, pat in _KIND_PATTERNS if re.search(pat, t, re.I)}
    if found & {"references", "ack", "appendix"}:
        found &= {"references", "ack", "appendix"}
    if re.search(r"本章|本节|小结", t):
        found.discard("conclusion")          # 各章的"本章小结"不是全文结论
    return frozenset(found)


class Section:
    __slots__ = ("start", "body", "end", "level", "title", "kinds")

    def __init__(self, start, body, end, level, title, kinds):
        self.start, self.body, self.end, self.level, self.title, self.kinds = start, body, end, level, title, kinds

    def __repr__(self):  # 调试用
        return f"Section({self.level}, {self.title!r}, {sorted(self.kinds)}, {self.body}-{self.end})"


def _in_literal_env(raw: str, off: int) -> bool:
    """LaTeX 标题命令写在 verbatim 之类的环境里（示例代码），不算标题。"""
    before = raw[:off]
    for env in ("verbatim", "lstlisting", "minted", "comment"):
        if before.rfind("\\begin{" + env) > before.rfind("\\end{" + env):
            return True
    return False


_BODY_CHAPTER = frozenset({"intro", "review", "method", "results"})


def _chapter_level_of(secs, fmt: str) -> int | None:
    if not secs:
        return None
    levels = sorted({s.level for s in secs})
    tops = [s for s in secs if s.level == levels[0]]
    if len(tops) == 1 and len(levels) > 1 and tops[0] is secs[0] and \
            (not tops[0].kinds or (fmt != "tex" and not tops[0].kinds & {"abstract", "keywords"})):
        return levels[1]
    return levels[0]


def _settle_kinds(secs, fmt: str) -> None:
    """标题本身看不出来的两种情况，按位置纠正：
    1. Word/Markdown 稿第一行"# 题目"包住全文，题目里有"方法""结论"不能让全文都算方法节、结论节；
    2. 结果章、方法章里的"假设检验结论""阶段性总结"是正文小节，不是全文结论（结论的数值核对、从严区不该罩到它）。"""
    top = _chapter_level_of(secs, fmt)
    if top is None:
        return
    if secs[0].level < top:
        secs[0].kinds = frozenset()
    chapters = [s for s in secs if s.level == top]
    for s in secs:
        if s.level <= top or "conclusion" not in s.kinds:
            continue
        host = next((c for c in chapters if c.start < s.start and s.end <= c.end), None)
        if host is not None and host.kinds & _BODY_CHAPTER and not host.kinds & {"conclusion", "discussion"}:
            s.kinds = s.kinds - {"conclusion"}


def _sections(doc: Doc) -> list[Section]:
    heads = []
    if doc.fmt == "tex":
        for m in _TEX_HEADING.finditer(doc.raw):
            if _in_literal_env(doc.raw, m.start()):
                continue
            heads.append((m.start(), m.end(), _TEX_LEVEL[m.group(1)], m.group(2)))
    else:
        fences = _spans(r"(?s)```.*?```|~~~.*?~~~", doc.raw)
        for m in _MD_HEADING.finditer(doc.raw):
            if any(a <= m.start() < b for a, b in fences):
                continue
            heads.append((m.start(), m.end(), len(m.group(1)), m.group(2)))
    out = []
    for i, (a, b, level, title) in enumerate(heads):
        end = len(doc.raw)
        for a2, _b2, level2, _t2 in heads[i + 1:]:
            if level2 <= level:
                end = a2
                break
        out.append(Section(a, b, end, level, clean_title(title), section_kinds(title)))
    _settle_kinds(out, doc.fmt)
    return out


def sections_of(doc: Doc, kind: str) -> list[Section]:
    return [s for s in doc.sections() if kind in s.kinds]


def top_sections_of(doc: Doc, kind: str) -> list[Section]:
    """同类节里最外层的那些（子节不重复算）。"""
    found = sections_of(doc, kind)
    return [s for s in found if not any(o is not s and o.start < s.start and s.end <= o.end for o in found)]


def chapter_level(doc: Doc) -> int | None:
    """"章"的标题层级。Word 稿第一行的 "# 题目" 常是唯一的一级标题，那就按下一级算。"""
    return _chapter_level_of(doc.sections(), doc.fmt)


def title_span(doc: Doc) -> tuple[int, int] | None:
    if doc.fmt == "tex":
        m = re.search(r"\\title\s*(?:\[[^\]\n]*\])?\s*\{((?:[^{}]|\{[^{}]*\})*)\}", doc.raw)
        return (m.start(1), m.end(1)) if m else None
    m = re.search(r"(?m)^#[ \t]+(.+)$", doc.raw)
    return (m.start(1), m.end(1)) if m else None


# ---------- 区域：摘要、结论、贡献段从严（照原型 regions()） ----------
_ABS_TOKEN = re.compile(r"摘\s*(?:(?:\\(?:hspace\*?\{[^}]*\}|quad|qquad|enspace|,)|~|　)\s*)*要|\bAbstract\b|\bABSTRACT\b")
_KW_TOKEN = re.compile(r"关键词|关键字|Key\s*words|Keywords|KEYWORDS|Index Terms")
_CONTRIB_P = re.compile(r"(?:本文|本研究|本论文|本课题)的?(?:主要)?(?:贡献|创新(?:点|之处)?)|主要贡献(?:如下|包括|有|在于)|"
                        r"(?:[Oo]ur|[Tt]he) (?:main |key |primary )?contributions? (?:are|is|of this|include)|"
                        r"[Ww]e make the following contributions|[Ww]e summari[sz]e our contributions")
KEY_REGIONS = frozenset({"abstract", "conclusion", "contribution"})


def _regions(doc: Doc) -> list[tuple[int, int, str]]:
    raw, out = doc.raw, []
    heads = doc.sections()
    for m in re.finditer(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", raw, re.S):
        out.append((m.start(1), m.end(1), "abstract"))
    head_ctx = re.compile(r"\s*(?:#{1,6}\s*|\\(?:chapter|section)\*?\{|\\textbf\{|\{\\[a-z]+\s*|"
                          r"\{\\zihao\{[^}]*\}\\[a-z]+\s*|\*\*|\\begin\{center\}\s*|[\s{]*)")
    abs_heads = []
    for m in _ABS_TOKEN.finditer(raw):
        line_start = raw.rfind("\n", 0, m.start()) + 1
        if head_ctx.fullmatch(raw[line_start:m.start()]):
            abs_heads.append(m)
    for k, m in enumerate(abs_heads):
        if any(a <= m.start() < b for a, b, _ in out):
            continue
        nl = raw.find("\n", m.end())
        rest = raw[m.end():nl if nl >= 0 else len(raw)]
        start = m.end() if rest.strip(" ：:*}\t") else (nl + 1 if nl >= 0 else m.end())
        nxt = [_KW_TOKEN.search(raw, start)] + ([abs_heads[k + 1]] if k + 1 < len(abs_heads) else [])
        later = [h for h in heads if h.start > start]
        ends = [x.start() for x in nxt if x] + ([later[0].start] if later else []) + [len(raw)]
        end = min(ends)
        if end - start > 20:
            out.append((start, end, "abstract"))
    for s in heads:
        if "conclusion" in s.kinds:
            out.append((s.body, s.end, "conclusion"))
        elif "contribution" in s.kinds:
            out.append((s.body, s.end, "contribution"))
        elif "intro" in s.kinds:
            out.append((s.body, s.end, "intro"))
    for m in _CONTRIB_P.finditer(raw):
        pstart = raw.rfind("\n\n", 0, m.start())
        pstart = 0 if pstart < 0 else pstart
        tail = raw[m.end():]
        lst = re.match(r"(?s).*?(?:\n\s*\n|$)(?:\s*\\begin\{(?:itemize|enumerate)\}.*?\\end\{(?:itemize|enumerate)\})?", tail)
        end = m.end() + (lst.end() if lst else 0)
        mm = re.match(r"(?:\s*(?:[-*+]|\d+[.)、]|（\d+）|\(\d+\))\s+[^\n]*\n?)+", raw[end:])
        if mm:
            end += mm.end()
        out.append((pstart, end, "contribution"))
    return out


def region_at(regs, off: int) -> str:
    best = "body"
    for a, b, name in regs:
        if a <= off < b:
            if name in KEY_REGIONS:
                return name
            best = name
    return best


def abstract_spans(doc: Doc) -> list[tuple[int, int]]:
    return [(a, b) for a, b, name in doc.regions() if name == "abstract"]


def conclusion_spans(doc: Doc) -> list[tuple[int, int]]:
    return [(s.body, s.end) for s in top_sections_of(doc, "conclusion")]


def _in(off: int, spans) -> bool:
    return any(a <= off < b for a, b in spans if a is not None)


# ---------- 证据辅助（照原型） ----------
SELF_ZH = re.compile(r"本文|本研究|本论文|本课题|本项目|本方法|本模型|本系统|本报告|本综述|所提(?:出)?的?|"
                     r"提出的(?:方法|模型|框架|算法)|我们|笔者")
SELF_EN = re.compile(r"\b(?:[Ww]e|[Oo]ur|[Tt]his (?:paper|work|study|thesis|article|research|report|review)|"
                     r"[Tt]he proposed)\b")
CITE_RAW = re.compile(
    r"\\(?:cite[a-zA-Z]*|upcite|parencite|textcite|autocite|footcite|supercite)\*?\s*(?:\[[^\]]*\]\s*)*\{[^{}]+\}"
    r"|\\footnote\s*\{"
    r"|\[\s*\d+(?:\s*[-–—,，、]\s*\d+)*\s*\]"
    r"|\[\^[^\]\s]+\]"
    r"|<sup>\s*\[?\d+"
    r"|[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]"
    r"|[（(][^（）()\n]{1,40}?[,，]\s*(?:19|20)\d{2}[a-z]?(?:\s*[:：，,]\s*(?:第\s*)?\d+(?:\s*[-–—]\s*\d+)?\s*页?)?[）)]"
    r"|[" + CJK + r"]{2,4}(?:等人?)?\s*[（(]\s*(?:19|20)\d{2}[a-z]?\s*[）)]"
    r"|[A-Z][A-Za-z\-']+(?: et al\.?| and [A-Z][A-Za-z\-']+)?\s*\(\s*(?:19|20)\d{2}[a-z]?\s*\)"
    r"|\([A-Z][A-Za-z\-' ]+(?: et al\.)?,? (?:19|20)\d{2}[a-z]?\)"
    r"|[A-Z][a-z]+ et al\.")
# 做过统计检验的写法。只认检验本身：p 值、置信区间、检验统计量、检验名称、显著性水平、回归表的显著性星号。
# "有待检验""test set"、Adam 的 β、Markdown 加粗的 ** 都不算（第 5 期语料实测：原型的"检验""tests?"让"显著"永远不报）
STATS = re.compile(
    r"(?i)\bp\s*(?:[<=>≤≥]|\\(?:le|leq|ge|geq|lt|gt)\b)\s*0?\.\d+|\bp\s*[-–]?\s*values?\b|[pP]\s*值|置信区间|\bCI\b|"
    r"\bt\s*\(\s*\d+\s*\)\s*=|\bt\s*=\s*-?\d|\bF\s*\(\s*\d+\s*,\s*\d+\s*\)|\bF\s*=\s*\d|χ\s*[²2]|\\chi\^?\{?2|\bz\s*=\s*-?\d|标准误|"
    r"(?:[tTFzZ]|卡方|χ2|秩和|符号秩|配对\s*t?|独立样本\s*t?|单样本\s*t?|显著性|假设|单位根|Hausman|Sobel|Bootstrap|"
    r"Breusch-Pagan|White|Durbin-Watson|置换|Kolmogorov-Smirnov|Shapiro-Wilk)\s*检验|"
    r"Wilcoxon|Mann[-–]Whitney|Kruskal|ANOVA|方差分析|Tukey|Bonferroni|McNemar|Fisher\s*精确|"
    r"\b(?:t|chi-square|chi-squared|Wilcoxon|permutation|paired|two-sided|one-sided|signed-rank|rank-sum)[- ]tests?\b|"
    r"\d+\s*\\?%\s*(?:的)?(?:统计)?(?:显著性)?水平|at the \d+\s*\\?%\s*level|statistically significant|"
    r"\d\s*\*{2,3}(?!\*)|\^\{?\*{1,3}\}?")   # 显著性星号只认数字后、上标里的（不认 Markdown 加粗）
SCOPE = re.compile(r"检索|查新|数据库|知网|CNKI|万方|维普|Web of Science|WoS|Scopus|PubMed|IEEE Xplore|Google Scholar|"
                   r"searched|search(?:ed)? (?:up )?to|as of|databases?")
DATE = re.compile(r"(?:19|20)\d{2}\s*年(?:\s*\d{1,2}\s*月)?|(?:January|February|March|April|May|June|July|August|"
                  r"September|October|November|December)\s+(?:19|20)\d{2}|截至|截止")
MATHCTX = re.compile(
    r"定理|引理|命题|推论|公式|式\s*[（(]?\s*\d|等式|不等式|收敛|极限|附录\s*[A-Z]|Theorem|Lemma|Proposition|"
    r"Corollary|Eq\.|equation|Appendix|induction|数学归纳|当且仅当|证明见|证明如下|可证|易证|得证|证毕|the proof|"
    r"we prove|单调|可分解|等价|必要(?:条件|项)|充分(?:条件|必要|性)|唯一|存在性|上界|下界|凸|可行解|最优解|可行域|"
    r"性质|递推|归纳|严格|monoton|equivalen|bound|convex|optimal")
ZH_COMPOUNDS = re.compile(
    r"其实(?=际|质|现|验|施|力|例|测|证|体|物)|首次(?=使用|出现|提及|引用|定义|访问|迭代|运行|见于|发表|就诊|确诊|发病|"
    r"入院|治疗|用药|手术|接种|给出全称|给出定义)|超级(?=节点|计算|电容|稻|链接|用户|市场|工程|对偶)|必然性|显著性|"
    r"领先指标|唯一解|唯一性|对称性打破|蛮力|蛮横")
EMPIRICAL = re.compile(r"实验|实证|数据|结果|调查|问卷|统计|回归|样本|案例|仿真结果|测试结果|results?|data|experiment|"
                       r"evidence|findings?|survey")
NEG_ZH = re.compile(r"(?:并非|并不|不是|并未|未|没有|尚未|尚无|无法|不能|不宜|难以|不可|非|绝非|未见|谈不上|称不上|而非|"
                    r"不再|不必|不应|不得|避免|切忌|勿|是否)[^，。；！？]{0,4}$")
NEG_EN = re.compile(r"(?i)\b(?:not|no|never|neither|nor|without|cannot|can't|isn't|aren't|wasn't|weren't|don't|"
                    r"doesn't|didn't|hardly|unlikely|whether)\b(?:\W+\w+){0,3}\W*$")
ATTRIB_BEFORE = re.compile(r"(?:称|所谓|指出|认为|写道|表示|提出|宣称|评价为|被称为|被誉为|so-called|termed|called|"
                           r"described as|refer(?:red)? to as)[\s“\"「]*$")
META_AFTER = re.compile(r"^[”\"」』]?\s*(?:一类|这类|此类|之类|式的|式|等(?:表述|说法|字样|用语|提法|措辞|自我评价)?|"
                        r"这样的|的说法|的提法|字样|words?|phrases?|expressions?|claims?)")
_REFNUM = re.compile(
    r"(?i)(?:Table|Tab\.|Fig(?:ure)?\.?|Section|Sec\.|Eq(?:uation)?\.?|Appendix|Chapter|图|表|式|第|章|节|附录)\s*[~\s]*"
    r"[（(]?\d+(?:[.\-]\d+)*[）)]?|\d+(?:\.\d+)+\s*(?:节|小节)|\\(?:ref|eqref|cite\w*)\{[^}]*\}|\[\d+(?:\s*[,，\-–]\s*\d+)*\]")


def has_quantity(text: str) -> bool:
    """同句里有实际数值（不算图表、章节、式、文献编号）。"""
    return bool(re.search(r"\d", _REFNUM.sub(" ", text)))


def quote_spans(raw: str) -> list[tuple[int, int]]:
    spans = []
    for pat in (r"“[^”\n]{0,400}”", r"‘[^’\n]{0,200}’", r"「[^」\n]{0,200}」", r"『[^』\n]{0,200}』",
                r"``[^'\n]{0,200}''", r"(?<![A-Za-z0-9])\"[^\"\n]{1,200}\""):
        spans += _spans(pat, raw)
    return spans


def cited(doc: Doc, a: int, b: int) -> bool:
    return bool(CITE_RAW.search(doc.raw[a:b]))


def _self(lang: str):
    return SELF_ZH if lang == "zh" else SELF_EN


# ---------- 用户自己的文字（题目、需求、检查点意见）：K1、S1 的例外和 T3 的核对来源 ----------
def user_texts(workspace: Path) -> str:
    ws = Path(workspace)
    parts = []
    try:
        with (ws / "CLAUDE.md").open(encoding="utf-8", errors="replace") as handle:
            first = handle.readline()
        parts.append(re.sub(r"^#\s*研究项目\s*[:：]\s*", "", first))
    except OSError:
        pass
    for name in ("CUSTOM_REQUIREMENTS.md", "checkpoint_feedback.md", "FORMAT_REQUIREMENTS.md"):
        parts.append(_read(ws / name)[:200_000])
    return "\n".join(parts)


_USER_OUTLINE_LINE = re.compile(
    r"(?m)^[ \t>*\-]*(?:#{1,6}[ \t]*|第[一二三四五六七八九十\d]+[章节部分]|[一二三四五六七八九十]+[、.．]|\d+(?:\.\d+)*[、.．\s])"
    r"[^\n]{2,40}$")


def user_gave_outline(user_text: str) -> bool:
    """用户需求里给了自己的大纲（3 行以上章节式的行，或明说大纲、目录、章节安排）。"""
    if re.search(r"大纲|目录|章节安排|章节结构|结构如下|按以下结构|按照以下结构|\boutline\b|table of contents", user_text or "", re.I):
        return True
    return len(_USER_OUTLINE_LINE.findall(user_text or "")) >= 3


# ---------- 用户上传的原文（H 组、T3 的核对来源） ----------
EXTRACT_SUFFIXES = ("_extracted.md", "_extracted.txt", "_doc_extracted.md", "_doc_extracted.txt", "_textlayer.txt")
PAGED_SUFFIX = "_paged.txt"
_PAGE_MARK = re.compile(r"〔PDF 第 (\d+) 页｜(?:印刷页码 ([^〕\n]{1,24})|印刷页码未知)〕")
_VISION_PAGE = re.compile(r"(?m)^## 第 (\d+) 页\s*$")
# 图像识别出的提取文字的首行说明（与 web/backend/services/extract_worker.py 的 _VISION_HEADER_MARKERS 一致）
_OCR_HEADERS = ("内容提取（Vision OCR）", "内容提取（部分识别")
_TEXT_SUFFIXES = {".txt", ".md", ".csv", ".tsv", ".json"}
_PUNCT = re.compile(r"[\s\u3000，。、；：？！“”‘’「」『』《》〈〉（）()\[\]【】{}…—–\-·,.;:?!'\"`~*_#|/\\<>^]+")


def _norm(text: str) -> str:
    return _PUNCT.sub("", unicodedata.normalize("NFKC", text or "")).lower()


class Source:
    """一份原文：归一化后的文字；分页文件还记下每个字在 PDF 第几页、各页的印刷页码。"""

    def __init__(self, name: str, text: str, kind: str, *, ocr: bool = False):
        self.name, self.kind = name, kind            # kind: paged / extracted / text
        self.ocr = ocr                               # 图像识别出的文字（可能有识别误差）：H5 只提示
        self.labels: dict[int, str | None] = {}
        self.page_of: list[int] | None = None
        if kind == "paged":
            out, pages, page, pos = [], [], 0, 0
            for m in list(_PAGE_MARK.finditer(text)) + [None]:
                chunk = text[pos:m.start()] if m else text[pos:]
                norm = _norm(chunk)
                out.append(norm)
                pages.extend([page] * len(norm))
                if m is None:
                    break
                page = int(m.group(1))
                self.labels[page] = (m.group(2) or "").strip() or None
                pos = m.end()
            self.norm, self.page_of = "".join(out), pages
        else:
            self.norm = _norm(text)


def load_sources(workspace: Path, *, limit_bytes: int = 60 * 1024 * 1024, limit_files: int = 400) -> list[Source]:
    """user_data/ 里后台提取的文字（4 种提取文件、带分页的 _paged.txt）和用户直接上传的文本文件。
    带分页的排在最前：同一份 PDF 的 _extracted.txt 和 _paged.txt 内容相同，引语要先在有印刷页码的那份里找到，
    H2 才核得了页码（按文件名排 _extracted 在前，真实工作区里页码核对曾经从不生效）。"""
    base = Path(workspace) / "user_data"
    if not base.is_dir():
        return []
    out: list[Source] = []
    used = 0
    for root, dirs, names in os.walk(base):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and not d.endswith("_media"))
        for name in sorted(names):
            if len(out) >= limit_files:
                return sorted(out, key=lambda s: s.kind != "paged")
            path = Path(root) / name
            if name.startswith(".") or name.endswith("_extracted_check.md"):
                continue
            if name.endswith(PAGED_SUFFIX):
                kind = "paged"
            elif name.endswith(EXTRACT_SUFFIXES):
                kind = "extracted"
            elif path.suffix.lower() in _TEXT_SUFFIXES:
                kind = "text"
            else:
                continue
            try:
                size = path.stat().st_size
                if used + size > limit_bytes:
                    continue
                used += size
                text = path.read_bytes().decode("utf-8", errors="replace")
            except OSError:
                continue
            ocr = False
            if kind == "extracted":
                first = _VISION_PAGE.search(text)          # 跳过系统写的识别说明
                ocr = bool(first) or any(mark in text[:400] for mark in _OCR_HEADERS)
                text = text[first.start():] if first else text
            out.append(Source(path.relative_to(Path(workspace)).as_posix(), text, kind, ocr=ocr))
    return sorted(out, key=lambda s: s.kind != "paged")     # 稳定排序：带分页的在前，其余保持原顺序


def _find_part(sources: list[Source], q: str, threshold: float):
    for src in sources:
        i = src.norm.find(q)
        if i >= 0:
            return src, i, i + len(q)
    if len(q) < 10:
        return None
    best = None
    anchors = {q[:6], q[len(q) // 2 - 3:len(q) // 2 + 3], q[-6:]}
    for src in sources:
        hay = src.norm
        seen: set[int] = set()
        for anchor in anchors:
            shift = q.find(anchor)
            start = 0
            for _ in range(60):
                i = hay.find(anchor, start)
                if i < 0:
                    break
                start = i + 1
                lo = max(0, i - shift - 8)
                if lo in seen:
                    continue
                seen.add(lo)
                window = hay[lo:lo + len(q) + 16]
                matcher = difflib.SequenceMatcher(None, q, window, autojunk=False)
                blocks = [blk for blk in matcher.get_matching_blocks() if blk.size]
                ratio = sum(blk.size for blk in blocks) / len(q)
                if ratio >= threshold and (best is None or ratio > best[0]):
                    best = (ratio, src, lo + blocks[0].b, lo + blocks[-1].b + blocks[-1].size)
    return (best[1], best[2], best[3]) if best else None


def find_in_sources(sources: list[Source], quote: str, *, threshold: float = 0.9):
    """引语在原文里的位置：归一化后子串匹配，找不到再用局部相似度（≥threshold）。中间用省略号隔开的，
    各段都要在同一份原文里按顺序找到。返回 (Source, 起点, 终点) 或 None。"""
    parts = [_norm(p) for p in re.split(r"…+|\.{3,}|⋯+|……", quote or "")]
    parts = [p for p in parts if len(p) >= 4]
    if not parts:
        return None
    if len(parts) == 1:
        return _find_part(sources, parts[0], threshold)
    for src in sources:
        pos, first = 0, None
        for part in parts:
            hit = _find_part([src], part, threshold)
            if hit is None or hit[1] < pos:
                break
            first = hit[1] if first is None else first
            pos = hit[2]
        else:
            return src, first, pos
    return None


# 引文里的校勘记号不算改字：〔县〕［县］[sic]（原文如此）（引者注：……）（下同）
_EDITORIAL = re.compile(r"〔[^〕\n]{0,20}〕|［[^］\n]{0,20}］|\[\s*sic\s*\]|"
                        r"[（(]\s*(?:sic|原文如此|下同|引者[^）)\n]{0,20}|笔者[^）)\n]{0,20})\s*[）)]", re.I)


def quote_changes(src: Source, lo: int, hi: int, quote: str) -> list[tuple[str, str]]:
    """引语和原文对上的那一段逐字比：引文里有、原文这处没有的字（改字、补字、加字）。原文多出来的不算——
    跨页引语中间夹着的页眉页脚、省略号省去的部分。返回 [(原文片段, 引文片段)]，都是去掉标点后的文字，各带前后 3 个字。"""
    parts = [_norm(p) for p in re.split(r"…+|\.{3,}|⋯+|……", _EDITORIAL.sub("", quote or ""))]
    q = "".join(p for p in parts if len(p) >= 4)
    hay = src.norm[lo:hi]
    if not q or q in hay:
        return []
    out = []
    matcher = difflib.SequenceMatcher(None, q, hay, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ("replace", "delete"):
            out.append((hay[max(0, j1 - 3):j2 + 3], q[max(0, i1 - 3):i2 + 3]))
    return out


# H6 照录原文不加引号（第 8 期样稿：人文稿多处整句照抄材料、不加引号，读者会当成作者自己的话）
H6_MIN = 20                 # 去掉标点空白后连续 20 个字与材料相同才算照录（一般是半句以上）
H6_MAX_SOURCE = 600_000     # 材料去标点后超过 60 万字不逐字比（20 字片段的集合太大）
H6_FLOOD = 0.3              # 正文三成以上与材料相同：多半是材料里有本文旧稿，不逐处列
_H6_MASK = re.compile(r"“[^”]*”|「[^」]*」|『[^』]*』|《[^》\n]{0,80}》|\"[^\"\n]{0,600}\"|^>[^\n]*$", re.M)


def unquoted_copies(doc: "Doc", sources: list[Source]) -> list[tuple[int, int]] | None:
    """正文（引号、引文块、书名号、参考文献、公式之外）连续 H6_MIN 字以上与材料逐字相同的片段 [(起点, 终点)]（doc.raw 的位置）。
    材料太大不比、正文大段与材料相同（材料里像是有本文旧稿）都不下结论，返回 None。"""
    if not sources or sum(len(s.norm) for s in sources) > H6_MAX_SOURCE:
        return None
    grams: set[str] = set()
    for src in sources:
        norm = src.norm
        grams.update(norm[i:i + H6_MIN] for i in range(len(norm) - H6_MIN + 1))
    raw = doc.raw
    skip = [(m.start(), m.end()) for m in _H6_MASK.finditer(raw)] + list(doc.math_spans)
    if doc.ref_span:
        skip.append(doc.ref_span)
    if doc.fmt != "md":
        skip += [(m.start(), m.end()) for m in re.finditer(r"\\begin\{(quote|quotation|verse)\}.*?\\end\{\1\}", raw, re.S)]
    skip.sort()
    segs: list[list[tuple[str, int]]] = []
    cur: list[tuple[str, int]] = []
    k = 0
    for i, ch in enumerate(raw):                   # 逐字去标点并记下在 raw 里的位置；遮住的地方断开
        while k < len(skip) and skip[k][1] <= i:
            k += 1
        if k < len(skip) and skip[k][0] <= i:
            if cur:
                segs.append(cur)
                cur = []
            continue
        for c in unicodedata.normalize("NFKC", ch).lower():
            if not _PUNCT.match(c):
                cur.append((c, i))
    if cur:
        segs.append(cur)
    hits: list[tuple[int, int]] = []
    copied = 0
    for seg in segs:
        text = "".join(c for c, _ in seg)
        j, n = 0, len(text)
        while j + H6_MIN <= n:
            if text[j:j + H6_MIN] not in grams:
                j += 1
                continue
            end = j + H6_MIN
            while end < n and text[end - H6_MIN + 1:end + 1] in grams:
                end += 1
            hits.append((seg[j][1], seg[end - 1][1] + 1))
            copied += end - j
            j = end
    prose = sum(len(seg) for seg in segs)
    if prose and copied > H6_FLOOD * prose:
        return None
    return hits


# ---------- 发现与汇总 ----------
class Finding:
    __slots__ = ("rule", "level", "off", "end", "note")

    def __init__(self, rule, level, off, end=None, note=""):
        self.rule, self.level, self.off, self.end, self.note = rule, level, off, end, note


RULE_TITLES = {
    "S1": "文体要求的章节", "S2": "引言末尾的结构安排", "I1": "引言提前报告结果",
    "R1": "文献罗列（甲认为、乙认为）", "R2": "\"研究表明\"后没有引用", "R3": "综述末尾没有引出本文问题",
    "R4": "中文文献没有覆盖",
    "D1": "讨论缺项", "C1": "结论在重复摘要", "C2": "结论引入了新数据",
    "N1": "话说过头（首次、填补空白、领先、优于所有）", "N2": "\"显著\"附近没有统计量", "N3": "非数学语境的\"证明了\"",
    "N4": "相关设计里用因果动词", "K1": "竞赛口吻", "K2": "串段套话（只计数，不是 AI 率）", "K3": "流程用语进了正文",
    "T1": "实验与计算的报告要素", "T2": "仿真的验证要素", "T3": "注册号与伦理批号", "T4": "计量实证的必要分析",
    "T5": "问卷调查的报告要素", "T6": "质性研究的报告要素", "T7": "模拟数据的披露",
    "H1": "原文引语核不到", "H2": "引语页码", "H3": "二手文献里的引语未核验", "H4": "学科的最低要素",
    "H5": "引语与原文不一致", "H6": "照录原文未加引号",
    "Q1": "开题必备部分", "Q2": "开题篇幅", "Q3": "参考文献篇数与构成", "Q4": "进度安排", "Q5": "计划语气",
    "Q6": "开题答辩准备",
}
RULE_FIX = {
    "N1": "删去自评（首次、填补空白、国际领先、优于所有方法），写清与最接近工作的具体差异（\"与文献[×]相比，本文……\"）；"
          "确为首次的，补检索范围与截止日期（\"经检索 CNKI、WoS（截至××年×月），未见……\"）",
    "N2": "全文没有做统计检验：把\"显著\"改为\"明显\"并给出数值（如\"降低 12.4%\"）；做了检验就补检验名、统计量和 p 值",
    "N3": "\"证明\"只用于数学证明；实证结果改为\"表明\"\"支持\"\"与……一致\"",
    "N4": "相关设计推不出因果：把\"导致\"\"决定了\"改为\"与……相关\"\"伴随\"，或写明识别策略",
    "K1": "改成学术论文的说法：\"问题一\"改为研究问题或章节名，\"问题重述\"\"模型假设\"按学术结构改写，删去评委、参赛、"
          "竞赛名称等用语",
    "R2": "在同一句紧跟具体文献引用，或删去\"研究表明\"式的模糊归因",
    "K3": "正文是写给读者的定稿：删去\"有待作者确认\"一类说明，直接写成保守的定稿表述（需要作者确认的只记进 OPEN_QUESTIONS.md）；"
          "不提用户材料、工作区、软件的文件名和检索过程；作者必须亲自补的信息（姓名、学校、伦理批号、基金号）用方括号占位，"
          "如\"［待作者填写：伦理批号］\"；用户写的材料说明、数据说明不列为参考文献，改引它们描述的原始来源",
}


def _loc_of(doc: Doc, a: int, b: int | None = None) -> dict:
    file, line = doc.location(a)
    return {"file": file, "line": line, "excerpt": doc.excerpt(a, b)}


def _finding_items(doc: Doc, findings: list[Finding]) -> list[dict]:
    """同一规则、同一级别的发现合成一项（位置最多列 8 处）。"""
    groups: dict[tuple[str, str], list[Finding]] = {}
    for f in findings:
        groups.setdefault((f.rule, f.level), []).append(f)
    items = []
    for (rule, level), fs in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1] != "fix")):
        fs.sort(key=lambda f: f.off)
        notes = list(dict.fromkeys(f.note for f in fs if f.note))
        message = RULE_FIX.get(rule, "")
        if notes:
            message = "；".join(notes[:4]) + ("；" + message if message else "")
        lead = f"{len(fs)} 处" + ("在摘要、结论或贡献段" if level == "fix" and rule == "N1" else "")
        items.append({"id": rule, "title": RULE_TITLES.get(rule, rule), "status": level,
                      "message": f"{lead}：{message}" if message else lead, "count": len(fs),
                      "locations": [_loc_of(doc, f.off, f.end) for f in fs[:MAX_LOCATIONS]]})
    return items


def _item_at(doc: Doc, rule: str, level: str, message: str, offs=(), *, count=None) -> dict:
    locations = []
    for off in list(offs)[:MAX_LOCATIONS]:
        a, b = off if isinstance(off, tuple) else (off, None)
        locations.append(_loc_of(doc, a, b))
    item = {"id": rule, "title": RULE_TITLES.get(rule, rule), "status": level, "message": message, "locations": locations}
    if count is not None:
        item["count"] = count
    return item


# ---------- S 组：结构 ----------
_LIMIT_WORDS = re.compile(r"局限|不足|限于|有待|尚未|未能|欠缺|缺憾|本(?:文|研究)(?:没有|并未|未|无法|不能|难以)|"
                          r"limitation|limited|shortcoming|caveat|weakness", re.I)
# 结论节标题本身点明了局限（"六、结论、建议与局限""结论与不足"），且下面有正文：算写了局限（真实验收 10-13：
# 局限写成"本文没有自建数据，给不出效应量……换一种分类，边界就要重画"，一个字眼都不沾，被判缺局限）
_LIMIT_TITLE = re.compile(r"局限|不足|limitation", re.I)
_OUTLOOK_WORDS = re.compile(r"展望|未来|今后|后续|下一步|进一步(?:研究|工作|探讨|考察)|future|further (?:work|research)", re.I)


def _has_body(doc: Doc, s: "Section") -> bool:
    text = doc.prose[s.body:s.end]
    return len(_CJK_CHAR.findall(text)) >= 10 or len(re.findall(r"[A-Za-z]{2,}", text)) >= 6


def separate_part(doc: Doc, kind: str, besides=()) -> bool:
    """单独成节、有正文的某类节（"第六章 总结与展望"这种标题本身不算写了展望，要看正文）。"""
    return any(_has_body(doc, s) for s in sections_of(doc, kind) if s not in besides and not s.kinds & {"conclusion"})


def has_limitations_part(doc: Doc) -> bool:
    if separate_part(doc, "limitations"):
        return True
    return bool(re.search(r"\\paragraph\*?\s*\{\s*(?:Limitations?|局限)|\\textbf\s*\{\s*(?:Limitations?|局限|研究局限|本文的局限)"
                          r"|^\s*\*\*\s*(?:Limitations?|局限|研究局限|本文的?局限|不足之处)", doc.raw, re.M))


def check_structure(doc: Doc, profile: dict, user_text: str) -> list[dict]:
    genre = str(profile.get("genre") or "")
    if genre not in JOURNALS | CONFERENCES | THESES | {"course_paper"}:
        why = "开题报告的必备部分在 Q1 查" if genre == "proposal" else "本文体不查章节要求"
        return [_item("S1", RULE_TITLES["S1"], "skipped", why)]
    outline = user_gave_outline(user_text)
    soft = outline or genre == "course_paper"
    why = ("（课程论文以老师要求为准，只提示）" if genre == "course_paper"
           else "（你在需求里给了自己的大纲，只提示）" if outline else "")
    required, advised = [], []
    if genre in DISCUSSION_JOURNALS and profile.get("research_type") != "theoretical" and not sections_of(doc, "discussion"):
        required.append("Discussion 节" if genre in ("journal_en", "nature") else "讨论（或\"结果与讨论\"）节")
    if genre in CONFERENCES and not has_limitations_part(doc):
        required.append("局限（Limitations）一节或一段")
    if genre == "conf_en" and not sections_of(doc, "discussion"):
        advised.append("Discussion 节（可以和 Limitations 合写）")
    if genre in THESES or genre == "course_paper":
        concl = top_sections_of(doc, "conclusion")
        text = " ".join(doc.prose[s.body:s.end] for s in concl)
        if not concl:
            required.append("结论（结语）章")
        else:
            titled = any(_LIMIT_TITLE.search(s.title) and _has_body(doc, s) for s in concl)
            if not (_LIMIT_WORDS.search(text) or titled or has_limitations_part(doc)):
                required.append("结语里的研究局限" if genre == "humanities_thesis" else "结论里的研究局限")
            if genre in STEM_THESES and not (_OUTLOOK_WORDS.search(text) or separate_part(doc, "outlook")):
                required.append("结论里的展望")
    items = []
    if required:
        items.append(_item("S1", RULE_TITLES["S1"], "hint" if soft else "fix",
                           f"缺{'、'.join(required)}{why}：按 _guide/WRITING_GUIDE.md 本文体一节补上；局限要对应具体结论，不写空话"))
    else:
        items.append(_item("S1", RULE_TITLES["S1"], "ok", "文体要求的章节齐全"))
    if advised:
        items.append(_item("S1", RULE_TITLES["S1"], "hint", f"建议加{'、'.join(advised)}"))
    if genre in JOURNALS:
        found = []
        for s in top_sections_of(doc, "intro"):
            for m in re.finditer(r"本文(?:的)?(?:结构|其余部分|内容)?(?:安排|组织)如下|本文其余(?:部分)?(?:内容)?(?:安排|组织)|"
                                 r"本文(?:余下|剩余)部分|[Tt]he rest of (?:this|the) paper is (?:organi[sz]ed|structured)|"
                                 r"[Tt]he remainder of (?:this|the) paper", doc.prose[s.body:s.end]):
                found.append((s.body + m.start(), s.body + m.end()))
        if found:
            items.append(_item_at(doc, "S2", "hint", "期刊引言一般不写\"本文结构安排如下\"，可以删去（学位论文可以写）", found[:3]))
    return items


# ---------- I 组：引言提前报告结果 ----------
_NUM_TOKEN = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*(%|％|‰|\\%)?")


def _num_key(value: str, pct: str | None) -> str:
    try:
        v = float(value)
    except ValueError:
        return value
    key = f"{v:.4f}".rstrip("0").rstrip(".")
    return key + ("%" if pct else "")


# 软件版本号不是数据：3.11.9 这种三段以上的点分数、"statsmodels 0.14.6""SPSS 26.0""3.2 版"
# （10-12 小白实测：引言里"分析使用 Python 3.11.9……statsmodels 0.14.6"被当成提前报告结果）
_VERSION_NUM = re.compile(
    r"\d+(?:\.\d+){2,}"
    r"|(?i:\b(?:python|spss|stata|amos|mplus|matlab|sas|eviews|smartpls|lavaan|statsmodels|semopy|scipy|numpy|pandas|"
    r"scikit-learn|sklearn|pytorch|torch|tensorflow|jasp|jamovi|nvivo|citespace|vosviewer)"
    r"\s*(?:v(?:ersion)?\.?\s*)?\d+(?:\.\d+)*)"
    r"|(?:版本号?|version)\s*[:：]?\s*\d+(?:\.\d+)*|\d+(?:\.\d+)+\s*版")


def numbers_in(text: str, *, decimals_or_pct_only: bool = False, min_int: int = 0) -> set[str]:
    clean = _VERSION_NUM.sub(" ", _REFNUM.sub(" ", text or ""))
    clean = re.sub(r"(?:19|20)\d{2}\s*(?:年|—|–|-|～|~|/)", " ", clean)
    out = set()
    for m in _NUM_TOKEN.finditer(clean):
        value, pct = m.group(1), m.group(2)
        if "." not in value and not pct:
            if decimals_or_pct_only:
                continue
            iv = int(value)
            if iv < min_int or 1900 <= iv <= 2100:
                continue
        out.add(_num_key(value, pct))
    return out


_RESULT_CLAIM_ZH = re.compile(r"(?:实验|仿真|实证|测试)结果(?:表明|显示)|实验表明|本文(?:提出的)?(?:方法|模型|算法)?(?:将|使)?"
                              r"[^。；]{0,15}(?:提高|提升|降低|减少|缩短)了")
_RESULT_CLAIM_EN = re.compile(r"(?i)\b(?:our|the proposed) (?:method|model|approach|framework) (?:achieves|improves|reduces|"
                              r"outperforms)|\bexperiments? (?:show|demonstrate)|\bour results (?:show|demonstrate)")


def check_intro_results(doc: Doc, profile: dict) -> list[dict]:
    genre = str(profile.get("genre") or "")
    clinical = profile.get("research_type") == "clinical"
    if not (genre == "journal_cn" or genre in THESES or (clinical and genre not in CONFERENCES)):
        return []
    intros = top_sections_of(doc, "intro")
    if not intros:
        return []
    intro = intros[0]
    result_secs = [s for s in doc.sections() if s.kinds & {"results", "discussion"} and s.start > intro.start]
    result_text = " ".join(doc.raw[s.body:s.end] for s in result_secs) if result_secs else doc.raw[intro.end:]
    result_nums = numbers_in(result_text, decimals_or_pct_only=True)
    heads = [(s.start, s.body) for s in doc.sections()]      # 标题行：引言下"1.1 研究背景"里的节号不是结果（同 C2）
    hits = []
    for a, b in doc.sentences():
        if a < intro.body or a >= intro.end or cited(doc, a, b):
            continue
        sent = doc.prose[a:b]
        for ha, hb in heads:
            if ha < b and hb > a:
                lo, hi = max(ha, a) - a, min(hb, b) - a
                sent = sent[:lo] + " " * (hi - lo) + sent[hi:]
        if not sent.strip():
            continue
        lg = lang_of(sent)
        common = numbers_in(sent, decimals_or_pct_only=True) & result_nums
        claim = (_RESULT_CLAIM_ZH if lg == "zh" else _RESULT_CLAIM_EN).search(sent)
        if common or (claim and _self(lg).search(sent)):
            hits.append((a + len(sent) - len(sent.lstrip()), min(b, a + 40)))
    if not hits:
        return [_item("I1", RULE_TITLES["I1"], "ok", "引言没有提前报告本研究的结果")]
    return [_item_at(doc, "I1", "hint", f"引言有 {len(hits)} 句提前报告了本研究的结果或数值：引言只写问题、缺口和本文要做什么，"
                     "结果和数字留到结果与结论部分", hits, count=len(hits))]


# ---------- R 组：综述 ----------
_NAME_ZH = r"[" + CJK + r"]{1,4}(?:等人?)?"
_NAME_EN = r"[A-Z][A-Za-z\-']+(?: et al\.?| and [A-Z][A-Za-z\-']+| 等)?"
_NAME_ORG = r"[^，。；\s]{2,16}(?:大学|学院|研究院|研究所|团队|课题组|实验室|公司|中心|机构)"
_YEAR_P = r"[（(]\s*(?:19|20)\d{2}[a-z]?\s*[）)]"
_CITE_P = r"(?:\[[\d,，\-–\s]+\]|\\cite\w*\s*(?:\[[^\]]*\]\s*)?\{[^}]*\}|\^\[[\d,，\-–]+\]\^|<sup>[^<]{1,12}</sup>)"
_AUTHOR_VERB = re.compile(
    r"^\s*(?:" + _NAME_ZH + "|" + _NAME_EN + "|" + _NAME_ORG + r")\s*(?:" + _YEAR_P + r"\s*" + _CITE_P + r"?|" + _CITE_P +
    r")\s*(?:在[^，。；]{1,20}(?:中|上|方面)\s*)?"
    r"(?:认为|提出|指出|研究了|发现|构建了|设计了|采用|利用|分析了|探讨了|考察了|证明|表明|论证|主张|强调|建立了|开发了|"
    r"proposed|showed|found|argued|introduced|developed|studied|investigated|presented|reported|designed|used|applied|"
    r"suggested|demonstrated)")
_EVAL_WORDS = re.compile(r"然而|但是|但|不足|局限|尚未|分歧|共识|相比|与之不同|这些研究|上述研究|总体而言|共同|争议|缺乏|"
                         r"however|but|whereas|in contrast|limitation|unlike|together|overall|these studies|consensus", re.I)
_VAGUE_RESEARCH_ZH = re.compile(r"(?<![本该此上前这])(?:有|已有|大量|许多|众多|不少|诸多|相关|国内外|以往|既有|近年来的?)?"
                                r"(?:研究|文献|学者|专家)(?:普遍|一致)?(?:表明|指出|认为|发现|证实|显示)|有学者|有研究者|"
                                r"有研究(?:表明|指出|发现|显示)|据研究(?:表明|指出|发现)|学界普遍认为")
_VAGUE_RESEARCH_EN = re.compile(r"(?i)\b(?:studies|research|scholars|experts|researchers|previous work|prior work|"
                                r"the literature) (?:have |has )?(?:shown|show|shows|suggest|suggests|suggested|indicate|"
                                r"indicates|argue|argues|found|demonstrated?)\b|\bit is (?:widely|generally|commonly) "
                                r"(?:believed|accepted|known)\b")
_GAP_WORDS = re.compile(r"不足|局限|尚未|缺乏|缺少|缺口|欠缺|尚无|较少|很少|极少|少见|罕见|鲜见|未见|鲜有|空白|有待|仍需|未能|没有|"
                        r"忽视|忽略|不够|少有|难以|无法|gap|lack|limited|few|rarely|seldom|scarce|insufficient|remain|"
                        r"unexplored|unresolved|overlook|neglect", re.I)
_SELF_ANY = re.compile(r"本文|本研究|本课题|本论文|本项目|this (?:paper|study|thesis|work|project)|\bwe\b", re.I)


def review_spans(doc: Doc, profile: dict) -> list[tuple[int, int]]:
    if profile.get("genre") == "review":
        secs = doc.sections()
        top = chapter_level(doc)
        body = [s for s in secs if s.level == top
                and not s.kinds & {"abstract", "keywords", "conclusion", "references", "appendix", "ack", "outlook"}]
        return [(s.body, s.end) for s in body] or [(0, len(doc.raw))]
    return [(s.body, s.end) for s in top_sections_of(doc, "review")]


def check_review(doc: Doc, profile: dict) -> list[dict]:
    items = []
    genre = str(profile.get("genre") or "")
    spans = review_spans(doc, profile)
    # R1：连续 4 句以上"某某（年份）[n] 认为/提出"，而这几段没有比较和评价
    runs = []
    for lo, hi in spans:
        run: list[tuple[int, int]] = []
        for a, b in [s for s in doc.sentences() if lo <= s[0] < hi] + [(None, None)]:
            if a is not None and _AUTHOR_VERB.search(doc.raw[a:b]):
                run.append((a, b))
                continue
            if len(run) >= 4:
                plo, _ = _paragraph_span(doc.prose, run[0][0], run[0][1])
                _, phi = _paragraph_span(doc.prose, run[-1][0], run[-1][1])
                if not _EVAL_WORDS.search(doc.prose[plo:phi]):
                    first = run[0][0] + len(doc.prose[run[0][0]:run[0][1]]) - len(doc.prose[run[0][0]:run[0][1]].lstrip())
                    runs.append((first, first + 30))
            run = []
    if spans:
        if runs:
            items.append(_item_at(doc, "R1", "hint",
                                  f"综述有 {len(runs)} 处连续 4 句以上\"某某认为、某某提出\"式罗列，而且没有比较或评价："
                                  "按观点或问题归类，写出分歧、共识和不足，再引出本文要做的", runs, count=len(runs)))
        else:
            items.append(_item("R1", RULE_TITLES["R1"], "ok", "综述没有连续罗列"))
    # R2：研究表明后同一句没有引用
    vague = []
    qspans = quote_spans(doc.raw)
    for a, b in doc.sentences():
        sent = doc.prose[a:b]
        lang = lang_of(sent)
        m = (_VAGUE_RESEARCH_ZH if lang == "zh" else _VAGUE_RESEARCH_EN).search(sent)
        if not m or cited(doc, a, b):
            continue
        prev = doc.prose[max(a, a + m.start() - 3):a + m.start()]
        if lang == "zh" and re.search(r"(?:本|该|此|上述|前述|以上|这些?|这一|笔者)$", prev):
            continue
        if _in(a + m.start(), doc.quote_ctx) or _in(a + m.start(), qspans):
            continue
        vague.append((a + m.start(), a + m.end()))
    if vague:
        items.append(_item_at(doc, "R2", "hint", f"{len(vague)} 处\"研究表明\"一类说法同一句里没有引用：" + RULE_FIX["R2"], vague,
                              count=len(vague)))
    # R3：综述最后一段要由不足引出本文问题
    if genre in THESES or genre in JOURNALS or genre == "proposal":
        tops = top_sections_of(doc, "review")
        if tops:
            last = tops[-1]
            for s in doc.sections():            # 紧跟的"述评、小结"节算在综述里
                if s.start >= last.end and s.level <= last.level:
                    if s.kinds & {"summary_review", "review"}:
                        last = s
                    break
            paras = _paragraphs(doc.prose, last.body, last.end)
            tail = doc.prose[paras[-1][0]:paras[-1][1]] if paras else ""
            if tail and not (_GAP_WORDS.search(tail) and _SELF_ANY.search(tail)):
                a = paras[-1][0] + len(tail) - len(tail.lstrip())
                items.append(_item_at(doc, "R3", "hint",
                                      "综述最后一段没有由已有研究的不足引出本文要做的：补一段述评，写清不足在哪、本文针对哪一点",
                                      [(a, a + 30)]))
            elif tail:
                items.append(_item("R3", RULE_TITLES["R3"], "ok", "综述末尾由不足引出了本文问题"))
    return items


# R4：中文期刊、学位论文没有中文文献（论证逻辑第 8 期真实样稿：改后计量篇 8 条、计量验证篇 10 条参考文献全是英文，
# OPEN_QUESTIONS.md 也没记中文检索；评审都指出"中文文献没有覆盖"）。只做提示：要求必须有，会逼模型凭记忆编中文文献；
# 检索过、查不到并在 OPEN_QUESTIONS.md 记下的不报。
R4_GENRES = THESES | {"journal_cn", "humanities_journal", "proposal", "review"}
_CN_SEARCH_NOTE = re.compile(r"中文.{0,12}(?:检索|文献|研究|题录)|知网|CNKI|万方|维普|国内(?:研究|文献)", re.I)
_REF_LINE = re.compile(r"(?m)^[ \t]*(?:[-*][ \t]*)?\\?\[?\d+\\?\]?[.、．]?[ \t]*\S.*$")


def reference_entries(workspace: Path, doc: Doc) -> list[str]:
    """参考文献条目的原文：成稿参考文献表里顺序编码的每一行、\\bibitem，以及 paper/*.bib 的每个条目。"""
    entries: list[str] = []
    if doc.ref_span:
        refs = doc.raw[doc.ref_span[0]:doc.ref_span[1]]
        entries += [m.group() for m in _REF_LINE.finditer(refs)]
        entries += re.findall(r"\\bibitem(?:\[[^\]]*\])?\{[^}]*\}([^\n]*)", refs)
    for path in sorted((Path(workspace) / "paper").glob("*.bib"))[:5]:
        text = re.sub(r"(?m)^[ \t]*%.*$", "", _read(path))     # 注释行（"% [VERIFY] 卷期页码请核对"）不是条目内容
        for entry in re.findall(r"@\w+\s*\{[^@]*", text):
            entries.append(re.sub(r"(?im)^[ \t]*(?:note|annote|abstract|keywords|comment)\s*=.*$", "", entry))
    return entries


def check_lit_coverage(workspace: Path, doc: Doc, profile: dict) -> list[dict]:
    genre = str(profile.get("genre") or "")
    if profile.get("language") != "zh" or genre not in R4_GENRES:
        return []
    entries = reference_entries(workspace, doc)
    if not entries:
        return []
    zh = [e for e in entries if len(_CJK_CHAR.findall(e)) >= 4]
    if zh:
        return [_item("R4", RULE_TITLES["R4"], "ok", f"参考文献里有 {len(zh)} 条中文文献")]
    note = Path(workspace) / "OPEN_QUESTIONS.md"
    if note.is_file() and _CN_SEARCH_NOTE.search(_read(note)):
        return [_item("R4", RULE_TITLES["R4"], "ok", "参考文献没有中文文献，OPEN_QUESTIONS.md 里记了中文检索的情况")]
    return [_item("R4", RULE_TITLES["R4"], "hint",
                  f"参考文献 {len(entries)} 条里没有中文文献，OPEN_QUESTIONS.md 也没记中文检索：中文期刊和学位论文的审稿人通常要看"
                  "国内相关研究。用中文检索（知网、万方等）查和本文直接相关的研究脉络，查到的真实文献补进综述和讨论；查不到的在 "
                  "OPEN_QUESTIONS.md 写明检索过哪些库、哪些检索词。不要凭记忆补文献")]


# ---------- D 组：讨论 ----------
_HEDGES = re.compile(r"可能|或许|也许|推测|似乎|在一定程度上|有待|大致|初步|\bmay\b|\bmight\b|\bcould\b|suggests?|possibly|"
                     r"likely|plausibl|appears? to|seems? to", re.I)


def check_discussion(doc: Doc, profile: dict) -> list[dict]:
    genre = str(profile.get("genre") or "")
    if not (genre in JOURNALS or genre in CONFERENCES or genre in THESES):
        return []
    secs = top_sections_of(doc, "discussion")
    if not secs:
        return []
    text_raw = " ".join(doc.raw[s.body:s.end] for s in secs)
    text = " ".join(doc.prose[s.body:s.end] for s in secs)
    missing = []
    if not CITE_RAW.search(text_raw):
        missing.append("与已有研究的比较（要有引用）")
    if not (_LIMIT_WORDS.search(text) or has_limitations_part(doc)):
        missing.append("局限")
    if not _HEDGES.search(text):
        missing.append("推断的限定语（可能、推测、may、suggest）")
    if not missing:
        return [_item("D1", RULE_TITLES["D1"], "ok", "讨论有比较、局限和限定语")]
    return [_item_at(doc, "D1", "hint", f"讨论缺{'、'.join(missing)}：讨论要概括发现、给出可能机制（标明推测）、和已有研究比较、"
                     "写局限和意义", [(secs[0].start, secs[0].body)])]


# ---------- C 组：结论 ----------
def _grams(text: str, lang: str) -> set:
    if lang == "zh":
        chars = "".join(_CJK_CHAR.findall(text))
        return {chars[i:i + 4] for i in range(max(0, len(chars) - 3))}
    words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z\-]+", text)]
    return {" ".join(words[i:i + 3]) for i in range(max(0, len(words) - 2))}


C1_OVERLAP = 0.5        # 结论的字符 4 元组（英文词 3 元组）里来自摘要的比例；语料标定见 test_academic_writing_draft.py


def check_conclusion(workspace: Path, doc: Doc, profile: dict) -> list[dict]:
    items = []
    concl = conclusion_spans(doc)
    if not concl:
        return items
    ctext = " ".join(doc.prose[a:b] for a, b in concl)
    lang = profile.get("language") or lang_of(ctext)
    abstracts = [(a, b) for a, b in abstract_spans(doc) if lang_of(doc.prose[a:b]) == lang] or abstract_spans(doc)
    atext = " ".join(doc.prose[a:b] for a, b in abstracts)
    cg, ag = _grams(ctext, lang), _grams(atext, lang)
    if cg and ag and len(cg) >= 20:
        ratio = len(cg & ag) / len(cg)
        if ratio >= C1_OVERLAP:
            items.append(_item_at(doc, "C1", "hint",
                                  f"结论约 {ratio:.0%} 的字句和摘要相同：结论要回答研究问题、说明意义、写局限和展望，不照抄摘要",
                                  [(concl[0][0], concl[0][0] + 30)]))
    for a, b in concl:
        m = re.search(r"本文的?(?:主要)?(?:贡献|创新(?:点)?)(?:如下|有|包括|主要有|在于)|[Oo]ur (?:main )?contributions? (?:are|include)",
                      doc.prose[a:b])
        if m:
            items.append(_item_at(doc, "C1", "hint", "结论在改述\"本文的主要贡献如下\"：结论回答研究问题、写局限和展望，贡献留在引言",
                                  [(a + m.start(), a + m.end())]))
            break
    if not items:
        items.append(_item("C1", RULE_TITLES["C1"], "ok", "结论没有重复摘要"))
    # C2：结论里的数值在正文和结果文件里找不到
    pieces, pos = [], 0
    for a, b in sorted(concl + abstracts):
        if a >= pos:
            pieces.append(doc.raw[pos:a])
            pos = b
    pieces.append(doc.raw[pos:])
    known = numbers_in(" ".join(pieces)) | _result_file_numbers(workspace)
    heads = [(s.start, s.body) for s in doc.sections()]      # 标题行：结论章下的"6.1 主要发现"里的节号不是数据
    new = []
    for a, b in concl:
        for sa, sb in doc.sentences():
            if sa < a or sa >= b:
                continue
            sent = doc.prose[sa:sb]
            for ha, hb in heads:
                if ha < sb and hb > sa:
                    lo, hi = max(ha, sa) - sa, min(hb, sb) - sa
                    sent = sent[:lo] + " " * (hi - lo) + sent[hi:]
            nums = numbers_in(sent, min_int=100) | numbers_in(sent, decimals_or_pct_only=True)
            unknown = sorted(n for n in nums if n not in known and n.rstrip("%") not in known)
            if unknown:
                new.append((sa + len(sent) - len(sent.lstrip()), unknown))
    if new:
        values = list(dict.fromkeys(n for _, u in new for n in u))
        items.append(_item_at(doc, "C2", "hint",
                              f"结论里有 {len(values)} 个数值在正文和结果文件里找不到（{'、'.join(values[:6])}"
                              f"{'等' if len(values) > 6 else ''}）：结论只总结正文报告过的结果，不引入新数据",
                              [(sa, sa + 30) for sa, _u in new], count=len(values)))
    return items


def _result_file_numbers(workspace: Path) -> set[str]:
    ws = Path(workspace)
    texts = [_read(ws / rel)[:600_000] for rel in ("RESULTS.md", "PROJECT_FACTS.md", "figures/all_results.json")]
    figs = ws / "figures"
    if figs.is_dir():
        for path in sorted(figs.glob("TABLE_*"))[:80]:
            if path.suffix.lower() in (".md", ".tex", ".csv"):
                texts.append(_read(path)[:200_000])
    out: set[str] = set()
    for text in texts:
        out |= numbers_in(text)
    return out


# ---------- N 组：话说过头（照原型 OC 规则；口径按规划附录 B） ----------
# (规则, 子类, 正则)；子类 first/gap/lead/all 都归 N1
OC_ZH = [
    ("N1", "first", r"(?:国内外|国际上|国内|国际|世界|业界|学界)?首次(?=\s*(?:系统(?:地)?)?(?:提出|发现|实现|揭示|证明|构建|建立|将|把|"
                    r"应用|引入|采用|设计|开发|研制|报道|研究|探讨|分析|考察|利用|结合|融合|从|对|在|基于))"
                    r"|率先(?=\s*(?:提出|实现|开展|建立|构建|发现|应用|将|把))|国内外首次|首创|开创(?:性|了)|开辟了"),
    ("N1", "gap", r"填补(?:了)?[^，。；]{0,10}空白"),
    ("N1", "lead", r"(?:国际|国内|世界|行业|业内)(?:领先|先进|一流)(?:水平)?|领先水平|达到(?:了)?[^，。；]{0,10}(?:国际|国内|世界)"
                   r"[^，。；]{0,4}水平|前所未有|史无前例|重大突破|突破性(?:进展|成果)?|革命性|颠覆性|里程碑(?:式|意义)?"),
    ("N1", "all", r"(?:优于|超过|超越|胜过|远超|远优于)(?:了)?(?:现有)?(?:所有|全部|一切)(?:现有|已有|其他)?的?(?:方法|模型|算法|研究)"
                  r"|(?:所有|全部)现有(?:方法|模型|算法)|适用于(?:所有|一切|任何)|普遍适用|具有普适性|放之四海|"
                  r"在(?:任何|一切)(?:情况|场景|条件)下"),
    ("N2", "sig", r"(?<!不)(?<!未)(?<!无)显著(?!性|水平|与否)"),
    ("N3", "prove", r"(?:充分|有力|进一步|再次|初步)?证明(?:了)?(?!见|如下|过程|思路|略|：|:|步骤)"),
]
OC_EN = [
    ("N1", "first", r"(?i)\b(?:for the first time|first[- ]ever|(?:is|are|was|be|being) the first (?:to|study|work|paper|attempt|"
                    r"method|approach|framework|model|system|investigation|report|demonstration)|first (?:framework|method|"
                    r"approach) that|first to (?:propose|introduce|show|demonstrate|apply|use|study|investigate|report)|pioneering)\b"),
    ("N1", "lead", r"(?i)\b(?:groundbreaking|ground-breaking|revolutionary|unprecedented|paradigm[- ]shift(?:ing)?|"
                   r"game[- ]chang(?:er|ing)|breakthrough|world[- ]leading|best[- ]in[- ]class)\b"),
    ("N1", "gap", r"(?i)\bfill(?:s|ed|ing)? (?:the|a|this|an important|a critical) (?:research |knowledge )?gap\b"),
    ("N1", "all", r"(?i)\b(?:outperform(?:s|ed|ing)?|surpass(?:es|ed|ing)?|superior to) (?:all|every) (?:existing|prior|previous|"
                  r"other|state-of-the-art|current)?\s*(?:methods?|approaches|models|work)?|\b(?:is|are) the best (?:approach|"
                  r"method|model|solution|choice)\b|\buniversally applicable\b|\bin all (?:cases|settings|scenarios)\b"),
    ("N2", "sig", r"(?i)\bsignificant(?:ly)?\b(?!\s+(?:level|test))"),
    ("N3", "prove", r"(?i)\bprov(?:e|es|ed|en)\b(?=\s+that)|\bconclusively\b"),
]
_CAUSAL_ZH = re.compile(r"导致(?:了)?|促使|决定了|造成(?:了)?|引起(?:了)?|是[^，。；]{1,12}的(?:根本|直接|主要)?原因")
_CAUSAL_EN = re.compile(r"(?i)\b(?:causes?|caused|leads? to|led to|drives?|determines?|results? in)\b")
_DATA_CTX = re.compile(r"回归|系数|显著|相关|变量|样本|问卷|数据|结果|受访者|统计|regression|coefficient|correlat|variable|"
                       r"sample|survey|respondent|data", re.I)
_IDENTIFICATION = re.compile(r"工具变量|两阶段最小二乘|2SLS|双重差分|DID\b|断点回归|RDD|随机(?:对照)?实验|随机对照|RCT|自然实验|"
                             r"倾向得分|PSM|合成控制|instrumental variable|difference-in-differences|regression discontinuity|"
                             r"randomi[sz]ed|natural experiment|propensity score|synthetic control", re.I)
_EXTERNAL_SUBJECT = re.compile(r"(?:报告|政府|国务院|部门|文件|政策|会议|规划|纲要|意见|通知|条例|学者|团队|公司|机构|组织|课题组)"
                               r"[^，。；]{0,8}$")


def check_overclaim(doc: Doc, profile: dict) -> list[dict]:
    findings: list[Finding] = []
    regs = doc.regions()
    qspans = quote_spans(doc.raw)
    prose, raw = doc.prose, doc.raw
    trig = ZH_COMPOUNDS.sub(lambda mm: "乂" * len(mm.group()), prose)
    pieces, pos = [], 0
    for a, b in sorted(abstract_spans(doc)):
        if a >= pos:
            pieces.append(raw[pos:a])
            pos = b
    pieces.append(raw[pos:])
    doc_has_stats = bool(STATS.search(" ".join(pieces)))
    sents = doc.sentences()

    def ctx(a: int) -> str:
        i = max(0, bisect.bisect_right(doc._sent_starts, a) - 1)
        return raw[sents[max(0, i - 1)][0]:sents[min(len(sents) - 1, i + 1)][1]]

    for a, b in sents:
        s = trig[a:b]
        lg = lang_of(prose[a:b])
        sraw = raw[a:b]
        selfref = _self(lg).search(sraw)
        is_cited = bool(CITE_RAW.search(sraw))
        for rid, family, pat in (OC_ZH if lg == "zh" else OC_EN):
            for m in re.finditer(pat, s):
                off = a + m.start()
                # 否定词窗口：中文看前 12 个字，英文按词数要看得更远（"we do not claim to be the first"）
                if (NEG_ZH if lg == "zh" else NEG_EN).search(prose[max(a, off - (12 if lg == "zh" else 40)):off]):
                    continue
                if rid == "N2" and lg == "zh" and re.search(r"^[^。]*?(?:是否|与否)", prose[off:b]):
                    continue
                region = region_at(regs, off)
                quoted = _in(off, qspans)
                if quoted:
                    qa = max(x[0] for x in qspans if x[0] <= off < x[1])
                    qb = min(x[1] for x in qspans if x[0] <= off < x[1])
                    if ATTRIB_BEFORE.search(raw[max(0, qa - 12):qa]) or META_AFTER.search(raw[qb - 1:qb + 8]) \
                            or region not in KEY_REGIONS:
                        continue
                if rid == "N2":
                    # 规划附录 B 的更正：全文做了统计检验就不查；没做检验又写"显著"才报
                    if doc_has_stats or STATS.search(ctx(a)) or (is_cited and not selfref):
                        continue
                    if region not in KEY_REGIONS and has_quantity(sraw):
                        continue
                    findings.append(Finding("N2", "hint", off, a + m.end()))
                    continue
                if rid == "N3":
                    if (not EMPIRICAL.search(sraw) or MATHCTX.search(sraw) or _in(off, doc.math_ctx)
                            or re.search(r"\$|\\\(|\\\[|\\begin\{(?:equation|align)", sraw)):
                        continue
                    findings.append(Finding("N3", "hint", off, a + m.end()))
                    continue
                if family == "all" and re.match(r"(?:适用于|在)", m.group()) and \
                        re.search(r"^[^，。；]{0,4}(?:具有|满足|含有|属于|形如|符合|“|\")", trig[a + m.end():b]):
                    continue  # "适用于任何满足……的问题"是带条件的全称
                if family == "first":
                    if not selfref and _EXTERNAL_SUBJECT.search(prose[a:off]):
                        continue  # 主语是外部主体（如"政府工作报告首次……"）
                    c = ctx(a)
                    if SCOPE.search(c) and DATE.search(c):
                        continue  # 附了检索范围和日期
                    if is_cited and not selfref:
                        continue  # 引述史实
                if family in ("gap", "lead") and is_cited and not selfref and re.search(r"鉴定|评价|评审|验收|认定|证书|evaluat", sraw):
                    continue
                level = "fix" if region in KEY_REGIONS and not quoted and (selfref or not is_cited) else "hint"
                findings.append(Finding("N1", level, off, a + m.end()))
    # N4：相关设计里的因果动词
    rt = profile.get("research_type")
    if rt in ("survey", "econometric", "mixed") and not (rt == "econometric" and _IDENTIFICATION.search(prose)):
        for a, b in sents:
            sent = prose[a:b]
            lg = lang_of(sent)
            if region_at(regs, a) == "intro" or cited(doc, a, b) or _HEDGES.search(sent) or not _DATA_CTX.search(sent):
                continue
            for m in (_CAUSAL_ZH if lg == "zh" else _CAUSAL_EN).finditer(sent):
                if (NEG_ZH if lg == "zh" else NEG_EN).search(sent[max(0, m.start() - 8):m.start()]):
                    continue
                findings.append(Finding("N4", "hint", a + m.start(), a + m.end()))
                break
    return _finding_items(doc, findings)


# ---------- K 组：口吻 ----------
_K1_PATTERNS = (
    r"问题重述|重述问题",
    r"(?<![研究科学关键核心主要子该此本])问题\s*[一二三四五六七八九十](?![直般些致样定旦切再起下同边言种类点方面个项是])",
    r"子问题\s*[（(]?\s*[一二三四五六七八九十\d]|针对(?:各个?|每个|这[一两三四]个)?子问题",
    r"第[一二三四五六七八九十]问(?![卷题答])",
    r"评委(?:老师|专家|们)|(?:供|请|各位)评委|评委(?:审阅|查阅|参考|评阅)",
    r"参赛(?:队|论文|作品|队员|队伍)|本参赛队",
    r"获奖论文|(?:数学)?建模(?:竞赛|比赛|大赛)|美赛|国赛|华为杯|数维杯|电工杯|统计建模大赛|MathorCup",
    r"数模(?!转换|混合|接口|信号|电路|芯片|器件)",
    r"(?i)\bSummary Sheet\b|\bTeam Control Number\b|\bTeam\s*#\s*\d+|\bour team\b|\bthe judges\b|\bCOMAP\b|\b(?:MCM|ICM)\b",
)
_K1_HEADINGS = re.compile(r"^(?:模型(?:的)?(?:基本)?假设|模型假设与符号说明|问题(?:的)?分析|问题重述)$")


def check_tone(doc: Doc, profile: dict, user_text: str) -> list[dict]:
    findings: list[Finding] = []
    qspans = quote_spans(doc.raw)
    user = (user_text or "").lower()
    for pat in _K1_PATTERNS:
        for m in re.finditer(pat, doc.prose):
            word = m.group().strip()
            if not word or _in(m.start(), qspans) or _in(m.start(), doc.quote_ctx) or word.lower() in user:
                continue
            findings.append(Finding("K1", "fix", m.start(), m.end()))
    secs = doc.sections()
    if secs:
        top = chapter_level(doc)
        for s in secs:
            if s.level == top and _K1_HEADINGS.match(s.title) and s.title.lower() not in user \
                    and not any(s.start <= f.off < s.body for f in findings):
                findings.append(Finding("K1", "fix", s.start, s.body, note=f"顶层标题\"{s.title}\"是竞赛论文的结构"))
    items = _finding_items(doc, findings) or [_item("K1", RULE_TITLES["K1"], "ok", "没有竞赛口吻")]
    items.append(_k2(doc))
    return items


# K3：流程用语进了正文（论证逻辑第 8 期真实样稿：硕士论文正文写"最终表述有待作者确认""用户材料中没有原始细胞图像"，
# 史学论文把软件里的材料说明列成参考文献"[2] 材料说明[Z]. 作者提供, 工作区 user_data."）。正文是写给读者的定稿：
# 待确认的只记进 OPEN_QUESTIONS.md，作者必须亲自补的信息用方括号占位（不报）。只收论文里几乎不会正常出现的说法：
# "用户上传""用户资料""需用户确认""user_data 表"在软件类论文里是正常用语，不收。
_K3_PATTERNS = (
    r"(?:有待|尚待|仍待|还待|待|需要|仍需|尚需|还需|需|须|请)(?:作者|本人)(?:本人)?(?:进一步)?(?:确认|核实|核对|补充|定夺|审定|斟酌)",
    r"以(?:作者|本人)(?:的)?(?:最终)?(?:确认|意见)为准",
    r"用户材料|用户(?:提供|给出?)的(?:材料|说明)",
    r"只(?:核到|查到|找到)了?(?:题录|摘要)",
    r"(?:需由|须由|应由|请)作者(?:自行|本人)?[^。；;\n]{0,12}?(?:改|换|补|填|导出|确认|核实|核对|决定|定夺|调整|替换|删)",
    r"(?i)\b(?:to be|pending|awaiting|subject to)\s+(?:confirm(?:ation|ed)?|verif(?:ication|ied))\s+by\s+the\s+authors?\b",
    r"(?i)\bthe\s+authors?\s+(?:should|must|needs?\s+to|will\s+need\s+to|(?:is|are)\s+asked\s+to)\s+(?:confirm|verify|supply|provide)\b",
    r"(?i)\buser[- ]provided\s+(?:material|note)s?\b|\bthe\s+uploaded\s+materials?\b",
)
_K3_INTERNAL = (r"user_data[/\\]|工作区\s*`?user_data|本工作区|OPEN_QUESTIONS|PAPER_PLAN|NARRATIVE_REPORT|WRITING_CHECK|"
                r"SIMULATED_REVIEW|FIGURE_REPORT|PAPER_DATA_CHECK|\b(?:RESULTS|OUTLINE|CLAUDE|DATA)\.md\b|_extracted\.(?:md|txt)\b|_paged\.txt\b|"
                r"(?:材料|数据|资料)说明\.md")
_K3_REF = re.compile(_K3_INTERNAL + r"|(?m:^[ \t]*(?:[-*][ \t]*)?\\?\[?\d+\\?\]?[.、．]?[ \t]*(?:材料|数据|资料)说明[ \t]*\[[A-Z]{1,3}\])"
                     r"|作者提供\s*[,，]\s*工作区")
_K3_BIB = re.compile(_K3_INTERNAL + r"|title\s*=\s*[{\"]\s*(?:材料|数据|资料)说明\s*[}\"]", re.I)
_K3_CODE_MD = re.compile(r"(`{3,}|~{3,}).*?\1|<!--.*?-->", re.S)
_K3_CODE_TEX = re.compile(r"\\begin\{(verbatim|lstlisting|minted|comment)\*?\}.*?\\end\{\1\*?\}|\\verb\*?(.).*?\2|\\lstinline\s*\{[^{}\n]*\}", re.S)


def _in_placeholder(text: str, a: int, b: int) -> bool:
    """命中处在同一行的方括号占位里（［待作者填写：……］、[待作者补充：……]、【……】）。"""
    ls = text.rfind("\n", 0, a) + 1
    le = text.find("\n", b)
    le = len(text) if le < 0 else le
    before = text[ls:a]
    opened = max(before.rfind(ch) for ch in "［[【")
    if opened < 0 or any(ch in before[opened:] for ch in "］]】"):
        return False
    return any(ch in text[b:le] for ch in "］]】")


def _raw_excerpt(text: str, a: int, b: int, width: int = 26) -> str:
    """原文里命中处的前后文（反引号、参考文献在正文视图里是空白，摘录要从原文取），命中部分用 ⟦⟧ 标出。"""
    ls = text.rfind("\n", 0, a) + 1
    le = text.find("\n", b)
    le = len(text) if le < 0 else le
    seg = text[max(ls, a - width):a] + "⟦" + text[a:b] + "⟧" + text[b:min(le, b + width)]
    return re.sub(r"\s+", " ", seg).strip()[:160]


def check_leaks(workspace: Path, doc: Doc, user_text: str) -> list[dict]:
    """K3：正文、参考文献、.bib 里的流程用语和软件内部文件名。各类合成一项，同一行只记一处。"""
    qspans = quote_spans(doc.raw)
    user = (user_text or "").lower()
    found: list[tuple[str, int, dict, str]] = []          # (文件, 行, 位置, 说明)

    def keep(a: int, b: int, word: str) -> bool:
        return not (_in(a, qspans) or _in(a, doc.quote_ctx) or _in_placeholder(doc.raw, a, b) or word.lower() in user)

    def add(loc: dict, note: str) -> None:
        if not any(f == loc["file"] and line == loc["line"] for f, line, _loc, _note in found):
            found.append((loc["file"], loc["line"], loc, note))

    for pat in _K3_PATTERNS:
        for m in re.finditer(pat, doc.prose):
            if keep(m.start(), m.end(), m.group().strip()):
                add(_loc_of(doc, m.start(), m.end()), "")
    code = _K3_CODE_TEX if doc.fmt == "tex" else _K3_CODE_MD
    skip = [m.span() for m in code.finditer(doc.raw)] + ([doc.ref_span] if doc.ref_span else [])
    for m in re.finditer(_K3_INTERNAL, doc.raw):
        if not _in(m.start(), skip) and keep(m.start(), m.end(), m.group()):
            file, line = doc.location(m.start())
            add({"file": file, "line": line, "excerpt": _raw_excerpt(doc.raw, m.start(), m.end())},
                f"软件内部的目录或文件名\"{m.group()}\"")
    if doc.ref_span:
        for pat in _K3_PATTERNS:                       # 参考文献节开头的说明文字也查（条目标题里不会正常出现这些说法）
            for m in re.compile(pat).finditer(doc.raw, *doc.ref_span):
                if keep(m.start(), m.end(), m.group().strip()):
                    file, line = doc.location(m.start())
                    add({"file": file, "line": line, "excerpt": _raw_excerpt(doc.raw, m.start(), m.end())},
                        "参考文献节里有写给作者的说明")
        for m in _K3_REF.finditer(doc.raw, *doc.ref_span):
            file, line = doc.location(m.start())
            add({"file": file, "line": line, "excerpt": _raw_excerpt(doc.raw, m.start(), m.end())},
                "参考文献表里有软件内部的材料说明或目录名")
    for path in sorted((Path(workspace) / "paper").glob("*.bib"))[:5]:
        text = _read(path)
        for m in _K3_BIB.finditer(text):
            add({"file": f"paper/{path.name}", "line": text.count("\n", 0, m.start()) + 1,
                 "excerpt": _raw_excerpt(text, m.start(), m.end())}, "参考文献条目（.bib）里有软件内部的材料说明或目录名")
    if not found:
        return [_item("K3", RULE_TITLES["K3"], "ok", "正文和参考文献里没有流程用语")]
    found.sort(key=lambda row: (row[0], row[1]))
    notes = list(dict.fromkeys(note for *_rest, note in found if note))
    message = f"{len(found)} 处：" + ("；".join(notes[:4]) + "；" if notes else "") + RULE_FIX["K3"]
    return [{"id": "K3", "title": RULE_TITLES["K3"], "status": "fix", "message": message, "count": len(found),
             "locations": [loc for _f, _line, loc, _note in found[:MAX_LOCATIONS]]}]


_K2_CONN_ZH = r"^(?:此外|另外|同时|与此同时|值得注意的是|需要指出的是|值得一提的是|需要注意的是|不仅如此|更重要的是|除此之外)"
_K2_CONN_EN = (r"^(?:Moreover|Furthermore|Additionally|In addition|Notably|Importantly|Interestingly|It is worth noting that|"
               r"It should be noted that|It is important to note that|Crucially)\b")
_K2_RECAP = r"^(?:综上所述|综上|总之|总而言之|由此可见|概言之|In summary|In conclusion|Overall|To sum up|Taken together|In short)"
_K2_TEMPLATE_ZH = r"首先[^。]*?(?:其次|然后)[^。]*?(?:最后|再次)|首先.*?。[^。]*?其次.*?。[^。]*?最后"
_K2_TEMPLATE_EN = r"(?is)\bFirst(?:ly)?,.*?\bSecond(?:ly)?,.*?\b(?:Third(?:ly)?|Finally),"
_K2_LEAD = re.compile(r"^\s*(?:首先|其次|再次|然后|最后|First(?:ly)?|Second(?:ly)?|Third(?:ly)?|Finally)[，,]")


def _k2(doc: Doc) -> dict:
    """串段套话只计数：首先—其次—最后、连接词起句堆叠、段末总结、相邻三段段首都是"首先/其次/最后"。"""
    prose = doc.prose
    template = conn = recap = lead = 0
    first_off = None
    leads = []
    sents = doc.sentences()
    for pa, pb in _paragraphs(prose):
        text = prose[pa:pb]
        lg = lang_of(text)
        lo = bisect.bisect_left(doc._sent_starts, pa)
        ps = []
        for sa, sb in sents[lo:]:
            if sa >= pb:
                break
            ps.append((sa, sb))
        if re.search(_K2_TEMPLATE_ZH if lg == "zh" else _K2_TEMPLATE_EN, text, re.S):
            template += 1
            first_off = pa if first_off is None else first_off
        c = [sa for sa, sb in ps if re.match(_K2_CONN_ZH if lg == "zh" else _K2_CONN_EN, prose[sa:sb].strip())]
        if len(c) >= 3:
            conn += 1
            first_off = c[0] if first_off is None else first_off
        if len(ps) >= 2 and re.match(_K2_RECAP, prose[ps[-1][0]:ps[-1][1]].strip()):
            recap += 1
        leads.append(bool(_K2_LEAD.match(text)))
    for i in range(len(leads) - 2):
        if leads[i] and leads[i + 1] and leads[i + 2]:
            lead += 1
    total = template + conn + recap + lead
    item = {"id": "K2", "title": RULE_TITLES["K2"], "status": "hint" if total else "ok", "count": total,
            "counts": {"template": template, "connective": conn, "recap": recap, "lead": lead}, "locations": [],
            "message": (f"首先—其次—最后 {template} 段；连接词起句堆叠（此外、值得注意的是……一段 3 句以上）{conn} 段；段末\"综上所述\"式"
                        f"总结 {recap} 段；相邻三段段首都是\"首先/其次/最后\" {lead} 处。这只是写法计数，不是 AI 率，也不判定是不是 AI "
                        "写的；真实的步骤可以保留，其余改成按逻辑关系衔接") if total else "没有串段套话"}
    if total and first_off is not None:
        item["locations"] = [_loc_of(doc, first_off + len(prose[first_off:first_off + 40]) - len(prose[first_off:first_off + 40].lstrip()))]
    return item


# ---------- T 组：按研究类型 ----------
def _missing_item(rule: str, checks: list[tuple[str, bool]], lead: str) -> dict:
    missing = [label for label, ok in checks if not ok]
    if not missing:
        return _item(rule, RULE_TITLES[rule], "ok", f"{lead}都写了")
    return _item(rule, RULE_TITLES[rule], "hint", f"没找到{'、'.join(missing)}：{lead}要写清；确实不适用的，在方法或局限里说明原因")


_REG_NO = re.compile(r"ChiCTR[-\s]?(?:[A-Z]{2,4}-)?\d{6,}|NCT\s?\d{8}|ISRCTN\s?\d{8}|ACTRN\s?\d{14}|DRKS\s?\d{8}|UMIN\s?\d{9}|"
                     r"CTRI/\d{4}/\d{2,3}/\d{6}|EudraCT\s*\d{4}-\d{6}-\d{2}")
_ETHICS_NO = re.compile(r"(?:伦理(?:审查)?(?:委员会)?(?:批准|批件|审批|审查)?(?:文号|编号|批号|号)|伦审|批件号|"
                        r"(?i:IRB)\s*(?:No\.?|number|#|approval\s*(?:No\.?|number)?)|(?i:ethics)\s+(?:committee\s+)?(?:approval\s+)?"
                        r"(?:No\.?|number))\s*[:：为是]?\s*([A-Za-z0-9〔〕\[\]（）()【】\-/_.]{4,40})")
_PLACEHOLDER_NO = re.compile(r"待(?:作者)?(?:填写|补充|确认)|XXX|xxx|×{2,}|＊{2,}|\*{3,}|［|【待|\[待|TBD|to be (?:added|filled)", re.I)


def check_research_type(doc: Doc, profile: dict, material_text: str) -> list[dict]:
    rt = profile.get("research_type")
    prose, raw = doc.prose, doc.raw
    if rt in ("experimental", "computational"):
        pm = [m.start() for m in re.finditer(r"±|\\pm\b", raw)]
        pm_ok = all(re.search(r"SD|SEM|标准差|标准误|置信区间|\bCI\b|\bstd\b|standard (?:deviation|error)|均值|\bmean\b",
                              raw[max(0, p - 200):p + 200], re.I) for p in pm[:40])
        checks = [
            ("运行或重复次数（如\"独立运行 5 次\"\"5 个随机种子\"）",
             bool(re.search(r"(?:独立)?(?:重复|运行|实验)\s*\d+\s*次|\d+\s*次(?:独立)?(?:重复|运行|实验)|随机种子|种子|"
                            r"\d+\s*(?:independent\s+)?(?:runs?|seeds?|trials|repetitions)|repeated|random seeds?|averaged over",
                            prose, re.I))),
            ("± 或误差线旁注明的 SD、SEM、CI", pm_ok),
        ]
        if rt == "computational" and re.search(r"基线|对比方法|baseline|compared methods|competing methods", prose, re.I):
            checks.append(("基线的调参说明（同等调参预算）",
                           bool(re.search(r"调参|超参数|网格搜索|随机搜索|grid search|random search|tuned|tuning|hyper-?parameter",
                                          prose, re.I))))
        return [_missing_item("T1", checks, "实验结果的可重复性和误差口径")]
    if rt == "simulation":
        return [_missing_item("T2", [
            ("网格收敛或网格无关性验证（或时间步长收敛、GCI）",
             bool(re.search(r"网格(?:无关|独立|收敛|敏感)|步长收敛|时间步收敛|GCI|mesh (?:independence|convergence|sensitivity)|"
                            r"grid (?:independence|convergence)", prose, re.I))),
            ("不确定度或误差分析", bool(re.search(r"不确定度|不确定性|误差分析|uncertaint|error analysis|verification and validation",
                                                prose, re.I))),
        ], "仿真的验证")]
    if rt == "clinical":
        found = [(m.start(), m.group().strip()) for m in _REG_NO.finditer(raw)]
        found += [(m.start(1), m.group(1).strip()) for m in _ETHICS_NO.finditer(raw) if not _PLACEHOLDER_NO.search(m.group(0))]
        src = _norm(material_text)
        fake = [(off, code) for off, code in found if _norm(code) and _norm(code) not in src]
        if fake:
            return [_item_at(doc, "T3", "fix",
                             f"注册号或伦理批号（{'、'.join(dict.fromkeys(c for _o, c in fake))}）在你上传的材料和需求里都找不到，"
                             "疑似编造：改成\"［待作者填写］\"，并写进 OPEN_QUESTIONS.md", [(o, o + len(c)) for o, c in fake])]
        if not found:
            return [_item("T3", RULE_TITLES["T3"], "hint",
                          "没写临床试验注册号和伦理审查批号：由作者填写（正文先写\"［待作者填写］\"），不要编")]
        return [_item("T3", RULE_TITLES["T3"], "ok", "注册号和伦理批号能在你的材料里找到")]
    if rt == "econometric":
        checks = [
            # 不写"内生性"三个字、实质讨论了识别问题的也算（第 8 期计量样稿："不使用工具变量""没有可供识别的外生变动"）
            ("内生性讨论", bool(re.search(r"内生性|内生问题|endogene|工具变量|instrumental variable|反向因果|互为因果|遗漏变量|"
                                     r"识别策略|识别假设|识别条件|可供识别|外生(?:冲击|变动|变异)", prose, re.I))),
            ("稳健性检验", bool(re.search(r"稳健性|robustness", prose, re.I))),
            # 经管实证也常写"中介变量、中介效应、影响渠道"（开题实测 10-13 第二轮："中介变量一是研发投入强度"被报没找到机制分析）
            ("机制分析", bool(re.search(r"机制(?:分析|检验)|(?:作用|影响|传导)(?:机制|渠道|路径)|渠道(?:检验|分析)|"
                                     r"中介(?:效应|变量|分析|检验|模型)|mechanism|mediat", prose, re.I))),
            ("异质性分析", bool(re.search(r"异质性|heterogene", prose, re.I))),
        ]
        if re.search(r"\*\*\*|\^\{\*{1,3}\}|\$\^\{\*", raw):
            checks.append(("回归表注的星号说明（如\"***、**、* 分别表示在 1%、5%、10% 水平显著\"）",
                           bool(re.search(r"分别表示|分别代表|p\s*[<＜]\s*0?\.[01]|显著性水平|\*\*\*\s*p|significan", raw, re.I))))
        return [_missing_item("T4", checks, "计量实证的必要分析")]
    if rt == "survey":
        return [_missing_item("T5", [
            ("信度（如 Cronbach's α）", bool(re.search(r"信度|Cronbach|克朗巴哈|α\s*系数|reliabilit", raw, re.I))),
            ("效度（如 KMO、因子分析、AVE）", bool(re.search(r"效度|KMO|Bartlett|因子分析|验证性因子|CFA|AVE|validity", raw, re.I))),
            ("共同方法偏差检验", bool(re.search(r"共同方法偏差|同源偏差|common method|Harman", prose, re.I))),
            ("发放、回收与有效份数", bool(re.search(r"发放|回收|有效问卷|有效样本|有效回收率|response rate|valid (?:responses|questionnaires)",
                                                prose, re.I))),
        ], "问卷调查的报告要素")]
    if rt == "qualitative":
        refs = [doc.ref_span] if doc.ref_span else []
        quotes = [m for m in re.finditer(r"“[^”\n]{15,400}”", raw) if not _in(m.start(), refs)]
        ids_ok = True
        if len(quotes) >= 2:
            ids_ok = any(re.search(r"受访者|访谈对象|被访者|编号|[（(]\s*[A-Z]\d{1,3}|[A-Z]\d{1,3}\s*[，,)）]|P\d+|participant|interviewee",
                                   raw[m.end():m.end() + 40], re.I) for m in quotes)
        return [_missing_item("T6", [
            ("抽样与招募", bool(re.search(r"抽样|招募|目的性|滚雪球|立意|purposive|snowball|recruit", prose, re.I))),
            ("停止收集的理由（如理论饱和）", bool(re.search(r"饱和|停止(?:收集|访谈)|saturation", prose, re.I))),
            ("编码步骤", bool(re.search(r"编码|主题分析|扎根|NVivo|coding|thematic", prose, re.I))),
            ("伦理与匿名化", bool(re.search(r"伦理|知情同意|匿名|化名|informed consent|anonymi|pseudonym", prose, re.I))),
            ("引语带受访者编号", ids_ok),
        ], "质性研究的报告要素")]
    return []


def simulated_marker(workspace: Path, profile: dict) -> bool:
    """工作区用了模拟数据（paper-analysis 生成的 data/simulated_data.csv，或规划里的"模拟数据规划"标题；只出现这四个字不算）。"""
    ws = Path(workspace)
    if (ws / "data" / "simulated_data.csv").is_file():
        return True
    return bool(re.search(r"(?m)^#+.*模拟数据规划", _read(ws / plan_rel_for(profile))))


_SIM_WORDS = re.compile(r"模拟数据|仿真数据|合成数据|模拟生成|随机生成|生成的数据|simulated data|synthetic data|simulated dataset", re.I)
_SIM_MECH = re.compile(r"分布|均值|方差|参数|随机种子|种子|服从|生成方式|生成机制|按照|distribution|\bmean\b|variance|\bseed|"
                       r"generated (?:from|by|with)", re.I)
_EMPIRICAL_CLAIM = re.compile(r"实证(?:研究|分析|结果|检验|数据)?|调查(?:显示|表明|发现)|实测|实地调研|empirical|survey (?:shows|found)|"
                              r"\bmeasured\b|field data", re.I)


def check_simulated(workspace: Path, doc: Doc, profile: dict) -> list[dict]:
    if not simulated_marker(workspace, profile):
        return []
    items = []
    mentions = [m.start() for m in _SIM_WORDS.finditer(doc.prose)]
    if not mentions:
        items.append(_item("T7", RULE_TITLES["T7"], "fix",
                           "这篇用了模拟数据（工作区有 data/simulated_data.csv 或规划里的\"模拟数据规划\"），稿件里却没写：在数据或方法节写明"
                           "\"本文使用模拟数据，仅作方法演示\"，并写出生成机制（分布、参数、随机种子）"))
    elif not any(_SIM_MECH.search(doc.prose[max(0, p - 300):p + 300]) for p in mentions):
        items.append(_item_at(doc, "T7", "hint", "写了用模拟数据，但没写生成机制（分布、参数、随机种子）", [(mentions[0], mentions[0] + 4)]))
    key = abstract_spans(doc) + conclusion_spans(doc)
    title = title_span(doc)
    claims = []
    for a, b in key + ([title] if title else []):
        view = doc.raw if title and (a, b) == title else doc.prose
        for m in _EMPIRICAL_CLAIM.finditer(view[a:b]):
            off = a + m.start()
            near = view[max(a, off - 20):off + 20]
            if NEG_ZH.search(view[max(a, off - 10):off]) or NEG_EN.search(view[max(a, off - 10):off]) or \
                    re.search(r"模拟|仿真|simulat|synthetic", near, re.I):
                continue
            claims.append((off, off + len(m.group())))
    if claims:
        items.append(_item_at(doc, "T7", "fix", "用的是模拟数据，题目、摘要或结论里却写了\"实证\"\"调查显示\"\"实测\"：改成\"基于模拟数据的方法演示\"一类说法",
                              claims, count=len(claims)))
    if not items:
        items.append(_item("T7", RULE_TITLES["T7"], "ok", "模拟数据已在稿件里说明"))
    return items


# ---------- Q 组：开题报告的交付核对（2026-10-12 按高校开题要求补） ----------
# 必备部分按标题认（任一级标题，或"**可行性分析**："这种段首标签）。各部分在学校文件里的出处见 academic_writing_zh.md
# 开题一节；章名与 academic_outlines.json 的开题骨架对得上（测试核对：照骨架写的稿子 Q1 全过）。
PROPOSAL_PARTS: dict[str, tuple[str, str]] = {
    "background": ("选题依据（背景与意义）",
                   r"选题依据|立论依据|选题背景|研究背景|选题缘由|选题的由来|选题由来|引言|问题的提出|研究意义|目的(?:和|与|及)意义|课题来源"),
    "review": ("研究现状及述评", r"研究现状|文献综述|研究综述|研究进展|学术史|研究动态|研究概况|文献回顾|研究述评|研究史|调研报告"),
    "content": ("研究目标、内容与关键问题", r"研究内容|研究目标|拟解决|关键问题|研究问题|科学问题|主要问题|研究的问题|论点"),
    "method": ("研究方法与技术路线",
               r"研究方法|技术路线|研究方案|实施方案|方案论证|研究思路|研究设计|技术方案|实验方案|设计方案|研究手段|研究步骤|研究方式"),
    "feasibility": ("可行性分析", r"可行性"),
    "innovation": ("创新点", r"创新|特色"),
    "basis": ("研究基础与工作条件", r"研究基础|工作基础|前期|已有基础|已有工作|已具备|工作条件|研究条件|实验条件|条件保障|经费"),
    "prior": ("前期研究与预研结果", r"前期|预研|已完成的?(?:研究)?工作|初步(?:研究|结果|工作)"),
    "difficulty": ("预期困难与解决措施", r"困难|风险|解决措施|应对措施|对策|解决办法|解决方法"),
    "schedule": ("进度安排", r"进度|时间安排|时间表|工作计划|研究计划|计划安排|日程"),
    "outcomes": ("预期成果与目标", r"预期成果|预期目标|预期结果|成果形式|预期达到|可能达到|预期的成果"),
    "outline": ("论文结构框架（章节提纲）", r"大纲|结构框架|论文框架|章节安排|章节结构|论文提纲|写作提纲|篇章结构|文章的结构|论文结构|论文的结构"),
    "references": ("参考文献", r"参考文献"),
}
_PART_RES = {key: re.compile(pattern) for key, (_label, pattern) in PROPOSAL_PARTS.items()}
_FAMILY_LABEL = {"stem": "理工农医", "social": "经管与社会科学", "humanities": "人文学科"}
_LEVEL_LABEL = {"bachelor": "本科", "master": "硕士", "doctor": "博士"}
_REQ_TABLE_RE = re.compile(r"交付要求")
_REQ_ROWS = {
    "chars": re.compile(r"字数|篇幅|字"),
    "refs": re.compile(r"参考文献|文献篇数|文献数"),
    "foreign": re.compile(r"外文|外国|英文"),
    "recent5": re.compile(r"近五年|近5年|五年内|5年内|近年"),
    "structure": re.compile(r"结构|章节|部分"),
}
_REQ_RULE = {"chars": "Q2", "refs": "Q3", "foreign": "Q3", "recent5": "Q3", "structure": "Q1"}
_QUOTE_RE = re.compile(r"[“\"「『‘]([^”\"」』’]{4,400})[”\"」』’]")
_DEFAULT_RE = re.compile(r"^\s*(?:默认|无|没有|未规定|待定|—|-|/)?\s*$")
_CN_FRAC = {"三分之一": (1, 3), "二分之一": (1, 2), "一半": (1, 2), "四分之一": (1, 4), "五分之一": (1, 5),
            "三分之二": (2, 3), "四分之三": (3, 4)}
_REF_TYPE_RE = re.compile(r"\[(?:J|M|C|D|R|S|P|N|A|G|Z|DB|CP|DS|EB|EB/OL|J/OL|M/OL|C/OL|D/OL|R/OL|N/OL|DB/OL)\]", re.I)
_YEAR_RE = re.compile(r"(?<![\d.])(19[4-9]\d|20[0-4]\d)(?!\d)")
_TEXTBOOK_RE = re.compile(r"\[S\]|教材|教程|textbook", re.I)
_SEARCH_NOTE_RE = re.compile(r"检索|查询|搜索")
PROPOSAL_PREP = "开题答辩准备.md"
# "照实记下了检索情况"要写出篇数（"共得 12 篇""只找到 18 篇"）或说明篇数不够；只写"中文文献一篇都没有采用"不算
_SEARCH_COUNT_RE = re.compile(r"\d+\s*篇|篇数|(?:不足|不够|达不到|未达到?)[^。\n]{0,12}(?:篇|文献|要求|目标)")
_NOTE_ITEM_SPLIT = re.compile(r"\n\s*\n|\n(?=[ \t]*(?:\d+[.、．)）]|[-*][ \t]))")
_PLAN_RESULT_RE = re.compile(
    r"(?:本研究|本文|本课题|本项目|笔者|我们)(?:已经?|最终)?(?:发现|证明了?|证实了?|表明|得出(?:了)?(?:结论)?|取得了|实现了)"
    r"|(?:实验|仿真|实证|调查)结果(?:表明|显示|证明)|(?:结果|数据)证明了")


def _search_documented(note_text: str) -> bool:
    """OPEN_QUESTIONS.md 里有一条（段落或编号条目）既写了检索过、又写了篇数或篇数不够。

    只记了某一类查不到（开题实测 10-12：只写了"中文……一篇都没有采用"），总篇数不够也被当成"已记下检索情况"
    只提示，学校要求的篇数就没人管了。"""
    return any(_SEARCH_NOTE_RE.search(part) and _SEARCH_COUNT_RE.search(part)
               for part in _NOTE_ITEM_SPLIT.split(note_text or ""))


def _proposal_targets(profile: dict) -> dict:
    """默认交付目标：后台算好的（.mh/writing_spec.json 的 proposal_targets）；老工作区没有时按学位层次补。"""
    targets = profile.get("proposal_targets")
    if isinstance(targets, dict) and targets.get("min_chars"):
        return dict(targets)
    level = profile.get("level") if profile.get("level") in _LEVEL_LABEL else "master"
    base = {"bachelor": (3000, 15, {"count": 2}, None, None), "master": (5000, 30, {"ratio": [1, 3]}, {"ratio": [1, 3]}, None),
            "doctor": (15000, 50, {"ratio": [1, 2]}, {"ratio": [1, 3]}, 1)}[level]
    out = dict(zip(("min_chars", "min_refs", "foreign", "recent5", "recent2_min"), base), level=level)
    if profile.get("proposal_family") == "humanities":
        out.update(foreign=None, recent5=None, recent2_min=None)
    return out


def _numbers_in(text: str) -> list[float]:
    text = unicodedata.normalize("NFKC", text or "")
    out = []
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(万)?", text):
        value = float(m.group(1)) * (10000 if m.group(2) else 1)
        out.append(value)
    return out


def _fraction_in(text: str) -> tuple[int, int] | None:
    text = unicodedata.normalize("NFKC", text or "")
    for word, frac in _CN_FRAC.items():
        if word in text:
            return frac
    m = re.search(r"(\d+)\s*/\s*(\d+)", text)
    if m and 0 < int(m.group(1)) < int(m.group(2)) <= 20:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    if m and 0 < float(m.group(1)) < 100:
        return round(float(m.group(1))), 100
    return None


def _quote_supports(kind: str, requirement: str, quote: str) -> bool:
    """引的原句里有这个数：字数、篇数按数字（含"1.5 万"），比例按分数（三分之一、1/3、33%）。"""
    if kind in ("chars", "refs"):
        want = _numbers_in(requirement)
        have = _numbers_in(quote)
        return bool(want) and any(abs(w - h) < 0.5 for w in want for h in have)
    if kind in ("foreign", "recent5"):
        want, have = _fraction_in(requirement), _fraction_in(quote)
        if want and have:
            return abs(want[0] / want[1] - have[0] / have[1]) < 0.02
        want_n, have_n = _numbers_in(requirement), _numbers_in(quote)
        return bool(want_n) and any(abs(w - h) < 0.5 for w in want_n for h in have_n)
    return True


_DOCX_TEXT_RE = re.compile(r"<w:t(?:\s[^>]*)?>([^<]*)</w:t>|</w:p>")


def docx_plain_text(path: Path, limit: int = 2_000_000) -> str:
    """Word 模板里的文字（只用标准库：解开 word/document.xml，取 <w:t>，段落之间换行）。读不了返回空串。"""
    import zipfile
    try:
        with zipfile.ZipFile(path) as archive:
            xml = archive.read("word/document.xml")[:limit].decode("utf-8", errors="replace")
    except (OSError, KeyError, zipfile.BadZipFile, RuntimeError):
        return ""
    parts = []
    for m in _DOCX_TEXT_RE.finditer(xml):
        parts.append(m.group(1) if m.group(1) is not None else "\n")
    text = "".join(parts)
    for ent, ch in (("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&apos;", "'"), ("&amp;", "&")):
        text = text.replace(ent, ch)
    return text


def _requirement_sources(workspace: Path) -> list[Source]:
    """核对"交付要求"引文的来源：用户的需求、上传的要求文档（CUSTOM_REQUIREMENTS.md）、格式要求、上传资料的提取文字，
    以及新建页传的学校 Word 模板（user_template/，模板格子里常写着"不少于 3000 字""文献不少于 30 篇"）。"""
    text = user_texts(workspace)
    sources = [Source("用户需求与要求文档", text, "text")]
    base = Path(workspace) / "user_template"
    if base.is_dir():
        for path in sorted(base.rglob("*"))[:20]:
            if path.is_file() and path.suffix.lower() in (".docx", ".dotx"):
                body = docx_plain_text(path)
                if body:
                    sources.append(Source(path.relative_to(Path(workspace)).as_posix(), body, "text"))
    return sources + load_sources(workspace)


def proposal_requirements(workspace: Path, profile: dict) -> tuple[dict, list[tuple[str, str]], bool]:
    """(本篇核对用的目标, [(规则号, 说明)], 学校规定了结构)。规划文件"交付要求"表里引的原句在用户材料里找得到、数字也对得上的
    才按它核对（学校要求可以比默认低，也可以比默认高）；引文核不到的按默认，并说明。"""
    targets = _proposal_targets(profile)
    targets["sources"] = {}
    notes: list[tuple[str, str]] = []
    school_structure = False
    text = _read(Path(workspace) / "PROPOSAL_PLAN.md")
    table = next((t for t in tables(text) if _REQ_TABLE_RE.search(t.heading or "")), None)
    if table is None:
        return targets, notes, school_structure
    sources = None
    for row in table.rows:
        if len(row) < 3:
            continue
        name, requirement, basis = (_clean(c) for c in row[:3])
        kind = next((k for k, rx in _REQ_ROWS.items() if rx.search(name)), None)
        if kind is None or _DEFAULT_RE.match(requirement):
            continue
        quotes = [q.strip() for q in _QUOTE_RE.findall(basis)]
        if sources is None:
            sources = _requirement_sources(workspace)
        found = next((q for q in quotes if find_in_sources(sources, q, threshold=0.9)), None)
        rule = _REQ_RULE[kind]
        if not found:
            notes.append((rule, f"交付要求表里\"{name}\"的依据" + ("没有照抄原句" if not quotes else f"“{quotes[0][:30]}”在你给的材料里没找到")
                          + "，这一项按默认核对"))
            continue
        if kind == "structure":
            school_structure = True
            continue
        if not _quote_supports(kind, requirement, found):
            notes.append((rule, f"交付要求表里\"{name}\"写的“{requirement[:20]}”在引的原句里对不上，这一项按默认核对"))
            continue
        if kind == "chars":
            nums = _numbers_in(requirement)
            if nums:
                targets["min_chars"] = int(max(nums))
        elif kind == "refs":
            nums = _numbers_in(requirement)
            if nums:
                targets["min_refs"] = int(max(nums))
        else:
            frac = _fraction_in(requirement)
            if frac:
                targets[kind] = {"ratio": [frac[0], frac[1]]}
            else:
                nums = _numbers_in(requirement)
                if nums:
                    targets[kind] = {"count": int(max(nums))}
        targets["sources"][kind] = found[:60]
    return targets, notes, school_structure


def _target_source(targets: dict, kind: str, profile: dict) -> str:
    quote = (targets.get("sources") or {}).get(kind)
    if quote:
        return f"按学校要求“{quote}”"
    level = _LEVEL_LABEL.get(str(targets.get("level") or profile.get("level") or ""), "硕士")
    return f"没有学校要求时的默认（{level}）"


def _part_found(doc: Doc, key: str) -> bool:
    rx = _PART_RES[key]
    if any(rx.search(s.title) for s in doc.sections()):
        return True
    # 段首标签："**可行性分析**："、"可行性分析："
    return bool(re.search(r"(?m)^[ \t>]*(?:\*\*)?[^\n*：:]{0,10}(?:" + PROPOSAL_PARTS[key][1] + r")[^\n*：:]{0,10}(?:\*\*)?[ \t]*[：:]",
                          doc.raw))


def _template_given(workspace: Path) -> bool:
    """用户传了学校的 Word 模板：结构以模板为准。"""
    base = Path(workspace) / "user_template"
    try:
        return base.is_dir() and any(p.suffix.lower() in (".docx", ".dotx", ".doc") for p in base.rglob("*") if p.is_file())
    except OSError:
        return False


def _required_parts(profile: dict) -> tuple[list[str], list[str]]:
    """(必备, 建议有)。依据：哈工大硕博、东南本硕博、华东政法、清华科技史、复旦 MPA 的开题报告内容要求。"""
    level = profile.get("level") if profile.get("level") in _LEVEL_LABEL else "master"
    family = profile.get("proposal_family")
    required = ["background", "review", "content", "method", "schedule", "references"]
    advised: list[str] = []
    if level == "bachelor":
        advised += ["feasibility", "difficulty"]
    else:
        required += ["feasibility", "innovation", "basis", "difficulty", "outcomes"]
    if level == "doctor":
        required.append("prior")
    if family == "humanities":
        (advised if level == "bachelor" else required).append("outline")
    elif level != "bachelor":
        advised.append("outline")
    return required, advised


def _proposal_chars(doc: Doc) -> int:
    """正文字数：汉字 + 英文词，含标题和表格里的字，不含参考文献、公式、代码。"""
    visible = len(_CJK_CHAR.findall(doc.prose)) + len(re.findall(r"[A-Za-z]+", doc.prose))
    raw = doc.raw
    if doc.ref_span:
        raw = raw[:doc.ref_span[0]] + raw[doc.ref_span[1]:]
    cells = "\n".join(line for line in raw.splitlines() if line.lstrip().startswith("|") and not _SEPARATOR_RE.match(line))
    return visible + len(_CJK_CHAR.findall(cells)) + len(re.findall(r"[A-Za-z]+", cells))


def _ref_year(entry: str, this_year: int) -> int | None:
    """著录里的出版年：文献类型标识（[J][M][C]…）之后第一个年份；没有标识时取不晚于明年的最大年份。"""
    m = _REF_TYPE_RE.search(entry)
    tail = entry[m.end():] if m else ""
    years = [int(y) for y in _YEAR_RE.findall(tail) if int(y) <= this_year + 1]
    if years:
        return years[0]
    years = [int(y) for y in _YEAR_RE.findall(entry) if int(y) <= this_year + 1]
    return max(years) if years else None


def _ratio_text(spec: dict | None) -> str:
    if not spec:
        return ""
    if spec.get("ratio"):
        return f"{spec['ratio'][0]}/{spec['ratio'][1]}"
    return f"{spec.get('count')} 篇"


def _meets(spec: dict | None, part: int, total: int) -> bool:
    if not spec or total == 0:
        return True
    if spec.get("ratio"):
        num, den = spec["ratio"]
        return part * den >= num * total
    return part >= int(spec.get("count") or 0)


def check_proposal(workspace: Path, doc: Doc, profile: dict, user_text: str, *, now: datetime | None = None) -> list[dict]:
    """开题报告的交付核对：Q1 必备部分、Q2 篇幅、Q3 参考文献篇数与构成、Q4 进度安排、Q5 计划语气。别的文体不查。"""
    if str(profile.get("genre") or "") != "proposal":
        return []
    workspace = Path(workspace)
    this_year = (now or datetime.now()).year
    targets, notes, school_structure = proposal_requirements(workspace, profile)
    level = profile.get("level") if profile.get("level") in _LEVEL_LABEL else "master"
    level_text = _LEVEL_LABEL[level] + ("（专业学位）" if profile.get("degree_type") == "professional" else "")
    items: list[dict] = []

    # Q1 必备部分
    required, advised = _required_parts(profile)
    soft = _template_given(workspace) or user_gave_outline(user_text) or school_structure
    missing = [PROPOSAL_PARTS[k][0] for k in required if not _part_found(doc, k)]
    missing_adv = [PROPOSAL_PARTS[k][0] for k in advised if not _part_found(doc, k)]
    why = ("（你传了学校模板、给了自己的大纲，或学校规定了结构：以那份结构为准，这里只提示）" if soft else "")
    if missing:
        items.append(_item("Q1", RULE_TITLES["Q1"], "hint" if soft else "fix",
                           f"缺{'、'.join(missing)}{why}：{level_text}开题报告通常要有这几部分（学校文件的出处见 "
                           "_guide/WRITING_GUIDE.md 开题一节）。各写成单独的小节，标题里写出名称；不知道的事实写"
                           "“［待作者填写：……］”，不编"))
    else:
        items.append(_item("Q1", RULE_TITLES["Q1"], "ok", f"{level_text}开题报告的必备部分齐全"))
    if missing_adv:
        items.append(_item("Q1", RULE_TITLES["Q1"], "hint", f"建议加{'、'.join(missing_adv)}（不少学校的开题报告要写，按学校要求取舍）"))
    if profile.get("degree_type") == "professional":
        practice = re.search(r"实践|行业|企业|工程项目|工程实际|案例|应用价值|合作单位|生产", doc.prose)
        if not practice:
            items.append(_item("Q1", RULE_TITLES["Q1"], "hint",
                               "专业学位开题要写清实践来源（哪个行业、企业或工程项目的什么实际问题）和应用价值，稿子里没找到"))

    # Q2 篇幅
    chars = _proposal_chars(doc)
    goal = int(targets.get("min_chars") or 0)
    src = _target_source(targets, "chars", profile)
    if goal and chars < goal * 0.6:
        items.append(_item("Q2", RULE_TITLES["Q2"], "fix",
                           f"正文约 {chars} 字，目标不少于 {goal} 字（{src}），差得多：先补实质内容——研究现状的述评、研究方案"
                           "和可行性的细节、进度安排；不为凑字数重复或空话"))
    elif goal and chars < goal:
        items.append(_item("Q2", RULE_TITLES["Q2"], "hint", f"正文约 {chars} 字，目标不少于 {goal} 字（{src}）；有该写没写的部分就补，不为凑字数扩写"))
    else:
        items.append(_item("Q2", RULE_TITLES["Q2"], "ok", f"正文约 {chars} 字（目标不少于 {goal} 字，{src}）"))

    # Q3 参考文献篇数与构成
    entries = reference_entries(workspace, doc)
    total = len(entries)
    want = int(targets.get("min_refs") or 0)
    src = _target_source(targets, "refs", profile)
    note_text = _read(workspace / "OPEN_QUESTIONS.md")
    searched = _search_documented(note_text)
    if want and total < want:
        status = "hint" if searched else "fix"
        tail = ("；OPEN_QUESTIONS.md 已记下检索情况，这里只提示" if searched else
                "：按技能 Step 2 换检索词、补中英文检索，把查到并核实过的真实文献用到研究现状和方法里；查不到就在 "
                "OPEN_QUESTIONS.md 写明检索过哪些库、哪些检索词、各得几篇。不要凭记忆补文献")
        items.append(_item("Q3", RULE_TITLES["Q3"], status, f"参考文献 {total} 篇，目标不少于 {want} 篇（{src}）{tail}"))
    elif total:
        items.append(_item("Q3", RULE_TITLES["Q3"], "ok", f"参考文献 {total} 篇（目标不少于 {want} 篇，{src}）"))
    if total:
        foreign = sum(1 for e in entries if len(_CJK_CHAR.findall(e)) < 4)
        years = [_ref_year(e, this_year) for e in entries]
        recent5 = sum(1 for y in years if y is not None and y >= this_year - 4)
        recent2 = sum(1 for y in years if y is not None and y >= this_year - 1)
        bits = []
        spec = targets.get("foreign")
        if spec and not _meets(spec, foreign, total):
            bits.append(f"外文 {foreign} 篇，目标 {_ratio_text(spec)}（{_target_source(targets, 'foreign', profile)}）")
        spec = targets.get("recent5")
        if spec and not _meets(spec, recent5, total):
            bits.append(f"近五年（{this_year - 4} 年以来）的 {recent5} 篇，目标 {_ratio_text(spec)}"
                        f"（{_target_source(targets, 'recent5', profile)}）")
        if targets.get("recent2_min") and recent2 < int(targets["recent2_min"]):
            bits.append(f"近两年（{this_year - 1} 年以来）的 {recent2} 篇，博士开题一般要有近两年的文献")
        flagged = [e for e in entries if _TEXTBOOK_RE.search(e)]
        if flagged:
            bits.append(f"{len(flagged)} 条像教材或技术标准（教材、技术标准、产品样本一般不列为参考文献，学校另有规定的从其规定）")
        if bits:
            items.append(_item("Q3", RULE_TITLES["Q3"], "hint", "；".join(bits) + "：定向补检索真实文献，不凭记忆补"))

    # Q4 进度安排
    schedule = [s for s in doc.sections() if _PART_RES["schedule"].search(s.title)]
    if schedule:
        span_text = "\n".join(doc.raw[s.body:s.end] for s in schedule)
        sched_tables = [t for t in tables(span_text) if t.rows]
        timed = any(re.search(r"\d|[一二三四五六七八九十]+[月周年季]|月|周|季度|学期", " ".join(r[:2] if len(r) > 1 else r))
                    for t in sched_tables for r in t.rows)
        if not sched_tables:
            items.append(_item("Q4", RULE_TITLES["Q4"], "hint", "进度安排没有用表格：用表格列出阶段、起止时间、主要工作、阶段成果"))
        elif not timed:
            items.append(_item("Q4", RULE_TITLES["Q4"], "hint", "进度表里没有时间：每个阶段写起止年月（不知道学校节点的，用相对月份并在 "
                                                            "OPEN_QUESTIONS.md 请作者改）"))
        else:
            items.append(_item("Q4", RULE_TITLES["Q4"], "ok", "进度安排有表格和时间"))

    # Q5 计划语气：研究现状（别人的结果）和研究基础、前期研究（真做过的）以外，不该出现"本研究发现""实验结果表明"
    excluded = [s for s in doc.sections() if _PART_RES["review"].search(s.title) or _PART_RES["prior"].search(s.title)
                or re.search(r"研究基础|工作基础|已有基础", s.title)]
    hits = []
    for m in _PLAN_RESULT_RE.finditer(doc.prose):
        off = m.start()
        if any(s.body <= off < s.end for s in excluded) or NEG_ZH.search(doc.prose[max(0, off - 6):off]):
            continue
        hits.append((off, m.end()))
    if hits:
        items.append(_item_at(doc, "Q5", "hint", "开题写的是打算做的事：\"本研究发现\"\"实验结果表明\"这类说法改成\"拟\"\"预期\"；"
                                                "已经做过的前期工作放到研究基础或前期研究一节，照实写", hits, count=len(hits)))
    # Q6 开题答辩准备（技能 Step 5 的交付物，给作者自己用）：开题实测 10-12 断流接回后模型写完正文就结束了，这份没写
    prep = _read(workspace / PROPOSAL_PREP)
    prep_chars = len(_CJK_CHAR.findall(prep))
    if prep_chars < 300:
        items.append(_item("Q6", RULE_TITLES["Q6"], "fix",
                           (f"{PROPOSAL_PREP} 只有约 {prep_chars} 字" if prep.strip() else f"没有 {PROPOSAL_PREP}")
                           + "：按技能 Step 5 写——汇报提纲（每页讲什么、用到哪张图表）、评议专家最可能问的 8 个以上问题和回答要点"
                           "（注明报告里对应的位置）、答辩前要补的［待作者填写：……］和 OPEN_QUESTIONS.md 里待确认的事"))
    else:
        asked = len(re.findall(r"[？?]", prep))
        if asked < 8:
            items.append(_item("Q6", RULE_TITLES["Q6"], "hint",
                               f"{PROPOSAL_PREP} 里专家可能问的问题约 {asked} 个，技能 Step 5 要 8 个以上（选题价值、和最接近的研究有什么不同、"
                               "数据或材料从哪来、方法为什么适合、做不成怎么办、工作量和进度、创新点站不站得住）"))
        else:
            items.append(_item("Q6", RULE_TITLES["Q6"], "ok", f"{PROPOSAL_PREP} 约 {prep_chars} 字，问题 {asked} 个"))
    for rule, note in notes:
        items.append(_item(rule, RULE_TITLES[rule], "hint", note))
    return items


# ---------- H 组：人文 ----------
_SECONDARY_TYPES = re.compile(r"\[(?:J|D|C|R|J/OL|D/OL|C/OL)\]|@(?:article|inproceedings|phdthesis|mastersthesis|thesis|"
                              r"conference|techreport)\b", re.I)
_TRANSFER = re.compile(r"转引自|转引|quoted in|cited in", re.I)
_PAGE_NUMS = re.compile(r"(?:第\s*)?(?:pp?\.\s*)?(\d{1,4})(?:\s*[-–—~～]\s*(\d{1,4}))?\s*页?")
# 引述动词紧挨在引语前（"鲁迅写道：""县志载：""奏疏称"）：说明这是引别人的话，不是作者给自己的说法加引号
# 排除指称和作者自述："所谓""号称""简称""又称"是给说法起名，"换句话说""就是说""所言""试问"是作者自己的话
_QUOTE_VERB = re.compile(r"(?:写道|说道|(?<![所话是])说|云|曰|载|记载|记|(?<![所号堪简俗又或通统并])称|指出|认为|(?<![简缩改])写|(?<![试疑])问|答|(?<!所)言|(?<![所可无])谓|(?<![知难一称])道|提到|强调|主张|表示|声称|奏称|疏称|呈称|批道|自述|回忆|宣称|断言|坦言)\s*[：:，,]?\s*$")
# 引语后跟着出处：[N]、^[N]、\cite、\footnote、[^n]、（作者，年份）、（第 N 页）
_CITE_AFTER = re.compile(r"^[\s”’」』]*(?:\^?\s*\[\s*\d|\\(?:cite|footnote)|\[\^|[（(][^（）()\n]{0,40}?(?:19|20)\d{2}|[（(]\s*(?:第\s*)?\d{1,4}\s*页)")
# 引语前面已经交代了页码（"县志第 45 页载：""p. 12 写道"）
_PAGE_BEFORE = re.compile(r"第\s*\d{1,4}\s*(?:[-–—~～]\s*\d{1,4}\s*)?页|\bpp?\.\s*\d{1,4}")


def _quote_items(doc: Doc) -> list[tuple[int, int, str]]:
    """直接引语：中文引号内 10 个汉字以上、Markdown 引文块、LaTeX quote/quotation/verse 环境。"""
    out = []
    skip = [doc.ref_span] if doc.ref_span else []
    for m in re.finditer(r"“([^”\n]{10,600})”", doc.raw):
        if len(_CJK_CHAR.findall(m.group(1))) >= 10 and not _in(m.start(), skip) and not _in(m.start(), doc.math_spans):
            out.append((m.start(), m.end(), m.group(1)))
    if doc.fmt == "md":
        for m in re.finditer(r"(?m)(?:^>[^\n]*\n?)+", doc.raw):
            body = re.sub(r"(?m)^>\s?", "", m.group())
            if len(_CJK_CHAR.findall(body)) >= 10 and not any(a <= m.start() < b for a, b, _ in out) and not _in(m.start(), skip):
                out.append((m.start(), m.end(), body))
    else:
        for m in re.finditer(r"\\begin\{(quote|quotation|verse)\}(.*?)\\end\{\1\}", doc.raw, re.S):
            body = re.sub(r"\\[A-Za-z@]+\*?|[{}]", " ", m.group(2))
            if len(_CJK_CHAR.findall(body)) >= 10 and not any(a <= m.start() < b for a, b, _ in out):
                out.append((m.start(), m.end(), body))
    out.sort()
    return out


def _ref_entry(doc: Doc, workspace: Path, after: str) -> str:
    """引语后面紧跟的文献条目（顺序编码 [N]、\\cite{key}）；找不到返回空串。"""
    m = re.match(r"^[\s”’」』]*(?:\^\s*)?\[\s*(\d+)\s*\]", after)
    if m:
        refs = doc.raw[doc.ref_span[0]:doc.ref_span[1]] if doc.ref_span else doc.raw[-30000:]
        e = re.search(r"(?m)^\s*(?:[-*]\s*)?\\?\[\s*" + m.group(1) + r"\s*\\?\][^\n]*", refs)
        return e.group() if e else ""
    m = re.match(r"^[\s”’」』]*\\cite\w*\s*(?:\[[^\]]*\]\s*)?\{([^},]+)", after)
    if m:
        key = m.group(1).strip()
        bib = re.search(r"\\bibitem(?:\[[^\]]*\])?\{" + re.escape(key) + r"\}([^\n]*(?:\n(?!\\bibitem)[^\n]*){0,3})", doc.raw)
        if bib:
            return bib.group(1)
        for path in sorted((Path(workspace) / "paper").glob("*.bib"))[:5]:
            e = re.search(r"@(\w+)\s*\{\s*" + re.escape(key) + r"\s*,", _read(path))
            if e:
                return "@" + e.group(1)
    return ""


def _range(m) -> tuple[int, int] | None:
    lo = int(m.group(1))
    hi = int(m.group(2)) if m.group(2) else lo
    return (lo, hi) if 0 < lo <= hi <= 9999 else None


def cited_pages(doc: Doc, after: str) -> tuple[int, int] | None:
    """引语后面标的页码：\\cite[第 12 页]{key}、[3]12、（作者，2001：12）、（第 12 页）、脚注里的"第 12 页"。"""
    head = after[:90]
    m = re.match(r"^[\s”’」』]*\\cite\w*\s*\[([^\]]+)\]", head)
    if m:
        p = _PAGE_NUMS.search(m.group(1))
        return _range(p) if p else None
    m = re.match(r"^[\s”’」』]*(?:\^\s*)?\[\s*\d+(?:\s*[,，\-–]\s*\d+)*\s*\]\s*(?:\^\s*)?[（(]\s*(?:第\s*)?(?:pp?\.\s*)?"
                 r"(\d{1,4})(?:\s*[-–—~～]\s*(\d{1,4}))?\s*页?\s*[）)]", head)          # [1]（第 12 页）
    if m:
        return _range(m)
    m = re.match(r"^[\s”’」』]*(?:\^\s*)?\[\s*\d+\s*\]\s*(?:\^\s*)?(?:\{\s*)?[:：，,]?\s*(?:第\s*)?(?:pp?\.\s*)?(\d{1,4})"
                 r"(?:\s*[-–—~～]\s*(\d{1,4}))?(?!\d)(?!\s*年)", head)                  # [3]12、[3]^{12}
    if m:
        return _range(m)
    m = re.match(r"^[\s”’」』]*[（(][^（）()]{0,40}?(?:19|20)\d{2}[a-z]?\s*[:：，,]\s*(?:第\s*)?(?:pp?\.\s*)?(\d{1,4})"
                 r"(?:\s*[-–—~～]\s*(\d{1,4}))?", head)
    if m:
        return _range(m)
    m = re.match(r"^[\s”’」』]*[（(]\s*(?:第\s*)?(?:pp?\.\s*)?(\d{1,4})(?:\s*[-–—~～]\s*(\d{1,4}))?\s*页?\s*[）)]", head)
    if m:
        return _range(m)
    m = re.match(r"^[\s”’」』]*\[\^([^\]\s]+)\]", head)
    if m:
        d = re.search(r"(?m)^\[\^" + re.escape(m.group(1)) + r"\]:\s*([^\n]*)", doc.raw)
        if d:
            p = re.search(r"第\s*(\d{1,4})(?:\s*[-–—~～]\s*(\d{1,4}))?\s*页|pp?\.\s*(\d{1,4})(?:\s*[-–—]\s*(\d{1,4}))?", d.group(1))
            if p:
                lo = int(p.group(1) or p.group(3))
                hi = int(p.group(2) or p.group(4) or lo)
                return (lo, hi) if lo <= hi else None
        return None
    m = re.match(r"^[\s”’」』]*\\footnote\s*\{([^{}]{0,300})\}", after[:360])
    if m:
        p = re.search(r"第\s*(\d{1,4})(?:\s*[-–—~～]\s*(\d{1,4}))?\s*页|pp?\.~?\s*(\d{1,4})(?:\s*-{1,2}\s*(\d{1,4}))?", m.group(1))
        if p:
            lo = int(p.group(1) or p.group(3))
            hi = int(p.group(2) or p.group(4) or lo)
            return (lo, hi) if lo <= hi else None
    return None


def _printed(label: str | None) -> int | None:
    m = re.fullmatch(r"\s*(\d{1,4})\s*", label or "")
    return int(m.group(1)) if m else None


def check_humanities(workspace: Path, doc: Doc, profile: dict, sources: list[Source]) -> list[dict]:
    if profile.get("genre") not in HUMANITIES:
        return []
    items = []
    quotes = _quote_items(doc)
    h1, h2_fix, h2_hint, h2_missing, h3 = [], [], [], [], []
    h5_fix, h5_hint, found = [], [], 0
    for a, b, body in quotes:
        after = doc.raw[b:b + 400]
        if _TRANSFER.search(doc.raw[max(0, a - 40):a]) or _TRANSFER.search(after[:120]):
            continue
        pages = cited_pages(doc, after)
        where = (a, min(b, a + 40))
        hit = find_in_sources(sources, _EDITORIAL.sub("", body)) if sources else None
        if hit is None:
            # 没有来源归属的引号（作者给命题、说法、概念加的引号）不当原文引语查：哲学稿常写"若'X'的意思是'Y'"
            block = doc.raw[a:a + 1] == ">" or doc.raw[a:a + 7] == "\\begin{"
            if not (block or _QUOTE_VERB.search(doc.raw[max(0, a - 12):a]) or _CITE_AFTER.match(after)):
                continue
            entry = _ref_entry(doc, workspace, after)
            if entry and _SECONDARY_TYPES.search(entry):
                h3.append((where, bool(pages)))
            else:
                h1.append(where)
            continue
        src, lo, hi = hit
        found += 1
        changes = quote_changes(src, lo, hi, body)
        if changes:
            orig, quoted = changes[0]
            (h5_hint if src.ocr else h5_fix).append((where, f"「{body[:10]}…」原文作「{orig}」，引文作「{quoted}」"))
        paged = src.kind == "paged" and bool(src.page_of)
        if paged:
            first = src.page_of[min(lo, len(src.page_of) - 1)]
            last = src.page_of[min(max(lo, hi - 1), len(src.page_of) - 1)]
            printed = [_printed(src.labels.get(p)) for p in range(first, last + 1)]
        if pages is None:
            # 原文有印刷页码、引语却没标（写作技能 R2：直接引语标页码）。前面已交代页码的不算
            if paged and printed and all(p is not None for p in printed) \
                    and not _PAGE_BEFORE.search(doc.raw[max(0, a - 40):a]):
                real_txt = f"{min(printed)}" + (f"–{max(printed)}" if max(printed) != min(printed) else "")
                h2_missing.append((where, f"「{body[:12]}…」在第 {real_txt} 页"))
            continue
        if not paged:
            h2_hint.append(where)
            continue
        if not printed or any(p is None for p in printed):
            h2_hint.append(where)
            continue
        if not (pages[0] <= max(printed) and pages[1] >= min(printed)):
            cited_txt = f"{pages[0]}" + (f"–{pages[1]}" if pages[1] != pages[0] else "")
            real_txt = f"{min(printed)}" + (f"–{max(printed)}" if max(printed) != min(printed) else "")
            h2_fix.append((where, f"稿件标第 {cited_txt} 页，原文印刷页码是第 {real_txt} 页（{src.name}）"))
    if h1:
        items.append(_item_at(doc, "H1", "fix",
                              f"{len(h1)} 段原文引语在你上传的材料里找不到（已搜 user_data/ 里的提取文字和分页文件）："
                              "改成概括，或注\"转引自\"并去掉页码；确有出处的，请把原文上传到项目资料里", h1, count=len(h1)))
    elif quotes:
        items.append(_item("H1", RULE_TITLES["H1"], "ok", "原文引语都能在你的材料里找到（或已注转引）"))
    if h2_fix:
        items.append(_item_at(doc, "H2", "fix", "引语页码和原文对不上：" + "；".join(n for _w, n in h2_fix[:4]) + "。按原文印刷页码改正",
                              [w for w, _n in h2_fix], count=len(h2_fix)))
    if h2_missing:
        items.append(_item_at(doc, "H2", "fix",
                              f"{len(h2_missing)} 段原文引语没标页码，原文的印刷页码查得到："
                              + "；".join(n for _w, n in h2_missing[:6])
                              + "。在引注后补上印刷页码（例如 [1]（第 45 页）），不要标 PDF 的第几页",
                              [w for w, _n in h2_missing], count=len(h2_missing)))
    if h2_hint:
        items.append(_item_at(doc, "H2", "hint", f"{len(h2_hint)} 处引语的页码未核验（原文没有印刷页码，或原文是 Word）：请作者对照原书核对",
                              h2_hint, count=len(h2_hint)))
    if h3:
        with_pages = sum(1 for _w, p in h3 if p)
        items.append(_item_at(doc, "H3", "hint",
                              f"{len(h3)} 段引语出自检索来的论文，原文不在工作区，无法核验"
                              f"{f'（其中 {with_pages} 段带了页码）' if with_pages else ''}：不带页码，或写\"转引自\"",
                              [w for w, _p in h3], count=len(h3)))
    if h5_fix:
        items.append(_item_at(doc, "H5", "fix",
                              f"{len(h5_fix)} 段原文引语和你上传的材料不一致（引文里有原文这处没有的字）："
                              + "；".join(n for _w, n in h5_fix[:4])
                              + "。直接引语照原文逐字录入；原文确有讹误、缺字的，照录后用〔〕注出校改（例如原文\"己\"当作\"已\"，"
                                "写成\"己〔已〕\"），或改成转述，不要直接改字", [w for w, _n in h5_fix], count=len(h5_fix)))
    if h5_hint:
        items.append(_item_at(doc, "H5", "hint",
                              f"{len(h5_hint)} 段引语和图像识别出的原文有出入（也可能是识别误差）："
                              + "；".join(n for _w, n in h5_hint[:4]) + "。请对照原件核对",
                              [w for w, _n in h5_hint], count=len(h5_hint)))
    elif found and not h5_fix:
        items.append(_item("H5", RULE_TITLES["H5"], "ok", "找得到的原文引语都和材料逐字一致"))
    copies = unquoted_copies(doc, sources) if sources else None
    if copies:
        items.append(_item_at(doc, "H6", "hint",
                              f"{len(copies)} 处正文与你上传的材料连续 {H6_MIN} 字以上逐字相同，却没加引号：直接引用的加引号并标页码，"
                              "转述的改写成自己的话（不加引号的照抄，读者会当成作者自己的话）；照录的是你自己写的说明文字的，可以不改",
                              [(a, min(b, a + 40)) for a, b in copies], count=len(copies)))
    elif copies is not None:
        items.append(_item("H6", RULE_TITLES["H6"], "ok", "正文没有不加引号照录材料的地方"))
    raw = doc.raw
    checks = {
        "history": [("史料出处信息（档号、卷次、版本）",
                     bool(re.search(r"档号|全宗|卷宗|卷[一二三四五六七八九十\d]+|第\s*\d+\s*卷|版本|刻本|抄本|影印|档案馆藏|藏于", raw)))],
        "law": [("法条的版本年份（如\"《民法典》（2020 年）\"或\"2018 年修正\"）",
                 bool(re.search(r"《[^》]{2,30}法[^》]{0,10}》\s*[（(]\s*(?:19|20)\d{2}\s*年?|(?:19|20)\d{2}\s*年(?:修正|修订|颁布|施行)", raw))
                 or not re.search(r"《[^》]{2,30}法[^》]{0,10}》", raw)),
                ("案号格式（如\"（2021）京 01 民终 123 号\"）",
                 bool(re.search(r"[（(]\s*(?:19|20)\d{2}\s*[）)]\s*[" + CJK + r"\d]{1,8}\s*\d*\s*[" + CJK + r"]{1,4}\s*\d+\s*号", raw))
                 or not re.search(r"判决|裁定|案例|案件", raw))],
        "philosophy": [("反驳与回应", bool(re.search(r"反驳|反对意见|可能的批评|批评者|有人可能会|回应|质疑|objection|reply|response to",
                                                    raw, re.I)))],
        "social": [("理论与材料的对应", bool(re.search(r"理论|框架|视角|概念", raw) and re.search(r"访谈|问卷|数据|材料|田野|案例|样本", raw)))],
    }.get(str(profile.get("discipline") or ""), [])
    if checks:
        items.append(_missing_item("H4", checks, f"{profile.get('discipline_label') or '本学科'}的最低要素"))
    return items


# ---------- 汇总 ----------
def _plan_items(workspace: Path, profile: dict, plan_file: str) -> list[dict]:
    text = _read(Path(workspace) / plan_file)
    items: list[dict] = []
    checks = (
        lambda: [check_spine(workspace, plan_file, text)],
        lambda: [check_contributions(plan_file, text)],
        lambda: check_decisions(workspace, profile, plan_file, text),
        lambda: [check_matrix(plan_file, text)],
    )
    for index, check in enumerate(checks, 1):
        try:
            items.extend(item for item in check() if item)
        except Exception as exc:  # noqa: BLE001 — 一项出错不连累别的项
            items.append(_item(f"P{index}", f"P{index}", "error", f"这一项没查成：{exc.__class__.__name__}: {str(exc)[:200]}"))
    return items


def _draft_items(workspace: Path, profile: dict, rel: str) -> tuple[list[dict], dict, int]:
    """稿件阶段的各组检查：(结果项, 读到的源文件 → sha256, 正文可见字数)。一组出错只记这一组"检查未完成"。"""
    doc = load_manuscript(workspace, rel)
    if doc is None:
        return [_item("S1", "成稿", "error", f"读不到 {rel}")], {}, 0
    user = user_texts(workspace)
    cache: dict = {}

    def sources() -> list[Source]:
        if "sources" not in cache:
            cache["sources"] = load_sources(workspace)
        return cache["sources"]

    def material() -> str:
        return "".join(src.norm for src in sources()) + _norm(user)

    groups = (
        ("S", lambda: check_structure(doc, profile, user)),
        ("I", lambda: check_intro_results(doc, profile)),
        ("R", lambda: check_review(doc, profile)),
        ("R4", lambda: check_lit_coverage(workspace, doc, profile)),
        ("D", lambda: check_discussion(doc, profile)),
        ("C", lambda: check_conclusion(workspace, doc, profile)),
        ("N", lambda: check_overclaim(doc, profile)),
        ("K", lambda: check_tone(doc, profile, user)),
        ("K3", lambda: check_leaks(workspace, doc, user)),
        ("T", lambda: check_research_type(doc, profile, material() if profile.get("research_type") == "clinical" else "")),
        ("T7", lambda: check_simulated(workspace, doc, profile)),
        ("H", lambda: check_humanities(workspace, doc, profile, sources())),
        ("Q", lambda: check_proposal(workspace, doc, profile, user)),
    )
    items: list[dict] = []
    for group, check in groups:
        try:
            items.extend(item for item in check() if item)
        except Exception as exc:  # noqa: BLE001
            items.append(_item(group, f"{group} 组", "error", f"这一组没查成：{exc.__class__.__name__}: {str(exc)[:200]}"))
    visible = len(_CJK_CHAR.findall(doc.prose)) + len(re.findall(r"[A-Za-z]+", doc.prose))
    return items, doc.files, visible


def fingerprint(files: dict) -> str:
    return hashlib.sha256(json.dumps(sorted((files or {}).items()), ensure_ascii=False).encode("utf-8")).hexdigest()


def is_current(workspace: Path, result: dict) -> bool:
    """这份结论还对应工作区里现在的稿件吗（稿件或 \\input 的文件改过、删过就不对应了）。"""
    rel = (result or {}).get("manuscript")
    if not rel:
        return True
    try:
        return fingerprint(manuscript_files(Path(workspace), rel)) == result.get("fingerprint")
    except Exception:  # noqa: BLE001
        return False


def run(workspace: Path, *, stage: str = "plan", skill: str, now: str | None = None, source: str | None = None) -> dict:
    workspace = Path(workspace)
    profile = load_profile(workspace) or {}
    items: list[dict] = []
    plan_file = PLAN_FILE_BY_SKILL.get(skill, "PAPER_PLAN.md") if stage == "plan" else (
        PLAN_FILE_BY_SKILL.get(skill) if stage == "draft" else None)
    if plan_file:
        items.extend(_plan_items(workspace, profile, plan_file))   # 开题、综述一步写规划和成稿：两组一起查
    manuscript, files, visible = None, {}, 0
    if stage in ("draft", "final"):
        manuscript = source or manuscript_rel(workspace, stage, skill, profile)
        if manuscript:
            try:
                draft, files, visible = _draft_items(workspace, profile, manuscript)
                items.extend(draft)
            except Exception as exc:  # noqa: BLE001
                items.append(_item("S1", "成稿", "error", f"读稿没成功：{exc.__class__.__name__}: {str(exc)[:200]}"))
    counts = Counter(item["status"] for item in items)
    result = {
        "schema_version": SCHEMA_VERSION,
        "stage": stage,
        "skill": skill,
        "plan_file": plan_file,
        "generated_at": now or datetime.now().strftime("%Y-%m-%d %H:%M"),
        "generated_epoch": time.time(),
        "profile": {key: profile.get(key) for key in (
            "template", "genre", "genre_label", "language", "research_type", "research_type_label",
            "research_type_source", "discipline_label", "report_kind", "course_subject",
            "level", "degree_type", "proposal_family", "proposal_field_label")},
        "counts": {status: counts.get(status, 0) for status in STATUSES},
        "items": items,
    }
    if stage in ("draft", "final"):
        result.update(manuscript=manuscript, sources=files, fingerprint=fingerprint(files), visible_chars=visible,
                      report=REPORT_NAME)
    elif plan_file and (workspace / plan_file).is_file():
        # 规划阶段也记下大纲的摘要：对话里改了大纲再查一遍时，认得出"动手前那次检查"查的是不是改之前那一版
        # （只用来比新旧，不当稿件指纹：规划阶段的结论没有过期一说）
        result["sources"] = {plan_file: _sha256(workspace / plan_file)}
    return result


def write_result(workspace: Path, result: dict) -> None:
    target = Path(workspace) / JSON_RELATIVE
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(target)
    if result.get("stage") in ("draft", "final") and result.get("manuscript"):
        # 给人看的报告只在稿件阶段写（规划阶段写在工作区根目录会被别的检查当成稿件扫）
        report = Path(workspace) / REPORT_NAME
        tmp_md = report.with_suffix(".md.tmp")
        tmp_md.write_text(render_markdown(result), encoding="utf-8")
        tmp_md.replace(report)


_STAGE_TITLE = {"plan": "规划核对", "draft": "写作检查（写作步完成后）", "final": "终稿写作检查（编译或导出后）"}


def render_markdown(result: dict) -> str:
    counts = result.get("counts") or {}
    prof = result.get("profile") or {}
    bits = [prof.get("genre_label") or ""]
    if prof.get("research_type_label"):
        source = {"user": "你选的", "ai": "AI 判断", "default": "默认"}.get(prof.get("research_type_source") or "", "")
        bits.append(f"研究类型 {prof['research_type_label']}" + (f"（{source}）" if source else ""))
    if prof.get("genre") == "proposal":
        level = _LEVEL_LABEL.get(str(prof.get("level") or ""), "")
        if level:
            bits.append(level + ("（专业学位）" if prof.get("degree_type") == "professional" else ""))
        family = prof.get("proposal_field_label") or _FAMILY_LABEL.get(str(prof.get("proposal_family") or ""))
        if family:
            bits.append(f"学科 {family}")
    elif prof.get("discipline_label"):
        bits.append(f"学科 {prof['discipline_label']}")
    files = result.get("sources") or {}
    if result.get("stage") == "final":
        fix_note = "终稿检查只报告、不改稿，照位置改源稿即可"
    elif result.get("auto_fix"):
        fix_note = "写作步完成后后台已按清单让写作步改过一轮，这里列的是改完仍有的"
    else:
        fix_note = "这次只报告，没有自动改稿"
    lines = [
        f"# {_STAGE_TITLE.get(result.get('stage'), '写作检查')}",
        "",
        f"- 稿件：`{result.get('manuscript')}`" + (f"（含 {len(files)} 个源文件）" if len(files) > 1 else ""),
        f"- 时间：{result.get('generated_at')}",
        f"- 写作档案：{' · '.join(b for b in bits if b)}",
        f"- 结果：需修 {counts.get('fix', 0)} 项 · 提示 {counts.get('hint', 0)} 项 · 通过 {counts.get('ok', 0)} 项"
        + (f" · 没查成 {counts['error']} 项" if counts.get("error") else ""),
        "",
        f"> 这份报告由规则自动生成，只读稿件、不改稿。\"需修\"是误报率很低的硬伤：{fix_note}；"
        "\"提示\"是倾向性问题，供你判断，不必清零。K2 只是写法计数，不是 AI 率。"
        "稿件之后再改过，这份结论就过期了，重新编译或导出时会再查一遍。",
        "",
    ]
    order = (("fix", "需修"), ("error", "没查成"), ("hint", "提示"))
    for status, label in order:
        chosen = [item for item in result.get("items") or [] if item.get("status") == status]
        if not chosen:
            continue
        lines += [f"## {label}（{len(chosen)} 项）", ""]
        for item in chosen:
            lines.append(f"### {item.get('id')} {item.get('title')}")
            lines.append("")
            lines.append(str(item.get("message") or ""))
            locs = item.get("locations") or []
            if locs:
                lines.append("")
                for loc in locs:
                    excerpt = str(loc.get("excerpt") or "").replace("|", "｜")
                    lines.append(f"- `{loc.get('file')}:{loc.get('line')}`" + (f"　{excerpt}" if excerpt else ""))
                more = (item.get("count") or len(locs)) - len(locs)
                if more > 0:
                    lines.append(f"- ……另有 {more} 处")
            lines.append("")
    passed = [item for item in result.get("items") or [] if item.get("status") in ("ok", "skipped")]
    if passed:
        lines += ["## 通过与不适用", ""]
        lines += [f"- {item.get('id')} {item.get('title')}：{item.get('message')}" for item in passed]
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def render_lines(result: dict) -> list[str]:
    lines = []
    for item in result.get("items") or []:
        tag = {"fix": "FIX", "hint": "HINT", "ok": "OK", "skipped": "SKIP", "error": "ERROR"}.get(item["status"], "INFO")
        where = ""
        locs = item.get("locations") or []
        if item["status"] in ("fix", "hint") and locs:
            where = "；位置：" + "、".join(f"{loc['file']}:{loc['line']}" for loc in locs[:4])
        lines.append(f"{tag}: [{item['id']} {item['title']}] {item['message']}{where}")
    counts = result.get("counts") or {}
    lines.append(f"WRITING_CHECK stage={result.get('stage')} fix={counts.get('fix', 0)} hint={counts.get('hint', 0)} "
                 f"error={counts.get('error', 0)}")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="学术写作检查：规划阶段核对大纲论证主线（P1–P4）；写作步、编译或导出步之后检查成稿（S/I/R/D/C/N/K/T/H 组）。"
                    "只读不改稿。",
        epilog="退出码：0 没有需修项；1 有需修项；2 不适用；3 检查没跑成。",
    )
    parser.add_argument("workspace", nargs="?", default=".", help="工作区根目录（默认当前目录）")
    parser.add_argument("--stage", choices=STAGES, default="plan")
    parser.add_argument("--skill", required=True, help="本步技能名，例如 paper-plan-zh、paper-write-zh、docx-export")
    parser.add_argument("--source", help="稿件阶段指定要查的成稿（工作区相对路径），默认按技能和模板找")
    parser.add_argument("--json", action="store_true", help="只打印结果 JSON，不写文件")
    args = parser.parse_args(argv)
    workspace = Path(args.workspace).resolve()
    if not applies(workspace, args.stage, args.skill, source=args.source):
        print("SKIP: 不适用（没有写作档案、这一阶段没有对应规则，或找不到成稿）")
        return EXIT_NOT_APPLICABLE
    result = run(workspace, stage=args.stage, skill=args.skill, source=args.source)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
    else:
        write_result(workspace, result)
        print("\n".join(render_lines(result)))
    return EXIT_FIX if (result.get("counts") or {}).get("fix") else EXIT_OK


def cli(argv: list[str] | None = None) -> int:
    """命令行入口：检查器自身出错时如实说没跑成（退出 3），不能当成通过或需修。"""
    try:
        return main(argv)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"[CHECK_UNAVAILABLE] 写作检查没有跑成：{type(exc).__name__}: {exc}")
        return EXIT_UNAVAILABLE


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(cli())
