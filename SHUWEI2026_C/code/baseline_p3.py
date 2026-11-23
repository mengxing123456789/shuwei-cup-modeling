"""Problem 3 官方口径的可复现 baseline。

实现依据：data/constraints/Problem_3_Requirements.pdf 第 1–3 页。
- 只用 train 拟合同族服务时长中位数；validation 只做验证。
- 每个 case、每个 seed 重新 random.Random(seed)，按 job_id 排序，从 validation 的
  同族 eligible 区间里 choice 一个有放回样本，保持 source_segment_index 原行序。
- 策略不偷看实际时长：EDD 选序，预留 b = 训练集同族服务时长中位数；不付费查看。
- 实现 release/predecessor/travel/changeover/cost/H、非抢占、预留不提前释放、
  censored/overrun/idle/invalid 以及全部 common metrics。

产物：data/results_baseline_p3.json、data/baseline_p3_trials.csv。
复现：python code\baseline_p3.py
"""

from __future__ import annotations

import json
import pathlib
import random

import numpy as np
import pandas as pd

WS = pathlib.Path(__file__).resolve().parents[1]
CON = WS / "data" / "constraints"
OUT = WS / "data" / "results_baseline_p3.json"
TRIALS_OUT = WS / "data" / "baseline_p3_trials.csv"
CHANGEOVER = 0.5


def distance(a: str, b: str, zones: dict[str, tuple[float, float]]) -> float:
    (x1, y1), (x2, y2) = zones[a], zones[b]
    return float(np.hypot(x1 - x2, y1 - y2))


def simulate(case: str, jobs: pd.DataFrame, assignment: dict[str, float], reserve: dict[str, float],
             zones: dict[str, tuple[float, float]], horizon: float, budget: float,
             alpha: float = 1.0, beta: float = 0.5) -> dict:
    info = {r.job_id: r for r in jobs.itertuples()}
    predecessors = {
        j: ([] if pd.isna(r.predecessors) else str(r.predecessors).split("|"))
        for j, r in info.items()
    }
    total_weight = float(jobs.priority_weight.sum())
    t, zone, cost = 0.0, "Z0", 0.0
    completed: dict[str, float] = {}
    executed: list[dict] = []
    pending = set(info)
    observations = 0
    invalid_actions = 0
    stopped = False

    while pending and t < horizon - 1e-9 and not stopped:
        ready = [j for j in pending
                 if info[j].release_s <= t + 1e-9 and all(p in completed for p in predecessors[j])]
        if not ready:
            future = [info[j].release_s for j in pending
                      if all(p in completed for p in predecessors[j])]
            if not future:
                stopped = True
                break
            t = max(t, min(future))
            continue
        # EDD；同 due 时权重高者优先，最后按 job_id 保证确定性。
        job = min(ready, key=lambda j: (info[j].due_s, -info[j].priority_weight, j))
        D = distance(zone, info[job].zone_id, zones)
        start = t + D + CHANGEOVER
        b = max(0.2, reserve[info[job].family_id])
        action_cost = 2.0 + 0.1 * b + 0.2 * D
        if start + b > horizon + 1e-9 or cost + action_cost > budget + 1e-9:
            # baseline 不发非法指令，直接停止；其余工作按未完成计入分母。
            stopped = True
            break
        cost += action_cost
        p = alpha * assignment[job] + beta
        completion = start + p
        available = start + max(p, b)
        censored = completion > horizon + 1e-9
        observed_end = min(completion, horizon)
        overrun = max(0.0, min(p, horizon - start) - b)
        idle = max(0.0, b - p) if not censored else 0.0
        executed.append({"job_id": job, "start_s": start, "p_s": p, "b_s": b,
                         "completion_s": completion, "censored": censored,
                         "overrun_s": overrun, "idle_s": idle, "cost": action_cost})
        if not censored:
            completed[job] = completion
        pending.remove(job)
        zone = info[job].zone_id
        t = min(available, horizon)
        if t >= horizon - 1e-9:
            break

    weighted_completion = sum(info[j].priority_weight for j in completed) / total_weight
    weighted_on_time = sum(info[j].priority_weight for j, c in completed.items()
                           if c <= info[j].due_s + 1e-9) / total_weight
    tardiness = 0.0
    for j in info:
        c = completed.get(j, horizon)
        tardiness += info[j].priority_weight * max(0.0, c - info[j].due_s)
    return {
        "weighted_completion_rate": weighted_completion,
        "weighted_on_time_rate": weighted_on_time,
        "weighted_tardiness_s": tardiness,
        "cost": cost,
        "observations": observations,
        "elapsed_s": t,
        "observed_overrun_s": sum(x["overrun_s"] for x in executed),
        "reserved_idle_s": sum(x["idle_s"] for x in executed),
        "censored_units": sum(x["censored"] for x in executed),
        "unfinished_units": len(info) - len(completed),
        "invalid_actions": invalid_actions,
        "valid_protocol": invalid_actions == 0,
        "stopped_early": stopped,
        "executed": executed,
    }


def main() -> int:
    tasks = pd.read_csv(CON / "tasks.csv")
    idx = pd.read_csv(CON / "source_segment_index.csv")
    conditions = json.loads((CON / "common_conditions.json").read_text(encoding="utf-8"))
    zones_df = pd.read_csv(CON / "service_zones.csv")
    zones = {r.zone_id: (float(r.x), float(r.y)) for r in zones_df.itertuples()}
    eligible = idx[idx["eligible"] == 1]
    train = eligible[eligible["split"] == "train"]
    validation = eligible[eligible["split"] == "validation"]
    # 训练集服务时长中位数：alpha=1、beta=0.5 下即 duration+0.5。
    reserve = {f: float(g["duration_s"].median()) + 0.5 for f, g in train.groupby("family_id")}
    pools = {f: g["duration_s"].tolist() for f, g in validation.groupby("family_id", sort=False)}
    seeds = conditions["validation_seeds"]
    cases = {c["case_id"]: c for c in conditions["cases"]}

    trial_rows = []
    summary = {"protocol": "official validation split and Python random.Random(seed).choice",
               "reserve_rule": "training-family median duration + 0.5 s", "cases": {}}
    for case, jobs in tasks.groupby("case_id", sort=True):
        jobs = jobs.sort_values("job_id")
        cfg = cases[case]
        metrics = []
        for trial, seed in enumerate(seeds, 1):
            rng = random.Random(int(seed))
            assignment = {}
            for r in jobs.itertuples():
                assignment[r.job_id] = float(rng.choice(pools[r.family_id]))
            result = simulate(case, jobs, assignment, reserve, zones,
                              float(cfg["horizon_s"]), float(cfg["cost_budget"]))
            metrics.append(result)
            trial_rows.append({
                "case_id": case, "split": "validation", "trial": trial, "seed": seed,
                "alpha": 1.0, "beta": 0.5,
                **{k: v for k, v in result.items() if k not in ("executed",)},
            })
        def values(key):
            return np.array([float(m[key]) for m in metrics])
        summary["cases"][case] = {
            "jobs": len(jobs), "horizon_s": cfg["horizon_s"], "cost_budget": cfg["cost_budget"],
            "n_trials": len(metrics),
            "weighted_completion_rate_mean": float(values("weighted_completion_rate").mean()),
            "weighted_on_time_rate_mean": float(values("weighted_on_time_rate").mean()),
            "weighted_tardiness_s_mean": float(values("weighted_tardiness_s").mean()),
            "cost_mean": float(values("cost").mean()),
            "elapsed_s_mean": float(values("elapsed_s").mean()),
            "observed_overrun_s_mean": float(values("observed_overrun_s").mean()),
            "reserved_idle_s_mean": float(values("reserved_idle_s").mean()),
            "censored_units_mean": float(values("censored_units").mean()),
            "unfinished_units_mean": float(values("unfinished_units").mean()),
            "stopped_early_trials": sum(bool(m["stopped_early"]) for m in metrics),
            "invalid_actions_total": sum(int(m["invalid_actions"]) for m in metrics),
            "valid_protocol_all": all(bool(m["valid_protocol"]) for m in metrics),
        }
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    pd.DataFrame(trial_rows).to_csv(TRIALS_OUT, index=False, encoding="utf-8")
    print(f"wrote {OUT} {OUT.stat().st_size} B; {TRIALS_OUT} {TRIALS_OUT.stat().st_size} B")
    for case, s in summary["cases"].items():
        print(f"{case}: completion {s['weighted_completion_rate_mean']:.3f} "
              f"on-time {s['weighted_on_time_rate_mean']:.3f} "
              f"tardiness {s['weighted_tardiness_s_mean']:.1f} "
              f"cost {s['cost_mean']:.2f}/{s['cost_budget']} "
              f"elapsed {s['elapsed_s_mean']:.1f}/{s['horizon_s']} "
              f"unfinished {s['unfinished_units_mean']:.2f} stop {s['stopped_early_trials']}/30")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())