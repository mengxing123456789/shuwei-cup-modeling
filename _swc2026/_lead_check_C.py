# -*- coding: utf-8 -*-
"""Lead 独立复核 C 题 P3：容量上界与可行性（不看 mm-c 的结论先算一遍）。

核心问题：在 common_conditions.json 的口径下，每个 case 的总工作量 vs horizon 是什么比例？
若总工作量远超 horizon，则 weighted_completion_rate 存在结构性上界 —— 这是 P3 的难点所在，
也是判断「η≥0.5 门槛是否有意义」的关键。
"""
import json
import numpy as np
import pandas as pd

D = (r"C:\Users\29900\Downloads\AsterLink\C_Problem_Data\C_Problem_Data"
     r"\Restocking_Problem_and_Data_EN\Restocking_Problem_and_Data_EN\Restocking_Tasks_and_Constraints")
OUT = r"E:\数学建模\_swc2026\_lead_check_C.json"

cc = json.load(open(D + r"\common_conditions.json", encoding="utf-8"))
tasks = pd.read_csv(D + r"\tasks.csv")
zones = pd.read_csv(D + r"\service_zones.csv")
seg = pd.read_csv(D + r"\source_segment_index.csv")
fam = pd.read_csv(D + r"\job_families.csv")

rep = {"protocol_version": cc["version"], "n_units": int(len(seg)),
       "n_eligible": int((seg.eligible == 1).sum()), "n_tasks": int(len(tasks))}

# --- 源片段时长的分布（按 family / split）---
rep["duration_by_family"] = {}
for f, g in seg[seg.eligible == 1].groupby("family_id"):
    d = g.duration_s.values
    rep["duration_by_family"][f] = {
        "n": int(len(d)), "mean": round(float(d.mean()), 2), "sd": round(float(d.std()), 2),
        "min": round(float(d.min()), 2), "p50": round(float(np.percentile(d, 50)), 2),
        "p90": round(float(np.percentile(d, 90)), 2), "max": round(float(d.max()), 2)}
rep["duration_by_split"] = {s: {"n": int(len(g)), "mean": round(float(g.duration_s.mean()), 2)}
                            for s, g in seg[seg.eligible == 1].groupby("split")}
rep["excluded"] = seg[seg.eligible != 1].exclusion_reason.fillna("NA").value_counts().to_dict()

# --- 每个 case：总工作量（服务 = α·d_f + β）+ 位置坐标 → 下界行程 ---
alpha, beta = cc["service"]["alpha"], cc["service"]["beta_s"]
speed, chg = cc["movement"]["speed"], cc["movement"]["changeover_s"]
zmap = {r.zone_id: (float(r.x), float(r.y)) for r in zones.itertuples()}
mean_d = {f: float(g.duration_s.mean()) for f, g in seg[seg.eligible == 1].groupby("family_id")}

def dist(a, b):
    return ((zmap[a][0] - zmap[b][0]) ** 2 + (zmap[a][1] - zmap[b][1]) ** 2) ** 0.5

rep["cases"] = {}
for case, case_tasks in tasks.groupby("case_id"):
    cfg = next(c for c in cc["cases"] if c["case_id"] == case)
    work = [(alpha * mean_d[r.family_id] + beta) for r in case_tasks.itertuples()]
    # 行程下界：从 Z0 出发，最近邻访问所有任务所在 zone（下界，不含跨 zone 的重复往返）
    remaining = list(case_tasks.zone_id)
    cur, trav, order = "Z0", 0.0, []
    while remaining:
        nxt = min(remaining, key=lambda z: dist(cur, z))
        trav += dist(cur, nxt) / speed + chg
        order.append(nxt)
        remaining.remove(nxt)
        cur = nxt
    total = sum(work) + trav
    rep["cases"][case] = {
        "jobs": int(len(case_tasks)), "horizon_s": cfg["horizon_s"],
        "budget": cfg["cost_budget"], "obs_limit": cfg["observation_limit"],
        "mean_service_s": round(float(np.mean(work)), 2),
        "sum_service_s": round(float(np.sum(work)), 1),
        "travel_lb_s": round(float(trav), 2),
        "total_lb_s": round(float(total), 1),
        "capacity_ratio": round(float(total / cfg["horizon_s"]), 3),
        "max_jobs_by_work": int(np.floor(cfg["horizon_s"] / np.mean(work))),
        "upper_bound_completion_rate": round(float(min(1.0, cfg["horizon_s"] / total)), 3),
        "nn_visit_order": order,
    }

# --- 观测（review）的预算约束是否真正绑定 ---
rep["review_budget"] = {}
for case, cfg in [(c["case_id"], c) for c in cc["cases"]]:
    n_obs_max = cfg["observation_limit"]
    cost_full = n_obs_max * cc["observation"]["cost"]
    rep["review_budget"][case] = {
        "obs_limit": n_obs_max, "cost_if_all_used": cost_full, "budget": cfg["cost_budget"],
        "service_fixed_total": round(2.0 * cfg["jobs"], 1),
        "budget_minus_service": round(cfg["cost_budget"] - 2.0 * cfg["jobs"], 1),
    }

# --- 截止期是否紧迫：due - release vs 平均服务时长 ---
rep["slack"] = {}
for case, g in tasks.groupby("case_id"):
    slack = (g.due_s - g.release_s).values
    rep["slack"][case] = {"mean_window_s": round(float(slack.mean()), 2),
                          "min_window_s": round(float(slack.min()), 2),
                          "jobs_with_window_lt_work": int((slack < 8 * np.mean(list(mean_d.values()))).sum())}

json.dump(rep, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(rep, ensure_ascii=False, indent=1))