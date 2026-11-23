# -*- coding: utf-8 -*-
"""P4：t=5 s 三重扰动下"保持原计划"与"重调度"的对比。"""
from __future__ import annotations

import itertools
import json
import math
import os
from functools import lru_cache

import numpy as np

import common as C

NAME = "p4.json"
SEED = 20261120
T_DIS = 5.0
N_MC = 500
H_NEW = 50.0
HORIZON = 60.0
R_MIN_NEW = (H_NEW - C.CAM_Z) / math.tan(math.radians(C.ELEV_MAX))
ALERTS = ("T1", "T2", "T3")
ALL4 = ALERTS + ("T4",)
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")


def load_base():
    return json.load(open(os.path.join(DATA, "p2.json"), encoding="utf-8"))["p2_2"]["unconstrained"]


def slot_stations(base, alert):
    out = []
    for v in C.VEH0:
        for e in base["timeline"].get(v, []):
            if e["alert"] == alert:
                st = tuple(round(float(x), 4) for x in e["station"])
                if st not in out:
                    out.append(st)
    return out


def travel(p, q, cache):
    key = (tuple(round(float(x), 2) for x in p), tuple(round(float(x), 2) for x in q))
    if key not in cache:
        cache[key] = float(C.travel_time(np.array(p, float), np.array(q, float)))
    return cache[key]


@lru_cache(maxsize=100000)
def slew_triple(st, alert):
    t = C.target_xyz(alert)
    pan = float(C.bearing_deg(st, t[:2]))
    elev = float(C.elev_deg(st[0], st[1], alert))
    return (float(C.slew_time(pan, elev, pan, elev)),
            float(C.slew_time(pan, elev, 0.0, 0.0)), elev)


def _vec_feasible(xs, ys):
    ok = np.ones(xs.shape, bool)
    lo, hi = C.FIELD[0] + C.VEH_R, C.FIELD[1] - C.VEH_R
    ok &= (xs >= lo) & (xs <= hi) & (ys >= lo) & (ys <= hi)
    for (_n, x1, x2, y1, y2, _h) in C.BUILDINGS:
        inside = (xs > x1 - C.VEH_R) & (xs < x2 + C.VEH_R) & (ys > y1 - C.VEH_R) & (ys < y2 + C.VEH_R)
        ok &= ~inside
    return ok


def new_alert_stations(theta, r, cache, pos):
    """新警报的两个站址：r=r_min 圆上取 γ=90° 的成对站，选两车欧氏距离和最小的那对。"""
    C.TARGETS["T4"] = (theta, r, H_NEW)
    tx, ty = float(C.target_xyz("T4")[0]), float(C.target_xyz("T4")[1])
    ang = np.radians(np.arange(0.0, 360.0, 5.0))
    xs, ys = tx + R_MIN_NEW * np.cos(ang), ty + R_MIN_NEW * np.sin(ang)
    ok = _vec_feasible(xs, ys)
    blocked = C.los_blocked(xs, ys, "T4")
    ok &= ~np.asarray(blocked, bool)
    cand = {int(round(a)): (float(x), float(y)) for a, x, y, o in zip(np.degrees(ang), xs, ys, ok) if o}
    if len(cand) < 2:
        return None, None
    P = np.array([pos[v] for v in C.VEH0], float)
    best = None
    for k, st in cand.items():
        k2 = (k + 90) % 360
        if k2 not in cand:
            continue
        s2 = cand[k2]
        d = np.sort(np.min(np.hypot(P[:, None, 0] - np.array([st[0], s2[0]]),
                                   P[:, None, 1] - np.array([st[1], s2[1]])), axis=0))
        sc = float(d[0] + d[1])
        if best is None or sc < best[0]:
            best = (sc, st, s2)
    if best is None:
        return None, None
    for st in (best[1], best[2]):
        for v in C.VEH0:
            travel(pos[v], st, cache)
    return best[1], best[2]


def sched(alerts, slots, veh, pos, avail, cache):
    """警报顺序固定；每条选 2 台车（可复用），枚举站槽分配，取 makespan 最小。"""
    opts = []
    for a in alerts:
        o = []
        for pair in itertools.combinations(veh, 2):
            o.append(list(zip(pair, slots[a])))
            o.append(list(zip(pair[::-1], slots[a])))
        opts.append(o)
    best = None
    for combo in itertools.product(*opts):
        free = {v: float(avail[v]) for v in veh}
        where = dict(pos)
        starts, ok = {}, True
        for a, pairs in zip(alerts, combo):
            rd = []
            for v, st in pairs:
                sw = slew_triple(tuple(st), a)[0]
                rd.append(free[v] + travel(where[v], st, cache) + sw)
            s = max(rd)
            if s > HORIZON:
                ok = False
                break
            starts[a] = s
            for (v, st) in pairs:
                free[v] = s + C.T_OBS + slew_triple(tuple(st), a)[1]
                where[v] = st
        if not ok:
            continue
        mk = max(starts.values()) if starts else float("inf")
        if best is None or mk < best[0] - 1e-9:
            best = (mk, dict(starts))
    return best


def policy_keep(base, frozen, dead, t_rec, new_st, veh, cache, states):
    starts = {}
    for a in ALERTS:
        if a in frozen:
            starts[a] = float(base["starts"][a])
        elif dead not in base["assign"][a]:
            starts[a] = float(base["starts"][a])
    free = {v: float(states["free"][v]) for v in veh if v != dead}
    for a in ALERTS:                      # 任务被丢弃的车提前空闲
        if a not in starts and a in base["assign"]:
            for v in base["assign"][a]:
                if v in free:
                    free[v] = min(free[v], T_DIS)
    live = list(free)
    best = None
    for pair in itertools.combinations(live, 2):
        for order in (pair, pair[::-1]):
            rd = [max(free[v], t_rec) + travel(states["pos"][v], st, cache) + slew_triple(tuple(st), "T4")[0]
                  for v, st in zip(order, new_st)]
            s = max(rd)
            if best is None or s < best[0]:
                best = (s, list(order))
    if best is not None:
        starts["T4"] = best[0]
    return starts


def policy_keep_strict(base, frozen, dead, t_rec):
    """字面意义的"保持原计划"：不接新警报，故障车占的警报按损失计。"""
    return {a: float(base["starts"][a]) for a in ALERTS
            if a in frozen or dead not in base["assign"][a]}


def policy_resched(base, frozen, dead, t_rec, new_st, veh, cache, states):
    starts = {}
    for a in ALERTS:
        if a in frozen or float(base["starts"][a]) <= t_rec + 1e-9:
            if a not in frozen and dead in base["assign"][a]:
                continue          # 该警报的观测窗口已在断电期被故障车占去，无法补救
            starts[a] = float(base["starts"][a])
    pend = [a for a in ALERTS if a not in starts]
    live = [v for v in veh if v != dead]
    avail = {}
    for v in live:
        busy = any(a in starts and v in base["assign"][a] for a in ALERTS)
        avail[v] = max(t_rec, float(states["free"][v])) if busy else t_rec
    slots = {a: slot_stations(base, a) for a in pend}
    slots["T4"] = [tuple(new_st[0]), tuple(new_st[1])]
    r = sched(pend + ["T4"], slots, live, states["pos"], avail, cache)
    if r is None:
        return starts
    starts.update(r[1])
    return starts


def metrics(starts, H=HORIZON):
    ok = [a for a in ALL4 if a in starts and starts[a] <= H + 1e-9]
    k = len(ok)
    tlast = max((starts[a] for a in ok), default=H)
    return dict(k=k, N=4, eta=k / 4.0, tlast=float(tlast) if k == 4 else H)


def main():
    base = load_base()
    C.TARGETS["T4"] = (0.0, 40.0, H_NEW)
    states = dict(pos={}, free={})
    for v in C.VEH0:
        ms = base["timeline"].get(v, [])
        started = [m for m in ms if float(m["obs_start"]) <= T_DIS]
        pos = started[-1]["station"] if started else (ms[0]["station"] if ms else list(C.VEH0[v]))
        states["pos"][v] = tuple(round(float(x), 4) for x in pos)
        states["free"][v] = float(started[-1]["free"]) if started else T_DIS
    frozen = {a for a in ALERTS if float(base["starts"][a]) <= T_DIS}

    rng = np.random.default_rng(SEED)
    cache, rows, samples = {}, [], []
    t_recs = rng.uniform(T_DIS, 30.0, N_MC)
    for i in range(N_MC):
        theta = float(rng.uniform(0.0, 360.0))
        r = float(rng.uniform(30.0, 50.0))
        vf = str(rng.choice(list(C.VEH0)))
        t_rec = float(t_recs[i])
        st1, st2 = new_alert_stations(theta, r, cache, states["pos"])
        if st1 is None:
            continue
        kp0 = policy_keep_strict(base, frozen, vf, t_rec)
        kp = policy_keep(base, frozen, vf, t_rec, (st1, st2), list(C.VEH0), cache, states)
        rs = policy_resched(base, frozen, vf, t_rec, (st1, st2), list(C.VEH0), cache, states)
        d = C.drms_pair(st1, st2, "T4")
        rows.append(dict(i=i, theta=round(theta, 3), R=round(r, 3), v_fail=vf, t_rec=round(t_rec, 3),
                         keep_strict=metrics(kp0), keep=metrics(kp), resched=metrics(rs),
                         starts_keep_strict={a: round(float(x), 4) for a, x in kp0.items()},
                         starts_keep={a: round(float(s), 4) for a, s in kp.items()},
                         starts_resched={a: round(float(s), 4) for a, s in rs.items()},
                         drms_new=None if d["degenerate"] else round(float(d["drms"]), 6)))
        if len(samples) < 5 and 10.5 <= t_rec <= 12.5:
            samples.append(dict(i=i, theta=round(theta, 3), R=round(r, 3), v_fail=vf, t_rec=round(t_rec, 3),
                                keep_times={a: round(float(s), 3) for a, s in sorted(kp.items())},
                                resched_times={a: round(float(s), 3) for a, s in sorted(rs.items())}))

    eta0 = np.array([x["keep_strict"]["eta"] for x in rows])
    tl0 = np.array([x["keep_strict"]["tlast"] for x in rows])
    eta1 = np.array([x["keep"]["eta"] for x in rows])
    eta2 = np.array([x["resched"]["eta"] for x in rows])
    tl1 = np.array([x["keep"]["tlast"] for x in rows])
    tl2 = np.array([x["resched"]["tlast"] for x in rows])
    win2 = (eta2 > eta1 + 1e-12) | ((np.abs(eta2 - eta1) < 1e-12) & (tl2 < tl1 - 1e-9))
    win1 = (eta1 > eta2 + 1e-12) | ((np.abs(eta2 - eta1) < 1e-12) & (tl1 < tl2 - 1e-9))
    by_t, by_f = [], []
    for lo, hi in [(5, 8), (8, 11), (11, 15), (15, 30.001)]:
        m = np.array([(lo <= x["t_rec"] < hi) for x in rows])
        if not m.any():
            continue
        by_t.append(dict(t_rec="[%g,%g)" % (lo, min(hi, 30)), n=int(m.sum()),
                         keep_strict_eta=round(float(eta0[m].mean()), 4),
                         keep_eta=round(float(eta1[m].mean()), 4), keep_tlast=round(float(tl1[m].mean()), 3),
                         resched_eta=round(float(eta2[m].mean()), 4), resched_tlast=round(float(tl2[m].mean()), 3),
                         win_resched=round(float(win2[m].mean()), 4)))
    for v in C.VEH0:
        m = np.array([x["v_fail"] == v for x in rows])
        by_f.append(dict(v_fail=v, n=int(m.sum()), keep_eta=round(float(eta1[m].mean()), 4),
                         resched_eta=round(float(eta2[m].mean()), 4),
                         win_resched=round(float(win2[m].mean()), 4)))
    # t_rec 阈值扫描：每个 t_rec 窗口内 保持 vs 重调度 的平均 η
    scan = []
    for lo in np.arange(5.0, 30.0, 2.5):
        m = np.array([(lo <= x["t_rec"] < lo + 2.5) for x in rows])
        if m.sum() < 5:
            continue
        scan.append(dict(t_rec_lo=round(float(lo), 2), n=int(m.sum()),
                         keep_eta=round(float(eta1[m].mean()), 4),
                         resched_eta=round(float(eta2[m].mean()), 4),
                         keep_tlast=round(float(tl1[m].mean()), 3),
                         resched_tlast=round(float(tl2[m].mean()), 3)))

    hor = []
    for H in (30.0, 45.0, 60.0):
        e1 = np.array([metrics(x["starts_keep"], H)["eta"] for x in rows])
        e2 = np.array([metrics(x["starts_resched"], H)["eta"] for x in rows])
        e0 = np.array([metrics(x["starts_keep_strict"], H)["eta"] for x in rows])
        hor.append(dict(horizon=H, keep_strict_eta=round(float(e0.mean()), 4),
                        keep_eta=round(float(e1.mean()), 4), resched_eta=round(float(e2.mean()), 4),
                        resched_win=round(float((e2 > e1 + 1e-12).mean()), 4)))
    # 按 t_rec 分档的最优策略：词典序 (η↑, t_last↓) 上的胜者
    seg = []
    for lo, hi in [(5, 8), (8, 11), (11, 15), (15, 20), (20, 30.001)]:
        m = np.array([(lo <= x["t_rec"] < hi) for x in rows])
        if not m.any():
            continue
        seg.append(dict(t_rec="[%g,%g)" % (lo, min(hi, 30)), n=int(m.sum()),
                        keep_strict_eta=round(float(eta0[m].mean()), 4),
                        keep_eta=round(float(eta1[m].mean()), 4), resched_eta=round(float(eta2[m].mean()), 4),
                        keep_tlast=round(float(tl1[m].mean()), 3), resched_tlast=round(float(tl2[m].mean()), 3),
                        win_keep=round(float(win1[m].mean()), 4), win_resched=round(float(win2[m].mean()), 4),
                        tie=round(float(np.mean(~win1[m] & ~win2[m])), 4)))

    def hist(x):
        vals, cnt = np.unique(np.round(x, 4), return_counts=True)
        return {str(float(v)): int(c) for v, c in zip(vals, cnt)}

    out = {"_meta": C.meta("q4.py")}
    out["p4"] = dict(
        n_mc=len(rows), seed=SEED, baseline="P2(2) 无距离上限解（p2.json:p2_2.unconstrained）",
        frozen_alerts=sorted(frozen), horizon=HORIZON, r_min_new=round(R_MIN_NEW, 4),
        base_starts={a: round(float(s), 4) for a, s in base["starts"].items()},
        keep_strict=dict(mean_eta=round(float(eta0.mean()), 4), mean_tlast=round(float(tl0.mean()), 3),
                         eta_hist=hist(eta0)),
        keep=dict(mean_eta=round(float(eta1.mean()), 4), mean_tlast=round(float(tl1.mean()), 3),
                  eta_hist=hist(eta1), tlast_p50=round(float(np.median(tl1)), 3),
                  tlast_p90=round(float(np.quantile(tl1, 0.9)), 3)),
        resched=dict(mean_eta=round(float(eta2.mean()), 4), mean_tlast=round(float(tl2.mean()), 3),
                     eta_hist=hist(eta2), tlast_p50=round(float(np.median(tl2)), 3),
                     tlast_p90=round(float(np.quantile(tl2, 0.9)), 3)),
        win_resched=round(float(win2.mean()), 4), win_keep=round(float(win1.mean()), 4),
        tie=round(float(np.mean(~win2 & ~win1)), 4),
        eta_gain_mean=round(float((eta2 - eta1).mean()), 4),
        tlast_gain_mean=round(float((tl1 - tl2).mean()), 3),
        by_t_rec=by_t, by_fail=by_f, scan=scan, by_horizon=hor, by_t_rec_lex=seg,
        n_skip_new_alert=500 - len(rows),
        threshold_rule=("保持原计划不变的必要条件：t_rec 已晚于所有待执行警报的基线开始时刻，"
                        "且故障车不在任何待执行警报的站对中。否则重调度的可行集包含保持方案，"
                        "在 (η, t_last) 词典序下不会更差——样本里 keep 与 resched 不并列的比例即该条件的触发率"),
        samples=samples, rows=rows,
        summary=dict(
            served_last_start={k: round(float(np.mean([max(r["starts_" + k].values()) for r in rows])), 3)
                               for k in ("keep_strict", "keep", "resched")},
            resched_tlast_max=round(float(tl2.max()), 3),
        ),
    )
    C.dump(NAME, out)
    print("N", len(rows), "keep_strict η", round(float(eta0.mean()), 4),
          "keep η", round(float(eta1.mean()), 4), "resched η", round(float(eta2.mean()), 4))
    print("win2", round(float(win2.mean()), 4), "win1", round(float(win1.mean()), 4),
          "tie", round(float(np.mean(~win2 & ~win1)), 4))
    print("t_last", round(float(tl1.mean()), 3), "->", round(float(tl2.mean()), 3))
    for x in by_t:
        print("T", x)
    for x in by_f:
        print("F", x)
    for x in scan:
        print("S", x)


if __name__ == "__main__":
    main()