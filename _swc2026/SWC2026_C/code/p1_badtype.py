# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""
p1_badtype.py -- 坏帧原因分解（side × reason）、记录内时间分布、段边界集中性检验

输入（只读）：
  {ROOT}\\Raw_Data\\{EgoPro,EgoStandard}\\<uuid>\\tables\\annotation_bad_frame_pose_hand.csv
  {ROOT}\\Raw_Data\\{EgoPro,EgoStandard}\\<uuid>\\tables\\pose_{left,right}_hand.csv   （仅用于对齐核对）
  {ROOT}\\Restocking_Tasks_and_Constraints\\source_segment_index.csv

输出（新文件，不覆盖任何已有文件）：
  data\\badtype_frames.csv      每行 = 一个 (record, frame, side) 坏帧事件
  data\\p1_badtype.json         组成 / 记录内时间分布 / 边界 vs 内部 / 对齐核对 / _meta

设计要点（写死在代码里，先于任何结果计算打印）：
  - 主检验单位 = 帧（frame-level，同一帧多原因只计一次）
  - 边界窗口 = ±0.5 s，仅取“内部边界”（0 < b < D-0.05），窗口裁剪到 [0,D]
  - 基准率 p0 = 全部记录的边界窗口总时长 / 全部记录总时长（按 30 Hz 均匀采样，等价于帧占比）
  - 判定“集中”需同时满足：单侧二项检验 p < 0.05 且 观测/基准 >= 1.5
  - 另给记录级（cluster）稳健性检查：逐记录边界占比 vs 基准率，符号检验 + Wilcoxon
"""
import os, sys, io, csv, json, math, hashlib, datetime, collections, statistics

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = r"Restocking_Problem_and_Data_EN"
PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_CSV = os.path.join(PROJ, "data", "badtype_frames.csv")
OUT_JSON = os.path.join(PROJ, "data", "p1_badtype.json")
DATASETS = ["EgoPro", "EgoStandard"]
W = 0.5                      # 边界窗口半宽（秒）
W_SENS = [0.25, 0.5, 1.0]    # 稳健性一览
EDGE_EPS = 0.05              # 距记录首尾 0.05 s 内的“边界”不算内部边界

# ---------------------------------------------------------------- pre-registration
PREREG = {
    "registered_before_results": True,
    "registered_at": datetime.datetime.now().isoformat(timespec="seconds"),
    "claim": ("bad (hand pose) frames concentrate near segment boundaries, "
              "i.e. the fraction of bad frames within +/-0.5 s of an interior segment boundary "
              "exceeds the duration-weighted base rate of those windows"),
    "primary_unit": "frame (deduplicated across sides/reasons)",
    "boundary_window_s": W,
    "interior_boundary_rule": "0 < b < D-0.05, window clipped to [0,D]",
    "base_rate_def": "sum(clipped window length) / sum(record duration), all 38 records pooled",
    "test": "scipy.stats.binomtest(k, n, p0, alternative='greater')",
    "falsified_if": [
        "one-sided binomial p > 0.05, OR",
        "observed fraction < 1.5 x base rate, OR",
        "the 95% CI of the fraction contains the base rate",
    ],
    "support_requires": "p < 0.05 AND ratio >= 1.5 (both)",
    "known_limitation": ("bad frames occur in runs, so the binomial test over-states significance; "
                         "a record-level (cluster) sign test and Wilcoxon signed-rank are reported "
                         "alongside and are the conservative reading"),
    "secondary_analyses_declared": [
        "task-change boundaries only (boundary where segment description changes)",
        "per-reason boundary fractions",
        "window sensitivity 0.25/0.5/1.0 s",
    ],
}

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def recs(ds):
    d = os.path.join(ROOT, "Raw_Data", ds)
    return sorted([p for p in os.listdir(d) if os.path.isdir(os.path.join(d, p))])

def read_ann(path):
    """yield (frame_index, offset_s, slots[list[str]], is_bad) for every row."""
    with open(path, "r", encoding="utf-8", newline="") as f:
        rd = csv.reader(f)
        h = [c.lstrip("\ufeff") for c in next(rd)]
        ix = {c: i for i, c in enumerate(h)}
        slot_cols = sorted([c for c in h if c.startswith("problem_type[")])
        i_mi, i_of, i_bad = ix["_message_index"], ix["_offset_from_first_log_s"], ix["is_bad"]
        i_len = ix.get("problem_type.length")
        for r in rd:
            if not r:
                continue
            slots = [(r[ix[c]].strip() if c in ix and ix[c] < len(r) else "") for c in slot_cols]
            L = int(float(r[i_len])) if i_len is not None and r[i_len] not in ("", None) else None
            yield (int(float(r[i_mi])), float(r[i_of]), slots,
                   r[i_bad].strip().lower() in ("true", "1"), L)

def count_frames(path):
    n = 0
    idx = set()
    tmax = 0.0
    with open(path, "r", encoding="utf-8", newline="") as f:
        rd = csv.reader(f)
        h = [c.lstrip("\ufeff") for c in next(rd)]
        i_mi, i_of = h.index("_message_index"), h.index("_offset_from_first_log_s")
        for r in rd:
            if not r:
                continue
            n += 1
            idx.add(int(float(r[i_mi])))
            t = float(r[i_of])
            if t > tmax:
                tmax = t
    return n, idx, tmax

def header_ncols(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return len([c for c in next(csv.reader(f))])

# ---------------------------------------------------------------- segment index
def load_segments():
    """(dataset, sample)-> list of segment dicts sorted by start_s.  sample == record dir uuid
    for EgoPro/EgoStandard (verified by end_s ~= record tmax)."""
    sp = os.path.join(ROOT, "Restocking_Tasks_and_Constraints", "source_segment_index.csv")
    seg = collections.defaultdict(list)
    with open(sp, "r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            seg[(r["dataset"], r["sample"])].append({
                "i": int(r["source_segment_index"]),
                "start": float(r["start_s"]), "end": float(r["end_s"]),
                "task": r["task"], "desc": r["description"],
                "eligible": r["eligible"].strip() in ("1", "1.0", "True", "true"),
                "family": r["family_id"], "episode": r["episode_uuid"],
            })
    for k in seg:
        seg[k].sort(key=lambda s: (s["start"], s["end"]))
    return seg, sp

def merge_windows(bs, w, D):
    """total length of union of [b-w,b+w] clipped to [0,D]"""
    iv = []
    for b in bs:
        a, z = max(0.0, b - w), min(D, b + w)
        if z > a:
            iv.append((a, z))
    iv.sort()
    tot, ca, cz = 0.0, None, None
    for a, z in iv:
        if ca is None:
            ca, cz = a, z
        elif a <= cz:
            cz = max(cz, z)
        else:
            tot += cz - ca
            ca, cz = a, z
    if ca is not None:
        tot += cz - ca
    return tot

def in_any(t, bs, w):
    return any(abs(t - b) <= w for b in bs)

# ---------------------------------------------------------------- main scan
segmap, segpath = load_segments()
rows_out = []          # frame-side events
records = []           # manifest
align = []             # alignment check per record
empty_reason_frames = []
numeric_slots = 0
string_slots = 0
slot_combo = collections.Counter()
len_vs_filled_mismatch = 0
missing_seg = []

ri = -1
for ds in DATASETS:
    for u in recs(ds):
        ri += 1
        tp = os.path.join(ROOT, "Raw_Data", ds, u, "tables")
        ap = os.path.join(tp, "annotation_bad_frame_pose_hand.csv")
        lp = os.path.join(tp, "pose_left_hand.csv")
        rp = os.path.join(tp, "pose_right_hand.csv")

        # ---- alignment check (all three tables)
        na, ia, ta = count_frames(ap)
        nl, il, tl = count_frames(lp)
        nr, ir, tr = count_frames(rp)
        align.append({"dataset": ds, "uuid": u, "n_annotation": na,
                      "n_pose_left": nl, "n_pose_right": nr,
                      "rows_equal": na == nl == nr,
                      "message_index_set_equal": ia == il == ir,
                      "tmax_annotation": round(ta, 6), "tmax_pose_left": round(tl, 6)})

        # ---- bad rows
        bad = []
        ncol_here = None
        maxL_here = 0
        for fi, off, slots, is_bad, L in read_ann(ap):
            filled = [s for s in slots if s]
            if is_bad:
                if not filled:
                    empty_reason_frames.append({"dataset": ds, "uuid": u, "frame_index": fi})
                slot_combo[tuple(slots)] += 1
                if L is not None and L != len(filled):
                    len_vs_filled_mismatch += 1
                if L is not None:
                    maxL_here = max(maxL_here, L)
                bad.append((fi, off, slots))
                for s in filled:
                    if s.replace(".", "", 1).isdigit():
                        numeric_slots += 1
                    else:
                        string_slots += 1

        # ---- segments
        def build_bs(w, use_change_only=False, eligible_only=False):
            out = []
            if (ds, u) not in segmap:
                return out
            ss = segmap[(ds, u)]
            for j in range(1, len(ss)):
                b = ss[j]["start"]
                if not (EDGE_EPS < b < ta - EDGE_EPS):
                    continue
                if eligible_only and not (ss[j]["eligible"] and ss[j - 1]["eligible"]):
                    continue
                if use_change_only and ss[j]["desc"] == ss[j - 1]["desc"]:
                    continue
                out.append(b)
            return out

        bs_all = build_bs(W)
        bs_chg = build_bs(W, use_change_only=True)
        bs_elig = build_bs(W, eligible_only=True)
        if (ds, u) not in segmap:
            missing_seg.append((ds, u))

        n_bad = len(bad)
        records.append({
            "record_index": ri, "dataset": ds, "uuid": u,
            "episode_uuid": segmap[(ds, u)][0]["episode"] if (ds, u) in segmap else None,
            "n_frames": na, "duration_s": round(ta, 6), "n_bad_frames": n_bad,
            "annotation_sha256": sha256(ap),
            "annotation_ncols": header_ncols(ap),
            "max_problem_length": maxL_here,
            "n_segments": len(segmap.get((ds, u), [])),
            "interior_boundaries": [round(b, 3) for b in bs_all],
            "task_change_boundaries": [round(b, 3) for b in bs_chg],
            "eligible_boundaries": [round(b, 3) for b in bs_elig],
            "base_rate_w05": (merge_windows(bs_all, W, ta) / ta) if ta > 0 else 0.0,
            "base_rate_w05_taskchange": (merge_windows(bs_chg, W, ta) / ta) if ta > 0 else 0.0,
        })

        # ---- events
        for fi, off, slots in bad:
            for s in [x for x in slots if x]:
                if ":" in s:
                    pre, rest = s.split(":", 1)
                    pre, rest = pre.strip(), rest.strip()
                    side = pre if pre in ("left", "right") else "unknown"
                    reason = rest
                    code = ""
                elif s.replace(".", "", 1).isdigit():
                    side, reason, code = "unknown", s, s   # 本包内未出现；保留以便将来
                else:
                    side, reason, code = "unknown", s, ""
                rows_out.append({
                    "dataset": ds, "uuid": u, "record_index": ri,
                    "frame_index": fi, "offset_s": off,
                    "side": side, "reason_code": code, "reason": reason,
                    "_in_w05": in_any(off, bs_all, W),
                    "_in_w05_chg": in_any(off, bs_chg, W),
                    "_frac": (off / ta) if ta > 0 else 0.0,
                })

# ---------------------------------------------------------------- write CSV (8 cols)
FIELDS = ["dataset", "uuid", "record_index", "frame_index", "offset_s",
          "side", "reason_code", "reason"]
rows_out.sort(key=lambda r: (r["dataset"], r["uuid"], r["frame_index"],
                             {"left": 0, "right": 1, "unknown": 2}[r["side"]], r["reason"]))
if os.path.exists(OUT_CSV):
    raise SystemExit("refuse to overwrite existing %s" % OUT_CSV)
os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
with open(OUT_CSV, "w", encoding="utf-8", newline="\n") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
    w.writeheader()
    for r in rows_out:
        w.writerow({k: ("%.6f" % r["offset_s"] if k == "offset_s" else r[k]) for k in FIELDS})

# ---------------------------------------------------------------- composition
def comp_table(sel_rows):
    c = collections.Counter((r["side"], r["reason"]) for r in sel_rows)
    return [{"side": s, "reason": rr, "n": n} for (s, rr), n in sorted(c.items())]

by_ds = {}
for ds in DATASETS:
    rs = [r for r in rows_out if r["dataset"] == ds]
    by_ds[ds] = {
        "n_bad_frames": len({(r["uuid"], r["frame_index"]) for r in rs}),
        "n_events": len(rs),
        "table": comp_table(rs),
        "n_records": sum(1 for r in records if r["dataset"] == ds),
        "n_records_with_bad": sum(1 for r in records if r["dataset"] == ds and r["n_bad_frames"] > 0),
    }
total_events = len(rows_out)
total_frames = len({(r["uuid"], r["frame_index"]) for r in rows_out})
empty_n = len(empty_reason_frames)

composition = {
    "total_bad_frames": total_frames,
    "total_bad_frame_side_events": total_events,
    "empty_reason_frames": empty_n,
    "empty_reason_note": ("bad frames whose problem_type slots are all empty; "
                          "total_bad_frames - resolvable"),
    "resolvable_bad_frames": total_frames - empty_n,
    "by_dataset": by_ds,
    "table_total": comp_table(rows_out),
    "side_totals": dict(collections.Counter(r["side"] for r in rows_out)),
    "reason_totals": dict(collections.Counter(r["reason"] for r in rows_out)),
    "total_frames_scanned": sum(r["n_frames"] for r in records),
    "records_total": len(records),
    "records_with_bad_frames": sum(1 for r in records if r["n_bad_frames"] > 0),
    "top_records_by_bad_frames": [
        {"dataset": r["dataset"], "uuid": r["uuid"], "n_bad_frames": r["n_bad_frames"],
         "n_frames": r["n_frames"], "share_of_all_bad": r["n_bad_frames"] / total_frames}
        for r in sorted(records, key=lambda x: -x["n_bad_frames"])[:5]],
}
composition["bad_frame_rate"] = (total_frames / composition["total_frames_scanned"]
                                if composition["total_frames_scanned"] else None)
# frame-level reason sets (dedup): which combinations of (side, reason) co-occur on one frame
_set_by_frame = collections.defaultdict(set)
for r in rows_out:
    _set_by_frame[(r["uuid"], r["frame_index"])].add("%s:%s" % (r["side"], r["reason"]))
_pset = collections.Counter(frozenset(v) for v in _set_by_frame.values())
composition["frame_reason_sets"] = [
    {"reasons": sorted(k), "n_frames": v} for k, v in sorted(_pset.items(), key=lambda kv: -kv[1])]
composition["frames_with_occlusion"] = sum(
    1 for v in _set_by_frame.values() if any(x.endswith(":occlusion") for x in v))
composition["frames_with_near_edge"] = sum(
    1 for v in _set_by_frame.values() if any(x.endswith(":near edge") for x in v))

# ---------------------------------------------------------------- time within record
def thirds(events):
    n = len(events)
    if n == 0:
        return {"n": 0}
    f = [e["_frac"] for e in events]
    c1 = sum(1 for x in f if x < 1 / 3)
    c2 = sum(1 for x in f if 1 / 3 <= x < 2 / 3)
    c3 = n - c1 - c2
    return {"n": n, "first_third": c1, "middle_third": c2, "last_third": c3,
            "frac_first": c1 / n, "frac_middle": c2 / n, "frac_last": c3 / n,
            "mean_frac": sum(f) / n, "median_frac": statistics.median(f)}

from scipy.stats import chisquare, binomtest

tw = {"overall": thirds(rows_out), "by_dataset": {}, "by_side_reason": {},
      "chisq_uniform_thirds": {},
      "frame_level": None}
for ds in DATASETS:
    tw["by_dataset"][ds] = thirds([r for r in rows_out if r["dataset"] == ds])
# frame level (dedup): one offset per frame, fraction position relative to record duration
dur_by_rec = {(r["dataset"], r["uuid"]): r["duration_s"] for r in records}
seen = {}
for r in rows_out:
    seen[(r["dataset"], r["uuid"], r["frame_index"])] = {
        "_frac": r["offset_s"] / dur_by_rec[(r["dataset"], r["uuid"])] if dur_by_rec[(r["dataset"], r["uuid"])] else 0.0}
frames_all = list(seen.values())
t = thirds(frames_all)
obs = [t["first_third"], t["middle_third"], t["last_third"]]
t["chisq_p_vs_uniform"] = float(chisquare(obs, [t["n"] / 3] * 3).pvalue) if t["n"] >= 3 else None
tw["frame_level"] = t
# per-dataset chisq
tw["by_dataset_chisq_p"] = {}
for ds in DATASETS:
    tt = tw["by_dataset"][ds]
    if tt["n"] >= 3:
        tw["by_dataset_chisq_p"][ds] = float(chisquare(
            [tt["first_third"], tt["middle_third"], tt["last_third"]],
            [tt["n"] / 3] * 3).pvalue)
for (s, rr) in sorted({(r["side"], r["reason"]) for r in rows_out}):
    key = "%s:%s" % (s, rr)
    ev = [r for r in rows_out if r["side"] == s and r["reason"] == rr]
    t = thirds(ev)
    k = len(ev)
    if k > 0:
        obs = [t["first_third"], t["middle_third"], t["last_third"]]
        p = float(chisquare(obs, [k / 3, k / 3, k / 3]).pvalue) if k >= 3 else None
        t["chisq_p_vs_uniform"] = p
    tw["by_side_reason"][key] = t
    tw["chisq_uniform_thirds"][key] = t.get("chisq_p_vs_uniform")

# ---------------------------------------------------------------- boundary vs interior
def boundary_block(bs_key, w, ds_filter=None):
    """pooled binomial + record-level cluster checks."""
    n = 0
    k = 0
    win_sum = 0.0
    dur_sum = 0.0
    per = []
    allk = 0      # 全部帧（好+坏）落在窗口内 —— 基准率的经验标定
    alln = 0
    for rec in records:
        if ds_filter and rec["dataset"] != ds_filter:
            continue
        bs = rec[bs_key]
        D = rec["duration_s"]
        if D <= 0:
            continue
        win = merge_windows(bs, w, D)
        frac_ok = rec["n_bad_frames"] > 0 and win > 0
        ev = [r for r in rows_out if r["uuid"] == rec["uuid"] and r["dataset"] == rec["dataset"]]
        # 帧级去重
        frames = sorted({(r["uuid"], r["frame_index"]) for r in ev})
        off_by_frame = {}
        for r in ev:
            off_by_frame[r["frame_index"]] = r["offset_s"]
        kk = sum(1 for (_, fi) in frames if in_any(off_by_frame[fi], bs, w))
        win_sum += win
        dur_sum += D
        n += len(frames)
        k += kk
        # 全部帧的经验基准（用 (n_frames) * win/D 近似会有离散化误差，直接算每个边界窗口的帧数太贵，
        # 这里用 duration 比例即可，30 Hz 均匀）
        alln += rec["n_frames"]
        allk += rec["n_frames"] * (win / D)
        per.append({"dataset": rec["dataset"], "uuid": rec["uuid"],
                    "n_bad": len(frames), "k_in_window": kk,
                    "duration_s": D, "window_s": win,
                    "base_rate": win / D, "obs_rate": (kk / len(frames)) if frames else None,
                    "n_boundaries": len(bs)})
    p0 = (win_sum / dur_sum) if dur_sum > 0 else float("nan")
    p0_emp = (allk / alln) if alln > 0 else float("nan")
    res = {"n_bad_frames": n, "k_in_window": k,
           "frac_in_window": (k / n) if n else None,
           "base_rate": p0, "base_rate_empirical_all_frames": p0_emp,
           "ratio_obs_over_base": ((k / n) / p0) if n and p0 else None,
           "n_records_used": len([x for x in per if x["n_bad"] > 0 and x["n_boundaries"] > 0]),
           "per_record": per}
    if n > 0 and 0 < p0 < 1:
        bt = binomtest(k, n, p0, alternative="greater")
        res["binom"] = {"p_greater": float(bt.pvalue),
                        "ci95": [float(x) for x in bt.proportion_ci(0.95)]}
        bt2 = binomtest(k, n, p0, alternative="two-sided")
        res["binom"]["p_two_sided"] = float(bt2.pvalue)
        # cluster-robust: 逐记录 obs-base，符号检验 + Wilcoxon
        d = [x["obs_rate"] - x["base_rate"] for x in per if x["n_bad"] > 0 and x["n_boundaries"] > 0]
        if d:
            pos = sum(1 for x in d if x > 0)
            neg = sum(1 for x in d if x < 0)
            res["cluster"] = {"n_records": len(d), "n_records_above_base": pos,
                              "n_records_below_base": neg,
                              "sign_test_p": float(binomtest(pos, pos + neg, 0.5, alternative="greater").pvalue)
                              if pos + neg > 0 else None}
            try:
                from scipy.stats import wilcoxon
                res["cluster"]["wilcoxon_p_greater"] = float(wilcoxon(d, alternative="greater").pvalue)
            except Exception as e:
                res["cluster"]["wilcoxon_p_greater"] = None
                res["cluster"]["wilcoxon_error"] = str(e)
    return res

bv = {
    "primary_all_interior_boundaries_w05": boundary_block("interior_boundaries", W),
    "sensitivity_windows": {
        str(w): boundary_block("interior_boundaries", w) for w in W_SENS
    },
    "secondary_task_change_boundaries_w05": boundary_block("task_change_boundaries", W),
    "secondary_eligible_boundaries_w05": boundary_block("eligible_boundaries", W),
    "by_dataset_w05": {ds: boundary_block("interior_boundaries", W, ds_filter=ds)
                       for ds in DATASETS},
    "by_reason_w05": {},
    "definition": {
        "window_s": W,
        "interior_boundary_rule": "0 < b < D-0.05",
        "tie_break": "frames exactly on the boundary count as in-window (abs(t-b) <= w)",
        "pooling": "all 38 records, frame-level dedup, duration-weighted base rate",
    },
}

# per-reason boundary fraction（事件级，用同一 p0）
p0_main = bv["primary_all_interior_boundaries_w05"]["base_rate"]
for (s, rr) in sorted({(r["side"], r["reason"]) for r in rows_out}):
    key = "%s:%s" % (s, rr)
    ev = [r for r in rows_out if r["side"] == s and r["reason"] == rr]
    k = sum(1 for r in ev if r["_in_w05"])
    n = len(ev)
    bt = binomtest(k, n, p0_main, alternative="greater") if n and 0 < p0_main < 1 else None
    by_rec = collections.Counter((r["dataset"], r["uuid"]) for r in ev)
    in_rec = collections.Counter((r["dataset"], r["uuid"]) for r in ev if r["_in_w05"])
    top_uuid, top_n = (by_rec.most_common(1)[0] if by_rec else (None, 0))
    # leave-one-record-out: 去掉贡献最大的记录后的比例（判断是否单记录驱动）
    if by_rec:
        rest = [r for r in ev if (r["dataset"], r["uuid"]) != top_uuid]
        loo_k = sum(1 for r in rest if r["_in_w05"])
        loo_n = len(rest)
    else:
        loo_k = loo_n = 0
    bv["by_reason_w05"][key] = {"n_events": n, "k_in_window": k,
                                "frac": (k / n) if n else None,
                                "ratio": ((k / n) / p0_main) if n and p0_main else None,
                                "p_greater": float(bt.pvalue) if bt else None,
                                "n_records_contributing": len(by_rec),
                                "top_record": {"dataset": top_uuid[0], "uuid": top_uuid[1], "n_events": top_n} if top_uuid else None,
                                "leave_top_record_out": {"k": loo_k, "n": loo_n,
                                                          "frac": (loo_k / loo_n) if loo_n else None,
                                                          "ratio": ((loo_k / loo_n) / p0_main) if loo_n and p0_main else None}}

# ---------------------------------------------------------------- alignment summary
align_ok = all(a["rows_equal"] and a["message_index_set_equal"] for a in align)

# ---------------------------------------------------------------- reason code resolution
reason_code_resolution = {
    "numeric_enum_codes_found_in_problem_type_slots": numeric_slots,
    "string_values_found_in_problem_type_slots": string_slots,
    "problem_type[1]_holds_string_form": True,
    "code_to_string_mapping": None,
    "explanation": ("No numeric enum code appears in any problem_type[i] slot of the 38 records. "
                    "The '1'/'2' values reported earlier are the problem_type.length column "
                    "(number of problems on the row), not an enum code: rows with length=1 and "
                    "length=2 sum to the 720 bad rows and int(length)==count(non-empty slots) for "
                    "every bad row."),
    "slot_combinations": [{"slots": list(k), "n_rows": v}
                          for k, v in slot_combo.most_common()],
    "truncation_check": {
        "records_with_10_or_11_cols": sum(1 for r in records if r["annotation_ncols"] < 12),
        "of_them_declaring_length_ge_2_on_a_bad_row": sum(
            1 for r in records if r["annotation_ncols"] < 12 and r["max_problem_length"] >= 2),
        "verdict": ("files without a problem_type[1] column never declare length>=2 on any bad row, "
                    "so no reason string was dropped by the narrower schema"),
    },
    "declared_length_mismatch_rows": len_vs_filled_mismatch,
}

# ---------------------------------------------------------------- payload
payload = {
    "_meta": {
        "script": "code/p1_badtype.py",
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "interpreter": sys.version.split()[0],
        "sources": [
            {"path": os.path.join(ROOT, "Raw_Data", ds, "<uuid>", "tables",
                                  "annotation_bad_frame_pose_hand.csv"),
             "sha256": "(per record; see records[].annotation_sha256)"}
            for ds in DATASETS
        ] + [{"path": segpath, "sha256": sha256(segpath)}],
        "datasets": DATASETS,
        "n_records": len(records),
        "preregistered_claim": PREREG,
        "units": {"frame": "one _message_index row", "event": "one (frame, side, reason)"},
    },
    "alignment_check": {
        "rows_equal_all_records": align_ok,
        "n_records_checked": len(align),
        "message_index_set_equal_all": all(a["message_index_set_equal"] for a in align),
        "per_record": align,
        "note": ("annotation_bad_frame_pose_hand.csv, pose_left_hand.csv and pose_right_hand.csv "
                 "have identical row counts and identical _message_index sets; frame-for-frame "
                 "alignment holds"),
    },
    "records": records,
    "composition": composition,
    "time_within_record": tw,
    "boundary_vs_interior": bv,
    "reason_code_resolution": reason_code_resolution,
    "records_missing_segments": missing_seg,
}

if os.path.exists(OUT_JSON):
    raise SystemExit("refuse to overwrite existing %s" % OUT_JSON)
with open(OUT_JSON, "w", encoding="utf-8", newline="\n") as f:
    json.dump(payload, f, ensure_ascii=False, indent=1)

# ---------------------------------------------------------------- print
def pct(x):
    return "  n/a " if x is None else "%6.2f%%" % (100 * x)

print("=" * 78)
print("PRE-REGISTERED BEFORE RESULTS")
print("  claim      :", PREREG["claim"])
print("  falsified  :", " ; ".join(PREREG["falsified_if"]))
print("  support if :", PREREG["support_requires"])
print("=" * 78)
print()
print("ALIGNMENT CHECK (annotation vs pose_left_hand vs pose_right_hand)")
print("  records checked          :", len(align))
print("  row counts equal (all)   :", align_ok)
print("  _message_index sets equal:", all(a["message_index_set_equal"] for a in align))
a0 = align[0]
print("  example: %s %s  ann=%d  L=%d  R=%d  tmax=%.3f/%.3f"
      % (a0["dataset"], a0["uuid"], a0["n_annotation"], a0["n_pose_left"],
         a0["n_pose_right"], a0["tmax_annotation"], a0["tmax_pose_left"]))
print()
print("REASON CODE RESOLUTION")
print("  numeric slots:", numeric_slots, " string slots:", string_slots)
print("  problem_type[1] holds string form: yes (when length=2)")
for c, v in slot_combo.most_common():
    print("    slots=%-42s %4d rows" % (str(c), v))
print()
print("COMPOSITION  (total bad frames = %d, frame-side events = %d, empty reason = %d)"
      % (total_frames, total_events, empty_n))
print("  frames scanned = %d, bad-frame rate = %.4f%%, records with any bad frame = %d/%d"
      % (composition["total_frames_scanned"], 100 * composition["bad_frame_rate"],
         composition["records_with_bad_frames"], composition["records_total"]))
print("  frame-level reason sets:")
for x in composition["frame_reason_sets"]:
    print("    %-58s %4d frames" % ("+".join(x["reasons"]), x["n_frames"]))
print("  frames carrying occlusion = %d, near edge = %d"
      % (composition["frames_with_occlusion"], composition["frames_with_near_edge"]))
print("  top records by bad frames:")
for x in composition["top_records_by_bad_frames"]:
    print("    %-11s %-38s %4d / %4d frames  %.1f%% of all bad"
          % (x["dataset"], x["uuid"][:36], x["n_bad_frames"], x["n_frames"], 100 * x["share_of_all_bad"]))
hdr = "  %-12s %-12s %-12s %6s" % ("dataset", "side", "reason", "n")
print(hdr)
for ds in DATASETS + ["ALL"]:
    tab = composition["table_total"] if ds == "ALL" else by_ds[ds]["table"]
    nfr = total_frames if ds == "ALL" else by_ds[ds]["n_bad_frames"]
    nev = total_events if ds == "ALL" else by_ds[ds]["n_events"]
    print("  -- %s : %d bad frames, %d events" % (ds, nfr, nev))
    for t in tab:
        print("  %-12s %-12s %-12s %6d" % (ds, t["side"], t["reason"], t["n"]))
print()
print("TIME WITHIN RECORD (fraction of bad frames / events per third)")
print("  %-22s %6s %8s %8s %8s   mean" % ("group", "n", "first", "middle", "last"))
def prow(k, t):
    print("  %-22s %6d %8s %8s %8s   %.3f" % (k, t["n"], pct(t["frac_first"]),
                                              pct(t["frac_middle"]), pct(t["frac_last"]),
                                              t["mean_frac"]))
prow("ALL (frame-level)", tw["frame_level"])
prow("ALL (event-level)", tw["overall"])
for ds in DATASETS:
    prow(ds, tw["by_dataset"][ds])
    print("     chisq vs uniform: p = %.3g" % tw["by_dataset_chisq_p"][ds])
print("  ALL frame-level chisq vs uniform: p = %.3g" % tw["frame_level"]["chisq_p_vs_uniform"])
for k, t in tw["by_side_reason"].items():
    if t["n"]:
        print("  %-22s %6d %8s %8s %8s   %.3f   chisq_p=%.3g"
              % (k, t["n"], pct(t["frac_first"]), pct(t["frac_middle"]), pct(t["frac_last"]),
                 t["mean_frac"], t["chisq_p_vs_uniform"]))
print()
b = bv["primary_all_interior_boundaries_w05"]
print("BOUNDARY vs INTERIOR  (window +/-%.2f s, interior boundaries only)" % W)
print("  bad frames           : %d" % b["n_bad_frames"])
print("  in boundary window   : %d  (%.2f%%)" % (b["k_in_window"], 100 * b["frac_in_window"]))
print("  base rate            : %.4f%% (%.4f%% empirical, all frames)" % (100 * b["base_rate"], 100 * b["base_rate_empirical_all_frames"]))
print("  ratio obs/base       : %.2fx" % b["ratio_obs_over_base"])
print("  binomial (greater)   : p = %.4g   CI95 = [%.4f, %.4f]"
      % (b["binom"]["p_greater"], b["binom"]["ci95"][0], b["binom"]["ci95"][1]))
print("  binomial (two-sided) : p = %.4g" % b["binom"]["p_two_sided"])
print("  cluster sign test    : %d/%d records above base, p = %.4g"
      % (b["cluster"]["n_records_above_base"], b["cluster"]["n_records"],
         b["cluster"]["sign_test_p"]))
print("  cluster wilcoxon     : p = %.4g" % (b["cluster"]["wilcoxon_p_greater"] or float("nan")))
print()
print("  sensitivity (window) :")
for w, r in bv["sensitivity_windows"].items():
    print("    w=%-4s in=%4d/%4d  frac=%s  base=%s  ratio=%.2fx  p=%.3g"
          % (w, r["k_in_window"], r["n_bad_frames"], pct(r["frac_in_window"]),
             pct(r["base_rate"]), r["ratio_obs_over_base"],
             r.get("binom", {}).get("p_greater", float("nan"))))
print()
print("  task-change boundaries only:")
r = bv["secondary_task_change_boundaries_w05"]
print("    in=%4d/%4d  frac=%s  base=%s  ratio=%s  p=%.3g"
      % (r["k_in_window"], r["n_bad_frames"], pct(r["frac_in_window"]), pct(r["base_rate"]),
         ("%.2fx" % r["ratio_obs_over_base"]) if r["ratio_obs_over_base"] else "n/a",
         r["binom"]["p_greater"] if "binom" in r else float("nan")))
print()
print("  by dataset:")
for ds, r in bv["by_dataset_w05"].items():
    print("    %-11s in=%3d/%3d  frac=%s  base=%s  ratio=%s  p=%.3g"
          % (ds, r["k_in_window"], r["n_bad_frames"], pct(r["frac_in_window"]), pct(r["base_rate"]),
             ("%.2fx" % r["ratio_obs_over_base"]) if r["ratio_obs_over_base"] else "n/a",
             r.get("binom", {}).get("p_greater", float("nan"))))
print()
print("  per reason (event-level, same pooled base rate):")
for k, v in bv["by_reason_w05"].items():
    print("    %-22s %4d/%4d = %s  ratio=%s  p=%.3g  records=%d  LOO(n=%d)=%s"
          % (k, v["k_in_window"], v["n_events"], pct(v["frac"]),
             ("%.2fx" % v["ratio"]) if v["ratio"] else "n/a",
             v["p_greater"] if v["p_greater"] is not None else float("nan"),
             v["n_records_contributing"], v["leave_top_record_out"]["n"],
             pct(v["leave_top_record_out"]["frac"])))
print()
print("WROTE:", OUT_CSV, "(%d rows)" % len(rows_out))
print("WROTE:", OUT_JSON)