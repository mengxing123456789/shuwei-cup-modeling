# -*- coding: utf-8 -*-
"""P2：两站交会精度（T2 最优站对）+ 三警报重调度。"""
from __future__ import annotations

import itertools
import json
import math
import os

import numpy as np

import common as C

NAME = "p2.json"
RNG_SEED = 20261120


# ============ (1) 两站交会：精度模型 ============
def pair_terms(s1, s2, name):
    """返回 (r1,r2,sin_gamma,drms)，不建协方差矩阵，便于向量化。"""
    t = C.target_xyz(name)[:2]
    d1 = t - np.asarray(s1, float)
    d2 = t - np.asarray(s2, float)
    r1 = np.hypot(d1[0], d1[1])
    r2 = np.hypot(d2[0], d2[1])
    cross = d1[0] * d2[1] - d1[1] * d2[0]
    sin_g = np.abs(cross) / (r1 * r2)
    drms = C.SIGMA_RAD * np.sqrt(r1**2 + r2**2) / np.maximum(sin_g, 1e-12)
    return r1, r2, sin_g, drms


def los_clearance(station, name):
    """视线越过各楼体时，在楼体 x-y 范围内的最低净空（z - h），取全局最小。"""
    t = C.target_xyz(name)
    s = np.array([station[0], station[1], C.CAM_Z], float)
    best = np.inf
    for b in C.BUILDINGS:
        _, x0, x1, y0, y1, h = b
        best = min(best, _min_clear_in_box(s, t, (x0, x1, y0, y1), h))
    return float(best)


def _min_clear_in_box(s, t, rect, h):
    """线段 s->t 与 rect 的平面交叠区间上，线高的最小值减去楼高（z 沿线段线性，端点即极值）。"""
    x0, x1, y0, y1 = rect
    d = t - s
    t0, t1 = 0.0, 1.0
    for k, (lo, hi) in enumerate(((x0, x1), (y0, y1))):
        if abs(d[k]) < 1e-12:
            if s[k] < lo or s[k] > hi:
                return np.inf
        else:
            a = (lo - s[k]) / d[k]
            b = (hi - s[k]) / d[k]
            t0 = max(t0, min(a, b))
            t1 = min(t1, max(a, b))
    if t0 > t1:
        return np.inf
    z = min(s[2] + t0 * d[2], s[2] + t1 * d[2])
    return float(z - h)


def mc_validate(s1, s2, name, n=100000, sigma_deg=C.SIGMA_DEG, seed=RNG_SEED):
    rng = np.random.default_rng(seed)
    t = C.target_xyz(name)[:2]
    a1 = math.atan2(t[1] - s1[1], t[0] - s1[0])
    a2 = math.atan2(t[1] - s2[1], t[0] - s2[0])
    d1 = rng.normal(0.0, math.radians(sigma_deg), n)
    d2 = rng.normal(0.0, math.radians(sigma_deg), n)
    ux1, uy1 = np.cos(a1 + d1), np.sin(a1 + d1)
    ux2, uy2 = np.cos(a2 + d2), np.sin(a2 + d2)
    dx, dy = s2[0] - s1[0], s2[1] - s1[1]
    den = ux1 * uy2 - uy1 * ux2
    tt = (dx * uy2 - dy * ux2) / den
    px = s1[0] + tt * ux1
    py = s1[1] + tt * uy1
    err = np.hypot(px - t[0], py - t[1])
    r1, r2, sg, drms = pair_terms(s1, s2, name)
    return dict(
        n=n, mc_rms=float(np.sqrt(np.mean(err**2))), mc_mean=float(err.mean()),
        mc_p95=float(np.percentile(err, 95)), mc_p99=float(np.percentile(err, 99)),
        closed_form=float(drms), rel_err=float(abs(np.sqrt(np.mean(err**2)) - drms) / drms),
        cov_sample=np.cov(np.stack([px, py])).tolist(),
    )


def p21(out):
    obs = C.observability("T2", 1.0, "3d")
    m = obs["obs"]
    X, Y = obs["X"], obs["Y"]
    cells = np.stack([X[m], Y[m]], axis=1)
    est = {v: C.travel_est_cells(p, cells) / C.SPEED for v, p in C.VEH0.items()}
    R = {v: est[v] <= 30.0 + 1e-12 for v in C.VEH0}
    tx, ty, tz = C.target_xyz("T2")
    r_min = (tz - C.CAM_Z) / math.tan(math.radians(C.ELEV_MAX))
    drms_lb = C.SIGMA_RAD * math.sqrt(2.0) * r_min

    # 粗筛：2 m 子采样上的可行站对（数值下界，验证不小于解析下界）
    # 2 m 子采样：格心为 *.5，判 (x-0.5)%2==0 且 (y-0.5)%2==0
    sub = (np.mod(cells[:, 0] - 0.5, 2.0) < 1e-9) & (np.mod(cells[:, 1] - 0.5, 2.0) < 1e-9)
    bestc = dict(drms=np.inf)
    for i, j in itertools.combinations(C.VEH0, 2):
        A = cells[R[i] & sub]
        B = cells[R[j] & sub]
        if len(A) == 0 or len(B) == 0:
            continue
        r1, r2, sg, dr = _outer_drms(A, B, (tx, ty))
        k = int(np.argmin(dr))
        if dr.flat[k] < bestc["drms"]:
            ia, ib = divmod(k, len(B))
            bestc = dict(drms=float(dr.flat[k]), pair=[i, j], s1=A[ia].tolist(), s2=B[ib].tolist(),
                         gamma_deg=float(np.degrees(np.arcsin(float(sg.flat[k])))))
    # 解析下界可达性：r=r_min 圆周上找两站，张角 90°，两车均可在 30 s 内到达
    ang = np.arange(0.0, 360.0, 0.02)
    px = tx + r_min * np.cos(np.radians(ang))
    py = ty + r_min * np.sin(np.radians(ang))
    ok = C.geom_ok(px, py) & (~C.los_blocked(px, py, "T2"))
    cells_a = np.stack([px, py], axis=1)
    trav = {v: C.travel_est_cells(p, cells_a) / C.SPEED for v, p in C.VEH0.items()}
    reach = {v: ok & (trav[v] <= 30.0 + 1e-12) for v in C.VEH0}
    attain = []
    for i, j in itertools.permutations(C.VEH0, 2):
        ka = np.where(reach[i])[0]
        for sgn in (+1, -1):
            step = int(round(90.0 / 0.02))  # ang 步长 0.02°，90° 正好对齐
            kb = (ka + sgn * step) % len(ang)
            okb = reach[j][kb]
            for a, bb in zip(ka[okb], kb[okb]):
                attain.append((max(trav[i][a], trav[j][bb]), trav[i][a] + trav[j][bb], i, j,
                               float(px[a]), float(py[a]), float(px[bb]), float(py[bb]), sgn))
    attain.sort(key=lambda z: (round(z[0], 6), round(z[1], 6), z[2], z[3]))
    a = attain[0] if attain else None
    attained_info = None
    if a:
        s1 = (a[4], a[5])
        s2 = (a[6], a[7])
        r1, r2, sg, dr = pair_terms(s1, s2, "T2")
        t1 = C.travel_time(C.VEH0[a[2]], s1)
        t2 = C.travel_time(C.VEH0[a[3]], s2)
        attained_info = dict(
            pair=[a[2], a[3]], s1=[round(s1[0], 4), round(s1[1], 4)], s2=[round(s2[0], 4), round(s2[1], 4)],
            r1=round(float(r1), 4), r2=round(float(r2), 4),
            gamma_deg=round(float(np.degrees(np.arcsin(sg))), 4),
            baseline=round(float(np.hypot(s2[0] - s1[0], s2[1] - s1[1])), 4),
            slew1_s=round(C.slew_time(0.0, 0.0, C.bearing_deg(s1, (tx, ty)), float(C.elev_deg(*s1, "T2"))), 4),
            slew2_s=round(C.slew_time(0.0, 0.0, C.bearing_deg(s2, (tx, ty)), float(C.elev_deg(*s2, "T2"))), 4),
            travel1_s=round(float(t1), 4), travel2_s=round(float(t2), 4),
            drms=round(float(dr), 6),
            elev1=round(float(C.elev_deg(*s1, "T2")), 4), elev2=round(float(C.elev_deg(*s2, "T2")), 4),
            los_clearance1=round(los_clearance(s1, "T2"), 4),
            los_clearance2=round(los_clearance(s2, "T2"), 4),
        )
        # 稳健变体：俯仰留 0.5° 余量（r = (H-2)/tan(79.5)）
        r_rob = (tz - C.CAM_Z) / math.tan(math.radians(C.ELEV_MAX - 0.5))
        attained_info["robust"] = dict(
            margin_deg=0.5, r_eff=round(float(r_rob), 4),
            drms=round(float(C.SIGMA_RAD * math.sqrt(2) * r_rob), 6),
            cost_pct=round(float((r_rob / r_min - 1) * 100), 4),
        )
        mc = mc_validate(s1, s2, "T2", 100000)
    else:
        mc = None

    # 退化：γ 解析扫描（固定 r1=r2=r_min，两站绕目标转，夹角即 γ；不追加可行性筛选）
    sweep = []
    for g in (0.5, 1, 2, 5, 10, 20, 30, 45, 60, 75, 90, 105, 120, 150, 170, 175, 179, 179.5):
        sg = abs(math.sin(math.radians(float(g))))
        sweep.append(dict(gamma_deg=float(g), sin_gamma=round(float(sg), 8),
                          drms=round(float(C.SIGMA_RAD * math.sqrt(2) * r_min / sg), 6)))

    # 边界性：俯仰约束在站址处是否为紧约束（单侧可行）
    frag = []
    if a:
        for name, st in (("s1", (a[4], a[5])), ("s2", (a[6], a[7]))):
            r0 = math.hypot(st[0] - tx, st[1] - ty)
            row = dict(station=name, r=round(float(r0), 6),
                       elev=round(float(C.elev_deg(st[0], st[1], "T2")), 6),
                       elev_ok_inward=[round(float(C.elev_deg(st[0] + e * (tx - st[0]) / r0,
                                                              st[1] + e * (ty - st[1]) / r0, "T2")), 6)
                                       for e in (0.01, 0.05, 0.10)],
                       los_ok=not bool(C.los_blocked(st[0], st[1], "T2")),
                       note="向目标方向任意小位移仰角>80°，硬约束不可行；向外可行")
            frag.append(row)

    out["p2_1"] = dict(
        obs_cells_T2=int(m.sum()),
        r_min_analytic=round(float(r_min), 6),
        drms_lower_bound=round(float(drms_lb), 6),
        coarse_grid=dict(note="2 m 子采样、逐车对枚举的数值最小（应 ≥ 下界）",
                         best=bestc, gap_to_lb=round(float(bestc["drms"] - drms_lb), 6)),
        attained=attained_info,
        n_attaining_pairs=len(attain),
        tie_break="下界可达且解不唯一：取 max(两车到达时间) 最小，再取 sum 最小，再按车号字典序",
        mc_validation=mc,
        gamma_sweep=sweep,
        boundary_fragility=frag,
        calibers=dict(
            drms="位置误差协方差迹的平方根（2σ 半径形式另见 mc_p95）",
            travel="绕障最短路（车心内缩 1.5 m、楼体外扩 1.5 m，可见图 Dijkstra）",
            gamma="两方位线夹角，取 mod 180；gamma_sweep 为解析扫描（r1=r2=r_min，站址未做可行性筛选）",
        ),
    )
    out["p2_1"]["clearance_tier"] = clearance_tier()


def clearance_tier(ds=0.5, cmin=1.0, rmax=20.0):
    """第三档：两站视线与楼顶竖直余隙均 ≥ cmin 的最小 DRMS（0.5 m 网格 + 0.05 m 局部细化）。"""
    obs = C.observability("T2", ds, "3d")
    X, Y = obs["X"][obs["obs"]], obs["Y"][obs["obs"]]
    clr = np.array([los_clearance((float(x), float(y)), "T2") for x, y in zip(X, Y)])
    tx, ty, tz = C.target_xyz("T2")
    r = np.hypot(tx - X, ty - Y)
    keep = (clr >= cmin) & (r <= rmax)
    X, Y = X[keep], Y[keep]
    best = (1e9, None, None, 0.0, 0.0, 0.0)
    for i in range(len(X) - 1):
        d1x, d1y = tx - X[i], ty - Y[i]
        r1 = math.hypot(d1x, d1y)
        d2x, d2y = tx - X[i + 1:], ty - Y[i + 1:]
        r2 = np.hypot(d2x, d2y)
        sin_g = np.abs(d1x * d2y - d1y * d2x) / np.maximum(r1 * r2, 1e-12)
        dr = C.SIGMA_RAD * np.sqrt(r1**2 + r2**2) / np.maximum(sin_g, 1e-12)
        j = int(np.argmin(dr))
        if dr[j] < best[0]:
            best = (float(dr[j]), (float(X[i]), float(Y[i])), (float(X[i + 1 + j]), float(Y[i + 1 + j])),
                    float(r1), float(r2[j]), float(np.degrees(np.arcsin(min(1.0, sin_g[j])))))

    def local(s, half=0.6, step=0.05):
        xs = np.arange(s[0] - half, s[0] + half + 1e-9, step)
        ys = np.arange(s[1] - half, s[1] + half + 1e-9, step)
        X2, Y2 = np.meshgrid(xs, ys)
        X2, Y2 = X2.ravel(), Y2.ravel()
        ok = C.geom_ok(X2, Y2) & C.elev_ok(X2, Y2, "T2") & (~C.los_blocked(X2, Y2, "T2"))
        X2, Y2 = X2[ok], Y2[ok]
        cl2 = np.array([los_clearance((float(x), float(y)), "T2") for x, y in zip(X2, Y2)])
        k2 = cl2 >= cmin
        return X2[k2], Y2[k2], cl2[k2]

    Xa, Ya, Ca = local(best[1])
    Xb, Yb, Cb = local(best[2])
    fine = (1e9, None, None, 0.0, 0.0, 0.0, 0.0, 0.0)
    for i in range(len(Xa)):
        d1x, d1y = tx - Xa[i], ty - Ya[i]
        r1 = math.hypot(d1x, d1y)
        d2x, d2y = tx - Xb, ty - Yb
        r2 = np.hypot(d2x, d2y)
        sin_g = np.abs(d1x * d2y - d1y * d2x) / np.maximum(r1 * r2, 1e-12)
        dr = C.SIGMA_RAD * np.sqrt(r1**2 + r2**2) / np.maximum(sin_g, 1e-12)
        j = int(np.argmin(dr))
        if dr[j] < fine[0]:
            fine = (float(dr[j]), (float(Xa[i]), float(Ya[i])), (float(Xb[j]), float(Yb[j])), float(r1),
                    float(r2[j]), float(np.degrees(np.arcsin(min(1.0, sin_g[j])))), float(Ca[i]), float(Cb[j]))
    s1, s2 = fine[1], fine[2]
    cand = []
    for s in (s1, s2):
        cand.append(sorted((C.travel_time(C.VEH0[v], s), v) for v in C.VEH0))
    # 两站分别给不同车：枚举候选配对，取 max(到达) 最小
    assign = None
    bestmax = 1e9
    for (ta, va) in cand[0][:3]:
        for (tb, vb) in cand[1][:3]:
            if va == vb:
                continue
            mx = max(ta, tb)
            if mx < bestmax:
                bestmax = mx
                assign = [(va, s1, ta), (vb, s2, tb)]
    return dict(cmin_m=cmin, grid_step_m=ds, refine_step_m=0.05,
                drms=round(float(fine[0]), 6), s1=[round(s1[0], 3), round(s1[1], 3)],
                s2=[round(s2[0], 3), round(s2[1], 3)],
                r1=round(fine[3], 4), r2=round(fine[4], 4), gamma_deg=round(fine[5], 4),
                clearance1_m=round(fine[6], 4), clearance2_m=round(fine[7], 4),
                penalty_vs_lb_pct=round((fine[0] / (C.SIGMA_RAD * math.sqrt(2) * ((tz - C.CAM_Z) / math.tan(math.radians(C.ELEV_MAX)))) - 1) * 100, 4),
                assign=[dict(vehicle=v, station=[round(p[0], 3), round(p[1], 3)], travel_s=round(t, 3))
                        for v, p, t in assign] if assign else None)


def _outer_drms(A, B, t):
    dxa = t[0] - A[:, 0]
    dya = t[1] - A[:, 1]
    ra = np.hypot(dxa, dya)
    dxb = t[0] - B[:, 0]
    dyb = t[1] - B[:, 1]
    rb = np.hypot(dxb, dyb)
    cross = dxa[:, None] * dyb[None, :] - dya[:, None] * dxb[None, :]
    sg = np.abs(cross) / (ra[:, None] * rb[None, :])
    dr = C.SIGMA_RAD * np.sqrt(ra[:, None] ** 2 + rb[None, :] ** 2) / np.maximum(sg, 1e-12)
    return ra, rb, sg, dr


def main():
    out = {"_meta": C.meta("q2.py")}
    p21(out)
    T = stations_table(3.0)
    P = prep_missions(T, topn=25)
    print("stations per alert:", {t: len(T[t]["cells"]) for t in C.TARGETS})
    best = p22(out, T, P)
    C.dump(NAME, out)
    a = out["p2_1"]["attained"]
    print("P2(1) 下界", out["p2_1"]["drms_lower_bound"], "达标站对", a)
    print("coarse", out["p2_1"]["coarse_grid"]["best"], "gap", out["p2_1"]["coarse_grid"]["gap_to_lb"])
    print("MC", {k: out["p2_1"]["mc_validation"][k] for k in ("mc_rms","closed_form","rel_err","mc_p95","mc_p99")})
    print("n_attaining", out["p2_1"]["n_attaining_pairs"])
    e = out["p2_2"]["exact"]
    g = out["p2_2"]["greedy"]
    print("P2(2) exact makespan", e["makespan"], e["assign"])
    print("      starts", e["starts"])
    print("      greedy", g["makespan"], g["starts"], "gap", out["p2_2"]["gap_s"], out["p2_2"]["gap_rel"])



# ============ (2) 三警报调度 ============
def stations_table(step=3.0, cap=np.inf):
    T = {}
    for t in C.TARGETS:
        o = C.observability(t, 1.0, "3d")
        m = o["obs"]
        cells = np.stack([o["X"][m], o["Y"][m]], axis=1)
        sel = (np.mod(cells[:, 0] - 0.5, step) < 1e-9) & (np.mod(cells[:, 1] - 0.5, step) < 1e-9)
        cells = cells[sel]
        tx, ty, tz = C.target_xyz(t)
        r = np.hypot(tx - cells[:, 0], ty - cells[:, 1])
        keep = r <= cap + 1e-9
        cells, r = cells[keep], r[keep]
        pan = np.degrees(np.arctan2(ty - cells[:, 1], tx - cells[:, 0])) % 360.0
        elev = np.degrees(np.arctan2(tz - C.CAM_Z, r))
        slew = np.maximum(np.abs(C.wrap180(pan)), np.abs(elev)) / C.RATE
        T[t] = dict(cells=cells, r=r, pan=pan, elev=elev, slew=slew, reset=slew.copy())
    return T


def prep_missions(T, topn=25):
    tcells = {t: T[t]["cells"] for t in C.TARGETS}
    trav0 = {}
    for v, p in C.VEH0.items():
        for t in C.TARGETS:
            trav0[(v, t)] = C.travel_est_cells(p, tcells[t]) / C.SPEED
    ready0 = {(v, t): trav0[(v, t)] + T[t]["slew"] for v in C.VEH0 for t in C.TARGETS}
    best1 = {k: int(np.argmin(ready0[k])) for k in ready0}
    leg = {}
    for v in C.VEH0:
        for A in C.TARGETS:
            for B in C.TARGETS:
                if A == B:
                    continue
                cand = np.argsort(ready0[(v, A)], kind="stable")[:topn]
                rows = []
                for ia in cand:
                    s = tcells[A][ia]
                    tot = C.travel_est_cells(s, tcells[B]) / C.SPEED + T[B]["slew"]
                    ib = int(np.argmin(tot))
                    rows.append((float(tot[ib]), int(ia), ib, float(tot[ib] - T[B]["slew"][ib])))
                leg[(v, A, B)] = rows
    return dict(T=T, trav0=trav0, ready0=ready0, best1=best1, leg=leg)


def _leg(P, v, A, B, ia):
    rows = P["leg"][(v, A, B)]
    row = next((r for r in rows if r[1] == ia), None)
    if row is None:
        row = min(rows, key=lambda r: abs(r[1] - ia))
    return row  # (tot, ia, ib, tt)


def eval_plan(assign, order, P, override=None):
    """override: {(v,alert): station_idx} 只作用于该车的第一段任务。"""
    override = override or {}
    seq = {v: [t for t in C.TARGETS if v in assign[t]] for v in C.VEH0}
    for v in C.VEH0:
        seq[v].sort(key=lambda t: (order.get(v, [t]).index(t) if t in order.get(v, []) else 99))
    starts = {}
    for _ in range(12):
        st = {}
        for v in C.VEH0:
            f, cur = 0.0, None
            for k, t in enumerate(seq[v]):
                if k == 0:
                    ia = override.get((v, t), P["best1"][(v, t)])
                    rd, arr = float(P["ready0"][(v, t)][ia]), float(P["trav0"][(v, t)][ia])
                else:
                    tot, ia0, ib, tt = _leg(P, v, cur, t, override.get((v, cur), P["best1"][(v, cur)]))
                    rd, ia, arr = f + tot, ib, f + tt
                st[(v, t)] = (float(rd), int(ia), float(arr))
                f = max(rd, starts.get(t, 0.0)) + C.T_OBS + float(P["T"][t]["reset"][ia])
                cur = t
        new = {t: max(st[(assign[t][0], t)][0], st[(assign[t][1], t)][0]) for t in C.TARGETS}
        if all(abs(new[t] - starts.get(t, -1e9)) < 1e-9 for t in C.TARGETS):
            return seq, new, st
        starts = new
    return None, None, None


def timeline_of(assign, order, P, starts, st, seq, override=None):
    T = P["T"]
    override = override or {}
    tl = {v: [] for v in C.VEH0}
    for v in C.VEH0:
        f, cur = 0.0, None
        for k, t in enumerate(seq[v]):
            rd, ia, arr = st[(v, t)]
            if k > 0:
                tot, ia0, ib, tt = _leg(P, v, cur, t, override.get((v, cur), P["best1"][(v, cur)]))
                ia, arr = ib, f + tt
            s = starts[t]
            slew = T[t]["slew"][ia]
            obs_end = s + C.T_OBS
            rst = T[t]["reset"][ia]
            tl[v].append(dict(alert=t, station=[round(float(x), 3) for x in T[t]["cells"][ia]],
                              r=round(float(T[t]["r"][ia]), 3),
                              depart=round(f, 4), arrive=round(arr, 4), slew=round(slew, 4),
                              ready=round(arr + slew, 4), wait=round(max(0.0, s - arr - slew), 4),
                              obs_start=round(s, 4), obs_end=round(obs_end, 4), reset=round(rst, 4),
                              free=round(obs_end + rst, 4)))
            f, cur = obs_end + rst, t
    return tl


def solve_exact(P):
    """指派与顺序穷尽枚举；再用坐标下降精修多任务车的首站。"""
    best = dict(makespan=np.inf)
    for combo in itertools.product(list(itertools.combinations(C.VEH0, 2)), repeat=3):
        assign = dict(zip(C.TARGETS, combo))
        multi = [v for v in C.VEH0 if sum(v in p for p in combo) >= 2]
        orders = [{}]
        for v in multi:
            al = [t for t in C.TARGETS if v in assign[t]]
            orders = [dict(o, **{v: list(pm)}) for o in orders for pm in itertools.permutations(al)]
        for o in orders:
            seq, starts, st = eval_plan(assign, o, P)
            if starts is None:
                continue
            mk = max(starts.values())
            if mk < best["makespan"] - 1e-9:
                best = dict(makespan=mk, assign={t: list(assign[t]) for t in C.TARGETS}, order=dict(o),
                            starts=dict(starts), st=st, seq=seq, override={})
    if best["makespan"] == np.inf:
        return None
    # 坐标下降：对多任务车的首站，在前 25 个"最早可达"候选中重选
    assign, order = best["assign"], best["order"]
    multi = [v for v in C.VEH0 if len(best["seq"][v]) >= 2]
    for _ in range(2):
        improved = False
        for v in multi:
            A = best["seq"][v][0]
            cur_ia = best["override"].get((v, A), P["best1"][(v, A)])
            cand = list(np.argsort(P["ready0"][(v, A)], kind="stable")[:25])
            for ia in cand:
                ov = dict(best["override"])
                ov[(v, A)] = int(ia)
                seq, starts, st = eval_plan(assign, order, P, ov)
                if starts is None:
                    continue
                mk = max(starts.values())
                if mk < best["makespan"] - 1e-9:
                    best = dict(makespan=mk, assign=assign, order=order, starts=dict(starts), st=st,
                                seq=seq, override=ov)
                    improved = True
        if not improved:
            break
    best["timeline"] = timeline_of(best["assign"], best["order"], P, best["starts"], best["st"],
                                   best["seq"], best["override"])
    return best


def plan_drms(tl):
    out = {}
    for t in C.TARGETS:
        ss = [(e["station"], v) for v in tl for e in tl[v] if e["alert"] == t]
        if len(ss) != 2:
            out[t] = None
            continue
        (s1, v1), (s2, v2) = ss
        d = C.drms_pair(s1, s2, t)
        out[t] = dict(vehicles=[v1, v2], r1=round(d["r1"], 3), r2=round(d["r2"], 3),
                      gamma_deg=round(d["gamma_deg"], 3), drms=round(d["drms"], 4))
    return out


def solve_greedy(P):
    """最近优先：警报按 T1->T2->T3 顺序，每次取"当前可最早开始"的两台车。"""
    T = P["T"]
    assign, starts, tl = {}, {}, {v: [] for v in C.VEH0}
    last, free = {}, {v: 0.0 for v in C.VEH0}
    for t in C.TARGETS:
        rank = []
        for v in C.VEH0:
            if v in last:
                rows = P["leg"][(v, last[v], t)]
                pick = next((r for r in rows if r[1] == P["best1"][(v, last[v])]), rows[0])
                rank.append((free[v] + pick[0], v, pick[2], pick[3]))
            else:
                ia = P["best1"][(v, t)]
                rank.append((P["ready0"][(v, t)][ia], v, ia, P["trav0"][(v, t)][ia]))
        rank.sort(key=lambda z: (z[0], z[1]))
        pair = rank[:2]
        assign[t] = [pair[0][1], pair[1][1]]
        s = max(x[0] for x in pair)
        starts[t] = s
        for (rd, v, ia, trav) in pair:
            tl[v].append(dict(alert=t, station=[round(float(x), 3) for x in T[t]["cells"][ia]],
                              r=round(float(T[t]["r"][ia]), 3), obs_start=round(s, 4),
                              obs_end=round(s + C.T_OBS, 4), reset=round(T[t]["reset"][ia], 4)))
            free[v] = s + C.T_OBS + T[t]["reset"][ia]
            last[v] = t
    return dict(makespan=max(starts.values()), starts=starts, assign=assign,
                order={v: [e["alert"] for e in tl[v]] for v in C.VEH0 if tl[v]},
                timeline=tl, drms=plan_drms(tl))


def refine_around(tl, cap, half=3.0, step=0.25):
    """把 3 m 解用到的站址在 ±half m 内铺 step 细网格，重解一次（检验网格依赖性）。"""
    tab = {}
    for t in C.TARGETS:
        pts = sorted({tuple(e["station"]) for v in C.VEH0 for e in tl.get(v, []) if e["alert"] == t})
        tx, ty, tz = C.target_xyz(t)
        cand = []
        for (x0, y0) in pts:
            xs = np.arange(x0 - half, x0 + half + 1e-9, step)
            ys = np.arange(y0 - half, y0 + half + 1e-9, step)
            X, Y = np.meshgrid(xs, ys)
            ok = C.geom_ok(X, Y) & C.elev_ok(X, Y, t) & (~C.los_blocked(X, Y, t))
            cand.append(np.stack([X[ok], Y[ok]], axis=1))
        c = np.vstack(cand) if cand else np.zeros((0, 2))
        r = np.hypot(tx - c[:, 0], ty - c[:, 1])
        keep = r <= cap + 1e-9
        c, r = c[keep], r[keep]
        pan = np.degrees(np.arctan2(ty - c[:, 1], tx - c[:, 0])) % 360.0
        elev = np.degrees(np.arctan2(tz - C.CAM_Z, r))
        slew = np.maximum(np.abs(C.wrap180(pan)), np.abs(elev)) / C.RATE
        tab[t] = dict(cells=c, r=r, pan=pan, elev=elev, slew=slew, reset=slew.copy())
    P = prep_missions(tab, topn=25)
    return solve_exact(P)


CAPS = [(1e9, "unconstrained"), (40.0, 40), (30.0, 30), (20.0, 20), (15.0, 15), (10.0, 10)]


def p22(out):
    rows = []
    keep = {}
    grid_refine = {}
    for cap, tag in CAPS:
        T = stations_table(3.0, cap)
        P = prep_missions(T, topn=25)
        ex = solve_exact(P)
        gr = solve_greedy(P)
        # 0.25 m 局部细化：3 m 栅格解是否网格依赖
        before = _stations(ex["timeline"])
        mk0 = float(ex["makespan"])
        rf = refine_around(ex["timeline"], cap) if ex else None
        if rf is not None and float(rf["makespan"]) < mk0 - 1e-9:
            ex = rf
        grid_refine[("inf" if cap > 1e8 else str(tag))] = dict(
            makespan_3m=round(mk0, 4), makespan_refined=round(float(ex["makespan"]), 4),
            delta_s=round(mk0 - float(ex["makespan"]), 4),
            stations_3m=before, stations_refined=_stations(ex["timeline"]))
        dr_ex = plan_drms(ex["timeline"])
        two_ok = all(bool(x) and np.isfinite(x["drms"]) for x in dr_ex.values())
        row = dict(cap_m=("inf" if cap > 1e8 else cap),
                   n_stations={t: len(T[t]["cells"]) for t in C.TARGETS},
                   exact_makespan=round(float(ex["makespan"]), 4),
                   exact_makespan_3m_grid=round(mk0, 4),
                   exact_starts={t: round(float(ex["starts"][t]), 4) for t in C.TARGETS},
                   exact_assign=ex["assign"], exact_order=ex["order"],
                   greedy_makespan=round(float(gr["makespan"]), 4),
                   greedy_assign=gr["assign"],
                   gap_s=round(float(gr["makespan"] - ex["makespan"]), 4),
                   gap_s_same_3m_caliber=round(float(gr["makespan"] - mk0), 4),
                   gap_rel=round(float(gr["makespan"] / ex["makespan"] - 1), 6),
                   drms_exact=dr_ex,
                   drms_greedy=gr["drms"],
                   two_station_ok=bool(two_ok),
                   note=("两车被迫共用同一站，双站交会退化（γ=0），该档按不可行处理" if not two_ok else ""))
        rows.append(row)
        if tag in ("unconstrained", 20):
            keep[tag] = dict(timeline=ex["timeline"], assign=ex["assign"], starts=ex["starts"],
                             order=ex["order"], makespan=ex["makespan"])
    out["p2_2"] = dict(
        rows=rows,
        unconstrained=keep["unconstrained"],
        cap20=keep.get(20),
        objective="min max_t start_t（题面 162 行）",
        calibers=dict(station="3 m 站址栅格（可观测域内）", travel="绕障估算（一折点精确，可见图角点）",
                      cap_m="站址到目标的水平距离上限；inf 为不设限",
                      drms="两站方位交会协方差迹的平方根（P2(1) 模型）"),
        finding="无距离约束时 makespan 最优解把车留在门口观测（r≈70 m），DRMS 退化到米级；"
                "R_cap 是把精度换回来的政策旋钮",
    )
    out["p2_2"]["grid_refine"] = grid_refine
    return out["p2_2"]


def _stations(tl):
    return {t: sorted({tuple(round(float(x), 3) for x in e["station"])
                       for v in C.VEH0 for e in tl.get(v, []) if e["alert"] == t}) for t in C.TARGETS}


def apply_grid_refine(p2):
    """对 inf 与 cap20 两档做 0.25 m 局部细化：检验 3 m 栅格解是否网格依赖。"""
    gr = {}
    for tag, cap in (("unconstrained", 1e9), ("cap20", 20.0)):
        src = p2.get(tag)
        if not src:
            continue
        before = _stations(src["timeline"])
        rf = refine_around(src["timeline"], cap)
        if rf is None:
            gr[tag] = dict(makespan_refined=None, delta_s=None, note="细化邻域内无可行解")
            continue
        orig = float(src["makespan"])
        delta = orig - float(rf["makespan"])
        rec = dict(makespan_before=round(orig, 4), makespan_refined=round(float(rf["makespan"]), 4),
                   delta_s=round(delta, 4), stations_before=before, stations_after=_stations(rf["timeline"]),
                   replaced_row=False)
        if delta > 0.05:
            src.update(dict(timeline=rf["timeline"], assign=rf["assign"], starts=rf["starts"],
                            order=rf["order"], makespan=rf["makespan"]))
            want = "inf" if tag == "unconstrained" else 20
            row = next(r for r in p2["rows"] if r["cap_m"] == want)
            row["exact_makespan"] = round(float(rf["makespan"]), 4)
            row["exact_starts"] = {t: round(float(rf["starts"][t]), 4) for t in C.TARGETS}
            row["exact_assign"] = rf["assign"]
            row["exact_order"] = rf["order"]
            row["drms_exact"] = plan_drms(rf["timeline"])
            row["gap_s"] = round(float(row["greedy_makespan"] - rf["makespan"]), 4)
            row["gap_rel"] = round(float(row["greedy_makespan"] / rf["makespan"] - 1), 6)
            rec["replaced_row"] = True
        gr[tag] = rec
    p2["grid_refine"] = gr
    p2["calibers"]["station"] = "3 m 站址栅格；unconstrained 与 cap20 另做 0.25 m 局部细化复核（±3 m 邻域）"
    return gr


def main():
    out = {"_meta": C.meta("q2.py")}
    p21(out)
    p22(out)
    C.dump(NAME, out)
    a = out["p2_1"]["attained"]
    print("P2(1) 下界", out["p2_1"]["drms_lower_bound"], "达标站对", a)
    print("coarse", out["p2_1"]["coarse_grid"]["best"], "gap", out["p2_1"]["coarse_grid"]["gap_to_lb"])
    print("MC", {k: out["p2_1"]["mc_validation"][k] for k in ("mc_rms", "closed_form", "rel_err", "mc_p95")})
    for r in out["p2_2"]["rows"]:
        print(f"cap={r['cap_m']:>4} n={sum(r['n_stations'].values()):4d}  makespan={r['exact_makespan']:7.3f} "
              f"greedy={r['greedy_makespan']:7.3f} gap={r['gap_s']:6.3f}  "
              f"drms={[round(r['drms_exact'][t]['drms'],3) if r['drms_exact'][t] else None for t in C.TARGETS]}")


if __name__ == "__main__":
    main()
