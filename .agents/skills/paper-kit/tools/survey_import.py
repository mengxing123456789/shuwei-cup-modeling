#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把回收的答卷数据导入成按变量编码表排好的整洁表，并记录数据来源。

支持：问卷星（按序号/按选项文字下载的 Excel/CSV）、腾讯问卷、问卷网、问卷互助中心导出、
按变量名命名列的通用表；格式 CSV（UTF-8/GBK）、XLSX、XLS（需要 xlrd）、SPSS SAV（需要 pyreadstat）。

做的事：
  1. 识别元数据列（序号、提交时间、所用时间、来源、IP）；所用时间换算成秒，IP 只保留括号里的地区；
     没有来源列的按文件类型记渠道（问卷平台导出 / 团队录入的纸质问卷等）；互助中心表里防公式加的 ' 去掉；
  2. 按"题号 → 题干相似度 → 变量名"把每一列对应到 CODEBOOK 变量，多选题/矩阵题按括号里的选项或行拆列；
  3. 选项既可以是编码也可以是选项文字；"(跳过)"、-2、-3 记为缺失；"其他〖…〗"拆出文字；
  4. 姓名/手机号等个人信息列移到 data/private/（不进分析表、不进报告）；
  5. 同一份答卷出现在两个文件里（重复下载：答卷编号、提交时间、作答都相同）只留第一次，记进 PROVENANCE.json；
  6. 写 data/raw_import.csv、data/import_mapping.json、data/PROVENANCE.json。
SPSS 数据的列按变量标签对应题号（标签带“5、……”这种题号时），问卷星的变量名 Q1、Q2 按印出来的题号编，和内部题号不一定一致。
拒收：带 __synthetic__ 列或来自 rehearsal/ 的文件（模拟数据不能当真实数据导入）。
演示模式：--kind demo_synthetic 只收带 __synthetic__ 列的模拟数据（生成演示作品用），来源如实记为模拟；
下游清洗、统计要加 --demo，导出的报告每页标注"演示样例 · 数据为程序模拟生成"，合规检查判为不得提交。

用法：
  python _utils/survey_import.py QUESTIONNAIRE.json 数据文件 [数据文件 ...] [--kind real_upload|mutual_aid_hub|demo_synthetic] [--outdir data]
退出码：0 成功；1 有需要人工确认的映射问题（结果照样写出）或拒收；2 输入缺失/读不了。
"""
from __future__ import annotations

import argparse
import datetime as dt
import difflib
import hashlib
import json
import math
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
import survey_render as R  # noqa: E402
import survey_schema as S  # noqa: E402

IMPORTER_VERSION = "survey_import/1"
DEMO_KIND = "demo_synthetic"
DEMO_NOTE = "演示用模拟数据（程序生成），不是调查数据，不得用于参赛"
MISSING_TOKENS = {"", "(跳过)", "（跳过）", "跳过", "(空)", "（空）", "-2", "-3", "nan", "NaN", "None", "null", "NA", "N/A"}
META_PATTERNS = [
    ("_platform_id", r"^(序号|编号|答卷编号|答卷序号|答题序号|ID|id|用户ID|答卷ID|_hub_response_id)$"),
    ("_submitted_at", r"(提交答卷时间|提交时间|结束答题时间|结束时间|答题结束时间|_submitted_at)"),
    ("_started_at", r"(开始答题时间|开始时间|答题开始时间|_started_at)"),
    ("_duration", r"(所用时间|答题时长|作答时长|用时|耗时|_duration_s)"),
    ("_source", r"^(来源|来源渠道|渠道|_source)$"),
    ("_ip", r"(来自IP|IP地址|^IP$|^ip$|填写IP)"),
    ("_quality", r"^(_quality_status)$"),
]
DROP_PATTERNS = r"^(总分|微信昵称|昵称|用户名|填写设备|操作系统|浏览器|来源详情|_respondent_verified|_questionnaire_version)$"
PII_HEADER = r"(姓名|名字|手机|电话|身份证|微信号|QQ|邮箱|电子邮件|家庭住址|详细地址|学号|工号)"
MULTI_SPLIT = r"[┋|;；,，、]"
# 互助中心导回的表（data/raw/hub_*.csv）里，以 = + - @ 开头的文字（本来就以 ' 加这些字符开头的也算）前面加了一个 '
# 防表格公式；导入时去掉这一个 ' 就是原文。曾原样带进分析数据，报告引用开放题原话多出一个 '
HUB_FORMULA_GUARD = re.compile(r"'+[=+\-@\t\r]")
# 没有来源列的文件按文件类型记渠道（survey_clean 换成中文渠道名）；曾记成“未记录”，调查实施记录里写出“未记录 4 份”
PLATFORM_CHANNEL, ENTRY_CHANNEL = "platform_export", "team_entry"


class ImportRefused(RuntimeError):
    pass


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_table(path: Path):
    import pandas as pd
    suffix = path.suffix.lower()
    if suffix == ".csv":
        last = None
        for enc in ("utf-8-sig", "gb18030"):
            try:
                return pd.read_csv(path, dtype=str, keep_default_na=False, encoding=enc)
            except UnicodeDecodeError as exc:
                last = exc
        raise RuntimeError(f"{path.name} 编码无法识别（试过 UTF-8、GBK）：{last}")
    if suffix in {".xlsx", ".xlsm"}:
        return pd.read_excel(path, dtype=str, keep_default_na=False, sheet_name=0, engine="openpyxl")
    if suffix == ".xls":
        try:
            import xlrd  # noqa: F401
        except ImportError as exc:
            raise RuntimeError("读取 .xls 需要 xlrd；请在 Excel 里另存为 .xlsx 后再上传") from exc
        return pd.read_excel(path, dtype=str, keep_default_na=False, sheet_name=0)
    if suffix == ".sav":
        try:
            import pyreadstat
        except ImportError as exc:
            raise RuntimeError("读取 SPSS .sav 需要 pyreadstat（客户端运行环境已内置；本机测试环境可能没有）") from exc
        frame, meta = pyreadstat.read_sav(str(path))
        frame = frame.astype(object).where(frame.notna(), "").astype(str)
        frame.attrs["column_labels"] = list(meta.column_labels or [])   # 题目标签：run_import 据此对应题号
        return frame
    raise RuntimeError(f"不支持的文件类型：{path.name}（支持 csv/xlsx/xls/sav）")


def _norm(text: str) -> str:
    text = str(text).strip()
    text = text.translate(str.maketrans("（）：，【】", "():,[]"))
    return re.sub(r"\s+", "", text)


def _strip_number(header: str) -> tuple[int | None, str]:
    m = re.match(r"^(?:Q|q|第)?(\d{1,3})(?:题)?\s*[、.．:：)\]]\s*(.*)$", header)
    if m:
        return int(m.group(1)), m.group(2)
    m = re.match(r"^(\d{1,3})\((.*)\)$", header)
    if m:
        return int(m.group(1)), f"({m.group(2)})"
    return None, header


def _paren_tail(text: str) -> str | None:
    # 问卷星“题号(选项或行)”：括号里的文字自己也可能带括号，如“14(健康监测（血压、血糖等）)”“8(其他（请注明）)”。
    # 曾只取最里层括号：矩阵行整列对不上，“其他”列被当成整题拆码，选了“其他”的人被记成选了第 1 项
    m = re.match(r"^\s*(?:Q|q|第)?\d{1,3}(?:题)?\s*[\(（](.*)[\)）]\s*$", text)
    if m and m.group(1).strip():
        return m.group(1).strip()
    m = re.search(r"[\(（]([^()（）]*)[\)）]\s*$", text)
    if m:
        return m.group(1).strip()
    m = re.search(r"[—\-_]{1,2}([^—\-_]+)$", text)
    return m.group(1).strip() if m else None


def _similar(a: str, b: str) -> float:
    a, b = _norm(a), _norm(b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if a in b or b in a:
        return 0.95 if min(len(a), len(b)) >= 4 else 0.7
    return difflib.SequenceMatcher(None, a, b).ratio()


def _best_option(item: dict, label: str) -> tuple[int | None, float]:
    best, score = None, 0.0
    target = re.sub(r"^[A-Za-z][.．、]\s*", "", label)
    for opt in item.get("options") or []:
        s = _similar(target, str(opt.get("label", "")))
        if s > score:
            best, score = opt.get("code"), s
    return best, score


def _best_row(item: dict, label: str) -> tuple[str | None, float]:
    best, score = None, 0.0
    target = re.sub(r"^[A-Za-z][.．、]\s*", "", label)
    for row in item.get("rows") or []:
        s = _similar(target, str(row.get("label", "")))
        if s > score:
            best, score = row.get("id"), s
    return best, score


def map_columns(q: dict, headers: list[str], allow_synthetic: bool = False) -> dict:
    """返回 {"columns": {原列名: 映射}, "meta": {原列名: 标准名}, "pii": [...], "dropped": [...], "unmapped": [...]}"""
    q = S.normalize(q)
    items = [i for i in S.questions(q) if S.answerable(i)]
    by_num = {}
    nums = R.display_numbers(q)
    for item in items:
        by_num[nums[item["id"]]] = item
    var_question = {v["name"]: v["question"] for v in S.variables(q)}
    var_names = set(var_question)
    result = {"columns": {}, "meta": {}, "pii": [], "dropped": [], "unmapped": []}
    for header in headers:
        h = str(header).strip()
        if h == "__synthetic__":
            if not allow_synthetic:
                raise ImportRefused("数据里有 __synthetic__ 列：这是模拟数据，不能当作真实调查数据导入")
            result["dropped"].append(h)  # 演示模式：模拟标记已记入数据来源，不进分析表
            continue
        meta = next((name for name, pat in META_PATTERNS if re.search(pat, h)), None)
        if meta:
            result["meta"][h] = meta
            continue
        if re.search(DROP_PATTERNS, h):
            result["dropped"].append(h)
            continue
        if h in var_names:
            result["columns"][h] = {"target": h, "question": var_question[h], "method": "name", "confidence": 1.0}
            continue
        num, rest = _strip_number(_norm(h))
        candidates = []
        if num is not None and num in by_num:
            item = by_num[num]
            title_sim = _similar(rest.split("(")[0], item.get("text", "")) if rest and not rest.startswith("(") else 1.0
            candidates.append((item, 0.6 + 0.4 * title_sim, "number"))
        if not candidates or candidates[0][1] < 0.75:
            base = re.sub(r"[\(（][^()（）]*[\)）]$", "", rest or h)
            for item in items:
                sim = _similar(base, item.get("text", ""))
                if sim >= 0.6:
                    candidates.append((item, sim, "title"))
        if not candidates:
            if re.search(PII_HEADER, h):
                result["pii"].append(h)
            else:
                result["unmapped"].append(h)
            continue
        item, conf, method = max(candidates, key=lambda c: c[1])
        qtype = item.get("type")
        tail = _paren_tail(h)
        mapping = {"question": item["id"], "method": method, "confidence": round(min(conf, 1.0), 2)}
        if qtype == "multi":
            if tail:
                code, sc = _best_option(item, tail)
                if code is not None and sc >= 0.6:
                    mapping.update(target=f"{item['id']}_{code}", layout="multi_binary", confidence=round(min(conf, sc), 2))
                else:
                    mapping.update(target=None, note=f"多选列“{h}”括号里的选项认不出")
            else:
                mapping.update(target=item["id"], layout="multi_joined")
        elif qtype in S.MATRIX_TYPES:
            if tail:
                rid, sc = _best_row(item, tail)
                if rid and sc >= 0.6:
                    mapping.update(target=rid, layout="matrix_row", confidence=round(min(conf, sc), 2))
                else:
                    mapping.update(target=None, note=f"矩阵列“{h}”括号里的行认不出")
            else:
                mapping.update(target=None, note=f"矩阵题“{h}”没有标明是哪一行")
        elif qtype == "rank":
            code, sc = _best_option(item, tail or "")
            mapping.update(target=f"{item['id']}_{code}" if code is not None and sc >= 0.6 else None, layout="rank")
        else:
            if item.get("type") in {"text", "number"} and re.search(L_PII, item.get("text", "")):
                result["pii"].append(h)
                continue
            mapping.update(target=item["id"], layout="single")
        if mapping.get("target") is None:
            result["unmapped"].append(h)
        result["columns"][h] = mapping
    return result


L_PII = r"(?:姓名|名字|手机号?|电话|身份证|学号|工号|家庭住址|详细地址|住址|邮箱|电子邮件|微信号|QQ号|银行卡)"


def parse_duration(value: str) -> float | None:
    v = str(value).strip()
    if not v or v in MISSING_TOKENS:
        return None
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(?:秒|s|S)?", v)
    if m:
        return float(m.group(1))
    m = re.fullmatch(r"(?:(\d+)\s*小时)?\s*(?:(\d+)\s*分(?:钟)?)?\s*(?:(\d+)\s*秒)?", v)
    if m and any(m.groups()):
        h, mi, s = (int(x) if x else 0 for x in m.groups())
        return float(h * 3600 + mi * 60 + s)
    m = re.fullmatch(r"(\d+):(\d{1,2}):(\d{1,2})", v)
    if m:
        h, mi, s = (int(x) for x in m.groups())
        return float(h * 3600 + mi * 60 + s)
    m = re.fullmatch(r"(\d+):(\d{1,2})", v)
    if m:
        return float(int(m.group(1)) * 60 + int(m.group(2)))
    return None


def parse_time(value: str) -> str | None:
    v = str(value).strip()
    if not v or v in MISSING_TOKENS:
        return None
    for fmt in ("%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return dt.datetime.strptime(v[:19], fmt).isoformat(timespec="seconds")
        except ValueError:
            continue
    return v


def region_from_ip(value: str) -> str | None:
    m = re.search(r"[\(（]([^()（）]+)[\)）]", str(value))
    return m.group(1).strip() if m else None


def decode_code(item: dict, raw: str):
    v = str(raw).strip()
    if v in MISSING_TOKENS:
        return None, None
    other_text = None
    m = re.search(r"〖(.*?)〗", v)
    if m:
        other_text = m.group(1).strip() or None
        v = v[: m.start()].strip()
    legal = S.valid_values(item) or []
    try:
        num = float(v)
        if num.is_integer() and int(num) in legal:
            return int(num), other_text
    except ValueError:
        pass
    m = re.match(r"^(\d+)\s*[\(（]", v)
    if m and int(m.group(1)) in legal:
        return int(m.group(1)), other_text
    if item.get("type") in S.CHOICE_TYPES:
        code, score = _best_option(item, v)
        if code is not None and score >= 0.85:
            return code, other_text
    if item.get("type") in S.SCALE_TYPES:
        labels = (item.get("scale") or {}).get("labels") or {}
        for key, lab in labels.items():
            if _norm(lab) == _norm(v):
                return int(key), other_text
    return "INVALID", other_text


def decode_position(item: dict, raw: str):
    """问卷星等平台“按选项序号”导出的是第几个选项（1、2、3……），不是选项编码。编码不是按顺序的 1..n 时
    （团队在编辑器里删过中间的选项、AI 用 9 表示“不清楚”），按第几个选项对应；曾按编码对应，整列错位且不报错
    （删掉“大一(1)”、加“研究生(4)”后，序号 1/2/3 被导成“无效/大二/大三及以上”）。数字以外的写法（选项文字）照旧。"""
    v = str(raw).strip()
    if v in MISSING_TOKENS:
        return None, None
    other_text = None
    m = re.search(r"〖(.*?)〗", v)
    if m:
        other_text = m.group(1).strip() or None
        v = v[: m.start()].strip()
    opts = [o for o in item.get("options") or [] if isinstance(o, dict)]
    try:
        num = float(v)
    except ValueError:
        num = None
    if num is not None and num.is_integer() and 1 <= int(num) <= len(opts):
        return opts[int(num) - 1].get("code"), other_text
    return decode_code(item, raw)


def _platform_export(mapping: dict) -> bool:
    """问卷星、腾讯问卷等平台的导出表：有平台写的提交时间、所用时间或 IP 列（互助中心的列名带下划线，不算）。"""
    return any(std in {"_submitted_at", "_duration", "_ip"} and not str(h).startswith("_")
               for h, std in mapping["meta"].items())


def _unguard(value):
    return value[1:] if isinstance(value, str) and HUB_FORMULA_GUARD.match(value) else value


def import_frames(q: dict, frames: list, kind: str) -> tuple[list[dict], dict]:
    q = S.normalize(q)
    variables = S.variables(q)
    var_names = [v["name"] for v in variables]
    owners = {}
    for item in S.questions(q):
        owners[item.get("id")] = item
        for row in item.get("rows") or []:
            if isinstance(row, dict):
                owners[row.get("id")] = {**item, "_row": row.get("id")}
    rows_out: list[dict] = []
    pii_rows: list[dict] = []
    report = {"files": [], "invalid_values": {}, "mapping": {}}
    rid = 0
    for name, frame in frames:
        headers = [str(c) for c in frame.columns]
        mapping = map_columns(q, headers, allow_synthetic=kind == DEMO_KIND)
        report["mapping"][name] = mapping
        platform = _platform_export(mapping)
        hub = "_hub_response_id" in headers
        # 互助中心的表自带来源（软件里 / 网页链接）；问卷平台导出没有“来源”列的、纸质问卷按录入模板录的表，按文件类型记渠道
        channel = "hub" if hub else PLATFORM_CHANNEL if platform else ENTRY_CHANNEL
        records = frame.to_dict(orient="records")
        if hub:
            records = [{k: _unguard(v) for k, v in rec.items()} for rec in records]
        for rec in records:
            rid += 1
            row = {"_rid": rid, "_file": name}
            for h, meta in mapping["meta"].items():
                value = rec.get(h, "")
                if meta == "_duration":
                    row["_duration_s"] = parse_duration(value)
                elif meta in {"_submitted_at", "_started_at"}:
                    row[meta] = parse_time(value)
                elif meta == "_ip":
                    row["_region"] = region_from_ip(value)
                elif meta == "_platform_id":
                    row["_platform_id"] = str(value).strip() or None
                else:
                    row[meta] = str(value).strip() or None
            if not row.get("_source") and kind != DEMO_KIND:
                row["_source"] = channel
            if row.get("_duration_s") is None and row.get("_started_at") and row.get("_submitted_at"):
                try:
                    row["_duration_s"] = (dt.datetime.fromisoformat(row["_submitted_at"]) - dt.datetime.fromisoformat(row["_started_at"])).total_seconds()
                except ValueError:
                    pass
            for var in var_names:
                row.setdefault(var, None)
            for h, m in mapping["columns"].items():
                target = m.get("target")
                if not target:
                    continue
                raw = rec.get(h, "")
                owner = owners.get(m.get("question"))
                layout = m.get("layout", "single")
                # 平台导出、按题号或题干对上的列：数字是第几个选项（变量名对上的列是 系统导出或录入模板，数字就是编码）
                by_position = platform and m.get("method") in {"number", "title"}
                if m.get("method") == "name":
                    owner = owners.get(target) or owners.get(re.sub(r"_\d+(_text)?$", "", target))
                    var = next((v for v in variables if v["name"] == target), {})
                    if var.get("kind") == "binary":
                        layout = "multi_binary"
                    elif var.get("kind") == "text":
                        layout = "text"
                    elif var.get("kind") == "numeric":
                        layout = "number"
                    elif var.get("kind") == "rank":
                        layout = "rank"
                    else:
                        layout = "single"
                if layout == "multi_binary":
                    v = str(raw).strip()
                    if v in MISSING_TOKENS:
                        row[target] = None
                    else:
                        row[target] = 0 if v in {"0", "未选", "否", "FALSE", "False"} else 1
                        other = re.search(r"〖(.*?)〗", v)
                        if other and other.group(1).strip() and f"{target}_text" in var_names:
                            row[f"{target}_text"] = other.group(1).strip()   # “其他（请注明）”的文字
                elif layout == "multi_joined":
                    v = str(raw).strip()
                    if v in MISSING_TOKENS:
                        continue
                    for part in [p for p in re.split(MULTI_SPLIT, v) if p.strip()]:
                        code, other = (decode_position if by_position else decode_code)({**owner, "type": "single"}, part)
                        if code not in (None, "INVALID"):
                            row[f"{owner['id']}_{code}"] = 1
                            if other:
                                row[f"{owner['id']}_{code}_text"] = other
                        elif code == "INVALID":
                            report["invalid_values"].setdefault(h, set()).add(part)
                    for c in S.option_codes(owner):
                        if row.get(f"{owner['id']}_{c}") is None:
                            row[f"{owner['id']}_{c}"] = 0
                elif layout == "rank" or (owner and owner.get("type") == "number") or layout in {"number"}:
                    v = str(raw).strip()
                    num = re.sub(r"[^\d.\-]", "", v)
                    try:
                        row[target] = float(num) if num not in {"", "-", "."} and v not in MISSING_TOKENS else None
                    except ValueError:
                        row[target] = None
                elif (owner and owner.get("type") == "text") or layout == "text":
                    v = str(raw).strip()
                    row[target] = None if v in MISSING_TOKENS else v
                else:
                    item = owner if owner and not owner.get("_row") else owner
                    positional = by_position and item and item.get("type") in {"single", "matrix_single"}
                    code, other = (decode_position if positional else decode_code)(item, raw)
                    if code == "INVALID":
                        report["invalid_values"].setdefault(h, set()).add(str(raw)[:30])
                        row[target] = None
                    else:
                        row[target] = code
                        if other and item:
                            other_opt = next((o for o in item.get("options") or [] if o.get("other")), None)
                            if other_opt:
                                row[f"{item['id']}_{other_opt.get('code')}_text"] = other
            if mapping["pii"]:
                pii_rows.append({"_rid": rid, **{h: rec.get(h, "") for h in mapping["pii"]}})
            row["_source_kind"] = kind
            rows_out.append(row)
    report["invalid_values"] = {k: sorted(v)[:10] for k, v in report["invalid_values"].items()}
    report["pii_rows"] = pii_rows
    return rows_out, report


def drop_cross_file_duplicates(rows: list[dict], var_names: list[str]) -> tuple[list[dict], list[dict]]:
    """同一份答卷在两个文件里各出现一次（先下载 200 份、后来又下载全部 300 份一起上传）只留第一次：平台答卷编号、
    提交时间和全部作答都相同才算。曾把两个文件的行数相加，份数翻倍，清洗又把后一批全判成“重复提交”。
    同一个文件里的重复交给清洗判“重复提交”；没有答卷编号的表不在这里去重（分不清是重复下载还是两个人答得一样）。"""
    seen: dict[tuple, str] = {}
    kept, dropped = [], {}
    for row in rows:
        pid = row.get("_platform_id")
        if pid in (None, ""):
            kept.append(row)
            continue
        key = (str(pid), str(row.get("_submitted_at") or ""),
               tuple("" if row.get(v) is None else str(row.get(v)) for v in var_names))
        first = seen.get(key)
        if first is not None and first != row["_file"]:
            dropped[(row["_file"], first)] = dropped.get((row["_file"], first), 0) + 1
            continue
        seen.setdefault(key, row["_file"])
        kept.append(row)
    return kept, [{"file": f, "same_as": s, "rows": n} for (f, s), n in dropped.items()]


def _sav_header(name: str, label: str, var_names: set[str]) -> str:
    """SPSS 文件的列：变量名对得上问卷的变量、标签又不像“5、您的……”这种带题号的题目时用变量名；否则用标签。
    问卷星的 SPSS 数据变量名是 Q1、Q2……（按问卷上印的题号），和内部题号不一定一致（团队删过题、加过题就对不上），
    标签里带着印出来的题号，按标签对应才不会错位。"""
    label = str(label or "").strip()
    if not label or label == name:
        return name
    if name in var_names and not re.match(r"^\s*(?:Q|q|第)?\d{1,3}\s*(?:题)?\s*[、.．:：)\]（(]", label):
        return name
    return label


def run_import(q: dict, paths: list[Path], kind: str, outdir: Path) -> dict:
    import pandas as pd
    frames, files = [], []
    var_names = {v["name"] for v in S.variables(S.normalize(q))}
    for path in paths:
        parts = {p.lower() for p in path.resolve().parts}
        if "rehearsal" in parts:
            raise ImportRefused(f"{path} 位于 rehearsal/（分析彩排的模拟数据），不能当作真实调查数据导入")
        frame = read_table(path)
        labels = frame.attrs.get("column_labels")
        if labels:
            headers, used = [], set()
            for name, label in zip([str(c) for c in frame.columns], labels):
                header = _sav_header(name, label, var_names)
                header = name if header in used else header
                used.add(header)
                headers.append(header)
            frame.columns = headers
        synthetic = "__synthetic__" in [str(c) for c in frame.columns]
        if synthetic and kind != DEMO_KIND:
            raise ImportRefused(f"{path.name} 带 __synthetic__ 列：这是模拟数据，不能当作真实调查数据导入")
        if kind == DEMO_KIND and not synthetic:
            raise ImportRefused(f"{path.name} 没有 __synthetic__ 列：演示模式只收明确标记为模拟的数据")
        frames.append((path.name, frame))
        files.append({"name": path.name, "sha256": sha256(path), "rows": int(len(frame)), "columns": int(frame.shape[1])})
    rows, report = import_frames(q, frames, kind)
    rows, duplicates = drop_cross_file_duplicates(rows, sorted(var_names))
    kept_rids = {r["_rid"] for r in rows}
    report["pii_rows"] = [p for p in report["pii_rows"] if p["_rid"] in kept_rids]
    pii_questions = {i["id"] for i in S.questions(S.normalize(q))
                     if i.get("type") in {"text", "number"} and re.search(L_PII, str(i.get("text", "")))}
    variables = [v["name"] for v in S.variables(S.normalize(q)) if v["name"] not in pii_questions]
    meta_cols = ["_rid", "_file", "_platform_id", "_submitted_at", "_started_at", "_duration_s", "_source", "_region", "_quality", "_source_kind"]
    columns = [c for c in meta_cols if any(c in r for r in rows)] + variables
    outdir.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows, columns=columns)
    frame.to_csv(outdir / "raw_import.csv", index=False, encoding="utf-8-sig")
    pii_rows = report.pop("pii_rows")
    if pii_rows:
        private = outdir / "private"
        private.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(pii_rows).to_csv(private / "pii.csv", index=False, encoding="utf-8-sig")
        (private / "README.txt").write_text("这里是答卷中的个人信息（如抽奖联系方式），只用于联系受访者，不进入分析、不写进报告、不随作品提交。\n", encoding="utf-8")
    mapped_vars = {m["target"] for mp in report["mapping"].values() for m in mp["columns"].values() if m.get("target")}
    for mp in report["mapping"].values():
        for m in mp["columns"].values():
            if m.get("layout") == "multi_joined":
                mapped_vars |= {v for v in variables if v.startswith(m["target"] + "_")}
    missing_vars = [v for v in variables if v not in mapped_vars and not v.endswith("_text")]
    low_conf = [{"column": h, **m} for mp in report["mapping"].values() for h, m in mp["columns"].items()
                if m.get("target") and m.get("confidence", 1) < 0.75]
    submitted = sorted(r["_submitted_at"] for r in rows if r.get("_submitted_at"))
    mapping_doc = {"schema": "paperkit.survey.import_mapping/v1", "files": report["mapping"],
                   "unmapped_variables": missing_vars, "low_confidence": low_conf,
                   "invalid_values": report["invalid_values"], "duplicates_across_files": duplicates}
    (outdir / "import_mapping.json").write_text(json.dumps(mapping_doc, ensure_ascii=False, indent=2, default=list), encoding="utf-8")
    provenance = {
        "schema": "paperkit.survey.provenance/v1", "kind": kind, "importer": IMPORTER_VERSION,
        "imported_at": dt.datetime.now().isoformat(timespec="seconds"),
        "files": files, "rows": len(rows),
        "collection_period": {"start": submitted[0] if submitted else None, "end": submitted[-1] if submitted else None},
        "pii_separated": bool(pii_rows),
    }
    if duplicates:
        provenance["duplicates_dropped"] = {"rows": sum(d["rows"] for d in duplicates), "detail": duplicates,
                                            "note": "同一份答卷出现在两个文件里（重复下载），只保留第一次出现的"}
    if kind == DEMO_KIND:
        provenance.update({"demo": True, "note": DEMO_NOTE})
    (outdir / "PROVENANCE.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"rows": len(rows), "missing_vars": missing_vars, "low_conf": low_conf,
            "invalid": report["invalid_values"], "unmapped_columns": [h for mp in report["mapping"].values() for h in mp["unmapped"]],
            "pii": bool(pii_rows), "duplicates": duplicates}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="答卷数据导入")
    ap.add_argument("questionnaire")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--kind", choices=["real_upload", "mutual_aid_hub", DEMO_KIND], default="real_upload")
    ap.add_argument("--outdir", default="data")
    args = ap.parse_args(argv)
    try:
        q = S.load_questionnaire(args.questionnaire)
    except S.SchemaError as exc:
        print(f"❌ {exc}")
        return 2
    paths = [Path(p) for p in args.files]
    missing = [str(p) for p in paths if not p.is_file()]
    if missing:
        print(f"❌ 找不到数据文件：{'、'.join(missing)}")
        return 2
    try:
        summary = run_import(q, paths, args.kind, Path(args.outdir))
    except ImportRefused as exc:
        print(f"❌ 拒收：{exc}")
        return 1
    except RuntimeError as exc:
        print(f"❌ {exc}")
        return 2
    print(f"✅ 导入 {summary['rows']} 份答卷 → {Path(args.outdir) / 'raw_import.csv'}")
    for d in summary["duplicates"]:
        print(f"ℹ️ {d['file']} 里有 {d['rows']} 份答卷和 {d['same_as']} 里的完全相同（重复下载），只保留一份")
    problems = 0
    if summary["missing_vars"]:
        problems += 1
        print(f"⚠️ 这些变量在数据里找不到对应列（将全部记为缺失）：{'、'.join(summary['missing_vars'][:20])}")
    if summary["low_conf"]:
        problems += 1
        print(f"⚠️ {len(summary['low_conf'])} 列靠题干相似度对应，置信不足 0.75，请核对 data/import_mapping.json")
    if summary["unmapped_columns"]:
        print(f"ℹ️ 未使用的列：{'、'.join(summary['unmapped_columns'][:15])}")
    if summary["invalid"]:
        problems += 1
        print(f"⚠️ 有认不出的取值（已置空）：{json.dumps(summary['invalid'], ensure_ascii=False)[:300]}")
    if summary["pii"]:
        print("ℹ️ 个人信息列已移到 data/private/，不进入分析")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
