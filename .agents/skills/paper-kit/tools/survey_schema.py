#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""市调大赛问卷规格 QUESTIONNAIRE.json：读取、结构校验、跳转逻辑解析、变量编码表、作答估时。

survey_lint / survey_render / survey_pretest / survey_rehearsal / survey_import /
survey_clean / survey_stats 共用这一份口径。只用标准库。
问卷互助中心用的是本文件的逐字节副本（survey-service/app/survey_schema.py），
所以互助中心和网页链接页顶的“预计 N 分钟”与体检报告的估时是同一个数。

用法：
  python _utils/survey_schema.py validate QUESTIONNAIRE.json
  python _utils/survey_schema.py codebook QUESTIONNAIRE.json --out CODEBOOK.json
退出码：0 通过；1 有结构错误；2 文件缺失或不是合法 JSON。

题型（type）：
  single 单选 | multi 多选 | text 开放填空 | number 数值填空 | scale 单题量表 |
  matrix_single 矩阵单选 | matrix_scale 矩阵量表 | rank 排序 | paragraph 段落说明（不作答）
数据列命名：
  single/text/number/scale → 题号本身（Q5）；multi → Q5_<选项编码>（0/1）；
  matrix_* → 行号（Q16_r1）；rank → Q9_<选项编码>（名次）；"其他（请注明）"→ Q5_<编码>_text
跳转表达式（show_if / terminate_if）：
  Q3 == 1、Q3 != 2、Q7 >= 4、Q3 in [1, 2]、Q4 contains 3、Q8 answered，
  用 and / or / not（也认 且 / 或 / 非）和括号组合。多选题用 == 表示"选了这一项"。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SCHEMA_ID = "paperkit.survey.questionnaire/v1"
QUESTION_TYPES = (
    "single", "multi", "text", "number", "scale",
    "matrix_single", "matrix_scale", "rank", "paragraph",
)
CHOICE_TYPES = {"single", "multi", "matrix_single", "rank"}
SCALE_TYPES = {"scale", "matrix_scale"}
MATRIX_TYPES = {"matrix_single", "matrix_scale"}
MEASURES = ("nominal", "ordinal", "interval", "ratio")
TYPE_LABELS = {
    "single": "单选题", "multi": "多选题", "text": "填空题", "number": "数值填空题",
    "scale": "量表题", "matrix_single": "矩阵单选题", "matrix_scale": "矩阵量表题",
    "rank": "排序题", "paragraph": "段落说明",
}
_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,39}$")


class SchemaError(ValueError):
    """问卷文件读不出来（不存在、不是 JSON、顶层不是对象）。"""


# ───────────────────────────── 读取 ─────────────────────────────

def load_json(path: str | Path) -> Any:
    p = Path(path)
    if not p.is_file():
        raise SchemaError(f"找不到文件：{p}")
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise SchemaError(f"{p.name} 不是合法 JSON：第 {exc.lineno} 行 {exc.msg}") from exc


def load_questionnaire(path: str | Path) -> dict:
    data = load_json(path)
    if not isinstance(data, dict):
        raise SchemaError("问卷文件顶层必须是 JSON 对象")
    return normalize(data)


# 清洗认的质控阈值。不按作答用时判无效（2026-10-10 用户定）：min_seconds、speed_ratio 不再是阈值，写了也不采用
QUALITY_THRESHOLDS = ("straightline_min_items", "core_missing_max")


def normalize(q: dict) -> dict:
    """补齐可推导的字段（矩阵行号、默认 required、默认测量尺度），不改动已有值。
    质控阈值直接写在 quality 下（如 "quality": {"core_missing_max": 0.3}）时补进 quality.thresholds：清洗脚本
    只读 thresholds，曾因写错一层，问卷设的阈值不生效、按默认值判。两处都写了以 thresholds 为准。"""
    q = json.loads(json.dumps(q, ensure_ascii=False))  # 深拷贝，避免改到调用方的对象
    quality = q.get("quality")
    if isinstance(quality, dict):
        loose = {k: quality[k] for k in QUALITY_THRESHOLDS if k in quality}
        if loose:
            current = quality.get("thresholds") if isinstance(quality.get("thresholds"), dict) else {}
            quality["thresholds"] = {**loose, **current}
    for item in q.get("questions") or []:
        if not isinstance(item, dict):
            continue
        qtype = item.get("type")
        item.setdefault("required", qtype != "paragraph")
        if qtype in MATRIX_TYPES:
            rows = item.get("rows") or []
            for idx, row in enumerate(rows, start=1):
                if isinstance(row, dict) and not row.get("id"):
                    row["id"] = f"{item.get('id')}_r{idx}"
        if "measure" not in item:
            item["measure"] = default_measure(qtype)
    return q


def default_measure(qtype: str | None) -> str:
    if qtype in SCALE_TYPES:
        return "interval"
    if qtype == "number":
        return "ratio"
    if qtype == "rank":
        return "ordinal"
    return "nominal"


def questions(q: dict) -> list[dict]:
    return [item for item in (q.get("questions") or []) if isinstance(item, dict)]


def answerable(item: dict) -> bool:
    return item.get("type") != "paragraph"


def option_codes(item: dict) -> list[int]:
    codes = []
    for opt in item.get("options") or []:
        if isinstance(opt, dict) and isinstance(opt.get("code"), int) and not isinstance(opt.get("code"), bool):
            codes.append(opt["code"])
    return codes


def option_label(item: dict, code: Any) -> str | None:
    for opt in item.get("options") or []:
        if isinstance(opt, dict) and opt.get("code") == code:
            return str(opt.get("label", ""))
    return None


def scale_range(item: dict) -> tuple[int, int] | None:
    scale = item.get("scale")
    if not isinstance(scale, dict):
        return None
    lo, hi = scale.get("min"), scale.get("max")
    if isinstance(lo, int) and isinstance(hi, int) and not isinstance(lo, bool) and not isinstance(hi, bool):
        return lo, hi
    return None


def valid_values(item: dict) -> list[int] | None:
    """单值题的合法取值；数值/开放题返回 None。"""
    qtype = item.get("type")
    if qtype in {"single", "matrix_single"}:
        return option_codes(item)
    if qtype in SCALE_TYPES:
        rng = scale_range(item)
        return list(range(rng[0], rng[1] + 1)) if rng else None
    return None


# ───────────────────────────── 变量编码表 ─────────────────────────────

def variables(q: dict) -> list[dict]:
    """按数据列展开的变量清单（CODEBOOK.json 的 variables）。"""
    out: list[dict] = []
    for item in questions(q):
        qid, qtype, text = item.get("id"), item.get("type"), str(item.get("text", "")).strip()
        if not qid or qtype == "paragraph":
            continue
        base = {
            "question": qid,
            "question_type": qtype,
            "construct": item.get("construct"),
            "rq": item.get("rq") or [],
            "role": item.get("role"),
        }
        values = {str(o["code"]): str(o.get("label", "")) for o in item.get("options") or [] if isinstance(o, dict) and "code" in o}
        if qtype == "single":
            out.append({**base, "name": qid, "label": text, "kind": "categorical",
                        "measure": item.get("measure", "nominal"), "values": values})
        elif qtype == "multi":
            for opt in item.get("options") or []:
                code = opt.get("code")
                out.append({**base, "name": f"{qid}_{code}", "label": f"{text}｜{opt.get('label', '')}",
                            "kind": "binary", "measure": "nominal", "values": {"0": "未选", "1": "选中"},
                            "option_code": code})
        elif qtype in {"text"}:
            out.append({**base, "name": qid, "label": text, "kind": "text", "measure": "nominal"})
        elif qtype == "number":
            out.append({**base, "name": qid, "label": text, "kind": "numeric",
                        "measure": item.get("measure", "ratio"), "unit": item.get("unit"),
                        "min": item.get("min"), "max": item.get("max")})
        elif qtype == "scale":
            rng = scale_range(item) or (None, None)
            out.append({**base, "name": qid, "label": text, "kind": "scale",
                        "measure": item.get("measure", "interval"), "min": rng[0], "max": rng[1],
                        "values": {str(k): str(v) for k, v in ((item.get("scale") or {}).get("labels") or {}).items()},
                        "reverse": bool(item.get("reverse"))})
        elif qtype in MATRIX_TYPES:
            rng = scale_range(item) or (None, None)
            for row in item.get("rows") or []:
                if not isinstance(row, dict):
                    continue
                var = {**base, "name": row.get("id"), "label": f"{text}｜{row.get('label', '')}",
                       "construct": row.get("construct", item.get("construct")), "row_label": row.get("label")}
                if qtype == "matrix_scale":
                    var.update({"kind": "scale", "measure": item.get("measure", "interval"),
                                "min": rng[0], "max": rng[1], "reverse": bool(row.get("reverse")),
                                "values": {str(k): str(v) for k, v in ((item.get("scale") or {}).get("labels") or {}).items()}})
                else:
                    var.update({"kind": "categorical", "measure": item.get("measure", "nominal"), "values": values})
                out.append(var)
        elif qtype == "rank":
            n = len(item.get("options") or [])
            for opt in item.get("options") or []:
                out.append({**base, "name": f"{qid}_{opt.get('code')}", "label": f"{text}｜{opt.get('label', '')}",
                            "kind": "rank", "measure": "ordinal", "min": 1, "max": n, "option_code": opt.get("code")})
        for opt in item.get("options") or []:
            if isinstance(opt, dict) and opt.get("other"):
                out.append({**base, "name": f"{qid}_{opt.get('code')}_text",
                            "label": f"{text}｜{opt.get('label', '其他')}（文字）", "kind": "text", "measure": "nominal"})
    return out


def constructs(q: dict) -> dict[str, list[str]]:
    """潜变量 → 测量它的题目变量名（量表/矩阵量表）。"""
    groups: dict[str, list[str]] = {}
    for var in variables(q):
        name = var.get("construct")
        if name and var.get("kind") == "scale":
            groups.setdefault(str(name), []).append(var["name"])
    return groups


def codebook(q: dict) -> dict:
    return {
        "schema": "paperkit.survey.codebook/v1",
        "title": q.get("title", ""),
        "questionnaire_version": (q.get("meta") or {}).get("version"),
        "variables": variables(q),
        "constructs": constructs(q),
    }


# ───────────────────────────── 作答估时 ─────────────────────────────
# 阅读按 400 字/分钟（卷首语、题干、选项、矩阵行都算），作答按题型计秒。
READ_CHARS_PER_MIN = 400
ANSWER_SECONDS = {"single": 4, "multi": 7, "scale": 3, "text": 25, "number": 8,
                  "matrix_row": 3, "rank_option": 3, "paragraph": 0}


def estimate_seconds(q: dict) -> dict:
    """整卷作答估时：total_seconds 秒、total_minutes（0.1 分钟）、minutes（给填写的人看的整分钟）、per_question 逐题秒数。"""
    per_question, total = {}, len(str(q.get("intro") or "")) / READ_CHARS_PER_MIN * 60
    for item in questions(q):
        qtype = item.get("type")
        chars = len(str(item.get("text", "")))
        chars += sum(len(str(o.get("label", ""))) for o in item.get("options") or [] if isinstance(o, dict))
        chars += sum(len(str(r.get("label", ""))) for r in item.get("rows") or [] if isinstance(r, dict))
        sec = chars / READ_CHARS_PER_MIN * 60
        if qtype in MATRIX_TYPES:
            sec += ANSWER_SECONDS["matrix_row"] * len(item.get("rows") or [])
        elif qtype == "rank":
            sec += ANSWER_SECONDS["rank_option"] * len(item.get("options") or [])
        else:
            sec += ANSWER_SECONDS.get(qtype, 4)
        per_question[item.get("id")] = round(sec, 1)
        total += sec
    minutes = round(total / 60, 1)
    return {"total_seconds": round(total), "total_minutes": minutes, "minutes": max(1, int(minutes + 0.5)),
            "per_question": per_question}


def estimate_minutes(q: dict) -> int:
    """互助中心、网页链接页顶的“预计 N 分钟”，也是卷首语该写的时长：total_minutes 四舍五入，至少 1 分钟。"""
    return estimate_seconds(q)["minutes"]


# ───────────────────────────── 跳转逻辑 ─────────────────────────────

class LogicError(ValueError):
    pass


_TOKEN_RE = re.compile(
    r"\s*(?:(?P<num>-?\d+(?:\.\d+)?)|(?P<op>==|!=|>=|<=|>|<)|(?P<punct>[()\[\],])"
    r"|(?P<word>[A-Za-z_][A-Za-z0-9_]*|且|或|非))"
)
_KEYWORDS = {"and": "and", "且": "and", "or": "or", "或": "or", "not": "not", "非": "not",
             "in": "in", "contains": "contains", "answered": "answered"}


def _tokenize(expr: str) -> list[tuple[str, str]]:
    tokens, pos, text = [], 0, expr.strip()
    while pos < len(text):
        m = _TOKEN_RE.match(text, pos)
        if not m or m.end() == pos:
            raise LogicError(f"无法识别的跳转表达式片段：{text[pos:pos + 12]!r}")
        pos = m.end()
        if m.group("num") is not None:
            raw = m.group("num")
            tokens.append(("num", raw))
        elif m.group("op"):
            tokens.append(("op", m.group("op")))
        elif m.group("punct"):
            tokens.append(("punct", m.group("punct")))
        else:
            word = m.group("word")
            kw = _KEYWORDS.get(word.lower() if word.isascii() else word)
            tokens.append(("kw", kw) if kw else ("id", word))
    return tokens


class _Parser:
    def __init__(self, tokens: list[tuple[str, str]]):
        self.tokens, self.i = tokens, 0

    def peek(self) -> tuple[str, str] | None:
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def take(self, kind: str | None = None, value: str | None = None) -> tuple[str, str]:
        tok = self.peek()
        if tok is None or (kind and tok[0] != kind) or (value and tok[1] != value):
            want = value or kind or "内容"
            raise LogicError(f"跳转表达式在第 {self.i + 1} 个记号处缺少 {want}")
        self.i += 1
        return tok

    def parse(self) -> tuple:
        node = self.or_expr()
        if self.peek() is not None:
            raise LogicError(f"跳转表达式多出了 {self.peek()[1]!r}")
        return node

    def or_expr(self) -> tuple:
        node = self.and_expr()
        while self.peek() == ("kw", "or"):
            self.take()
            node = ("or", node, self.and_expr())
        return node

    def and_expr(self) -> tuple:
        node = self.not_expr()
        while self.peek() == ("kw", "and"):
            self.take()
            node = ("and", node, self.not_expr())
        return node

    def not_expr(self) -> tuple:
        if self.peek() == ("kw", "not"):
            self.take()
            return ("not", self.not_expr())
        return self.atom()

    def atom(self) -> tuple:
        if self.peek() == ("punct", "("):
            self.take()
            node = self.or_expr()
            self.take("punct", ")")
            return node
        ident = self.take("id")[1]
        tok = self.peek()
        if tok == ("kw", "answered"):
            self.take()
            return ("answered", ident)
        if tok == ("kw", "in"):
            self.take()
            self.take("punct", "[")
            values = [self._number()]
            while self.peek() == ("punct", ","):
                self.take()
                values.append(self._number())
            self.take("punct", "]")
            return ("in", ident, tuple(values))
        if tok == ("kw", "contains"):
            self.take()
            return ("cmp", "==", ident, self._number())
        op = self.take("op")[1]
        return ("cmp", op, ident, self._number())

    def _number(self) -> float | int:
        raw = self.take("num")[1]
        return float(raw) if "." in raw else int(raw)


def parse_logic(expr: str) -> tuple:
    if not isinstance(expr, str) or not expr.strip():
        raise LogicError("跳转表达式为空")
    return _Parser(_tokenize(expr)).parse()


def referenced(node: tuple) -> list[tuple[str, list]]:
    """表达式里引用的 (题号, 比较用到的取值列表)。"""
    kind = node[0]
    if kind in {"and", "or"}:
        return referenced(node[1]) + referenced(node[2])
    if kind == "not":
        return referenced(node[1])
    if kind == "answered":
        return [(node[1], [])]
    if kind == "in":
        return [(node[1], list(node[2]))]
    return [(node[2], [node[3]])]


def evaluate(node: tuple, response: dict) -> bool:
    """response：题号/行号 → 取值（多选为编码集合，未作答为 None）。"""
    kind = node[0]
    if kind == "and":
        return evaluate(node[1], response) and evaluate(node[2], response)
    if kind == "or":
        return evaluate(node[1], response) or evaluate(node[2], response)
    if kind == "not":
        return not evaluate(node[1], response)
    if kind == "answered":
        value = response.get(node[1])
        return value not in (None, "", set(), frozenset(), [])
    value = response.get(node[1] if kind == "in" else node[2])
    if value is None or value == "":
        return False
    if kind == "in":
        if isinstance(value, (set, frozenset, list, tuple)):
            return bool(set(value) & set(node[2]))
        return value in node[2]
    op, target = node[1], node[3]
    if isinstance(value, (set, frozenset, list, tuple)):
        members = set(value)
        if op == "==":
            return target in members
        if op == "!=":
            return target not in members
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return {
        "==": number == target, "!=": number != target, ">=": number >= target,
        "<=": number <= target, ">": number > target, "<": number < target,
    }[op]


def is_shown(item: dict, response: dict) -> bool:
    """单看这一道题的显示条件。要判断整份作答里哪些题显示，用 shown_view（按顺序、只认还显示着的题）。"""
    expr = item.get("show_if")
    if not expr:
        return True
    try:
        return evaluate(parse_logic(expr), response)
    except LogicError:
        return True


def item_keys(item: dict) -> list[str]:
    """一道题的作答占的键：矩阵题是各行号，其余是题号；有“其他（请注明）”的，再加说明的键（Q5_<编码>_text）。"""
    qid = item.get("id")
    if item.get("type") in MATRIX_TYPES:
        keys = [r["id"] for r in item.get("rows") or [] if isinstance(r, dict) and r.get("id")]
    else:
        keys = [qid] if qid else []
    return keys + [f"{qid}_{o.get('code')}_text" for o in item.get("options") or [] if isinstance(o, dict) and o.get("other")]


def other_chosen(item: dict, response: dict, code: Any) -> bool:
    """“其他（请注明）”这一项选了没有（单选等于它、多选包含它）。没选时写的说明是改答案留下的旧字。"""
    value = response.get(item.get("id"))
    if isinstance(value, (set, frozenset, list, tuple)):
        return code in value
    return value == code


def shown_view(q: dict, response: dict) -> tuple[set, dict]:
    """按题目顺序判断每道题显不显示，返回（显示的题号集合，去掉不显示的题的作答后的作答）。
    后面题的显示条件只认前面还显示着的题：前面的题被跳转藏起来以后，它的旧答案不再撑开后面的题。
    曾在第 3 题改成“没听说过”后，付费题的旧答案仍让“每月付多少钱”显示、必答，导出的数据也留着。
    显示条件只能引用前面的题（validate 的 logic_forward_ref），所以按顺序算一遍就够。"""
    view = dict(response)
    shown: set = set()
    for item in questions(q):
        if is_shown(item, view):
            shown.add(item.get("id"))
        else:
            for key in item_keys(item):
                view.pop(key, None)
    return shown, view


# ───────────────────────────── 结构校验 ─────────────────────────────

def _issue(rule: str, message: str, qid: str | None = None, severity: str = "error", suggestion: str = "") -> dict:
    return {"rule": rule, "severity": severity, "question": qid, "message": message,
            "suggestion": suggestion, "confidence": 1.0, "source": "schema"}


def validate(q: dict) -> list[dict]:
    issues: list[dict] = []
    if q.get("schema") not in (None, SCHEMA_ID):
        issues.append(_issue("schema_id", f"schema 应为 {SCHEMA_ID}", severity="warning"))
    if not str(q.get("title", "")).strip():
        issues.append(_issue("title_missing", "问卷缺少标题"))
    items = questions(q)
    if not items:
        issues.append(_issue("no_questions", "问卷没有任何题目"))
        return issues
    sections = {s.get("id") for s in q.get("sections") or [] if isinstance(s, dict)}
    seen_ids: dict[str, str] = {}
    order: dict[str, int] = {}
    by_id: dict[str, dict] = {}

    def claim(name: str, owner: str) -> None:
        if name in seen_ids:
            issues.append(_issue("duplicate_id", f"编号 {name} 重复（{seen_ids[name]} 与 {owner}）", owner))
        else:
            seen_ids[name] = owner

    for idx, item in enumerate(items):
        qid, qtype = item.get("id"), item.get("type")
        label = qid or f"第{idx + 1}题"
        if not isinstance(qid, str) or not _ID_RE.match(qid):
            issues.append(_issue("bad_id", f"{label} 的题号不合法（字母开头，只含字母数字下划线）", label))
            continue
        claim(qid, qid)
        order.setdefault(qid, idx)   # 题号重复时以第一次出现的为准，重复项另报错
        by_id.setdefault(qid, item)
        if qtype not in QUESTION_TYPES:
            issues.append(_issue("bad_type", f"{qid} 的题型 {qtype!r} 不认识，可选：{'、'.join(QUESTION_TYPES)}", qid))
            continue
        if not str(item.get("text", "")).strip():
            issues.append(_issue("text_missing", f"{qid} 缺少题干", qid))
        if sections and item.get("section") and item.get("section") not in sections:
            issues.append(_issue("bad_section", f"{qid} 指向不存在的部分 {item.get('section')}", qid))
        if item.get("measure") and item["measure"] not in MEASURES:
            issues.append(_issue("bad_measure", f"{qid} 的测量尺度 {item['measure']!r} 不认识", qid))
        if qtype in CHOICE_TYPES:
            opts = item.get("options") or []
            codes = option_codes(item)
            if len(opts) < 2:
                issues.append(_issue("too_few_options", f"{qid} 至少需要 2 个选项", qid))
            if len(codes) != len(opts):
                issues.append(_issue("bad_option_code", f"{qid} 的选项编码必须都是整数", qid))
            if len(set(codes)) != len(codes):
                issues.append(_issue("duplicate_option_code", f"{qid} 的选项编码有重复", qid))
            elif codes and len(codes) == len(opts) and codes != list(range(1, len(codes) + 1)):
                # 问卷星“按选项序号”导出的是第几个选项（1、2、3……），编码跳号或乱序时数据会整体错位且不报错
                issues.append(_issue("option_codes_unordered",
                                     f"{qid} 的选项编码不是按选项顺序的 1、2、3……（现在是 {codes}）："
                                     "用问卷星“按选项序号”导出的数据会对不上选项", qid, severity="warning"))
            labels = [str(o.get("label", "")).strip() for o in opts if isinstance(o, dict)]
            if any(not lab for lab in labels):
                issues.append(_issue("empty_option", f"{qid} 有空白选项", qid))
            if len(set(labels)) != len(labels):
                issues.append(_issue("duplicate_option_label", f"{qid} 有重复的选项文字", qid))
        if qtype in SCALE_TYPES:
            rng = scale_range(item)
            if not rng or rng[0] >= rng[1] or not 2 <= rng[1] - rng[0] + 1 <= 11:
                issues.append(_issue("bad_scale", f"{qid} 的量表需要整数 min < max，且 2–11 个刻度", qid))
        if qtype in MATRIX_TYPES:
            rows = [r for r in item.get("rows") or [] if isinstance(r, dict)]
            if not rows:
                issues.append(_issue("no_rows", f"{qid} 是矩阵题但没有行", qid))
            row_labels = [str(r.get("label", "")).strip() for r in rows]
            if any(not lab for lab in row_labels):
                issues.append(_issue("empty_row", f"{qid} 有空白的行标题", qid))
            for row in rows:
                rid = row.get("id")
                if not isinstance(rid, str) or not _ID_RE.match(rid):
                    issues.append(_issue("bad_row_id", f"{qid} 的行号 {rid!r} 不合法", qid))
                else:
                    claim(rid, qid)
                    order[rid] = idx
        if qtype == "multi":
            codes = set(option_codes(item))
            lo, hi = item.get("min_select"), item.get("max_select")
            n = len(codes)
            for key, val in (("min_select", lo), ("max_select", hi)):
                if val is not None and (not isinstance(val, int) or not 1 <= val <= max(n, 1)):
                    issues.append(_issue("bad_select_limit", f"{qid} 的 {key} 应在 1–{n} 之间", qid))
            if isinstance(lo, int) and isinstance(hi, int) and lo > hi:
                issues.append(_issue("bad_select_limit", f"{qid} 的最少选择数大于最多选择数", qid))
            extra = set(item.get("exclusive_options") or []) - codes
            if extra:
                issues.append(_issue("bad_exclusive", f"{qid} 的互斥选项 {sorted(extra)} 不在选项里", qid))
        for var in _generated_names(item):
            claim(var, qid)

    for item in items:
        qid = item.get("id")
        if qid not in by_id:
            continue
        for key in ("show_if", "terminate_if"):
            expr = item.get(key)
            if not expr:
                continue
            try:
                node = parse_logic(expr)
            except LogicError as exc:
                issues.append(_issue("bad_logic", f"{qid} 的 {key} 写法有误：{exc}", qid))
                continue
            for ref, values in referenced(node):
                if ref not in order:
                    issues.append(_issue("logic_unknown_ref", f"{qid} 的 {key} 引用了不存在的 {ref}", qid))
                    continue
                if key == "show_if" and order[ref] >= order[qid]:
                    issues.append(_issue("logic_forward_ref", f"{qid} 的显示条件引用了它自己或后面的 {ref}", qid))
                if key == "terminate_if" and order[ref] > order[qid]:
                    issues.append(_issue("logic_forward_ref", f"{qid} 的甄别条件引用了后面的 {ref}", qid))
                owner = by_id.get(ref) or next((it for it in items if any(
                    isinstance(r, dict) and r.get("id") == ref for r in it.get("rows") or [])), None)
                legal = valid_values(owner) if owner else None
                if owner and owner.get("type") == "multi":
                    legal = option_codes(owner)
                if legal is not None:
                    bad = [v for v in values if v not in legal]
                    if bad:
                        issues.append(_issue("logic_bad_code", f"{qid} 的 {key} 用了 {ref} 不存在的取值 {bad}", qid))

    for quota in q.get("quotas") or []:
        if not isinstance(quota, dict):
            continue
        ref = quota.get("question")
        owner = by_id.get(ref)
        if not owner or owner.get("type") not in {"single", "scale"}:
            issues.append(_issue("bad_quota", f"配额指向的 {ref} 不存在或不是单选/量表题", ref))
            continue
        targets = quota.get("targets") or {}
        legal = {str(v) for v in (valid_values(owner) or [])}
        unknown = [k for k in targets if str(k) not in legal]
        if unknown:
            issues.append(_issue("bad_quota", f"{ref} 的配额用了不存在的选项编码 {unknown}", ref))
        try:
            shares = [float(v) for v in targets.values()]
        except (TypeError, ValueError):
            shares = []
            issues.append(_issue("bad_quota", f"{ref} 的配额比例必须是数字", ref))
        if shares and all(0 <= s <= 1 for s in shares) and abs(sum(shares) - 1) > 0.02:
            issues.append(_issue("bad_quota", f"{ref} 的配额比例之和为 {sum(shares):.2f}，应为 1", ref, severity="warning"))

    # 质控设置写错了，清洗时只会悄悄不生效：逻辑矛盾检查解析不了、引用了删掉的题
    quality = q.get("quality") if isinstance(q.get("quality"), dict) else {}
    for check in quality.get("consistency_checks") or []:
        if not isinstance(check, dict) or not str(check.get("invalid_if") or "").strip():
            continue
        name = check.get("id") or check.get("message") or ""
        try:
            node = parse_logic(check["invalid_if"])
        except LogicError as exc:
            issues.append(_issue("bad_quality_check", f"逻辑矛盾检查 {name} 写法有误，清洗时不会生效：{exc}", severity="warning"))
            continue
        unknown = sorted({ref for ref, _ in referenced(node) if ref not in order})
        if unknown:
            issues.append(_issue("bad_quality_check", f"逻辑矛盾检查 {name} 用到了问卷里没有的 {'、'.join(unknown)}，"
                                 "清洗时不会生效", severity="warning"))
            continue
        # 只凭一个作答就判整份无效（10-12 小白实测：AI 写了“新规知识题选了错误说法且没选不清楚”，264 份如实作答的答卷被剔掉）：
        # 自相矛盾要两个作答对照才算；答错知识题、选了少见的选项是真实数据。明显荒谬的陷阱题确实可以这样用，所以只提醒、不拦定稿
        keys = {ref for ref, _ in referenced(node)}
        if len(keys) == 1:
            owner = seen_ids.get(next(iter(keys)), next(iter(keys)))
            label = f"“{check['message']}”" if str(check.get("message") or "").strip() else name
            issues.append(_issue("bad_quality_check", f"逻辑矛盾检查{label}只看 {owner} 一道题的作答：自相矛盾要两个作答对照才算；"
                                 "只凭一道题选了某个选项就判整份无效（比如知识题答错、选了少见的选项），会把如实作答的人当成乱答剔掉，"
                                 "样本会偏向“懂行”的人。想挑出乱答的人请用注意力题；确实要用陷阱题，只能用任何认真读题的人都知道不可能的说法，"
                                 "否则把这条规则删掉", owner, severity="warning"))
    return issues


def _generated_names(item: dict) -> Iterable[str]:
    qid, qtype = item.get("id"), item.get("type")
    if qtype in {"multi", "rank"}:
        for code in option_codes(item):
            yield f"{qid}_{code}"
    for opt in item.get("options") or []:
        if isinstance(opt, dict) and opt.get("other"):
            yield f"{qid}_{opt.get('code')}_text"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="问卷规格校验与变量编码表")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_val = sub.add_parser("validate", help="结构校验")
    p_val.add_argument("questionnaire")
    p_cb = sub.add_parser("codebook", help="生成变量编码表")
    p_cb.add_argument("questionnaire")
    p_cb.add_argument("--out", default="CODEBOOK.json")
    args = parser.parse_args(argv)
    try:
        q = load_questionnaire(args.questionnaire)
    except SchemaError as exc:
        print(f"❌ {exc}")
        return 2
    issues = validate(q)
    errors = [i for i in issues if i["severity"] == "error"]
    for issue in issues:
        mark = "❌" if issue["severity"] == "error" else "⚠️"
        print(f"{mark} [{issue['rule']}] {issue['message']}")
    if args.cmd == "validate":
        if not errors:
            print(f"✅ 问卷结构校验通过：{len(questions(q))} 题，{len(variables(q))} 个数据变量")
        return 1 if errors else 0
    if errors:
        print("❌ 结构有错误，未生成编码表")
        return 1
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(codebook(q), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 已写出 {out}（{len(variables(q))} 个变量）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
