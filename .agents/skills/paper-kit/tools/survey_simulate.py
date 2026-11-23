#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""模拟填问卷：按定稿的问卷，用程序（不调模型）生成一批明确标注为“模拟”的答卷，在真实答卷回来之前把分析、报告整条跑一遍。

用户 2026-10-21：“问卷能不能加一个程序自动去模拟填问卷，但是要标注模拟的，然后可以根据模拟的出论文这样”。
大赛不允许用模拟数据参赛：模拟答卷出的只是“练习稿”——每行带 __synthetic__=1、_source=simulated，导入用
--kind demo_synthetic，清洗、统计加 --demo，报告每页标注“演示样例 · 数据为程序模拟生成”，合规检查判为不得提交，参赛版不给打包。

和分析彩排（survey_rehearsal.py，均匀随机，只为把流程跑通）不同，这里要能写出像样的分析：
· 每份先抽一个受访者画像：问卷里有配额（quotas）的人口题按配额分；没配额的按选项给一组固定的不均匀占比；
· 每个构念（量表题的 construct）给一个潜在态度分，构念之间通过一个总体态度分有中等相关；同一构念的量表题围绕
  这个分作答（带噪声，反向题反过来），所以信度、相关、回归有正常的结果；没有构念的量表题也略受总体态度影响；
· 跳题（show_if）按顺序走，只认前面还显示着的题；甄别题（terminate_if）约 8% 是非调查对象（照样答完整份问卷，清洗时单列）；
  注意力题（attention_check）约 4% 答错；约 2% 的人在一道矩阵量表上整列同选；其余尽量不触发问卷写的判无效规则；
· 多选题守 min_select / max_select 和互斥项；排序题按选项的基础偏好排；数字题在范围里；文字题从短句里挑，非必答题少数人不答；
· 提交时间分布在最近 10 天里，作答用时按问卷估时上下浮动；种子固定（同一项目重跑结果一样）。

用法：
  python _utils/survey_simulate.py QUESTIONNAIRE.json [--n 300] [--seed 20261021] [--sampling SAMPLING_PLAN.json]
         [--plan ANALYSIS_PLAN.json] [--outdir simulation]
产出：simulation/simulated_responses.csv（UTF-8 带 BOM）、simulation/SIMULATION.json（份数、种子、问卷指纹、提醒）、
     simulation/README.txt
退出码：0 成功；2 输入缺失或问卷不能用。
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import random
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
import survey_schema as S  # noqa: E402

GENERATOR = "paperkit.survey.simulate/v1"
SEED = 20261021
# 提交时间、生成时间都按北京时间写（桌面端进程的时区不一定是本地时区）
CST = dt.timezone(dt.timedelta(hours=8))
N_MIN, N_MAX = 30, 5000
SCREEN_OUT_SHARE = 0.08
ATTENTION_FAIL_SHARE = 0.04
STRAIGHTLINE_SHARE = 0.02
OPTIONAL_SKIP_SHARE = 0.10
# 入口题（后面的题只在选了某几项时才显示）：能打开后续题的选项合起来至少占这么多。10-22 实测：随机占比把
# “有没有闲置物品”抽成约 15% / 85%，1125 份里只有 165 份答了核心题，练习稿的分析只剩一百多人
GATE_OPEN_SHARE = 0.7
# 分支题（选不同的项问不同的追问）：每个能打开追问的选项至少占这么多（选项多时按 0.6/选项数 降低），
# 不然那条分支的追问只有几个人答（同一次实测：“走到了哪一步”抽成 83% 挤在一项，选“成交过”的只有 1.2%）
BRANCH_FLOOR = 0.1
NOTE = "模拟数据·由程序按问卷生成·不是真实调查数据·只能用于练习，不得用于参赛提交"
PSM_KEYS = ("too_cheap", "cheap", "expensive", "too_expensive")
TEXT_POOL = ("暂时没有想法", "希望价格再实惠一些", "希望更方便、更省时间", "整体还可以", "希望服务更周到", "没有特别的意见",
             "希望质量更稳定", "多做一些宣传", "希望选择更多一些", "无")
OTHER_TEXT = ("其他原因", "说不太清楚", "朋友推荐", "看情况")


def fingerprint(q: dict) -> str:
    """定稿问卷的指纹（和题目内容有关，和格式无关）：模拟答卷记下它，问卷改过就知道这批答卷对不上了"""
    blob = json.dumps(q, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _clip(value: float, lo: int, hi: int) -> int:
    return int(min(hi, max(lo, round(value))))


def _weights(rng: random.Random, n: int, skew: float = 1.0) -> list[float]:
    """一组固定的不均匀占比（像真实数据那样有多有少），skew 越大越悬殊"""
    raw = [rng.gammavariate(1.0 / max(skew, 0.2), 1.0) + 0.05 for _ in range(n)]
    total = sum(raw)
    return [w / total for w in raw]


def _quota_targets(q: dict, sampling: dict | None, items: dict) -> dict[str, dict[int, float]]:
    """配额：题号 → {选项编码: 占比}。问卷里的 quotas 优先，抽样计划里的补上"""
    out: dict[str, dict[int, float]] = {}
    for quota in list(q.get("quotas") or []) + list((sampling or {}).get("quotas") or []):
        if not isinstance(quota, dict):
            continue
        qid = quota.get("question")
        item = items.get(qid)
        targets = quota.get("targets")
        if not item or qid in out or not isinstance(targets, dict) or item.get("type") != "single":
            continue
        codes = set(S.option_codes(item))
        shares = {}
        for key, share in targets.items():
            try:
                code, value = int(key), float(share)
            except (TypeError, ValueError):
                continue
            if code in codes and value > 0:
                shares[code] = value
        if shares:
            out[qid] = shares
    return out


def _allocate(shares: dict[int, float], n: int, rng: random.Random) -> list[int]:
    """最大余数法把 n 个名额按占比分到各选项，再打乱"""
    total = sum(shares.values()) or 1.0
    raw = {code: n * w / total for code, w in shares.items()}
    base = {code: int(math.floor(x)) for code, x in raw.items()}
    left = n - sum(base.values())
    for code, _ in sorted(raw.items(), key=lambda t: t[1] - math.floor(t[1]), reverse=True)[:left]:
        base[code] += 1
    seq = [code for code, k in base.items() for _ in range(k)]
    rng.shuffle(seq)
    return seq


def _opening_codes(item: dict, codes: list[int], later: list[dict]) -> set[int]:
    """后面哪些题只看这一题决定显示：逐个选项试，能让它们显示出来的选项"""
    qid = item.get("id")
    opening: set[int] = set()
    for other in later:
        expr = other.get("show_if")
        if not expr:
            continue
        try:
            node = S.parse_logic(expr)
        except S.LogicError:
            continue
        if {name for name, _values in S.referenced(node)} != {qid}:
            continue
        opening.update(code for code in codes if S.evaluate(node, {qid: code}))
    return opening


def _floored(weights: list[float], codes: list[int], keep: set[int], floor: float) -> list[float]:
    """keep 里的选项各至少占 floor：不够的抬到 floor，其余按原来的比例分剩下的（抬一轮可能又压低别的，多抬几轮）"""
    out, fixed = list(weights), set()
    for _ in range(len(codes)):
        low = {i for i, code in enumerate(codes) if code in keep and i not in fixed and out[i] < floor}
        if not low:
            break
        fixed |= low
        rest = [i for i in range(len(codes)) if i not in fixed]
        mass, total = 1 - floor * len(fixed), sum(weights[i] for i in rest)
        out = [floor if i in fixed else (mass * weights[i] / total if total > 0 else mass / len(rest))
               for i in range(len(codes))]
    return out


def _terminating_values(item: dict, view: dict) -> set:
    """这道题选哪些值会被甄别掉（按问卷写的 terminate_if 逐个试）"""
    expr = item.get("terminate_if")
    values = S.valid_values(item) or S.option_codes(item)
    if not expr or not values:
        return set()
    try:
        node = S.parse_logic(expr)
    except S.LogicError:
        return set()
    bad = set()
    for value in values:
        trial = dict(view)
        trial[item.get("id")] = {value} if item.get("type") == "multi" else value
        try:
            if S.evaluate(node, trial):
                bad.add(value)
        except Exception:  # noqa: BLE001 - 表达式算不了就当这一项不淘汰
            continue
    return bad


class Plan:
    """整批共用的东西：各题的基础占比、构念、配额、价格题（每份答卷都用同一套，像同一个总体）"""

    def __init__(self, q: dict, sampling: dict | None, analysis: dict | None, n: int, rng: random.Random):
        self.q = q
        self.items = {i.get("id"): i for i in S.questions(q)}
        self.quotas = _quota_targets(q, sampling, self.items)
        self.quota_seq = {qid: _allocate(shares, n, rng) for qid, shares in self.quotas.items()}
        self.base: dict[str, list[float]] = {}
        self.multi_p: dict[str, dict[int, float]] = {}
        self.rank_bias: dict[str, dict[int, float]] = {}
        self.scale_mean: dict[str, float] = {}
        for item in S.questions(q):
            qid, qtype = item.get("id"), item.get("type")
            codes = S.option_codes(item)
            if qtype in {"single", "matrix_single"} and codes:
                self.base[qid] = _weights(rng, len(codes), 1.2)
            elif qtype == "multi" and codes:
                self.multi_p[qid] = {c: 0.12 + 0.5 * rng.random() for c in codes}
            elif qtype == "rank" and codes:
                self.rank_bias[qid] = {c: rng.random() for c in codes}
            if qtype in S.SCALE_TYPES:
                self.scale_mean[qid] = rng.uniform(-0.35, 0.45)     # 这道题整体偏高还是偏低（单位：标准差）
        self._open_gates(S.questions(q))
        self.constructs = S.constructs(q)
        self.construct_of: dict[str, str] = {}
        for name, names in self.constructs.items():
            for var in names:
                self.construct_of[var] = name
        names = {v["name"] for v in S.variables(q)}
        self.psm = [[a.get(k) for k in PSM_KEYS] for a in (analysis or {}).get("analyses") or []
                    if isinstance(a, dict) and a.get("type") == "psm" and all(a.get(k) in names for k in PSM_KEYS)]
        self.matrix_scales = [i.get("id") for i in S.questions(q) if i.get("type") == "matrix_scale" and i.get("rows")]
        self.checks = []
        for check in (q.get("quality") or {}).get("consistency_checks") or []:
            expr = check.get("invalid_if") if isinstance(check, dict) else None
            if expr:
                try:
                    self.checks.append(S.parse_logic(expr))
                except S.LogicError:
                    continue
        self.seconds = S.estimate_seconds(q).get("total_seconds") or 300

    def _open_gates(self, items: list[dict]) -> None:
        """后面有题只看这一题决定显示的单选题：能打开追问的选项各至少占 BRANCH_FLOOR；
        其中入口题（有的选项一道追问都不打开）记进 self.gates，重抽答卷时照第一次的答（见 simulate_one），
        能打开追问的选项合起来不到 GATE_OPEN_SHARE 时按比例放大到这么多，组内比例不变。
        配额题按配额、甄别题和注意力题按各自的规则出答案，占比不在这里改"""
        self.gates: set[str] = set()
        for pos, item in enumerate(items):
            qid = item.get("id")
            if item.get("type") != "single" or item.get("attention_check"):
                continue
            codes = S.option_codes(item)
            opening = _opening_codes(item, codes, items[pos + 1:])
            if not opening:
                continue
            if len(opening) < len(codes):
                self.gates.add(qid)
            if qid not in self.base or qid in self.quotas or item.get("terminate_if"):
                continue
            weights = _floored(self.base[qid], codes, opening, min(BRANCH_FLOOR, 0.6 / len(codes)))
            share = sum(w for code, w in zip(codes, weights) if code in opening)
            if 0 < share < GATE_OPEN_SHARE:
                weights = [w * GATE_OPEN_SHARE / share if code in opening else w * (1 - GATE_OPEN_SHARE) / (1 - share)
                           for code, w in zip(codes, weights)]
            self.base[qid] = weights


class Respondent:
    def __init__(self, plan: Plan, index: int, rng: random.Random):
        self.rng = rng
        self.general = rng.gauss(0, 1)
        self.trait = {name: 0.6 * self.general + 0.8 * rng.gauss(0, 1) for name in plan.constructs}
        self.screened_out = rng.random() < SCREEN_OUT_SHARE
        self.careless = rng.random() < ATTENTION_FAIL_SHARE
        self.straightline = plan.matrix_scales and rng.random() < STRAIGHTLINE_SHARE
        self.straight_item = rng.choice(plan.matrix_scales) if self.straightline else None
        self.fixed = {qid: seq[index] for qid, seq in plan.quota_seq.items() if index < len(seq)}


def _scale_value(plan: Plan, rsp: Respondent, item: dict, var: str, reverse: bool) -> int:
    lo, hi = S.scale_range(item) or (1, 5)
    construct = plan.construct_of.get(var)
    latent = rsp.trait.get(construct) if construct else 0.35 * rsp.general
    z = plan.scale_mean.get(item.get("id"), 0.0) + 0.75 * latent + 0.7 * rsp.rng.gauss(0, 1)
    if reverse:
        z = -z
    center, spread = (lo + hi) / 2, (hi - lo) / 4.2
    return _clip(center + spread * z, lo, hi)


def _choose(rng: random.Random, codes: list[int], weights: list[float], shift: float = 0.0) -> int:
    """按基础占比挑一个；shift（总体态度）让后面的选项稍多或稍少一点——选项一般按程度由低到高排"""
    if not codes:
        return 0
    k = len(codes)
    adjusted = [w * math.exp(shift * 0.35 * ((i / (k - 1) - 0.5) if k > 1 else 0)) for i, w in enumerate(weights)]
    return rng.choices(codes, weights=adjusted)[0]


def _answer_item(plan: Plan, rsp: Respondent, item: dict, view: dict, row: dict) -> None:
    rng = rsp.rng
    qid, qtype = item.get("id"), item.get("type")
    codes = S.option_codes(item)
    if not item.get("required") and qtype not in {"single", "multi"} and rng.random() < OPTIONAL_SKIP_SHARE:
        return
    if qtype == "single":
        if item.get("terminate_if"):
            bad = _terminating_values(item, view)
            pool = [c for c in codes if (c in bad) == rsp.screened_out] or codes
            value = rng.choice(pool) if rsp.screened_out else _choose(rng, pool, [plan.base[qid][codes.index(c)] for c in pool])
        elif qid in rsp.fixed:
            value = rsp.fixed[qid]
        else:
            value = _choose(rng, codes, plan.base.get(qid) or [1.0] * len(codes), rsp.general)
        row[qid] = view[qid] = value
    elif qtype == "scale":
        value = _scale_value(plan, rsp, item, qid, bool(item.get("reverse")))
        if item.get("terminate_if"):
            bad = _terminating_values(item, view)
            good = [v for v in (S.valid_values(item) or []) if v not in bad]
            if rsp.screened_out and bad:
                value = rng.choice(sorted(bad))
            elif value in bad and good:
                value = min(good, key=lambda v: abs(v - value))
        row[qid] = view[qid] = value
    elif qtype == "multi":
        exclusive = set(item.get("exclusive_options") or [])
        normal = [c for c in codes if c not in exclusive]
        probs = plan.multi_p.get(qid, {})
        lo = max(1, int(item.get("min_select") or 1))
        hi = int(item.get("max_select") or len(normal) or 1)
        if exclusive and rng.random() < 0.06:
            chosen = {rng.choice(sorted(exclusive))}
        else:
            chosen = {c for c in normal if rng.random() < probs.get(c, 0.3) * (1 + 0.15 * rsp.general)}
            ranked = sorted(normal, key=lambda c: -probs.get(c, 0.3) - 0.1 * rng.random())
            for c in ranked:
                if len(chosen) >= lo:
                    break
                chosen.add(c)
            while len(chosen) > max(lo, hi):
                chosen.discard(min(chosen, key=lambda c: probs.get(c, 0.3) + 0.1 * rng.random()))
            if not chosen and codes:
                chosen = {codes[0]}
        for c in codes:
            row[f"{qid}_{c}"] = 1 if c in chosen else 0
        view[qid] = chosen
        for opt in item.get("options") or []:
            if isinstance(opt, dict) and opt.get("other") and opt.get("code") in chosen:
                row[f"{qid}_{opt.get('code')}_text"] = rng.choice(OTHER_TEXT)
    elif qtype in S.MATRIX_TYPES:
        rows = [r for r in item.get("rows") or [] if isinstance(r, dict) and r.get("id")]
        if qtype == "matrix_scale" and rsp.straight_item == qid:
            lo, hi = S.scale_range(item) or (1, 5)
            same = rng.randint(lo, hi)
            for r in rows:
                row[r["id"]] = view[r["id"]] = same
            return
        for r in rows:
            if qtype == "matrix_scale":
                value = _scale_value(plan, rsp, item, r["id"], bool(r.get("reverse")))
            else:
                value = _choose(rng, codes, plan.base.get(qid) or [1.0] * len(codes), rsp.general)
            row[r["id"]] = view[r["id"]] = value
    elif qtype == "number":
        lo = item.get("min") if isinstance(item.get("min"), (int, float)) else 0
        hi = item.get("max") if isinstance(item.get("max"), (int, float)) else max(lo + 100, 100)
        mid, width = (lo + hi) / 2, (hi - lo) / 6 or 1
        value = _clip(mid + width * (0.4 * rsp.general + rng.gauss(0, 1)), int(math.ceil(lo)), int(math.floor(hi)))
        row[qid] = view[qid] = value
    elif qtype == "rank":
        bias = plan.rank_bias.get(qid, {})
        order = sorted(codes, key=lambda c: -(bias.get(c, 0.5) + 0.45 * rng.random()))
        for pos, c in enumerate(order, start=1):
            row[f"{qid}_{c}"] = pos
        view[qid] = order[0] if order else None
    elif qtype == "text":
        if not item.get("required") and rng.random() < 0.35:
            return
        row[qid] = view[qid] = rng.choice(TEXT_POOL)
    if qtype == "single":
        for opt in item.get("options") or []:
            if isinstance(opt, dict) and opt.get("other") and opt.get("code") == row.get(qid):
                row[f"{qid}_{opt.get('code')}_text"] = rng.choice(OTHER_TEXT)


def _attention(item: dict, rsp: Respondent, row: dict, view: dict) -> None:
    """注意力题：大多数人答成要求的那一项，粗心的人答别的"""
    expected = item.get("attention_expected")
    if not item.get("attention_check") or expected is None:
        return
    qid = item.get("id")
    values = S.valid_values(item) or S.option_codes(item)
    if item.get("type") in S.MATRIX_TYPES:
        return
    if rsp.careless and values:
        others = [v for v in values if v != expected]
        value = rsp.rng.choice(others or values)
    else:
        value = expected
    if qid in row and item.get("type") != "multi":
        row[qid] = view[qid] = value


def simulate_one(plan: Plan, index: int, rng: random.Random) -> tuple[dict, dict]:
    rsp = Respondent(plan, index, rng)
    pinned: dict[str, dict] = {}
    for _ in range(20):
        row: dict = {}
        view: dict = {}
        for item in S.questions(plan.q):
            if not S.answerable(item) or not S.is_shown(item, view):
                continue
            qid = item.get("id")
            if qid in pinned:
                row.update(pinned[qid])
                view[qid] = pinned[qid][qid]
                continue
            _answer_item(plan, rsp, item, view, row)
            _attention(item, rsp, row, view)
        for cols in plan.psm:
            values = [row.get(c) for c in cols]
            if all(isinstance(v, (int, float)) for v in values):
                for c, v in zip(cols, sorted(values)):
                    row[c] = view[c] = v
        if rsp.careless or not any(_safe_eval(node, view) for node in plan.checks):
            break
        # 触发了判无效规则要重抽：入口题照第一次的答，只重抽别的题。整份重抽会一轮轮偏向“选了不打开后续题”的答卷
        # （那样碰不到规则），10-22 实测 1125 份里“有闲置”的只剩 165 份
        if not pinned:
            pinned = {qid: {key: value for key, value in row.items() if key == qid or key.startswith(qid + "_")}
                      for qid in plan.gates if qid in row}
    return row, {"screened_out": rsp.screened_out, "careless": rsp.careless, "straightline": bool(rsp.straight_item)}


def _safe_eval(node, view) -> bool:
    try:
        return bool(S.evaluate(node, view))
    except Exception:  # noqa: BLE001
        return False


def simulate(q: dict, n: int, seed: int, sampling: dict | None = None, analysis: dict | None = None,
             now: dt.datetime | None = None) -> tuple[list[dict], dict]:
    q = S.normalize(q)
    n = max(N_MIN, min(int(n), N_MAX))
    rng = random.Random(seed)
    plan = Plan(q, sampling, analysis, n, rng)
    names = [v["name"] for v in S.variables(q)]
    end = (now or dt.datetime.now(CST).replace(tzinfo=None)).replace(microsecond=0)
    start = end - dt.timedelta(days=10)
    times = sorted(start + dt.timedelta(seconds=rng.randint(0, 10 * 24 * 3600 - 1)) for _ in range(n))
    rows, stats = [], {"screened_out": 0, "careless": 0, "straightline": 0}
    for index in range(n):
        answers, flags = simulate_one(plan, index, rng)
        for key in stats:
            stats[key] += 1 if flags[key] else 0
        duration = int(max(45, plan.seconds * math.exp(rng.gauss(0, 0.35))))
        rows.append({"_rid": f"S{index + 1:04d}", "__synthetic__": 1, "_submitted_at": times[index].strftime("%Y-%m-%d %H:%M:%S"),
                     "_duration_s": duration, "_source": "simulated", **{name: answers.get(name) for name in names}})
    return rows, stats


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="模拟填问卷（标注为模拟，只能出练习稿）")
    ap.add_argument("questionnaire")
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--sampling", default="SAMPLING_PLAN.json")
    ap.add_argument("--plan", default="ANALYSIS_PLAN.json")
    ap.add_argument("--outdir", default="simulation")
    args = ap.parse_args(argv)
    try:
        raw = S.load_json(args.questionnaire)
    except S.SchemaError as exc:
        print(f"❌ {exc}")
        return 2
    if not isinstance(raw, dict) or not S.questions(raw):
        print("❌ 问卷里没有题目")
        return 2
    errors = [i for i in S.validate(S.normalize(raw)) if i.get("severity") == "error"]
    if errors:
        print("❌ 问卷有结构错误，先改好再模拟：" + "；".join(str(e.get("message")) for e in errors[:3]))
        return 2
    outdir = Path(args.outdir)
    if outdir.resolve().name != "simulation":
        print("❌ 模拟答卷只能写在 simulation/ 目录（不能混进 data/、user_data/）")
        return 2

    def optional(path: str) -> dict | None:
        try:
            value = S.load_json(path) if path and Path(path).is_file() else None
        except S.SchemaError:
            return None
        return value if isinstance(value, dict) else None

    rows, stats = simulate(raw, args.n, args.seed, optional(args.sampling), optional(args.plan))
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / "simulated_responses.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    meta = {"schema": "paperkit.survey.simulation/v1", "generator": GENERATOR, "kind": "simulated", "warning": NOTE,
            "generated_at": dt.datetime.now(CST).isoformat(timespec="seconds"), "rows": len(rows), "seed": args.seed,
            "questionnaire_sha256": fingerprint(S.normalize(raw)), "designed": stats,
            "file": "simulation/simulated_responses.csv"}
    (outdir / "SIMULATION.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    (outdir / "README.txt").write_text(
        "本目录是程序按问卷生成的模拟答卷（每行带 __synthetic__=1、_source=simulated），不是真人填写的调查数据。\n"
        "只用于在真实答卷回来之前练习分析和写报告：用它出的报告每页标注“演示样例 · 数据为程序模拟生成”，不得作为参赛作品提交。\n"
        "不要把这些答卷复制进 data/、user_data/，也不要上传到问卷平台。\n", encoding="utf-8")
    print(f"✅ 生成 {len(rows)} 份模拟答卷 → {path}（其中设计为非调查对象 {stats['screened_out']} 份、注意力题答错 "
          f"{stats['careless']} 份、整列同选 {stats['straightline']} 份；全部标注为模拟）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
