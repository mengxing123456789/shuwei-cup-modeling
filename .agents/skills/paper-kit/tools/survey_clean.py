#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""答卷质量清洗：每份答卷判为 有效 / 无效 / 待复核 / 非调查对象，并写明原因；不静默删除。

规则（阈值可在 QUESTIONNAIRE.json 的 "quality.thresholds" 覆盖；直接写在 "quality" 下的同名阈值也认，
超出合理范围的不采用、按默认值判）：
  非调查对象  terminate_if 成立（甄别淘汰，不计入无效）
  互助中心质检 互助中心导出的答卷（_quality 列）判为无效的 → 无效；待人工复核（疑似互刷）的 → 待复核
  重复提交    作答向量完全相同，或同一文件里平台答卷编号重复 → 保留第一份（不同文件的编号各自独立：两份问卷星
              问卷的“序号”都从 1 起，曾把第二份文件的答卷全判成重复；同一份数据重复下载的，导入时已去掉）
  作答用时    不判定（2026-10-10 用户定取消用时检查）：只统计中位用时写进结果；问卷里写的 min_seconds、
              speed_ratio 不再采用，也不提示
  整列同选    同一矩阵量表或同一潜变量 ≥ straightline_min_items(5) 题全部相同：
              含反向题（不论选的是哪一档） → 无效；两处以上 → 无效；只有一处、又没有反向题 → 有效、只做标记
              （2026-10-15 用户定，和问卷互助中心同一口径：曾列为待复核、默认不进分析，互助中心却算有效、计入收满份数，
              小白看到“已收 420 份够了”，点“数据够了”又说只有 404 份；含反向题、整列选中间那一档的曾算不矛盾，
              互助中心算无效，同日也统一成无效）
  注意力题    attention_check 题未选 attention_expected 指定的编码 → 无效
  逻辑矛盾    quality.consistency_checks: [{"id","invalid_if": 跳转表达式,"message"}] 成立 → 无效
  核心题缺失  有研究问题归属（rq）的应答题缺失比例 > core_missing_max(0.2) → 无效
  越界取值    不在编码表内 → 置空并告警
  跳转外作答  按 show_if 不该显示却有值 → 置空并告警
  开放题乱填  重复字符、键盘乱敲、纯符号 → 只在明细里标记，不改变有效/无效判定；
              “无”“没有”“不知道”是正常回答（没有建议），不算乱填

人工复核：待复核的答卷默认不进入分析。团队逐份看过后，把决定写进 data/review_decisions.csv
  （列：_rid、决定（有效 / 无效）、理由）再重跑本脚本；只对本次判为待复核的答卷生效（判了无效的不能借此改回有效），
  没写理由的不采用。结果计入 DATA_QUALITY.json 的 review_kept_n / review_dropped_n，review_n 是仍未复核的份数。
有效率 = 有效 / 符合调查对象（valid_rate_pct）；有效回收率 = 有效 / 回收（valid_of_raw_pct）。

可选加权：--margins 总体边际 JSON（{"Q2": {"1": 0.49, "2": 0.51}}）做 raking，权重截断在 [0.3, 3]，
报告 Kish 设计效应。

用法：
  python _utils/survey_clean.py QUESTIONNAIRE.json [--data data/raw_import.csv] [--provenance data/PROVENANCE.json]
      [--margins margins.json] [--outdir data] [--quality-out DATA_QUALITY.json] [--fieldwork-out FIELDWORK_LOG.json]
      [--review-decisions data/review_decisions.csv] [--demo]
演示模式：数据来源为 demo_synthetic（演示用模拟数据）时必须加 --demo，结果标记 demo=true；--demo 不收真实数据。
退出码：0 成功；1 拒收（数据来源不是真实调查）或有效样本为 0；2 输入缺失。
"""
from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
import survey_schema as S  # noqa: E402

DEFAULTS = {"straightline_min_items": 5, "core_missing_max": 0.2}
# 阈值的合理范围，超出的不采用。不按作答用时判无效：问卷里的 min_seconds、speed_ratio 不是阈值，写了也不采用
LIMITS = {"straightline_min_items": (2, 50), "core_missing_max": (0, 1)}
# 这两条原因写进数据质量文件，报告正文、清洗流程图和附录照抄，所以不写平台名（2026-10-16 用户：“正文不要提到什么
# 互助中心什么的”；原为“互助中心质检判为无效……”“互助中心待人工复核（疑似互刷）”）
HUB_INVALID = "线上问卷广场质检判为无效（注意力题答错、整列同选等）"
HUB_HELD = "线上问卷广场标记待人工复核（疑似相互敷衍填答）"
REAL_KINDS = {"real_upload", "mutual_aid_hub"}
DEMO_KIND = "demo_synthetic"
DEMO_NOTE = "演示用模拟数据（程序生成），不是调查数据，不得用于参赛"
# 开放题乱填：只认明显的乱敲。曾把“无”“没有”这类正常回答也算乱填并送去待复核，整份答卷因此不进分析
JUNK = [r"^(.)\1{2,}$", r"^(啊+|嗯+|哈+|111+|aaa+|asd.*|qwe.*|123+|[\W_]+)$"]
STATUS_ORDER = {"screened_out": 0, "invalid": 1, "review": 2, "valid": 3}
STATUS_LABEL = {"screened_out": "非调查对象", "invalid": "无效", "review": "待复核", "valid": "有效"}
DECISIONS = {"keep": {"有效", "保留", "keep", "valid"}, "drop": {"无效", "剔除", "drop", "invalid"}}


class Refused(RuntimeError):
    pass


def thresholds(q: dict) -> tuple[dict, list[str]]:
    """问卷设的质控阈值（quality.thresholds；直接写在 quality 下的由 survey_schema.normalize 补进来），
    缺的用默认值；不是数字或超出合理范围的不采用，返回 (阈值, 没采用的说明)。"""
    raw = q.get("quality") if isinstance(q.get("quality"), dict) else {}
    given = dict(raw.get("thresholds") or {}) if isinstance(raw.get("thresholds"), dict) else {}
    for key in DEFAULTS:
        if key not in given and key in raw:
            given[key] = raw[key]
    out, ignored = dict(DEFAULTS), []
    for key, value in given.items():
        if key not in DEFAULTS:
            continue
        lo, hi = LIMITS[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not lo <= value <= hi:
            ignored.append(f"{key}={value!r}（不在 {lo}–{hi} 之间，按默认值 {DEFAULTS[key]:g}）")
            continue
        out[key] = int(value) if key == "straightline_min_items" else value
    return out, ignored


def _is_missing(value) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return isinstance(value, str) and not value.strip()


def _num(value):
    if _is_missing(value):
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return int(f) if f.is_integer() else f


def response_view(q: dict, row: dict) -> dict:
    """把一行数据还原成跳转表达式能用的作答：多选 → 编码集合。"""
    view = {}
    for item in S.questions(q):
        qid, qtype = item.get("id"), item.get("type")
        if qtype == "multi":
            chosen = {c for c in S.option_codes(item) if _num(row.get(f"{qid}_{c}")) == 1}
            answered = any(not _is_missing(row.get(f"{qid}_{c}")) for c in S.option_codes(item))
            view[qid] = chosen if answered else None
        elif qtype in S.MATRIX_TYPES:
            for r in item.get("rows") or []:
                view[r.get("id")] = _num(row.get(r.get("id")))
        elif qtype in {"text"}:
            view[qid] = None if _is_missing(row.get(qid)) else row.get(qid)
        elif qtype != "paragraph":
            view[qid] = _num(row.get(qid))
    return view


def _question_vars(item: dict) -> list[str]:
    qid, qtype = item.get("id"), item.get("type")
    if qtype in {"multi", "rank"}:
        return [f"{qid}_{c}" for c in S.option_codes(item)]
    if qtype in S.MATRIX_TYPES:
        return [r.get("id") for r in item.get("rows") or []]
    return [qid]


def _answered(item: dict, row: dict) -> bool:
    return any(not _is_missing(row.get(v)) for v in _question_vars(item))


def straightline_blocks(q: dict, min_items: int) -> list[dict]:
    blocks = []
    for item in S.questions(q):
        if item.get("type") == "matrix_scale" and len(item.get("rows") or []) >= min_items:
            rows = item["rows"]
            blocks.append({"name": item["id"], "vars": [r["id"] for r in rows],
                           "reverse": [r["id"] for r in rows if r.get("reverse")]})
    covered = {v for b in blocks for v in b["vars"]}
    by_construct: dict[str, list[dict]] = {}
    for var in S.variables(q):
        if var.get("kind") == "scale" and var.get("construct"):
            by_construct.setdefault(var["construct"], []).append(var)
    for name, members in by_construct.items():
        names = [m["name"] for m in members]
        if len(names) >= min_items and not set(names) <= covered:
            blocks.append({"name": f"潜变量:{name}", "vars": names, "reverse": [m["name"] for m in members if m.get("reverse")]})
    return blocks


def clean_rows(q: dict, rows: list[dict], quality: dict) -> tuple[list[dict], dict]:
    q = S.normalize(q)
    items = [i for i in S.questions(q) if S.answerable(i)]
    variables = {v["name"]: v for v in S.variables(q)}
    notes = Counter()
    # 越界取值、跳转外作答：置空。显示条件按题目顺序、只认前面还显示着的题（survey_schema.shown_view）：
    # 前面的题判为跳转外置空后，它的旧答案不再让后面的题算作显示（曾留下“没听说过”却填了每月付多少钱）
    for row in rows:
        shown, kept_view = S.shown_view(q, response_view(q, row))
        for item in items:
            legal = S.valid_values(item)
            vars_ = _question_vars(item)
            others = [f"{item['id']}_{o.get('code')}_text" for o in item.get("options") or [] if isinstance(o, dict) and o.get("other")]
            if item.get("id") not in shown:
                if any(not _is_missing(row.get(v)) for v in vars_ + others):
                    notes["跳转外作答已置空"] += 1
                    for v in vars_ + others:
                        if v in row:
                            row[v] = None
                continue
            if item.get("type") in {"single", "multi"}:      # 改选别的项以后留下的“其他”说明
                for opt in item.get("options") or []:
                    key = f"{item['id']}_{opt.get('code')}_text" if isinstance(opt, dict) and opt.get("other") else None
                    if key and not _is_missing(row.get(key)) and not S.other_chosen(item, kept_view, opt.get("code")):
                        notes["没选“其他”却写了说明，已置空"] += 1
                        row[key] = None
            if legal is not None:
                for v in vars_:
                    val = _num(row.get(v))
                    if val is not None and val not in legal:
                        notes[f"{v} 越界取值已置空"] += 1
                        row[v] = None
    durations = [r.get("_duration_s") for r in rows if _num(r.get("_duration_s")) is not None]
    screened_flags = []
    for row in rows:
        view = response_view(q, row)
        screened = any(i.get("terminate_if") and _safe_eval(i["terminate_if"], view) for i in items)
        screened_flags.append(screened)
    eligible_durations = [float(r["_duration_s"]) for r, s in zip(rows, screened_flags) if not s and _num(r.get("_duration_s")) is not None]
    median = statistics.median(eligible_durations) if eligible_durations else None    # 只统计，不按用时判无效
    blocks = straightline_blocks(q, quality["straightline_min_items"])
    attention = [i for i in items if i.get("attention_check")]
    checks = [c for c in (q.get("quality") or {}).get("consistency_checks") or [] if isinstance(c, dict) and c.get("invalid_if")]
    core_items = [i for i in items if i.get("rq")]
    seen_vectors: dict[tuple, int] = {}
    seen_ids: dict[tuple, int] = {}     # (来源文件, 平台答卷编号)
    answer_vars = [n for n, v in variables.items() if v.get("kind") != "text"]
    for row, screened in zip(rows, screened_flags):
        reasons, review, marks = [], [], []      # marks：只标记、不影响判定
        view = response_view(q, row)
        if screened:
            row["_status"], row["_reasons"] = "screened_out", "甄别：不属于调查对象"
            continue
        hub_status = str(row.get("_quality") or "").strip()
        if hub_status == "held":
            review.append(HUB_HELD)
        pid = row.get("_platform_id")
        if not _is_missing(pid):
            key = (str(row.get("_file") or ""), str(pid))
            if key in seen_ids:
                reasons.append(f"重复提交：答卷编号重复（与第 {seen_ids[key]} 行）")
            else:
                seen_ids[key] = row["_rid"]
        vector = tuple("" if _is_missing(row.get(v)) else str(_num(row.get(v))) for v in answer_vars)
        if sum(1 for x in vector if x) >= max(1, len(vector) // 2):
            if vector in seen_vectors:
                reasons.append(f"重复提交：作答完全相同（与第 {seen_vectors[vector]} 行）")
            else:
                seen_vectors[vector] = row["_rid"]
        straight = []
        for block in blocks:
            vals = [_num(row.get(v)) for v in block["vars"]]
            vals = [v for v in vals if v is not None]
            if len(vals) >= quality["straightline_min_items"] and len(set(vals)) == 1:
                # 含反向题的整列同选一律无效，选中间那一档也一样（和问卷互助中心同一口径，2026-10-15）
                straight.append((block["name"], bool(block["reverse"])))
        if any(c for _, c in straight) or len(straight) >= 2:
            reasons.append("整列同选：" + "、".join(n for n, _ in straight) + ("（含反向题，各行却选了同一项）" if any(c for _, c in straight) else ""))
        elif straight:
            marks.append(f"整列同选：{straight[0][0]}（仅标记）")
            notes["整列同选只有一处（仅标记）"] += 1
        for item in attention:
            expected = item.get("attention_expected")
            if expected is not None and S.is_shown(item, view):
                if _num(row.get(item["id"])) != expected:
                    reasons.append(f"注意力题 {item['id']} 答错")
        for check in checks:
            if _safe_eval(check["invalid_if"], view):
                reasons.append(f"逻辑矛盾：{check.get('message') or check.get('id')}")
        shown_core = [i for i in core_items if S.is_shown(i, view) and i.get("required", True)]
        if shown_core:
            missing = sum(1 for i in shown_core if not _answered(i, row))
            if missing / len(shown_core) > quality["core_missing_max"]:
                reasons.append(f"核心题缺失 {missing}/{len(shown_core)}")
        for item in items:
            if item.get("type") == "text" and S.is_shown(item, view):
                text = str(row.get(item["id"]) or "").strip()
                if text and any(re.fullmatch(p, text, re.I) for p in JUNK):
                    marks.append(f"开放题 {item['id']} 疑似乱填（仅标记）")
                    notes["开放题疑似乱填（仅标记）"] += 1
        # 互助中心判无效看的是注意力题和整列同选：清洗自己也查出同类原因时只记具体原因。曾两样都记，
        # 同一批 49 份在原因统计里成了“互助中心质检判为无效 49、注意力题答错 49”，清洗流程图看着像剔了 98 份
        if hub_status == "invalid" and not any(r.startswith(("注意力题", "整列同选")) for r in reasons):
            reasons.insert(0, HUB_INVALID)
        if reasons:
            row["_status"], row["_reasons"] = "invalid", "；".join(reasons + review + marks)
            row["_why"] = reasons            # 判无效的原因（不含同一份答卷上待复核、仅标记的提示），供原因统计
        elif review:
            row["_status"], row["_reasons"] = "review", "；".join(review + marks)
        else:
            row["_status"], row["_reasons"] = "valid", "；".join(marks)
    # straightline_single：只有一处整列同选怎么处理，附录的判定规则表按它写（这个字段以前没有，旧项目的附录照旧写“待复核”）
    info = {"median_duration_s": median, "notes": dict(notes),
            "straightline_blocks": [b["name"] for b in blocks], "attention_items": [i["id"] for i in attention],
            "duration_available": bool(durations), "straightline_single": "mark", "straightline_reverse": "any"}
    return rows, info


def apply_review_decisions(rows: list[dict], path: Path) -> dict:
    """团队人工复核的决定：只对本次判为“待复核”的答卷生效，每条都要写理由。
    （说明里曾写“人工确认后可在 flagged.csv 中改为有效再重跑”，可重跑并不读它，改了也会被覆盖。）"""
    info = {"file": path.as_posix(), "kept_n": 0, "dropped_n": 0, "ignored": []}
    if not path.is_file():
        return info
    import csv
    with path.open(encoding="utf-8-sig", newline="") as fh:
        records = list(csv.DictReader(fh))
    by_rid = {r["_rid"]: r for r in rows}
    for line, rec in enumerate(records, start=2):
        word = str(rec.get("决定") or rec.get("decision") or "").strip()
        why = str(rec.get("理由") or rec.get("reason") or "").strip()
        decision = next((k for k, words in DECISIONS.items() if word.lower() in words), None)
        row = by_rid.get(_num(rec.get("_rid")))
        problem = ("找不到这份答卷" if row is None else
                   "不是待复核的答卷（判了无效的不能改回有效）" if row["_status"] != "review" else
                   f"决定只能写“有效”或“无效”（现在是“{word}”）" if decision is None else
                   "没写理由" if not why else None)
        if problem:
            info["ignored"].append(f"第 {line} 行（_rid={rec.get('_rid')}）：{problem}")
            continue
        row["_status"] = "valid" if decision == "keep" else "invalid"
        row["_review"] = decision
        row["_reasons"] = "；".join(x for x in (row["_reasons"], f"人工复核：{'确认有效' if decision == 'keep' else '剔除'}（{why}）") if x)
        info["kept_n" if decision == "keep" else "dropped_n"] += 1
    return info


def reason_key(part: str) -> str:
    """无效原因归类：去掉行内细节（用时数字、与第几行重复、核心题缺失比例），整列同选不分是哪几道矩阵题。
    只去掉结尾的括号：原因本身带括号的（如“高职（专科）院校却选了研究生”）曾被截成“高职”；
    整列同选曾按矩阵组合拆成好几种，清洗流程图的前五个原因里出现好几个“整列同选”。"""
    part = re.sub(r"\s*[（(][^（()）]*[)）]\s*$", "", str(part).strip())
    part = re.sub(r"\s*\d+/\d+$", "", part)
    return "整列同选" if part.startswith("整列同选") else part


def _safe_eval(expr: str, view: dict) -> bool:
    try:
        return S.evaluate(S.parse_logic(expr), view)
    except S.LogicError:
        return False


def rake(rows: list[dict], margins: dict, max_iter: int = 50, trim=(0.3, 3.0)) -> dict:
    weights = [1.0] * len(rows)
    for _ in range(max_iter):
        delta = 0.0
        for var, target in margins.items():
            total = sum(weights)
            for code, share in target.items():
                idx = [i for i, r in enumerate(rows) if str(_num(r.get(var))) == str(code)]
                cur = sum(weights[i] for i in idx)
                if cur <= 0:
                    continue
                factor = (float(share) * total) / cur
                delta = max(delta, abs(factor - 1))
                for i in idx:
                    weights[i] *= factor
        weights = [min(max(w, trim[0]), trim[1]) for w in weights]
        if delta < 1e-4:
            break
    mean = sum(weights) / len(weights) if weights else 1
    weights = [w / mean for w in weights]
    deff = len(weights) * sum(w * w for w in weights) / (sum(weights) ** 2) if weights else 1
    for r, w in zip(rows, weights):
        r["_weight"] = round(w, 6)
    return {"variables": list(margins), "kish_deff": round(deff, 3), "effective_n": round(len(weights) / deff, 1) if deff else None,
            "trim": list(trim)}


def structure(q: dict, valid: list[dict]) -> dict:
    out = {}
    quotas = {qu.get("question"): qu.get("targets") or {} for qu in q.get("quotas") or [] if isinstance(qu, dict)}
    for item in S.questions(q):
        if item.get("type") != "single" or not (item.get("role") in {"demographic", "screening"} or item.get("id") in quotas):
            continue
        counts = Counter(_num(r.get(item["id"])) for r in valid)
        total = sum(v for k, v in counts.items() if k is not None)
        dist = {}
        for opt in item.get("options") or []:
            n = counts.get(opt.get("code"), 0)
            share = n / total if total else 0
            entry = {"label": opt.get("label"), "n": n, "pct": round(share * 100, 1)}
            target = quotas.get(item["id"], {}).get(str(opt.get("code")))
            if target is not None:
                entry["target_pct"] = round(float(target) * 100, 1)
                entry["deviation_pp"] = round(share * 100 - float(target) * 100, 1)
            dist[str(opt.get("code"))] = entry
        out[item["id"]] = {"question": item.get("text"), "valid_n": total, "distribution": dist}
    return out


def main(argv=None) -> int:
    import pandas as pd
    ap = argparse.ArgumentParser(description="答卷质量清洗")
    ap.add_argument("questionnaire")
    ap.add_argument("--data", default="data/raw_import.csv")
    ap.add_argument("--provenance", default="data/PROVENANCE.json")
    ap.add_argument("--margins")
    ap.add_argument("--outdir", default="data")
    ap.add_argument("--quality-out", default="DATA_QUALITY.json")
    ap.add_argument("--fieldwork-out", default="FIELDWORK_LOG.json")
    ap.add_argument("--review-decisions", default="data/review_decisions.csv", help="团队人工复核待复核答卷的决定")
    ap.add_argument("--demo", action="store_true", help="只用于演示用模拟数据（数据来源 demo_synthetic）")
    args = ap.parse_args(argv)
    try:
        q = S.load_questionnaire(args.questionnaire)
        prov = S.load_json(args.provenance)
    except S.SchemaError as exc:
        print(f"❌ {exc}")
        return 2
    kind = prov.get("kind")
    if args.demo and kind != DEMO_KIND:
        print(f"❌ --demo 只用于演示用模拟数据（数据来源 demo_synthetic），当前是 {kind!r}")
        return 1
    if not args.demo and kind not in REAL_KINDS:
        print(f"❌ 拒收：数据来源是 {kind!r}，只有真实回收的数据（real_upload/mutual_aid_hub）才能清洗分析"
              + ("；演示用模拟数据要加 --demo" if kind == DEMO_KIND else ""))
        return 1
    data_path = Path(args.data)
    if not data_path.is_file():
        print(f"❌ 找不到 {data_path}")
        return 2
    frame = pd.read_csv(data_path, encoding="utf-8-sig", dtype=object, keep_default_na=False)
    if "__synthetic__" in frame.columns and not args.demo:
        print("❌ 拒收：数据带 __synthetic__ 列（模拟数据）")
        return 1
    rows = [{k: (None if v == "" else v) for k, v in rec.items()} for rec in frame.to_dict(orient="records")]
    for r in rows:
        r["_rid"] = int(float(r["_rid"]))
    quality, ignored = thresholds(q)
    rows, info = clean_rows(q, rows, quality)
    if ignored:
        info["thresholds_ignored"] = ignored
    review = apply_review_decisions(rows, Path(args.review_decisions))
    valid = [r for r in rows if r["_status"] == "valid"]
    weighting = None
    if args.margins and Path(args.margins).is_file() and valid:
        weighting = rake(valid, S.load_json(args.margins))
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    cols = list(frame.columns) + (["_weight"] if weighting else [])
    pd.DataFrame(valid, columns=cols).to_csv(outdir / "clean.csv", index=False, encoding="utf-8-sig")
    flagged_cols = ["_rid", "_platform_id", "_status", "_reasons", "_duration_s"]
    flagged = [{c: r.get(c) for c in flagged_cols} | {"_status": STATUS_LABEL[r["_status"]]} for r in rows]
    pd.DataFrame(flagged, columns=flagged_cols).to_csv(outdir / "flagged.csv", index=False, encoding="utf-8-sig")
    status = Counter(r["_status"] for r in rows)
    reason_counts = Counter()
    for r in rows:
        if r["_status"] == "invalid" and r.get("_review") != "drop":     # 人工复核剔除的单独计数
            for part in r.get("_why") or str(r["_reasons"]).split("；"):
                reason_counts[reason_key(part)] += 1
    eligible = len(rows) - status["screened_out"]
    result = {
        "schema": "paperkit.survey.data_quality/v1",
        "provenance": {"kind": prov.get("kind"), "files": prov.get("files"), "collection_period": prov.get("collection_period")},
        "thresholds": quality,
        "counts": {"raw_n": len(rows), "screened_out_n": status["screened_out"], "eligible_n": eligible,
                   "invalid_n": status["invalid"], "review_n": status["review"], "valid_n": status["valid"],
                   "review_kept_n": review["kept_n"], "review_dropped_n": review["dropped_n"],
                   # 按规则判定无效的份数（不含人工复核后剔除的）：报告和清洗流程图要单独写这个数，曾只能现算
                   "rule_invalid_n": status["invalid"] - review["dropped_n"],
                   "valid_rate_pct": round(status["valid"] / eligible * 100, 1) if eligible else None,
                   "valid_of_raw_pct": round(status["valid"] / len(rows) * 100, 1) if rows else None},
        "invalid_reasons": dict(reason_counts),
        "rules": info,
        "sample_structure": structure(S.normalize(q), valid),
        "weighting": weighting,
        "review_policy": ("待复核的答卷不进入分析；团队逐份人工复核后，把决定写进 data/review_decisions.csv"
                          "（_rid、决定（有效 / 无效）、理由）再重跑本脚本，只对待复核的答卷生效"),
    }
    if Path(args.review_decisions).is_file():
        result["review_decisions"] = {"file": review["file"], "ignored": review["ignored"]}
    if args.demo:
        result.update({"demo": True, "demo_note": DEMO_NOTE})
    Path(args.quality_out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    # 来源代码换成评委看得懂的渠道名（调查实施记录原样进附录，不能出现内部代码）；后两个是导入时按文件类型补的。
    # 不写软件、平台的名字（2026-10-16 用户：“正文不要提到什么互助中心什么的”），只说明是怎样的渠道
    channel_names = {"hub": "线上问卷广场（受访者在线自愿填写）",
                     "web": "网页链接（团队转发，手机浏览器 / 微信填写）",
                     "platform_export": "在线问卷平台（问卷星、腾讯问卷等）",
                     "team_entry": "团队录入的答卷（纸质问卷、线下拦截等）",
                     "simulated": "程序按问卷生成的模拟答卷（练习用，不是真实调查）"}
    sources = Counter(channel_names.get(r.get("_source") or "", r.get("_source") or "未记录") for r in rows)
    regions = Counter((r.get("_region") or "未记录") for r in rows)
    fieldwork = {"schema": "paperkit.survey.fieldwork/v1",
                 "collection_period": prov.get("collection_period"), "files": prov.get("files"),
                 "kind": prov.get("kind"), "channels": dict(sources.most_common()),
                 "regions_top10": dict(regions.most_common(10)), "raw_n": len(rows)}
    if args.demo:
        fieldwork.update({"demo": True, "demo_note": DEMO_NOTE})
    Path(args.fieldwork_out).write_text(json.dumps(fieldwork, ensure_ascii=False, indent=2), encoding="utf-8")
    c = result["counts"]
    print(f"✅ 回收 {c['raw_n']} 份：非调查对象 {c['screened_out_n']}，无效 {c['invalid_n']}，待复核 {c['review_n']}，"
          f"有效 {c['valid_n']}（有效率 {c['valid_rate_pct']}%，有效回收率 {c['valid_of_raw_pct']}%）")
    if review["kept_n"] or review["dropped_n"]:
        print(f"   人工复核：确认有效 {review['kept_n']}，剔除 {review['dropped_n']}（{review['file']}）")
    for msg in review["ignored"]:
        print(f"⚠️ 复核决定未采用：{msg}")
    for msg in ignored:
        print(f"⚠️ 问卷设的质控阈值没采用：{msg}")
    for k, v in reason_counts.most_common():
        print(f"   无效原因：{k} × {v}")
    if info["median_duration_s"] is not None:
        print(f"   中位作答用时 {info['median_duration_s']:.0f} 秒（只统计，不按用时判无效）")
    if weighting:
        print(f"   已加权：Kish 设计效应 {weighting['kish_deff']}，有效样本量约 {weighting['effective_n']}")
    if not c["valid_n"]:
        print("❌ 有效样本为 0，无法分析")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
