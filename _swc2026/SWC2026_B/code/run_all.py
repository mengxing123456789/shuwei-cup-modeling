# -*- coding: utf-8 -*-
"""一键重跑：q1 → q2 → q3 → q4 → sens → q2b → figures，并打印关键数字汇总表。

用法：python code/run_all.py
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = sys.executable


def run(script, label):
    t0 = time.time()
    r = subprocess.run([PY, "-u", os.path.join(HERE, script)], cwd=HERE,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    dt = time.time() - t0
    tail = (r.stdout or "").strip().splitlines()[-3:]
    for line in tail:
        print("   ", line)
    if r.returncode != 0:
        print("[FAIL] %s exit=%d (%.1fs)" % (script, r.returncode, dt))
        print(r.stdout)
        sys.exit(r.returncode)
    print("[OK] %s -> %s (%.1fs)" % (label[0], label[1], dt))
    return dt


def load(name):
    with open(os.path.join(ROOT, "data", name), encoding="utf-8") as f:
        return json.load(f)


def main():
    t0 = time.time()
    print("=" * 62)
    print("SWC2026 B 题：全流程重跑")
    print("=" * 62)
    run("q1.py", ("q1", "data/p1.json"))
    run("q2.py", ("q2", "data/p2.json"))
    run("q3.py", ("q3", "data/p3.json"))
    run("q4.py", ("q4", "data/p4.json"))
    run("sens.py", ("sens", "data/sens.json"))
    run("q2b.py", ("q2b", "data/q2b.json 独立复核时间线"))
    run("figures.py", ("figures", "figures/*.png"))

    p1, p2, p3, p4 = load("p1.json"), load("p2.json"), load("p3.json"), load("p4.json")
    se = load("sens.json")["sens"]
    c = p1["p1_T1"]["continuous"]
    at = p2["p2_1"]["attained"]
    d4 = p4["p4"]
    rows = [
        ("P1 Q=1/r 上确界", "%.6f" % p1["p1_T1"]["q_sup"], "连续最优站 (%.4f, %.4f)" % (c["x"], c["y"])),
        ("P2(1) DRMS 下界", "%.6f m" % p2["p2_1"]["drms_lower_bound"], "站对 %s/%s，γ=%.2f°" % (at["pair"][0], at["pair"][1], at["gamma_deg"])),
        ("P2(2) makespan", "%.4f s" % p2["p2_2"]["unconstrained"]["makespan"], "0.25 m 局部细化后"),
        ("P3 s_max", "%.4f m" % p3["p3"]["s_max"], "MC P=%.5f" % p3["p3"]["mc_at_s_max"]),
        ("P4 η 保持原计划", "%.4f" % d4["keep_strict"]["mean_eta"], "t_last %.3f s" % d4["keep_strict"]["mean_tlast"]),
        ("P4 η 保持+补派", "%.4f" % d4["keep"]["mean_eta"], "t_last %.3f s" % d4["keep"]["mean_tlast"]),
        ("P4 η 重调度", "%.4f" % d4["resched"]["mean_eta"], "t_last %.3f s" % d4["resched"]["mean_tlast"]),
        ("P4 重调度胜率", "%.4f" % d4["win_resched"], "tie %.4f" % d4["tie"]),
        ("敏感性 σ 斜率", "%.4f" % se["joint"]["log_slope_drms_T2_vs_sigma"], "log-log 斜率，1.0=严格线性"),
    ]
    print("\n" + "-" * 62)
    print("%-18s %-14s %s" % ("量", "值", "备注"))
    print("-" * 62)
    for a, b, c2 in rows:
        print("%-18s %-14s %s" % (a, b, c2))
    print("-" * 62)
    print("总耗时 %.1f s（预算 480 s）" % (time.time() - t0))
    if time.time() - t0 > 480:
        print("[WARN] 超过 8 分钟预算")
    print("[OK] run_all 完成")


if __name__ == "__main__":
    main()
