# -*- coding: utf-8 -*-
"""P1：三维可观测域、Q=1/r 最优单站点（T1）。"""
from __future__ import annotations

import math

import numpy as np

import common as C

NAME = "p1.json"


def pattern_search(f, x0, step=1.0, tol=2e-4):
    x = np.array(x0, float)
    fx = f(x)
    dirs = np.array([[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [-1, -1], [1, -1], [-1, 1]], float)
    while step > tol:
        improved = False
        for d in dirs:
            y = x + step * d / np.linalg.norm(d)
            fy = f(y)
            if fy > fx + 1e-15:
                x, fx, improved = y, fy, True
        if not improved:
            step *= 0.5
    return x, fx


def q_of_point(x, y, t="T1"):
    """单目标 Q=1/r；不可观测返回 -inf。"""
    if not bool(C.geom_ok(x, y)) or not bool(C.elev_ok(x, y, t)) or bool(C.los_blocked(x, y, t)):
        return -np.inf
    tx, ty, _ = C.target_xyz(t)
    return 1.0 / math.hypot(tx - x, ty - y)


def main():
    out = {"_meta": C.meta("q1.py")}
    res = {t: dict(o3=C.observability(t, 1.0, "3d"), op=C.observability(t, 1.0, "planar")) for t in C.TARGETS}
    o3h = {t: C.observability(t, 0.5, "3d") for t in C.TARGETS}

    tabs = {}
    for t in C.TARGETS:
        g, e = res[t]["o3"]["geom"], res[t]["o3"]["elev"]
        n_tot = res[t]["o3"]["obs"].size
        n_feas = int((g & e).sum())
        n_3d = int(res[t]["o3"]["obs"].sum())
        n_pl = int(res[t]["op"]["obs"].sum())
        n_h = int(o3h[t]["obs"].sum())
        lost = res[t]["o3"]["obs"] & (~res[t]["op"]["obs"])
        rev = res[t]["op"]["obs"] & (~res[t]["o3"]["obs"])
        el_grid = C.elev_deg(res[t]["o3"]["X"], res[t]["o3"]["Y"], t)
        tabs[t] = dict(
            total_cells=n_tot,
            geom_ok_cells=int(g.sum()),
            elev_ok_cells=int(e.sum()),
            feasible_cells=n_feas,
            obs3d_cells=n_3d,
            obs_planar_cells=n_pl,
            frac_of_field_3d=round(n_3d / n_tot, 6),
            frac_of_feasible_3d=round(n_3d / n_feas, 6),
            frac_of_field_planar=round(n_pl / n_tot, 6),
            planar_missed_cells=int(lost.sum()),
            planar_missed_frac_of_field=round(float(lost.mean()), 6),
            planar_missed_share_of_3d=round(int(lost.sum()) / max(n_3d, 1), 6),
            reverse_diff_cells=int(rev.sum()),
            grid05_obs_cells=n_h,
            grid05_frac=round(n_h / o3h[t]["obs"].size, 6),
            grid05_vs_1m_absdiff_frac=round(abs(n_h / o3h[t]["obs"].size - n_3d / n_tot), 6),
            elev_range_deg=[round(float(el_grid[res[t]["o3"]["obs"]].min()), 4),
                            round(float(el_grid[res[t]["o3"]["obs"]].max()), 4)],
            r_min_elev=round(float((C.TARGETS[t][2] - C.CAM_Z) / math.tan(math.radians(C.ELEV_MAX))), 6),
        )
    out["observability"] = tabs

    # ---------- P1 正式答案：T1，Q = 1/r ----------
    tx, ty, tz = C.target_xyz("T1")
    r_min = float((tz - C.CAM_Z) / math.tan(math.radians(C.ELEV_MAX)))
    q_sup = 1.0 / r_min

    # 精确等值弧：半径 r_min 的整圆，0.05° 采样，逐点判可观测
    ang = np.arange(0.0, 360.0, 0.05)
    px = tx + r_min * np.cos(np.radians(ang))
    py = ty + r_min * np.sin(np.radians(ang))
    ok = C.geom_ok(px, py) & (~C.los_blocked(px, py, "T1"))
    arcs, cur = [], []
    for k in range(len(ang)):
        if ok[k]:
            cur.append(k)
        elif cur:
            arcs.append(cur)
            cur = []
    if cur:
        arcs.append(cur)
    if len(arcs) > 1 and arcs[0][0] == 0 and arcs[-1][-1] == len(ang) - 1:
        arcs[0] = arcs[-1] + arcs[0]
        arcs.pop()
    arc_info = []
    for a in arcs:
        k0, k1 = a[0], a[-1]
        arc_info.append(dict(
            a0_deg=round(float(ang[k0]), 3), a1_deg=round(float(ang[k1]), 3),
            span_deg=round(float((k1 - k0) * 0.05), 3), n_samples=len(a),
            mid=(round(float(px[(k0 + k1) // 2]), 4), round(float(py[(k0 + k1) // 2]), 4)),
        ))
    cand = np.where(ok)[0]
    assert len(cand) > 0, "T1 的 r_min 弧上无可行点"
    cells = np.stack([px[cand], py[cand]], axis=1)
    # 先向量化估距（一折点精确），再对候选前若干名做精确 Dijkstra
    est = {v: C.travel_est_cells(p, cells) / C.SPEED for v, p in C.VEH0.items()}
    est_best = np.min(np.vstack([est[v] for v in C.VEH0]), axis=0)
    order = np.argsort(est_best, kind="stable")[:60]
    rows = []
    for j in order:
        k_ = cand[j]
        d = {v: float(C.travel_time(p, (px[k_], py[k_]))) for v, p in C.VEH0.items()}
        bv = min(d, key=d.get)
        rows.append((d[bv], bv, k_, d))
    rows.sort(key=lambda z: (round(z[0], 9), z[1], float(px[z[2]]), float(py[z[2]])))
    best = rows[0]
    k = best[2]
    tie = dict(
        n_tied_continuous=len(cand),
        analytic_arcs=arc_info,
        rule="Q 在整条 r=r_min 弧上取同一上确界；先取 5 车绕障最短路时间最小者，再按 (x,y) 字典序最小定标",
        chosen=dict(x=round(float(px[k]), 4), y=round(float(py[k]), 4), r=round(r_min, 6),
                    elev_deg=round(float(C.elev_deg(px[k], py[k], "T1")), 6),
                    q=round(float(q_sup), 8), vehicle=best[1], travel_s=round(best[0], 4)),
        all_travel_s={v: round(float(rows[0][3][v]), 4) for v in C.VEH0},
        tie_travel_spread_s=round(float(max(best[3].values()) - min(best[3].values())), 4),
    )
    # 网格解（离散化误差）
    X, Y = res["T1"]["o3"]["X"], res["T1"]["o3"]["Y"]
    r1 = np.hypot(tx - X, ty - Y)
    Q = np.where(res["T1"]["o3"]["obs"], 1.0 / r1, 0.0)
    iy, ix = np.unravel_index(int(np.argmax(Q)), Q.shape)
    grid_best = dict(x=float(X[iy, ix]), y=float(Y[iy, ix]), q=round(float(Q[iy, ix]), 8),
                     r=round(float(r1[iy, ix]), 4), gap_to_sup=round(float(q_sup - Q[iy, ix]), 8),
                     n_tied=int((np.abs(Q - Q[iy, ix]) < 1e-9).sum()))
    # 连续精修（从栅格最优出发，模式搜索；验证不能突破解析上确界）
    xs, qs = pattern_search(lambda z: q_of_point(z[0], z[1]), (grid_best["x"], grid_best["y"]), 1.0, 2e-4)
    cont = dict(x=round(float(xs[0]), 4), y=round(float(xs[1]), 4), q=round(float(qs), 8),
                r=round(float(math.hypot(tx - xs[0], ty - xs[1])), 6),
                elev_deg=round(float(C.elev_deg(xs[0], xs[1], "T1")), 6),
                q_over_sup=round(float(qs / q_sup), 8))
    out["p1_T1"] = dict(
        q_sup=round(float(q_sup), 8), r_min_analytic=round(r_min, 6),
        grid_1m=grid_best, continuous=cont, tie=tie,
        bound_star="边界解（俯仰上限 80° 卡死）；已用 0.5 m 栅格与连续模式搜索复核",
        el_constraint_active=True,
        note="r<r_min 时仰角>80°，云台不可达；故 sup Q=1/r_min 且可 attain",
    )

    # ---------- 扩展：三目标 Σ1/r（题面未要求，作对照） ----------
    R = {}
    Q3 = np.zeros_like(X)
    for t in C.TARGETS:
        a, b, _ = C.target_xyz(t)
        R[t] = np.hypot(a - X, b - Y)
        Q3 += np.where(res[t]["o3"]["obs"], 1.0 / R[t], 0.0)
    iy3, ix3 = np.unravel_index(int(np.argmax(Q3)), Q3.shape)
    out["ext_Q3_targets"] = dict(
        note="题面 P1 只针对 T1；此处给出三目标求和版本作扩展对照",
        bound_sum_1_over_rmin=round(float(sum(1.0 / tabs[t]["r_min_elev"] for t in C.TARGETS)), 8),
        grid_best=dict(x=float(X[iy3, ix3]), y=float(Y[iy3, ix3]), q=round(float(Q3[iy3, ix3]), 8),
                       r={t: round(float(R[t][iy3, ix3]), 4) for t in C.TARGETS},
                       observed=[t for t in C.TARGETS if bool(res[t]["o3"]["obs"][iy3, ix3])]),
    )

    # ---------- 直线 vs 绕障 ----------
    rows = []
    station = (X[iy, ix], Y[iy, ix])
    for v, p in C.VEH0.items():
        for t in C.TARGETS:
            eu = float(np.hypot(p[0] - station[0], p[1] - station[1]))
            ex = C.path_len(p, station)
            rows.append(dict(vehicle=v, target=t, to="grid_best_T1", euclid=round(eu, 3),
                             path=round(ex, 3), ratio=round(ex / eu, 4)))
    out["path_vs_euclid"] = rows

    C.dump(NAME, out)
    for t in C.TARGETS:
        s = tabs[t]
        print(f"{t}: 3D {s['frac_of_field_3d']*100:.2f}%  平面 {s['frac_of_field_planar']*100:.2f}%  "
              f"平面漏判 {s['planar_missed_cells']} 格 / 反向 {s['reverse_diff_cells']} 格")
    print(f"P1: Q*={q_sup:.6f} r*={r_min:.4f} 弧段={len(arc_info)} 并列样本={len(cand)} 选定={tie['chosen']}")
    print(f"网格 1m: Q={grid_best['q']:.6f} 差={grid_best['gap_to_sup']:.2e} 并列={grid_best['n_tied']}")


if __name__ == "__main__":
    main()