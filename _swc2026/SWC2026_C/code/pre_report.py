
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""P2 预训练判决实验 —— 聚合、判定、出表。

输入（全部只读）：
  data/pre_p2_runs.jsonl     富曲线 run 记录
  data/pre_p2_results.json   聚合视图
  data/pre_p2_ssl.json       预训练记录
  data/pre_split.json        划分与窗口数
  data/pre_p2_prereg.json    预注册（门槛写死在这里）
  data/p2_gpu.json           C1 现成 GRU 基线
  data/pre_p2_lr.json        （可选）学习率敏感性
  data/pre_p2_tau.json       （可选）温度敏感性

输出：
  data/pre_p2_summary.json   均值±标准差、配对差、判定位
  data/pre_p2_tables.md      报告用表格（纯数字，不做解释）
"""
import json
import os

import numpy as np

from common import DATA

RUNS = os.path.join(DATA, "pre_p2_runs.jsonl")
SUMMARY = os.path.join(DATA, "pre_p2_summary.json")
TABLES = os.path.join(DATA, "pre_p2_tables.md")

METRICS = ["rmse_cm", "endpoint_rmse_cm", "median_cm", "q90_cm",
           "cov80_endpoint", "cov90_endpoint", "cov80_all", "cov90_all",
           "pit_maxdev"]
L_NAME = {6: "0.2 s (6 帧)", 18: "0.6 s (18 帧)", 30: "1.0 s (30 帧)",
          60: "2.0 s (60 帧)"}


def load_json(name):
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def load_runs():
    out = []
    with open(RUNS, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def agg(vals):
    v = np.asarray(vals, float)
    return float(v.mean()), (float(v.std(ddof=1)) if len(v) > 1 else 0.0)


def cell(m, s, nd=3):
    return f"{m:.{nd}f} ± {s:.{nd}f}"


def main():
    runs = load_runs()
    prereg = load_json("pre_p2_prereg.json")
    ssl = load_json("pre_p2_ssl.json")
    split = load_json("pre_split.json")
    c1 = load_json("p2_gpu.json")
    lr = load_json("pre_p2_lr.json")
    tau = load_json("pre_p2_tau.json")

    seeds = sorted({r["seed"] for r in runs})
    Ls = sorted({r["L"] for r in runs})
    groups = {}          # (arm, task, L) -> list of runs
    for r in runs:
        groups.setdefault((r["arm"], r.get("ssl_task"), r["L"]), []).append(r)

    summary = {"_meta": {"n_runs": len(runs), "seeds": seeds, "Ls": Ls,
                         "prereg": prereg.get("decision") if prereg else None},
               "groups": {}, "paired": {}, "decision": {}}

    c1rows = {}
    if c1:
        for r in c1.get("rows", []):
            if r.get("variant") == "v2":
                c1rows[int(r["L_frames"])] = dict(
                    rmse_cm=r["test_rmse_m"] * 100.0,
                    endpoint_rmse_cm=r["test_endpoint_rmse_m"] * 100.0,
                    median_cm=r["test_median_err_m"] * 100.0,
                    best_epoch=r.get("best_val_epoch"))

    # ---- 分组均值 ± 标准差
    for (arm, task, L), rs in sorted(groups.items(), key=lambda kv: (kv[0][2], kv[0][0], str(kv[0][1]))):
        d = {"n_seeds": len(rs), "arm": arm, "ssl_task": task, "L": L,
             "L_s": round(L / 30.0, 3)}
        for m in METRICS:
            vals = [r[m] for r in rs if m in r]
            if vals:
                mu, sd = agg(vals)
                d[m + "_mean"], d[m + "_std"] = mu, sd
        d["best_epoch"] = [r.get("best_epoch") for r in rs]
        d["epochs_run"] = [r.get("epochs_run") for r in rs]
        d["val_rmse_cm"] = [round(r.get("val_rmse_cm", float("nan")), 3) for r in rs]
        d["seconds"] = [r.get("seconds") for r in rs]
        if arm == "C2":
            d["alpha"] = [r.get("alpha") for r in rs]
        if "curve" in rs[0]:
            # 各 run 早停轮数不同 -> 曲线取最短长度求均值（不做插值）
            n = min(len(r["curve"]) for r in rs)
            cm = np.mean([[c["train_rmse_cm"] for c in r["curve"][:n]] for r in rs], axis=0)
            vm = np.mean([[c["val_rmse_cm"] for c in r["curve"][:n]] for r in rs], axis=0)
            d["curve_epochs"] = int(n)
            d["curve_train_mean"] = [round(float(x), 3) for x in cm]
            d["curve_val_mean"] = [round(float(x), 3) for x in vm]
        summary["groups"][f"{arm}|{task or '-'}|{L}"] = d

    # ---- 同种子配对：C3 - C0（以及 C3B - C3A）
    def get(arm, task, seed, L):
        for r in runs:
            if r["arm"] == arm and r.get("ssl_task") == task and r["seed"] == seed and r["L"] == L:
                return r
        return None

    for L in Ls:
        for task in ("A", "B"):
            rows = []
            for s in seeds:
                c0, c3 = get("C0", None, s, L), get("C3", task, s, L)
                if not (c0 and c3):
                    continue
                rows.append(dict(seed=s,
                                 c0_rmse=c0["rmse_cm"], c3_rmse=c3["rmse_cm"],
                                 d_rmse_pct=(c3["rmse_cm"] - c0["rmse_cm"]) / c0["rmse_cm"] * 100,
                                 c0_endpoint=c0["endpoint_rmse_cm"],
                                 c3_endpoint=c3["endpoint_rmse_cm"],
                                 d_endpoint_pct=(c3["endpoint_rmse_cm"] - c0["endpoint_rmse_cm"])
                                 / c0["endpoint_rmse_cm"] * 100,
                                 c0_median=c0["median_cm"], c3_median=c3["median_cm"],
                                 c0_q90=c0["q90_cm"], c3_q90=c3["q90_cm"]))
            if rows:
                summary["paired"][f"L{L}|{task}"] = rows

    # ---- 预注册判定：1.0 s / 2.0 s 两档、RMSE 改善 ≥10%、3 种子同向
    rule = (prereg or {}).get("decision", {})
    thr = float(rule.get("min_improvement_pct", 10.0))
    need_agree = int(rule.get("require_seeds_agree", 3))
    verdict = {}
    for task in ("A", "B"):
        det = {}
        for L in (30, 60):
            rows = summary["paired"].get(f"L{L}|{task}", [])
            if not rows:
                det[L] = {"ok": False, "reason": "未跑"}
                continue
            impr = [-r["d_rmse_pct"] for r in rows]        # 正 = 改善
            agree = sum(1 for x in impr if x > 0)
            ok = all(x >= thr for x in impr) and agree >= need_agree
            det[L] = {"ok": bool(ok), "improvement_pct": [round(x, 2) for x in impr],
                      "mean_improvement_pct": round(float(np.mean(impr)), 2),
                      "seeds_improved": int(agree), "n_seeds": len(rows),
                      "threshold_pct": thr}
        verdict[task] = {"pass": all(det[L].get("ok", False) for L in (30, 60)),
                         "detail": det}
    verdict["pass_any"] = any(verdict[t]["pass"] for t in ("A", "B"))
    summary["decision"] = verdict

    # ---- 报告表格
    lines = ["# P2 预训练判决实验 —— 数字表", ""]
    lines.append(f"runs={len(runs)}  seeds={seeds}  L={Ls}  "
                 f"（C1 引用 data/p2_gpu.json，不在此表重算）")
    lines.append("")
    lines.append("## 表 1 四组对照 × 四档位（test 全滑窗，RMSE cm，均值 ± 标准差，n=3 种子）")
    lines.append("")
    lines.append("| 组 | 初始化 | 0.2 s | 0.6 s | 1.0 s | 2.0 s |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    arms = [("C0", None, "C0 从零（同骨架 TCN）"),
            ("C1", None, "C1 现成 GRU 基线（data/p2_gpu.json）"),
            ("C2", "A", "C2 冻结探针（任务 A 掩码重构）"),
            ("C2", "B", "C2 冻结探针（任务 B 时序对比）"),
            ("C3", "A", "C3 全量微调（任务 A 掩码重构）"),
            ("C3", "B", "C3 全量微调（任务 B 时序对比）")]
    for arm, task, label in arms:
        if arm == "C1":
            vals = []
            for L in (6, 18, 30, 60):
                v = c1rows.get(L, {}).get("rmse_cm")
                vals.append("—" if v is None else f"{v:.2f}")
            lines.append(f"| {label} | 不适用 | " + " | ".join(vals) + " |")
            continue
        cells = []
        for L in (6, 18, 30, 60):
            g = summary["groups"].get(f"{arm}|{task or '-'}|{L}")
            if not g or "rmse_cm_mean" not in g:
                cells.append("未跑")
            else:
                cells.append(cell(g["rmse_cm_mean"], g["rmse_cm_std"], 2))
        lines.append(f"| {label} | {'预训练' if arm != 'C0' else '随机'} | "
                     + " | ".join(cells) + " |")
    lines.append("")
    lines.append("| 组 | 初始化 | 0.2 s | 0.6 s | 1.0 s | 2.0 s |（端点 RMSE cm）")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for arm, task, label in arms:
        if arm == "C1":
            vals = []
            for L in (6, 18, 30, 60):
                v = c1rows.get(L, {}).get("endpoint_rmse_cm")
                vals.append("—" if v is None else f"{v:.2f}")
            lines.append(f"| {label} | 不适用 | " + " | ".join(vals) + " |")
            continue
        cells = []
        for L in (6, 18, 30, 60):
            g = summary["groups"].get(f"{arm}|{task or '-'}|{L}")
            if not g or "endpoint_rmse_cm_mean" not in g:
                cells.append("未跑")
            else:
                cells.append(cell(g["endpoint_rmse_cm_mean"], g["endpoint_rmse_cm_std"], 2))
        lines.append(f"| {label} | {'预训练' if arm != 'C0' else '随机'} | "
                     + " | ".join(cells) + " |")

    lines += ["", "## 表 2 中位 / q90 / 分布质量（test 全滑窗）", "",
              "| 组 | 档位 | 中位 cm | q90 cm | cov80端点 | cov90端点 | PIT 最大偏差 |",
              "| --- | --- | --- | --- | --- | --- | --- |"]
    for arm, task, label in arms:
        if arm == "C1":
            continue
        for L in (6, 18, 30, 60):
            g = summary["groups"].get(f"{arm}|{task or '-'}|{L}")
            if not g or "median_cm_mean" not in g:
                continue
            lines.append(f"| {arm}{('-' + task) if task else ''} | {L_NAME[L]} | "
                         f"{g['median_cm_mean']:.2f} ± {g['median_cm_std']:.2f} | "
                         f"{g['q90_cm_mean']:.2f} ± {g['q90_cm_std']:.2f} | "
                         f"{g['cov80_endpoint_mean']:.3f} | "
                         f"{g['cov90_endpoint_mean']:.3f} | "
                         f"{g['pit_maxdev_mean']:.3f} |")

    lines += ["", "## 表 3 同种子配对差（C3 − C0，负 = 改善）", "",
              "| 档位 | 任务 | 种子 | C0 RMSE | C3 RMSE | Δ% | C0 端点 | C3 端点 | Δ端点% |",
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for L in (6, 18, 30, 60):
        for task in ("A", "B"):
            for r in summary["paired"].get(f"L{L}|{task}", []):
                lines.append(f"| {L_NAME[L]} | {task} | {r['seed']} | {r['c0_rmse']:.3f} | "
                             f"{r['c3_rmse']:.3f} | {r['d_rmse_pct']:+.1f} | "
                             f"{r['c0_endpoint']:.3f} | {r['c3_endpoint']:.3f} | "
                             f"{r['d_endpoint_pct']:+.1f} |")

    lines += ["", "## 表 4 预注册判定", "",
              f"门槛：1.0 s 与 2.0 s 两档 RMSE 改善 ≥ {thr:.0f}%，且 {need_agree} 个种子同向。", "",
              "| 任务 | 档位 | 各种子改善% | 均值改善% | 同向种子 | 判位 |",
              "| --- | --- | --- | --- | --- | --- |"]
    for task in ("A", "B"):
        for L in (30, 60):
            d = verdict[task]["detail"].get(L, {})
            if "improvement_pct" not in d:
                lines.append(f"| {task} | {L_NAME[L]} | 未跑 | — | — | — |")
                continue
            lines.append(f"| {task} | {L_NAME[L]} | "
                         f"{', '.join(f'{x:+.1f}' for x in d['improvement_pct'])} | "
                         f"{d['mean_improvement_pct']:+.1f} | "
                         f"{d['seeds_improved']}/{d['n_seeds']} | "
                         f"{'PASS' if d['ok'] else 'FAIL'} |")
    lines += ["", f"总判位：A={'PASS' if verdict['A']['pass'] else 'FAIL'}，"
                  f"B={'PASS' if verdict['B']['pass'] else 'FAIL'}，"
                  f"任一通过={verdict['pass_any']}"]

    # ---- 失败模式：过拟合曲线 / best_epoch / 学习率 / 温度
    lines += ["", "## 表 5 训练过程（train / val RMSE cm，按种子均值）", "",
              "| 组 | 档位 | ep1 train | ep1 val | 末轮 train | 末轮 val | 最好 val | best_epoch | epochs_run |",
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for arm, task in [("C0", None), ("C3", "A"), ("C3", "B")]:
        for L in (6, 18, 30, 60):
            g = summary["groups"].get(f"{arm}|{task or '-'}|{L}")
            if not g or "curve_train_mean" not in g:
                continue
            ct, cv = g["curve_train_mean"], g["curve_val_mean"]
            lines.append(f"| {arm}{('-' + task) if task else ''} | {L_NAME[L]} | {ct[0]:.2f} | "
                         f"{cv[0]:.2f} | {ct[-1]:.2f} | {cv[-1]:.2f} | "
                         f"{min(cv):.2f} | {g['best_epoch']} | {g['epochs_run']} |")

    if lr:
        lines += ["", "## 表 6 学习率敏感性（1.0 s / 2.0 s，seed="
                      f"{lr.get('_meta', {}).get('seed')}）", "",
                  "| 学习率 | 组 | 1.0 s RMSE | 2.0 s RMSE | best_epoch(1.0/2.0) |",
                  "| --- | --- | --- | --- | --- |"]
        for row in lr.get("rows", []):
            lines.append(f"| {row['lr']:g} | {row['arm']} | "
                         f"{row.get('rmse_L30', float('nan')):.3f} | "
                         f"{row.get('rmse_L60', float('nan')):.3f} | "
                         f"{row.get('best_ep_L30')}/{row.get('best_ep_L60')} |")
    else:
        lines += ["", "## 表 6 学习率敏感性", "", "未跑（见报告「未跑项」）。"]

    if tau:
        lines += ["", "## 表 7 温度敏感性（任务 B，1.0 s / 2.0 s）", "",
                  "| tau | 1.0 s RMSE | 2.0 s RMSE |", "| --- | --- | --- |"]
        for row in tau.get("runs", []):
            lines.append(f"| {row['tau']:g} | {row.get('rmse_L30', float('nan')):.3f} | "
                         f"{row.get('rmse_L60', float('nan')):.3f} |")
    else:
        lines += ["", "## 表 7 温度敏感性", "", "未跑（见报告「未跑项」）。"]

    # ---- 预训练记录
    if ssl:
        lines += ["", "## 表 8 自监督预训练记录（700 步固定预算）", "",
                  "| 任务 | 种子 | best_step | best_val | 选中步 | 选中 val | 选择规则 | 耗时 s |",
                  "| --- | --- | --- | --- | --- | --- | --- | --- |"]
        for r in ssl["runs"]:
            lines.append(f"| {r['task']} | {r['seed']} | {r['best_step']} | "
                         f"{r['best_val']:.4f} | {r['selected_step']} | "
                         f"{r['selected_val']:.4f} | {r.get('select', 'best')} | {r['seconds']} |")

    if split:
        t = split.get("totals", {})
        lines += ["", "## 表 9 划分与窗口池（pre_split.json）", "",
                  "| 档位 | train 窗 | val 窗 | test 窗 |", "| --- | --- | --- | --- |"]
        for L in (6, 18, 30, 60):
            lines.append(f"| {L_NAME[L]} | {t.get('train', {}).get('windows', {}).get('L' + str(L), '—')} | "
                         f"{t.get('validation', {}).get('windows', {}).get('L' + str(L), '—')} | "
                         f"{t.get('test', {}).get('windows', {}).get('L' + str(L), '—')} |")

    with open(TABLES, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    with open(SUMMARY, "w", encoding="utf-8", newline="\n") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    print("\n".join(lines[-6:]))
    print(f"\n-> {TABLES}\n-> {SUMMARY}")
    for task in ("A", "B"):
        for L in (30, 60):
            d = verdict[task]["detail"].get(L, {})
            print(task, L, d.get("improvement_pct"), "PASS" if d.get("ok") else "FAIL")


if __name__ == "__main__":
    main()