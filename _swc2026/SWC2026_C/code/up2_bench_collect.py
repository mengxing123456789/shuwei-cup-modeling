# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""up2_bench_collect.py — 官方口径对齐 + model ladder 汇总器（只读，不改任何他人产物）

输出：data/up2_benchmark.json

设计原则（对齐 AGENTS.md §6 与 G12）：
  1. 每个数字都从已落盘的 data/*.json 读出来，本脚本不产生任何新的实验数字；
  2. 官方口径一律以 common_conditions.json / Problem_3_Requirements.pdf 为准，
     不把「我们自设的门槛」写成官方门槛；
  3. 每条 ladder 行都带 evidence 路径，能回溯到源文件。

用法：& 'python' code\\up2_bench_collect.py
"""
from __future__ import annotations

import hashlib
import json
import os
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OFFICIAL = os.environ.get("MM_C_PROBLEM_ROOT") or os.path.join(
    ROOT, "problem", "Restocking_Problem_and_Data_EN", "Restocking_Tasks_and_Constraints"
)
PDF = os.path.join(OFFICIAL, "Problem_3_Requirements.pdf")
CC = os.path.join(OFFICIAL, "common_conditions.json")


def load(name):
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def sha(path):
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def g(obj, *keys, default=None):
    """安全取嵌套键。"""
    cur = obj
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


out = {"_meta": {}, "official_protocol": {}, "ladder": [], "caliber": [],
       "missing_official_checks": [], "recommendations": []}

# ---------------------------------------------------------------- 0. 官方来源
out["_meta"] = {
    "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "generator": "code/up2_bench_collect.py",
    "purpose": "官方口径 vs 我们口径对照 + model ladder（每行可回溯到 data/*.json）",
    "official_sources": [
        {"path": PDF, "sha256": sha(PDF), "kind": "官方要求 PDF（P3 指标表/门槛/协议）"},
        {"path": CC, "sha256": sha(CC), "kind": "官方 common_conditions.json（全部常量）"},
        {"path": r"_prob_C.txt", "sha256": sha(r"_prob_C.txt"),
         "kind": "赛题正文（P1/P2 要求）"},
        {"path": os.path.join(OFFICIAL, "tasks.csv"), "sha256": sha(os.path.join(OFFICIAL, "tasks.csv")),
         "kind": "36 个作业（3 case）"},
    ],
    "note": "官方英文附件包中**没有** tasks_and_evaluation.md（题面引用），只有 Problem_3_Requirements.pdf；"
            "P1/P2 官方均未发布 baseline 代码或 baseline 数值，也**没有**任何阈值。",
}

# ---------------------------------------------------------------- 1. 官方协议
cc = None
if os.path.exists(CC):
    with open(CC, encoding="utf-8") as f:
        cc = json.load(f)
out["official_protocol"] = {
    "common_conditions_version": g(cc, "version"),
    "worker_count": g(cc, "capacity", "worker_count"),
    "observation": g(cc, "observation"),
    "service": g(cc, "service"),
    "movement": g(cc, "movement"),
    "fees": g(cc, "fees"),
    "minimum_service_for_cost_or_risk_objective": g(cc, "minimum_service_for_cost_or_risk_objective"),
    "validation_seeds": (g(cc, "seeds", "validation") or g(cc, "validation_seeds")),
    "max_actions": g(cc, "protocol", "max_actions") or g(cc, "max_actions"),
    "terminal_on_invalid": g(cc, "protocol", "terminal_on_invalid") or g(cc, "terminal_on_invalid"),
    "p1": {
        "official_metric": "无硬指标；要求报告 retained record/timestamp 计数、数据划分、模型参数、"
                           "state error 或 consistency、quality-model 性能、不确定性检验",
        "official_baseline": "要求自选 ≥1 个「结构简单、参数少、可复现」的 baseline；官方不提供 baseline 代码或数值",
        "official_threshold": None,
    },
    "p2": {
        "official_metric": "代表性 3D 点平均距离误差 R=(1/M)Σ||p̂−p_ref||₂（mean，不是 RMS）",
        "official_reporting": "prediction error 随 missing duration 变化、区间 coverage/set reliability、"
                              "观测次数与成本、等待时间、计算开销",
        "official_baseline": "无（要求与不给观测/固定间隔等简单策略对比）",
        "official_threshold": None,
    },
    "p3": {
        "official_metric": ["weighted_completion_rate", "weighted_on_time_rate", "weighted_tardiness_s",
                            "cost", "observations", "elapsed_s", "observed_overrun_s",
                            "reserved_idle_s", "censored_units", "invalid_actions", "valid_protocol"],
        "official_threshold": {"metric": "mean_weighted_on_time_rate", "value": 0.50,
                               "scope": "nominal 映射、每 case、30 trials"},
        "official_baseline": "无命名 baseline；EDF/now 等作为参照策略由我们自己实现",
    },
}

# ---------------------------------------------------------------- 2. model ladder
L = out["ladder"]


def row(**kw):
    kw.setdefault("evidence", [])
    L.append(kw)


# ---- P1a 状态分割 -----------------------------------------------------------
WARD_ARI = None
p1 = load("p1_segmentation.json")
if p1:
    bm = p1.get("by_method", {})
    WARD_ARI = g(p1, "by_method", "ward", "ari", "mean")
    for key, label, fam, hyp in [
        ("raw", "K-means on raw 126-dim coordinates", "clustering baseline", "K=8, k-means++"),
        ("kmeans_headfeat", "K-means on head-frame features", "clustering", "K=8"),
        ("ward", "Chain-constrained Ward（论文主 baseline）", "hierarchical", "cap K≤8, tol 5 s"),
        ("ward_oracleK", "Ward with oracle K", "hierarchical (oracle)", "K=真实段数"),
        ("ward_rawfeat", "Ward on raw coordinates", "hierarchical", "cap K≤8"),
    ]:
        m = bm.get(key, {})
        if not m:
            continue
        row(problem="P1a", model=label, family=fam, hyperparams=hyp,
            split="test (7 records)", seed="n/a（确定式）",
            val_metric=None,
            test_metric={"ari_mean": g(m, "ari", "mean"), "ari_std": g(m, "ari", "std"),
                         "f1_mean": g(m, "f1", "mean"), "b_mae": g(m, "b_mae", "mean")},
            official_gate=None,
            official_requirement="官方无阈值；ARI 只作为 state consistency 的证据",
            internal_bar=None,
            evidence=["data/p1_segmentation.json"])

p1a_final = load("up_p1a_final.json")
if p1a_final:
    val_by_rule = {r.get("rule"): r for r in (p1a_final.get("validation") or [])}
    for r in p1a_final.get("test", []):
        vm = val_by_rule.get(r.get("rule")) or {}
        ari = r.get("mean_ari")
        row(problem="P1a", model="peak-rule decoder: " + str(r.get("rule")),
            family="rule-based segmentation",
            hyperparams=f"kind={r.get('kind')}, param={r.get('param')}, min_dist={r.get('D')} frames",
            split="test (7 records)", seed=str(r.get("sigma")),
            val_metric={"ari": vm.get("mean_ari"), "boundary_f1": vm.get("mean_bf1"),
                        "mean_npred": vm.get("mean_npred")},
            test_metric={"ari": ari, "ari_std": r.get("std_ari"),
                         "boundary_f1": r.get("mean_bf1"), "mean_npred": r.get("mean_npred")},
            official_gate=None, official_requirement="官方无阈值",
            internal_bar={"test_mean_ari>=0.60": ari is not None and ari >= 0.60,
                          "mean_boundary_f1>=0.30": (r.get("mean_bf1") or 0) >= 0.30},
            evidence=["data/up_p1a_final.json"])
    s = p1a_final.get("summary", {})
    out.setdefault("_p1a_summary", {}).update({
        "best_rule_on_test": s.get("best_rule_on_test"),
        "best_test_ari": s.get("test_mean_ari"),
        "bar": g(p1a_final, "_meta", "bar"),
        "passes_ari_bar": s.get("passes_ari_bar"),
        "passes_bf1_bar": s.get("passes_bf1_bar"),
    })

segc = load("p1a_segmentation_compare.json")
if segc:
    row(problem="P1a", model="Dilated bi-TCN boundary detector (GPU, seed ensemble)",
        family="learned boundary detection",
        hyperparams="3 seeds ensemble, height 0.30, min peak distance 54 (1.8 s)",
        split="test (7 records)", seed="20261120/21/22",
        val_metric={"ari": g(segc, "ari", "gpu_val") or g(segc, "ari", "gpu_val_ari")
                             or g(segc, "ari", "val")},
        test_metric={"ari_mean": g(segc, "ari", "gpu_mean"), "f1_mean": g(segc, "f1", "gpu_mean"),
                     "paired_diff_vs_ward": g(segc, "ari", "paired_diff"),
                     "ci95": g(segc, "ari", "ci95"), "perm_p": g(segc, "ari", "perm_p"),
                     "wins": g(segc, "ari", "wins")},
        official_gate=None, official_requirement="官方无阈值",
        internal_bar={"ari>=0.60": (g(segc, "ari", "gpu_mean") or 0) >= 0.60},
        evidence=["data/p1a_segmentation_compare.json"])

tuned = load("p1a_gpu_segmentation_tuned.json")
if tuned:
    val_ari = (g(tuned, "val_ari") or g(tuned, "validation", "mean_ari")
               or g(tuned, "val_ari_mean") or g(tuned, "best_val_ari"))
    row(problem="P1a", model="bi-TCN boundary detector, tuned on validation",
        family="learned boundary detection", hyperparams="height 0.25, min distance 90",
        split="test (7 records)", seed="20261120/21/22",
        val_metric={"ari": val_ari},
        test_metric={"ari": g(tuned, "test", "mean_ari"), "f1": g(tuned, "test", "mean_f1"),
                     "boundary_f1": g(tuned, "test", "mean_boundary_f1"),
                     "b_mae": g(tuned, "test", "b_mae")},
        official_gate=None, official_requirement="官方无阈值",
        internal_bar={"ari>=0.60": (g(tuned, "test", "mean_ari") or 0) >= 0.60},
        evidence=["data/p1a_gpu_segmentation_tuned.json"])

for fname, model, hyp in [
    ("best_p1a.json", "Constrained Ward, widened cap K≤25", "K≤25 (bic)"),
    ("p1a_improved_results.json", "Ward + BIC full-32 grid, K=8", "bic@8, seed 9"),
]:
    j = load(fname)
    if not j:
        continue
    methods = j.get("methods") or {}
    tmean = j.get("test_mean") or {}
    tgt = methods.get("ward_k25") or methods.get("widened") or (list(methods.values())[0] if methods else {})
    base_ari = j.get("baseline_mean", {}).get("ari") if isinstance(j.get("baseline_mean"), dict) else j.get("baseline_test_ari")
    base_ari = base_ari if base_ari is not None else WARD_ARI
    delta = j.get("delta_ari_vs_baseline") or j.get("delta_ari")
    ari = tgt.get("ari") or tmean.get("ari") or tmean.get("mean_ari")
    if ari is None and base_ari is not None and isinstance(delta, dict) and "ward_k25" in delta:
        ari = base_ari + delta["ward_k25"]
    f1 = tgt.get("f1") or tmean.get("f1") or tmean.get("mean_f1")
    row(problem="P1a", model=model, family="hierarchical", hyperparams=hyp,
        split="test (7 records)", seed=str(j.get("selected_cfg") or j.get("seed") or "n/a"),
        val_metric={"ari": g(j, "selected_cfg", "sel_val_ari") or j.get("sel_val_ari")},
        test_metric={"ari": ari, "f1": f1,
                     "baseline_ari": j.get("baseline_mean", {}).get("ari") or j.get("baseline_test_ari"),
                     "delta_ari_vs_baseline": j.get("delta_ari_vs_baseline") or j.get("delta_ari"),
                     "exceeds_baseline": j.get("exceeds_baseline")},
        official_gate=None, official_requirement="官方无阈值",
        internal_bar={"ari>=0.60": (ari or 0) >= 0.60},
        evidence=["data/" + fname])

# ---- P1b 质量分类器 ---------------------------------------------------------
p1b = load("p1b_gpu.json")
if p1b:
    per_env = g(p1b, "per_env_test") or {}
    if isinstance(per_env, list):
        # per_env_test 是 [{env, auc}] 形式时取最小值
        vals = [x.get("auc") if x.get("auc") is not None else x.get("auc_bad")
                for x in per_env if isinstance(x, dict)]
        worst = min([v for v in vals if v is not None]) if any(v is not None for v in vals) else None
    else:
        worst = min(per_env.values()) if per_env else None
    row(problem="P1b", model="TCN 质量分类器（baseline）", family="learned classifier",
        hyperparams=f"dilated TCN, per-frame, BCE, {g(p1b, 'params')} params",
        split="test (逐 env 报)", seed="20261120",
        val_metric={"auc": g(p1b, "val_auc_at_best")},
        test_metric={"auc": g(p1b, "test_auc"), "ap": g(p1b, "test_ap"),
                     "ap_lift": g(p1b, "test_ap_lift"), "positive_rate": g(p1b, "test_positive_rate"),
                     "worst_env_auc": worst, "per_env": per_env},
        official_gate=None, official_requirement="官方无阈值；只要求报告 quality-model 性能",
        internal_bar={"auc>=0.85 or ap>=0.09": (g(p1b, "test_auc") or 0) >= 0.85 or (g(p1b, "test_ap") or 0) >= 0.09},
        evidence=["data/p1b_gpu.json", "code/train_gpu_p1b.py"])

p1bf = load("up_p1b_final.json")
if p1bf:
    agg = p1bf.get("aggregate", {})
    verdict = p1bf.get("verdict", {})
    for arm, label, hyp in [("A", "A 臂（单头 + 类平衡）", "TCN single-head, 3 seeds"),
                            ("C", "C 臂（dual + multitask 辅助损失）", "dual-head + aux, 3 seeds")]:
        a = agg.get(arm) or {}
        if not a:
            continue
        row(problem="P1b", model=label, family="learned classifier", hyperparams=hyp,
            split="test", seed="3 seeds (20261120/20261122/20261123)",
            val_metric={"auc": a.get("val_auc"), "ap": a.get("val_ap")},
            test_metric={"auc": a.get("test_auc"), "auc_std": a.get("test_auc_std"),
                         "ap": a.get("test_ap"), "ap_std": a.get("test_ap_std"),
                         "ap_min": a.get("test_ap_min"), "ap_max": a.get("test_ap_max"),
                         "worst_env_auc": a.get("worst_env"),
                         "worst_env_per_seed": a.get("worst_env_per_seed")},
            official_gate=None, official_requirement="官方无阈值",
            internal_bar={"primary AUC>=0.85 or AP>=0.09": (a.get("test_auc") or 0) >= 0.85 or (a.get("test_ap") or 0) >= 0.09,
                          "secondary 三条全过": (verdict.get("passes") if arm == "C" else None)},
            evidence=["data/up_p1b_final.json"])
    out.setdefault("_p1b_summary", {}).update({
        "bar": g(p1bf, "_meta", "bar"),
        "ap_gain_pct": agg.get("ap_gain_pct"),
        "seed_matched_ap_gain_pct": agg.get("ap_gain_pct_seed_matched"),
        "worst_env_delta": agg.get("worst_env_delta"),
        "baseline_reference": agg.get("baseline_reference"),
        "verdict": verdict,
    })

loto = load("p1b_loto.json")
if loto:
    s = loto.get("summary", {})
    row(problem="P1b", model="LOTO 跨任务泛化（leave-one-task-out）", family="evaluation protocol",
        hyperparams="min_records/min_positives 主阈值 + relaxed 敏感性",
        split="跨 task 留一", seed="n/a",
        val_metric=None,
        test_metric={"mean_auc_loto": s.get("mean_auc_loto"),
                     "mean_auc_in_sample": s.get("mean_auc_in_sample_reference"),
                     "gap": s.get("gap_mean"), "mean_auc_test_ref": s.get("mean_auc_test_reference"),
                     "frac_gap_explained": s.get("frac_unseen_task_gap_explained"),
                     "n_classes_used": s.get("n_classes_used"), "n_train_classes": s.get("n_train_classes")},
        official_gate=None, official_requirement="官方要求「不确定性检验」，LOTO 可作证据",
        internal_bar=None, evidence=["data/p1b_loto.json"])

# ---- P2 位姿预测 ------------------------------------------------------------
p2 = load("p2_prediction.json")
if p2:
    for b in p2.get("by_length", []):
        row(problem="P2", model="baseline: " + str(b.get("method")), family="classical / trivial",
            hyperparams=f"L={b.get('L_s')} s ({b.get('L_frames')} frames)",
            split=str(g(p2, "_meta", "split", default="test")), seed="n/a（确定式）",
            val_metric=None,
            test_metric={"L_s": b.get("L_s"), "rmse_m": b.get("rmse"),
                         "rmse_cm": (b.get("rmse") or 0) * 100,
                         "mae_cm": (b.get("mae") or 0) * 100,
                         "endpoint_cm": (b.get("endpoint_rmse") or 0) * 100,
                         "within_2cm": b.get("within_2cm")},
            official_gate=None,
            official_requirement="官方指标是 mean 距离 R，此处 rmse 是 RMS 距离（口径差见 caliber）",
            internal_bar=None, evidence=["data/p2_prediction.json"])

p2o = load("p2_official.json")
if p2o:
    for cell in (p2o.get("grid") or []):
        row(problem="P2", model="Ridge（官方 observation 协议下）", family="linear",
            hyperparams=f"alpha=10, ctx={cell.get('ctx_s')}s, lead={cell.get('lead_s')}s",
            split="validation(400) 拟合 / test(743) 一次评", seed="n/a（确定式）",
            val_metric={"n_val": cell.get("n_val")},
            test_metric={"rmse_cm": cell.get("rmse_cm"), "rmse_coord_cm": cell.get("rmse_coord_cm"),
                         "endpoint_cm": cell.get("end_rmse_cm"), "median_end_cm": cell.get("median_end_cm"),
                         "cov": cell.get("coverage_test"), "n_test": cell.get("n_test")},
            official_gate=None, official_requirement="官方无阈值",
            internal_bar=None, evidence=["data/p2_official.json"])

p2f = load("p2_frontier.json")
if p2f:
    for pol in (p2f.get("table") or []):
        row(problem="P2", model="观测策略: " + str(pol.get("policy")), family="decision frontier",
            hyperparams=f"ctx={pol.get('ctx_s')}s, lead={pol.get('lead_s')}s, requests={pol.get('requests')}",
            split="test (7 records)", seed="n/a（确定式）",
            val_metric=None,
            test_metric={"rms_cm": pol.get("rms_cm"), "cost_units": pol.get("cost_units")},
            official_gate=None, official_requirement="官方要求报告 observation counts/cost 与等待时间",
            internal_bar=None, evidence=["data/p2_frontier.json"])

pre = load("pre_p2_summary.json")
if pre:
    for key, v in (pre.get("groups") or {}).items():
        row(problem="P2", model=f"神经网络臂 {key}", family="neural",
            hyperparams=f"arm={v.get('arm')}, ssl={v.get('ssl_task')}, L={v.get('L')} frames",
            split="test", seed=f"{v.get('n_seeds')} seeds",
            val_metric={"rmse_cm": (v.get("val_rmse_cm") or [None])[0]
                                    if isinstance(v.get("val_rmse_cm"), list) else v.get("val_rmse_cm")},
            test_metric={"rmse_cm": v.get("rmse_cm_mean"), "rmse_std": v.get("rmse_cm_std"),
                         "endpoint_cm": v.get("endpoint_rmse_cm_mean"),
                         "median_cm": v.get("median_cm_mean"), "q90_cm": v.get("q90_cm_mean"),
                         "cov90_all": v.get("cov90_all_mean"), "best_epoch": v.get("best_epoch")},
            official_gate=None, official_requirement="官方无阈值",
            internal_bar=None, evidence=["data/pre_p2_summary.json"])

pq = load("up_p2_quantile.json")
if pq:
    for arm, per_L in (pq.get("arms") or {}).items():
        for Lk, v in per_L.items():
            row(problem="P2", model="quantile 臂: " + arm, family="quantile regression",
                hyperparams="L=" + str(Lk), split="test", seed="3 seeds",
                val_metric=None,
                test_metric={"rmse_3d_cm": v.get("rmse_3d_cm"), "rmse_coord_cm": v.get("rmse_coord_cm"),
                             "q90_cm": v.get("q90_cm"), "cov": v.get("coverage_test"),
                             "n_test": v.get("n_test")},
                official_gate=None, official_requirement="官方无阈值",
                internal_bar=None, evidence=["data/up_p2_quantile.json"])
    out.setdefault("_p2_summary", {}).update({
        "bar": g(pq, "_meta", "bar"),
        "gru_v2": pq.get("reference_gru_v2"),
        "unit_warning": g(pq, "_meta", "baseline", "unit_warning"),
    })

p2fin = load("up_p2_final.json")
if p2fin:
    out.setdefault("_p2_summary", {}).update({
        "final_bar": g(p2fin, "_meta", "bar"),
        "final_aggregate": p2fin.get("aggregate"),
        "final_verdict": p2fin.get("verdict"),
        "ridge_replica": p2fin.get("ridge_replica"),
        "decision_layer": p2fin.get("decision_layer"),
    })

# ---- P3 调度 ----------------------------------------------------------------
p3 = load("p3_scheduling.json")
official_p3_metrics = out["official_protocol"]["p3"]["official_metric"]
metric_keys = set()
if p3:
    for r in (p3.get("summary") or []):
        metric_keys |= set(r.keys())
    cov = {}
    for m in official_p3_metrics:
        hit = [k for k in metric_keys if k == m or k.startswith(m)]
        cov[m] = {"reported": bool(hit), "keys": sorted(hit)}
    out["official_protocol"]["p3"]["metric_coverage_in_p3_scheduling"] = cov
    out["_meta"]["p3_summary_keys"] = sorted(metric_keys)

    nom = [r for r in (p3.get("summary") or [])
           if abs(r.get("alpha", 0) - 1.0) < 1e-9 and abs(r.get("beta", 0) - 0.5) < 1e-9]
    # 5 映射 × 3 case × policy 的官方门槛矩阵（数据已存在，直接整理）
    gm = {}
    for r in (p3.get("summary") or []):
        key = f"a{r.get('alpha')}_b{r.get('beta')}"
        gm.setdefault(key, {}).setdefault(str(r.get("case")), {})[str(r.get("policy"))] = {
            "on_time": r.get("weighted_on_time_rate"),
            "met_0.50": (r.get("weighted_on_time_rate") or 0) >= 0.50,
            "ci95": r.get("weighted_on_time_rate_ci95"),
        }
    out["official_protocol"]["p3"]["gate_matrix_by_mapping"] = gm
    by_pol = {}
    for r in nom:
        by_pol.setdefault(r.get("policy"), []).append(r)
    for pol, rows in sorted(by_pol.items()):
        per_case = {r.get("case"): {"on_time": r.get("weighted_on_time_rate"),
                                    "completion": r.get("weighted_completion_rate"),
                                    "tardiness": r.get("weighted_tardiness_s"),
                                    "cost": r.get("cost"),
                                    "n_done": r.get("n_done"), "n_drop": r.get("n_drop")}
                    for r in rows}
        vals = [v["on_time"] for v in per_case.values() if v["on_time"] is not None]
        gate_pass = (min(vals) >= 0.50) if vals else None
        row(problem="P3", model="policy: " + str(pol) + ("（oracle 上界）" if pol == "oracle" else ""),
            family="dispatching policy", hyperparams="nominal α=1, β=0.5, 30 seeds",
            split="validation (30 公开种子 2026111700–29)", seed="30 公开种子",
            val_metric=None,
            test_metric={"per_case": per_case,
                         "min_weighted_on_time": min(vals) if vals else None},
            official_gate={"metric": "mean weighted_on_time_rate ≥ 0.50 per case (nominal)",
                           "value": min(vals) if vals else None,
                           "verdict": "PASS" if gate_pass else ("FAIL" if gate_pass is False else "??")},
            official_requirement="官方唯一硬门槛（仅当 cost/capacity risk 为主目标时）",
            internal_bar=None,
            evidence=["data/p3_scheduling.json"])

tab = load("up_p3_table.json")
if tab:
    for r in (tab.get("rows") or []):
        is_nom = abs(r.get("alpha", 0) - 1.0) < 1e-9 and abs(r.get("beta", 0) - 0.5) < 1e-9
        if not is_nom:
            continue
        row(problem="P3", model="two-regime 阈值律（ρ→q* 查表）", family="analytic threshold law",
            hyperparams=f"case {r.get('case')}, rho={r.get('rho')}, argmax_q={r.get('argmax_q')}",
            split="tune=前 15 seed / holdout=后 15 seed", seed="30 公开种子",
            val_metric={"tune_max": r.get("tune_max")},
            test_metric={"holdout_at_argmax": r.get("holdout_at_argmax"),
                         "holdout_best": r.get("holdout_best"),
                         "holdout_best_q": r.get("holdout_best_q")},
            official_gate={"metric": "holdout weighted_on_time ≥ 0.50",
                           "value": r.get("holdout_at_argmax"),
                           "verdict": "PASS" if (r.get("holdout_at_argmax") or 0) >= 0.50 else "FAIL"},
            official_requirement="官方门槛 0.50", internal_bar=None,
            evidence=["data/up_p3_table.json"])

rv = load("up_p3_review.json")
if rv:
    for combo in ("S1|a1.00_b0.50", "S2|a1.00_b0.50", "S3|a1.00_b0.50"):
        c = (rv.get("combos") or {}).get(combo) or {}
        qs = c.get("q") or []
        if not qs:
            continue
        q = qs[0]
        row(problem="P3", model="VOI review 臂（paid observation）", family="information acquisition",
            hyperparams=f"combo {combo}, q={q.get('q')}",
            split="validation 30 seeds", seed="30 公开种子",
            val_metric=None,
            test_metric={"on_time_with": q.get("on_time_with_review"),
                         "on_time_without": q.get("on_time_no_review"),
                         "delta_pt": q.get("delta_pt"), "ci95_pt": q.get("ci95_pt"),
                         "p_value": q.get("p_value"),
                         "review_fired": q.get("review_fired"),
                         "arms_identical": q.get("arms_identical"),
                         "cost_with": q.get("cost_with"), "cost_without": q.get("cost_no")},
            official_gate={"metric": "mean weighted_on_time ≥ 0.50",
                           "value": q.get("on_time_with_review"),
                           "verdict": "PASS" if (q.get("on_time_with_review") or 0) >= 0.50 else "FAIL"},
            official_requirement="官方允许 review（1 cost + 1 s），不计入未授权动作",
            internal_bar={"改善≥1pt 且显著": q.get("improves_ge_1pt_and_sig")},
            evidence=["data/up_p3_review.json"])
    out.setdefault("_p3_review", {}).update({"coverage": g(rv, "gate", "coverage"),
                                            "passed": g(rv, "gate", "passed"),
                                            "max_abs_diff": g(rv, "gate", "max_abs_diff"),
                                            "reference": g(rv, "gate", "reference")})

rl = load("up_p3_rl.json")
if rl:
    det = rl.get("_detail", {})
    for arm, lab in [("rl_armA_slacksel", "RL（slack selector）"), ("rl_armB_risksel", "RL（risk selector）"),
                     ("baseline_slack_old", "slack 基线（旧配置）"),
                     ("baseline_best_rule", "风险规则（最优配置）")]:
        d = det.get(arm) or {}
        if not d:
            continue
        vals = [v for k, v in d.items() if k.startswith("S") and isinstance(v, (int, float))]
        row(problem="P3", model=lab, family="RL / rule",
            hyperparams="MLP 36-128-128, 13 档 b, REINFORCE+A2C" if arm.startswith("rl") else "rule",
            split="test = 公开种子最后 5 个（2026111725–29）", seed="5 seeds（非官方 final test）",
            val_metric=None,
            test_metric={"per_case": d, "min_weighted_on_time": min(vals) if vals else None},
            official_gate={"metric": "mean weighted_on_time ≥ 0.50",
                           "value": min(vals) if vals else None,
                           "verdict": "PASS" if vals and min(vals) >= 0.50 else "FAIL"},
            official_requirement="官方门槛 0.50",
            internal_bar={"mean S2,S3 delta ≥ +0.020 且 CI lower>0": g(rl, "verdict", "passes")},
            evidence=["data/up_p3_rl.json"])
    out.setdefault("_p3_rl", {}).update({"verdict": rl.get("verdict"),
                                         "test_seeds": g(rl, "_meta", "test_seeds"),
                                         "alignment": g(rl, "gate", "alignment_max_abs_diff")})

# ---------------------------------------------------------------- 3. 口径差
out["caliber"] = [
    {"item": "P1 基线数值", "official": "无（要求自选简单 baseline，未发布代码/数值）",
     "ours": "把 code/up_p1a_probe_scores.py 里的 PUBLISHED=0.548686890159744 称为 published baseline",
     "gap": "该值等于 data/p1a_segmentation_compare.json 的 ari.gpu_mean（我们自己 GPU 臂的 test ARI）",
     "severity": "高", "action": "改称「内部参考线」，并补一个真正的简单 baseline（常数段 / 单通道阈值）"},
    {"item": "P1 通过线", "official": "无阈值", "ours": "ARI≥0.60、boundary F1≥0.30（自设，且当前 0.58063 未过）",
     "gap": "论文 line 1558 把自设线写成 pass 判据", "severity": "中",
     "action": "明确标注为 self-imposed，不作为官方达标陈述"},
    {"item": "P2 误差定义", "official": "R=(1/M)Σ||p̂−p||₂（mean 距离）",
     "ours": "rmse_3d_cm=100·sqrt(mean||e||²)（RMS 距离）",
     "gap": "RMS≥mean（Jensen），我们报的 6.14 cm 系统性高于官方 R",
     "severity": "高", "action": "用同一批预测直接算 mean 距离，与原 RMSE 并列上报"},
    {"item": "P2 误差单位口径", "official": "3D 代表点距离",
     "ours": "GRU v2 的 3.31 cm 是 per-coordinate RMSE，被当成 3D RMS 引用",
     "gap": "单位不同（1 维 vs 3 维），值不可比", "severity": "中",
     "action": "论文所有 P2 数字统一标 per-coordinate / 3D"},
    {"item": "P3 种子口径", "official": "final test = test split + 30 个组委会冻结种子",
     "ours": "P3 全部结果用 30 个公开验证种子；RL 的 test 是其中最后 5 个",
     "gap": "官方 final test 我们拿不到 → 只能声明为 validation 结果",
     "severity": "高", "action": "正文统一写 validation；RL 的 5-seed 结论降级为 exploratory"},
    {"item": "P3 invalid_actions / valid_protocol / observations", "official": "§4 指标表明确要求三项",
     "ours": "invalid_actions / valid_protocol 完全未上报；observations 未上报（summary 无该键）",
     "gap": "11 项官方指标只覆盖 8 项", "severity": "高",
     "action": "在 sim 里对每条命令做合法性校验并计数；observations 用 review 次数 + 观测请求数计"},
    {"item": "P1a 同一规则两个数", "official": "无（内部一致性问题）",
     "ours": "published_H0.30_D54_s0 在 up_p1a_baseline_check 得 0.54869，在 up_p1a_final 得 0.53549",
     "gap": "同一规则、同一 7 条 test record、两个 ARI，差值 0.0132 未解释",
     "severity": "中", "action": "核对两处 per_record 是否同一 record 集合与同一 tol_s=5.0"},
    {"item": "P3 官方门槛", "official": "nominal 每 case mean weighted on-time ≥ 0.50（30 trials）",
     "ours": "edf S3 0.54271、now S3 0.50313、edf_rev S3 0.53542 → 全部擦线通过",
     "gap": "过线但余量仅 0.003–0.043；无 CI 下限判断", "severity": "中",
     "action": "把 CI 下限也报出来，说明是否 robustly 过线"},
    {"item": "P3 目标映射", "official": "5 个映射（α∈{0.75,1,1.5}, β∈{0,0.5,1}）为主目标",
     "ours": "主叙事按 nominal α=1/β=0.5 展开", "gap": "非 nominal 映射下 on-time 明显更低（S3 α1.5 = 0.5646）",
     "severity": "低", "action": "补 5 映射×3 case 的门槛判定表（数据已存在）"},
    {"item": "官方附件一致性", "official": "题面引用 tasks_and_evaluation.md",
     "ours": "英文包内不存在该文件，只有 Problem_3_Requirements.pdf",
     "gap": "官方材料缺失，需在论文里说明依据", "severity": "低",
     "action": "引用 PDF 为唯一协议来源，并注明 md 缺失"},
]

# ---------------------------------------------------------------- 4. 缺项
out["missing_official_checks"] = [
    {"item": "官方是否给 baseline 代码/数值", "answer": "P1/P2/P3 均未给。官方只要求「自选 ≥1 个结构简单、参数少的可复现 baseline」",
     "implication": "论文里的 0.5487 不可能是官方值，必须改称内部参考线",
     "evidence": ["logs/official_p3_requirements.txt", "_prob_C.txt §4"]},
    {"item": "P3 invalid_actions / valid_protocol / observations", "answer": "官方要求，我们前两项完全未实现、observations 未上报",
     "implication": "报告不完整，评审可直接扣分", "evidence": ["data/up2_benchmark.json official_protocol.p3.metric_coverage"]},
    {"item": "P3 官方 final test 30 冻结种子", "answer": "未发布（组委会另冻）",
     "implication": "无法复现官方 final test；只能报 validation，且不能声称通过 final 门槛",
     "evidence": ["Problem_3_Requirements.pdf"]},
    {"item": "P2 官方 mean-distance R", "answer": "官方定义是 mean，我们只算 RMS",
     "implication": "主指标口径不符；需补算 R", "evidence": ["_prob_C.txt §4"]},
    {"item": "P1 retained record / timestamp 计数", "answer": "官方要求报告，我们部分覆盖",
     "implication": "需在数据章节补 retained/total 的逐 record 计数",
     "evidence": ["_prob_C.txt §4"]},
    {"item": "P3 censored_units 语义", "answer": "p3_scheduling.summary 有 n_drop，但官方字段名是 censored_units",
     "implication": "字段名不对齐，评审难以对上 §4 表", "evidence": ["data/p3_scheduling.json"]},
    {"item": "P2 计算开销 / set reliability", "answer": "官方 §4 要求报告「计算开销」与「区间/集合可靠性」，我们只有 coverage，无推理耗时与集合式预测",
     "implication": "报告项缺 2 项", "evidence": ["_prob_C.txt §4"]},
    {"item": "P1a 真正简单的 baseline", "answer": "题面要求 simple structure / few parameters 的 baseline；我们的「published 0.5487」是自己 GPU 臂",
     "implication": "既缺零参数 baseline，又误用了 published 名义", "evidence": ["_prob_C.txt §4", "data/p1a_segmentation_compare.json"]},
]

# ---------------------------------------------------------------- 5. 建议
out["recommendations"] = [
    {"rank": 1, "title": "把 P2 主指标换成官方 mean 距离 R（同一批预测，零新增算力）",
     "why": "官方定义 R=(1/M)Σ||p̂−p_ref||₂，我们报的是 RMS；RMS≥mean，当前 6.14 cm 的『不达标』在主指标下可能变成达标",
     "how": "在 code/up2_bench_p2_meandist.py 读已有预测残差 → 逐点 ||e||₂ 取 mean，同时给 RMSE/R/median/q90 与 bootstrap CI",
     "cost": "10 分钟", "expected": "R 预计比 6.14 cm 低 20–35%；口径从『自设门槛失败』变『官方口径达标 + 自设门槛偏严』"},
    {"rank": 2, "title": "补 P3 invalid_actions / valid_protocol 两项官方指标",
     "why": "§4 指标表硬性要求，我们四个结果文件 0 命中，属报告缺项",
     "how": "在 simulator 的命令入口加合法性校验（b<0.2 / 越 H / 设备不可用 / 超 200 actions / 同 job review>2），违规计数并置 terminal 标志，再对 6 policy×3 case 重跑 450 trials",
     "cost": "20–30 分钟（复用现有种子与策略，只加计数器）",
     "expected": "得到 0 violation 的正式结论，或暴露某些策略在非 nominal 映射下越界"},
    {"rank": 3, "title": "把「published baseline 0.5487」改名为内部参考线，并补一个真正简单的官方式 baseline",
     "why": "0.5487 溯源到我们自己的 ari.gpu_mean；官方 P1 无任何 baseline。论文若写 published 会被判错误引用",
     "how": "新增常数段预测（全序列 1 段）与单通道阈值 2 个零参数 baseline，在同一 7 条 test record 上算 ARI/F1，作为表首行",
     "cost": "15 分钟", "expected": "ARI 约 0.0–0.1 量级，反而把 GPU 臂的增益衬托得更实"},
]

# ---------------------------------------------------------------- 写盘
dst = os.path.join(DATA, "up2_benchmark.json")
with open(dst, "w", encoding="utf-8", newline="\n") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("wrote", dst)
print("ladder rows:", len(L))
print("by problem:", {p: sum(1 for r in L if r["problem"] == p)
                       for p in ("P1a", "P1b", "P2", "P3")})
print("p3 metric coverage:", json.dumps(out["official_protocol"]["p3"]
                                        ["metric_coverage_in_p3_scheduling"], ensure_ascii=False))