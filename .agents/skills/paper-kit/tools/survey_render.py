#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 QUESTIONNAIRE.json 导出成可读/可发放的形式。

  markdown   报告附录用的完整问卷（Markdown，交给 Word 导出引擎排版）
  wjx        问卷星"从文本创建问卷"可直接粘贴的文本 + 手工设置清单（跳转逻辑问卷星导不进）
  codebook   附录用的变量编码表（Markdown）

用法：
  python _utils/survey_render.py markdown QUESTIONNAIRE.json --out fieldwork/问卷.md [--appendix] [--anonymize 学校名]
  （--appendix 附录版：把 .mh/blind_terms.json 里的学校、指导教师名和“我们是××大学”这类自称换成"某高校"；
   发出去的问卷、问卷星导入文本保留团队写的真实学校——受访者看到真实学校更愿意填，盲评只管参赛报告）
  python _utils/survey_render.py wjx QUESTIONNAIRE.json --out fieldwork/问卷星导入.txt
  python _utils/survey_render.py codebook QUESTIONNAIRE.json --out fieldwork/变量编码表.md
退出码：0 成功；1 问卷结构有错误；2 输入缺失。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
import survey_schema as S  # noqa: E402

KIND_LABELS = {"categorical": "类别", "binary": "二分类（0/1）", "scale": "量表", "numeric": "数值",
               "rank": "排序名次", "text": "文本"}


def blind_terms(path: str | None) -> list[str]:
    """读 .mh/blind_terms.json 的 {"terms": [...]}；没有文件时返回空列表。"""
    if not path or not Path(path).is_file():
        return []
    try:
        data = S.load_json(path)
    except S.SchemaError:
        return []
    terms = data.get("terms") if isinstance(data, dict) else data
    return [str(t) for t in terms or [] if str(t).strip()]


def display_numbers(q: dict) -> dict[str, int]:
    nums, n = {}, 0
    for item in S.questions(q):
        if S.answerable(item):
            n += 1
            nums[item["id"]] = n
            for row in item.get("rows") or []:
                if isinstance(row, dict):
                    nums[row.get("id")] = n
    return nums


def numbered(text: str, nums: dict) -> str:
    """文字里的内部题号（Q12、K1）换成问卷上印的题号（第12题）：附录问卷按 1、2、3……编号，内部题号和它对不上
    （K1 印出来是第 15 题）。“注意力题 Q12 答错”写成“注意力题（第12题）答错”；题号两侧原来的西文空格去掉
    （“第2题 仅当 第1题 选”）。流程图和附录共用，两处写法一致。"""
    ids = sorted((k for k in nums if k), key=len, reverse=True)
    if not ids:
        return text
    pattern = re.compile(r"(?<![A-Za-z0-9_])(" + "|".join(re.escape(k) for k in ids) + r")(?![A-Za-z0-9_])")
    text = re.sub(r"注意力题 (\S+) 答错", lambda m: f"注意力题（{m.group(1)}）答错", text)
    text = pattern.sub(lambda m: f"第{nums[m.group(1)]}题", text)
    text = re.sub(r"(第[\d–、]+题)\s+(?=[\u4e00-\u9fff“（])", r"\1", text)
    return re.sub(r"(?<=[\u4e00-\u9fff”）])\s+(第[\d–、]+题)", r"\1", text)


def _owner(q: dict, ref: str) -> tuple[dict | None, dict | None]:
    for item in S.questions(q):
        if item.get("id") == ref:
            return item, None
        for row in item.get("rows") or []:
            if isinstance(row, dict) and row.get("id") == ref:
                return item, row
    return None, None


def humanize(q: dict, expr: str) -> str:
    """'Q2 == 1 and Q5 >= 4' → '第2题选“男”且第5题 ≥ 4'。"""
    try:
        node = S.parse_logic(expr)
    except S.LogicError:
        return expr
    nums = display_numbers(q)

    def name(ref):
        item, row = _owner(q, ref)
        n = nums.get(ref, "?")
        return f"第{n}题“{row.get('label')}”行" if row else f"第{n}题"

    def label(ref, value):
        item, row = _owner(q, ref)
        if item and item.get("type") in S.CHOICE_TYPES:
            lab = S.option_label(item, value)
            if lab is not None:
                return f"“{lab}”"
        return str(value)

    def walk(node, top=True):
        kind = node[0]
        if kind in {"and", "or"}:
            text = f"{walk(node[1], False)}{'且' if kind == 'and' else '或'}{walk(node[2], False)}"
            return text if top else f"（{text}）"
        if kind == "not":
            return f"并非{walk(node[1], False)}"
        if kind == "answered":
            return f"已回答{name(node[1])}"
        if kind == "in":
            return f"{name(node[1])}选{'或'.join(label(node[1], v) for v in node[2])}"
        op, ref, val = node[1], node[2], node[3]
        if op == "==":
            return f"{name(ref)}选{label(ref, val)}"
        if op == "!=":
            return f"{name(ref)}未选{label(ref, val)}"
        return f"{name(ref)} {op.replace('>=', '≥').replace('<=', '≤')} {val}"

    return walk(node)


# 卷首语里的自称：“我们是××大学……”“本团队来自××学院”。附录版换成“某高校”，盲评词表里没登记的学校名也不会漏
SELF_INTRO = re.compile(r"(我们是来自|我们来自|我们是|本团队来自|本小组来自|我是来自|我是)(?!某高校|某大学|某学院)"
                        r"[^，。,.；;！!？?\s“”\"、]{0,20}(?:大学(?!生)|学院|学校)")      # 贪婪：“××大学××学院”整个换掉


def anonymize(text: str, schools: list[str], intro: bool = False) -> str:
    out = str(text)
    if intro:                                    # 先换整句自称，免得先换掉“××大学”后剩下“某高校××学院”
        out = SELF_INTRO.sub(lambda m: m.group(1) + "某高校", out)
    for name in sorted({s for s in schools if s}, key=len, reverse=True):   # 长的先换：“××大学××学院”先于“××大学”
        out = out.replace(name, "某高校")
    return out


def _type_note(item: dict) -> str:
    qtype = item.get("type")
    note = S.TYPE_LABELS.get(qtype, "")
    if qtype == "multi":
        lo, hi = item.get("min_select"), item.get("max_select")
        if lo and hi:
            note += f"，选 {lo}–{hi} 项"
        elif hi:
            note += f"，最多选 {hi} 项"
        elif lo:
            note += f"，至少选 {lo} 项"
    if qtype in S.SCALE_TYPES:
        rng = S.scale_range(item)
        labels = (item.get("scale") or {}).get("labels") or {}
        if rng and labels:
            lo_lab = labels.get(str(rng[0]), labels.get(rng[0]))
            hi_lab = labels.get(str(rng[1]), labels.get(rng[1]))
            if lo_lab and hi_lab:
                note += f"，{rng[0]}=“{lo_lab}”，{rng[1]}=“{hi_lab}”"
    return note


def to_markdown(q: dict, *, appendix: bool = False, schools: list[str] | None = None) -> str:
    q = S.normalize(q)
    terms = schools or []

    def anon(text) -> str:                        # 附录版另把“我们是××大学”这类自称换掉
        return anonymize(text, terms, intro=appendix)
    nums = display_numbers(q)
    sections = {s.get("id"): s for s in q.get("sections") or [] if isinstance(s, dict)}
    lines: list[str] = []
    title = anon(q.get("title", "调查问卷"))
    lines.append(f"## 附录 调查问卷：{title}" if appendix else f"# {title}")
    lines.append("")
    if q.get("intro"):
        lines.append(anon(q["intro"]))
        lines.append("")
    current = None
    for item in S.questions(q):
        sec = item.get("section")
        if sec and sec != current and sec in sections:
            current = sec
            lines.append(f"{'###' if appendix else '##'} {anon(sections[sec].get('title', sec))}")
            lines.append("")
            if sections[sec].get("description"):
                lines.append(anon(sections[sec]["description"]))
                lines.append("")
        qtype = item.get("type")
        text = anon(item.get("text", ""))
        if qtype == "paragraph":
            lines.append(text)
            lines.append("")
            continue
        star = "*" if item.get("required", True) else ""
        lines.append(f"**{nums[item['id']]}. {text}**{star}（{_type_note(item)}）")
        lines.append("")
        if item.get("show_if"):
            lines.append(f"> 显示条件：{humanize(q, item['show_if'])}时回答本题")
            lines.append("")
        mark = "□" if qtype == "multi" else "○"
        if qtype in {"single", "multi", "rank"}:
            for opt in item.get("options") or []:
                lab = anon(opt.get("label", ""))
                tail = "______" if opt.get("other") else ""
                prefix = "____" if qtype == "rank" else mark
                lines.append(f"- {prefix} {lab}{tail}")
            lines.append("")
        elif qtype in {"text"}:
            lines.append("________________________________________")
            lines.append("")
        elif qtype == "number":
            unit = item.get("unit") or ""
            lines.append(f"________ {unit}".rstrip())
            lines.append("")
        elif qtype == "scale":
            rng = S.scale_range(item) or (1, 5)
            lines.append("  ".join(f"○ {k}" for k in range(rng[0], rng[1] + 1)))
            lines.append("")
        elif qtype in S.MATRIX_TYPES:
            if qtype == "matrix_scale":
                rng = S.scale_range(item) or (1, 5)
                cols = [str(k) for k in range(rng[0], rng[1] + 1)]
            else:
                cols = [anon(o.get("label", "")) for o in item.get("options") or []]
            lines.append("| 题项 | " + " | ".join(cols) + " |")
            lines.append("|---|" + "---|" * len(cols))
            for row in item.get("rows") or []:
                lab = anon(row.get("label", ""))
                lines.append(f"| {lab} | " + " | ".join("○" for _ in cols) + " |")
            lines.append("")
        if item.get("terminate_if"):   # 甄别题不提前结束作答（2026-10-14 用户定），曾写“的受访者结束作答”
            lines.append(f"> 甄别：{humanize(q, item['terminate_if'])}的受访者不属于调查对象（照常答完，分析时单列）")
            lines.append("")
    lines.append("问卷到此结束，感谢您的参与！")
    return "\n".join(lines).rstrip() + "\n"


def _wjx_clean(text: str) -> str:
    # 问卷星按行切题、按空格切矩阵列，题干和选项里不能有换行
    return re.sub(r"\s*\n\s*", " ", str(text)).strip()


def to_wjx(q: dict) -> tuple[str, list[str]]:
    """返回 (可粘贴文本, 需要在问卷星里手工设置的事项)。"""
    q = S.normalize(q)
    nums = display_numbers(q)
    blocks, manual = [], []
    for item in S.questions(q):
        qtype = item.get("type")
        text = _wjx_clean(item.get("text", ""))
        if qtype == "paragraph":
            blocks.append(f"{text}[段落说明]")
            continue
        n = nums[item["id"]]
        head = f"{n}.{text}"
        note = ""
        if qtype in S.SCALE_TYPES:
            rng = S.scale_range(item) or (1, 5)
            labels = (item.get("scale") or {}).get("labels") or {}
            lo_lab = labels.get(str(rng[0]), labels.get(rng[0]))
            hi_lab = labels.get(str(rng[1]), labels.get(rng[1]))
            if lo_lab and hi_lab:
                note = f"（{rng[0]}为{lo_lab}，{rng[1]}为{hi_lab}）"
        if qtype == "single":
            lines = [head] + [_wjx_clean(o.get("label", "")) for o in item.get("options") or []]
        elif qtype == "multi":
            lines = [f"{head}[多选题]"] + [_wjx_clean(o.get("label", "")) for o in item.get("options") or []]
            if item.get("exclusive_options"):
                labels = [S.option_label(item, c) for c in item["exclusive_options"]]
                manual.append(f"第{n}题：把“{'、'.join(l for l in labels if l)}”设为互斥选项")
            if item.get("min_select") or item.get("max_select"):
                manual.append(f"第{n}题：设置最少选 {item.get('min_select') or 1} 项、最多选 {item.get('max_select') or len(item.get('options') or [])} 项")
        elif qtype in {"text", "number"}:
            lines = [f"{head}[填空题]"]
            if qtype == "number":
                manual.append(f"第{n}题：在填空校验里设为“数字”" + (f"，范围 {item.get('min')}–{item.get('max')}" if item.get("min") is not None else ""))
        elif qtype == "scale":
            rng = S.scale_range(item) or (1, 5)
            lines = [f"{head}{note}[量表题]"] + [str(k) for k in range(rng[0], rng[1] + 1)]
        elif qtype == "matrix_scale":
            rng = S.scale_range(item) or (1, 5)
            lines = [f"{head}{note}[矩阵量表题]", " ".join(str(k) for k in range(rng[0], rng[1] + 1))]
            lines += [_wjx_clean(r.get("label", "")) for r in item.get("rows") or []]
        elif qtype == "matrix_single":
            cols = [re.sub(r"\s+", "", _wjx_clean(o.get("label", ""))) for o in item.get("options") or []]
            lines = [f"{head}[矩阵题]", " ".join(cols)] + [_wjx_clean(r.get("label", "")) for r in item.get("rows") or []]
        elif qtype == "rank":
            lines = [f"{head}[排序题]"] + [_wjx_clean(o.get("label", "")) for o in item.get("options") or []]
        else:
            continue
        for opt in item.get("options") or []:
            if isinstance(opt, dict) and opt.get("other"):
                manual.append(f"第{n}题：给“{opt.get('label')}”打开“允许填空”")
        if not item.get("required", True):
            manual.append(f"第{n}题：取消“必答”")
        if item.get("show_if"):
            manual.append(f"第{n}题：设置显示逻辑——{humanize(q, item['show_if'])}时才显示")
        if item.get("terminate_if"):   # 不提前关闭问卷（2026-10-14 用户定），曾让设成“时结束作答（甄别）”
            manual.append(f"第{n}题是甄别题（{humanize(q, item['terminate_if'])}的受访者不属于调查对象）：不要设置“结束作答”跳转，"
                          "让所有人答完；回收后清洗时会按这题把非调查对象单列")
        if item.get("attention_check"):
            manual.append(f"第{n}题是注意力检测题，不要删；导出数据后清洗步骤会用它识别乱答")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n", manual


def wjx_quality_settings(q: dict) -> list[str]:
    """问卷星整卷要手工设的质控项（文本导入带不进去）：同一人只能填一次。
    不按作答用时判无效（2026-10-10 用户定），清单不再让设最短答题时间，问卷里写了 min_seconds 也不提。"""
    q = S.normalize(q)
    quality = q.get("quality") if isinstance(q.get("quality"), dict) else {}
    dedup = "、".join(str(d) for d in quality.get("dedup") or [] if str(d).strip()) or "IP"
    return [f"整卷：在“设置”里限制同一个人只能填一次（按{dedup}去重，如每个 IP / 每台设备只能填写 1 次）"]


def codebook_markdown(q: dict) -> str:
    q = S.normalize(q)
    lines = ["| 变量名 | 题目 | 类型 | 取值说明 |", "|---|---|---|---|"]
    for var in S.variables(q):
        values = var.get("values") or {}
        if var.get("kind") in {"scale", "rank"} and var.get("min") is not None:
            desc = f"{var['min']}–{var['max']}"
            if values:
                desc += "（" + "，".join(f"{k}={v}" for k, v in values.items()) + "）"
        elif values:
            desc = "；".join(f"{k}={v}" for k, v in values.items())
        else:
            desc = "原样记录" if var.get("kind") == "text" else ""
        if var.get("reverse"):
            desc += "（反向题，分析前重新编码）"
        label = str(var.get("label", "")).replace("|", "/")
        lines.append(f"| {var['name']} | {label} | {KIND_LABELS.get(var.get('kind'), var.get('kind'))} | {desc} |")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="问卷导出")
    ap.add_argument("mode", choices=["markdown", "wjx", "codebook"])
    ap.add_argument("questionnaire")
    ap.add_argument("--out", required=True)
    ap.add_argument("--appendix", action="store_true")
    ap.add_argument("--anonymize", action="append", default=[])
    ap.add_argument("--blind-file", default=".mh/blind_terms.json",
                    help="盲评词表（学校、指导教师等），附录版（--appendix）按它匿名化")
    args = ap.parse_args(argv)
    # 只有附录版匿名化：发出去的问卷（问卷.md、问卷星导入文本）照团队写的来，卷首语可以写真实学校
    args.anonymize = list(args.anonymize) + (blind_terms(args.blind_file) if args.appendix else [])
    try:
        q = S.load_questionnaire(args.questionnaire)
    except S.SchemaError as exc:
        print(f"❌ {exc}")
        return 2
    errors = [i for i in S.validate(q) if i["severity"] == "error"]
    if errors:
        for i in errors:
            print(f"❌ {i['message']}")
        print("❌ 问卷结构有错误，先修正再导出")
        return 1
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if args.mode == "markdown":
        out.write_text(to_markdown(q, appendix=args.appendix, schools=args.anonymize), encoding="utf-8")
    elif args.mode == "codebook":
        out.write_text(codebook_markdown(q), encoding="utf-8")
    else:
        text, manual = to_wjx(q)
        out.write_text(text, encoding="utf-8")
        guide = out.with_name(out.stem + "_手工设置清单.md")
        body = ["# 问卷星导入说明", "",
                "1. 登录问卷星 → 创建问卷 → 选择“从文本创建问卷/导入文本”，把同目录的导入文本整段粘贴进去。",
                f"2. 问卷标题填：{q.get('title', '')}",
                "3. 问卷说明（卷首语）填：", "", str(q.get("intro", "")), "",
                "4. 粘贴后逐题核对题型，再按下面清单手工设置（问卷星的文本导入不支持这些设置）：", ""]
        body += [f"- {m}" for m in manual + wjx_quality_settings(q)]
        body += ["", "5. 回收结束后：数据分析 → 下载答卷数据 → 选“按选项序号下载”的 Excel 或 SPSS，"
                 "回到平台上传，清洗步骤会自动识别问卷星格式。"]
        guide.write_text("\n".join(body) + "\n", encoding="utf-8")
        print(f"✅ 手工设置清单：{guide}")
    print(f"✅ 已写出 {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
