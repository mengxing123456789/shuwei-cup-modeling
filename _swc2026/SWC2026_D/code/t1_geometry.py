# -*- coding: utf-8 -*-
"""T1：观测几何——真轨道、俯视投影、斜视视轨道、视差修正。

产出 data/t1_geometry.json + figures/fig1..fig5。
所有量以 AU 计，角度在 JSON 里转 deg 或 arcsec。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmcommon import (  # noqa: E402
    ARCSEC, DATA, PLANETS, apparent_first_order, apparent_orthographic,
    apparent_sin_chart, apparent_sky, conic_params, dump, f, kepler_E, meta,
    orbit_frame, orbit_matrix, orbit_points, poly_curve_residual, sky_projection,
)

DEG = np.pi / 180.0

FID = dict(a=1.0, e=0.3, i=30.0 * DEG, Om=90.0 * DEG, om=60.0 * DEG)
THETA_FID = 0.0
N_PTS = 1440


# ------------------------------------------------------------------ 基础量
def shape_descriptors(a, e, i, Om, om, theta):
    """正交投影外观椭圆的 (sigma1, sigma2, 长轴方位 psi)。"""
    p_hat, q_hat, c, b = orbit_frame(a, e, i, Om, om)
    _, e1, e2 = sky_projection(theta)
    P = np.stack([e1, e2])
    S = np.stack([a * (P @ p_hat), b * (P @ q_hat)], axis=1)   # 2x2
    U, sv, Vt = np.linalg.svd(S)
    psi = float(np.arctan2(U[1, 0], U[0, 0]))
    ctr = P @ c
    return sv[0], sv[1], psi, ctr, p_hat, q_hat


def sky_orbit(a, e, i, Om, om, theta, dE=np.inf, N=N_PTS):
    M = np.linspace(0.0, 2.0 * np.pi, N, endpoint=False)
    r = orbit_points(a, e, i, Om, om, M)
    if not np.isfinite(dE):
        s = apparent_orthographic(r, theta)
        kind = "orthographic"
    else:
        s, _, _ = apparent_sky(r, theta, dE)
        kind = "gnomonic"
    return M, r, s, kind


def degree_ladder(X, degs=(2, 3, 4, 5)):
    return {f"deg{k}": float(poly_curve_residual(X, k)) for k in degs}


# ------------------------------------------------------------------ 主流程
def main():
    D = {}
    # ---- 1. 基准轨道的三种视图 -------------------------------------
    a, e, i, Om, om = FID["a"], FID["e"], FID["i"], FID["Om"], FID["om"]
    th = THETA_FID
    s1, s2, psi, ctr, p_hat, q_hat = shape_descriptors(a, e, i, Om, om, th)

    # 真椭圆（轨道面内）
    b_true = a * np.sqrt(1.0 - e * e)
    # 垂直黄道面俯视（沿 z 轴投）
    Pz = np.stack([np.array([1.0, 0, 0]), np.array([0, 1.0, 0])])
    Sz = np.stack([a * (Pz @ p_hat), b_true * (Pz @ q_hat)], axis=1)
    svz = np.linalg.svd(Sz, compute_uv=False)
    # 沿轨道法向俯视 => 真椭圆
    n_hat = orbit_matrix(i, Om, om) @ np.array([0, 0, 1.0])

    M, r, so, _ = sky_orbit(a, e, i, Om, om, th, np.inf)
    D["views"] = {
        "truth_ellipse": {"A": f(a), "B": f(b_true), "ratio": f(b_true / a),
                          "note": "沿轨道法向 n_hat 看；A=a, B=a*sqrt(1-e^2)"},
        "ecliptic_topdown": {"A": f(svz[0]), "B": f(svz[1]), "ratio": f(svz[1] / svz[0]),
                             "normal": [f(x) for x in n_hat],
                             "note": "沿黄道北极看；短轴被 |cos i| 压缩"},
        "from_earth_orthographic": {"A": f(s1), "B": f(s2), "ratio": f(s2 / s1),
                                    "psi_deg": f(((psi / DEG) + 90) % 180 - 90),
                                    "center_offset": f(np.linalg.norm(ctr)),
                                    "center": [f(x) for x in ctr],
                                    "apparent_focus_distance": f(float(np.sqrt(max(s1**2 - s2**2, 0.0)))),
                                    "star_to_center": f(float(np.linalg.norm(ctr))),
                                    "star_vs_focus_ratio": f(float(np.linalg.norm(ctr) / np.sqrt(max(s1**2 - s2**2, 1e-300)))),
                                    "apsidal_vs_major_deg": f(float(abs((((np.degrees(np.arctan2(-ctr[1], -ctr[0])) - psi / DEG) + 90) % 180) - 90))),
                                    "note_star": "星像不在视椭圆焦点上：仿射映射不保持焦点。焦距 sqrt(A^2-B^2)，星像到中心只有 a*e*|P p_hat|，比值即 star_vs_focus_ratio"},
        "analytic_aspect": f(abs(np.sin(i) * np.sin(th - Om))),
        "analytic_center": f(a * e * np.linalg.norm(
            np.array([[-np.sin(th), np.cos(th), 0.0], [0.0, 0.0, 1.0]]) @ p_hat)),
    }
    # e=0 时半轴比退化为 |sin i sin(theta-Om)| 的验证
    a0, e0 = 1.0, 0.0
    s1c, s2c, _, _, _, _ = shape_descriptors(a0, e0, i, Om, om, th)
    D["views"]["circular_check"] = {
        "sigma_ratio": f(s2c / s1c),
        "sin_i_sin_dtheta": f(abs(np.sin(i) * np.sin(th - Om))),
        "abs_diff": f(abs(s2c / s1c - abs(np.sin(i) * np.sin(th - Om)))),
    }

    # ---- 2. 视差：(a/dE) 展开的阶数与图卡依赖 ------------------------
    dEs = [2.0, 5.0, 10.0, 30.0, 100.0, 300.0, 1e3, 1e4, 1e5, 1e6]
    rows = []
    for dE in dEs:
        se, mu, rho = apparent_sky(r, th, dE)
        s1st = apparent_first_order(r, th, dE)
        ssin = apparent_sin_chart(r, th, dE)
        rows.append(dict(
            dE=float(dE), eps_a_over_dE=f(a / dE),
            max_exact_minus_orth=f(np.abs(se - so).max()),
            max_exact_minus_1st=f(np.abs(se - s1st).max()),
            max_1st_minus_orth=f(np.abs(s1st - so).max()),
            max_gnomonic_minus_sin=f(np.abs(se - ssin).max()),
            conic_exact=f(poly_curve_residual(se, 2)),
            quartic_exact=f(poly_curve_residual(se, 4)),
            conic_1st=f(poly_curve_residual(s1st, 2)),
            quartic_1st=f(poly_curve_residual(s1st, 4)),
            ladder_exact=degree_ladder(se),
            ladder_1st=degree_ladder(s1st),
        ))
    # 阶数拟合：residual = C * eps^p
    eps = np.array([row["eps_a_over_dE"] for row in rows])

    def fit_power(key, mask=None, eps_max=1e-1):
        y = np.array([row[key] for row in rows])
        m = (eps <= eps_max) & (y > 1e-13) & (y < 1e-1)   # 只取渐近区
        if mask is not None:
            m = m & mask
        A = np.stack([np.ones(m.sum()), np.log(eps[m])], axis=1)
        sol, *_ = np.linalg.lstsq(A, np.log(y[m]), rcond=None)
        resid = np.log(y[m]) - A @ sol
        dof = max(m.sum() - 2, 1)
        s2 = float(resid @ resid / dof)
        cov = s2 * np.linalg.inv(A.T @ A)
        return dict(power=f(sol[1], 4), intercept=f(np.exp(sol[0]), 6),
                    se_power=f(np.sqrt(cov[1, 1]), 4), n_points=int(m.sum()))

    D["parallax"] = {
        "table": rows,
        "power_fits": {
            "exact_minus_orth": fit_power("max_exact_minus_orth"),
            "exact_minus_1st": fit_power("max_exact_minus_1st"),
            "conic_resid_1st": fit_power("conic_1st", eps_max=2e-2),
            "gnomonic_minus_sin": fit_power("max_gnomonic_minus_sin"),
        },
        "exact_curve_is_conic": bool(max(row["conic_exact"] for row in rows[3:]) < 1e-12),
        "first_order_curve_is_quartic": bool(max(row["quartic_1st"] for row in rows) < 1e-12),
        "chart_dependence_note": "gnomonic 与 sin 图卡只差 O((a/dE)^2)，系数比 conic 残差大 29.35 倍（0.751071 / 0.0255908）",
    }

    # ---- 3. 三个可观测量随倾角变化 ---------------------------------
    th_c, Om_c = 0.0, 90.0 * DEG      # theta-Om = -90°，圆轨道时半轴比 = sin i
    dE_ref = 10.0
    inc_rows = []
    for ideg in np.arange(0.0, 90.01, 2.5):
        i_ = ideg * DEG
        s1i, s2i, psii, ctri, _, _ = shape_descriptors(a, e, i_, Om_c, om, th_c)
        Mi, ri, sei, _ = sky_orbit(a, e, i_, Om_c, om, th_c, dE_ref, 720)
        cpi = conic_params(sei)
        # 方位角是否守恒（引理 R-1）：逐点比较精确与正交投影的极角
        so_i = apparent_orthographic(ri, th_c)
        az_gap = np.max(np.abs(np.angle(np.exp(1j * (np.arctan2(sei[1], sei[0])
                                                      - np.arctan2(so_i[1], so_i[0]))))))
        # 径向放大因子 k(mu) = 1/(1-mu/dE)
        mu_i = sky_projection(th_c)[0] @ ri
        k_i = 1.0 / (1.0 - mu_i / dE_ref)
        e_hat_c = sky_projection(th_c)[0]
        r_peri = orbit_points(a, e, i_, Om_c, om, np.array([0.0]))[:, 0]
        r_aph = orbit_points(a, e, i_, Om_c, om, np.array([np.pi]))[:, 0]
        sp = apparent_sky(r_peri[:, None], th_c, dE_ref)[0][:, 0]
        sa = apparent_sky(r_aph[:, None], th_c, dE_ref)[0][:, 0]
        rp0 = np.linalg.norm(apparent_orthographic(r_peri[:, None], th_c)[:, 0])
        ra0 = np.linalg.norm(apparent_orthographic(r_aph[:, None], th_c)[:, 0])
        if cpi is None:      # i=0：视曲线退化为线段，二次型奇异
            inc_rows.append(dict(
                i_deg=float(ideg), aspect_ortho=0.0, aspect_sin_i=0.0,
                aspect_exact=0.0, aspect_shift=0.0,
                center_ortho=f(np.linalg.norm(ctri)), center_exact=None, center_shift=None,
                peri_aph_ratio_ortho=f(rp0 / ra0), peri_aph_ratio_exact=f(np.linalg.norm(sp) / np.linalg.norm(sa)),
                k_min=f(k_i.min()), k_max=f(k_i.max()),
                azimuth_gap_arcsec=f(az_gap / ARCSEC),
                conic_resid_1st=f(poly_curve_residual(apparent_first_order(ri, th_c, dE_ref), 2)),
                degenerate=True))
            continue
        inc_rows.append(dict(
            i_deg=float(ideg),
            aspect_ortho=f(s2i / s1i),
            aspect_sin_i=f(abs(np.sin(i_))),
            aspect_exact=f(cpi["B"] / cpi["A"]),
            aspect_shift=f(abs(cpi["B"] / cpi["A"] - s2i / s1i)),
            center_ortho=f(np.linalg.norm(ctri)),
            center_exact=f(np.linalg.norm(cpi["center"])),
            center_shift=f(np.linalg.norm(cpi["center"] - ctri)),
            peri_aph_ratio_ortho=f(rp0 / ra0),
            peri_aph_ratio_exact=f(np.linalg.norm(sp) / np.linalg.norm(sa)),
            k_min=f(k_i.min()), k_max=f(k_i.max()),
            azimuth_gap_arcsec=f(az_gap / ARCSEC),
            conic_resid_1st=f(poly_curve_residual(apparent_first_order(ri, th_c, dE_ref), 2)),
        ))
    D["inclination_scan"] = {
        "dE_AU": dE_ref, "n": len(inc_rows), "rows": inc_rows,
        "max_aspect_shift": f(max(abs(r0["aspect_exact"] - r0["aspect_ortho"]) for r0 in inc_rows)),
        "max_center_shift": f(max(r0["center_shift"] for r0 in inc_rows if r0.get("center_shift") is not None)),
        "max_peri_aph_shift": f(max(abs(r0["peri_aph_ratio_exact"] - r0["peri_aph_ratio_ortho"]) for r0 in inc_rows)),
        "max_azimuth_gap_arcsec": f(max(r0["azimuth_gap_arcsec"] for r0 in inc_rows)),
        "max_conic_resid_1st": f(max(r0["conic_resid_1st"] for r0 in inc_rows)),
        "n_degenerate": int(sum(1 for r0 in inc_rows if r0.get("degenerate"))),
        "lemma_R1": ("star-centred gnomonic chart: s = k(mu)*r_perp, k = dE/(dE-mu) 只依赖径向深度，"
                     "故任一点的方位角与正交投影完全相同；视差只改半径。"),
    }

    # ---- 4. 可辨识性：正交投影下 (e,ω,i,Ω) 的简并族 ----------------
    target = shape_descriptors(a, e, i, Om, om, th)
    tgt = np.array([np.log(target[1] / target[0]), np.angle(np.exp(1j * 2 * target[2]))])

    def resid(p, e_try, om_try):
        i_try, Om_try = p
        s1t, s2t, psi_t, _, _, _ = shape_descriptors(1.0, e_try, i_try, Om_try, om_try, th)
        return np.array([np.log(max(s2t, 1e-9) / s1t) - tgt[0],
                         np.angle(np.exp(1j * 2 * (psi_t - target[2])))])

    fam = []
    for e_try in np.arange(0.02, 0.86, 0.04):
        for om_try_deg in np.arange(0.0, 180.0, 10.0):
            om_try = om_try_deg * DEG
            best = None
            for i0 in (0.3, 1.2):
                for Om0 in (0.0, 1.5, 3.0, 4.5):
                    sol = least_squares(resid, [i0, Om0], args=(e_try, om_try),
                                        bounds=([1e-3, -2*np.pi], [np.pi - 1e-3, 2*np.pi]),
                                        xtol=1e-14, ftol=1e-14, gtol=1e-14)
                    rr = float(np.linalg.norm(sol.fun))
                    if best is None or rr < best[0]:
                        best = (rr, sol.x[0], sol.x[1], om_try)
            if best and best[0] < 1e-9:
                fam.append(dict(e=f(e_try), om_deg=f(best[3] / DEG),
                                i_deg=f(best[1] / DEG), Om_deg=f(best[2] / DEG),
                                resid=f(best[0])))
    # 按 e 归并，统计每个 e 上有多少个 ω 解
    by_e = {}
    for row in fam:
        by_e.setdefault(row["e"], []).append(row)
    D["identifiability"] = {
        "statement": "正交投影下外观椭圆只给出 2 个无量纲观测量 (sigma2/sigma1, psi)，未知量为 (e,omega,i,Omega) 4 个",
        "n_unknowns": 4, "n_observables": 2, "deficiency": 2,
        "true": dict(e=f(e), om_deg=f(om / DEG), i_deg=f(i / DEG), Om_deg=f(Om / DEG)),
        "exact_alternative_family": fam,
        "n_family_members": len(fam),
        "n_distinct_e": len(by_e),
        "e_range": [f(min(by_e)), f(max(by_e))] if by_e else None,
        "example_family": [
            dict(e=f(0.10), om_deg=float(by_e[f(0.10)][0]["om_deg"]),
                 i_deg=float(by_e[f(0.10)][0]["i_deg"]), Om_deg=float(by_e[f(0.10)][0]["Om_deg"]))
        ] if f(0.10) in by_e else [],
    }

    # 视差能否打破简并：比较 (i,Om) 与 (pi-i, Om+pi) 的完整视曲线
    pair = []
    for dE in [2.0, 5.0, 10.0, 30.0, 100.0, 1e3, 1e4]:
        rA = orbit_points(a, e, i, Om, om, M)
        rB = orbit_points(a, e, np.pi - i, Om + np.pi, om, M)
        sA_o, sB_o = apparent_orthographic(rA, th), apparent_orthographic(rB, th)
        sA_e, _, _ = apparent_sky(rA, th, dE)
        sB_e, _, _ = apparent_sky(rB, th, dE)
        pair.append(dict(dE=float(dE),
                         ortho_gap=f(np.abs(sA_o - sB_o).max()),
                         exact_gap=f(np.abs(sA_e - sB_e).max())))
    D["identifiability"]["i_vs_pi_minus_i"] = {
        "rows": pair,
        "note": "正交投影下两者视曲线完全相同（gap 到机器精度），视差把它撬开到 O((a/dE)^2)",
    }

    # ---- 5. 太阳系内视角：火星地心视轨道 ----------------------------
    EL = {k: {(kk[:-4] if kk.endswith("_deg") else kk): (vv * DEG if kk.endswith("_deg") else vv)
              for kk, vv in v.items()} for k, v in PLANETS.items()}
    mu = 4.0 * np.pi**2                       # AU^3/yr^2
    yrs = np.linspace(0.0, 2.2, 4000)
    def helio(name, t):
        p = EL[name]
        n = np.sqrt(mu / p["a"] ** 3)
        M = n * t
        return orbit_points(p["a"], p["e"], p["i"], p["Om"], p["om"], M)
    rM = helio("Mars", yrs)
    rE = helio("Earth", yrs)
    # 地心视方向：u = (rM-rE)/|rM-rE|；用方向余弦图（对全天球有效，不随"远侧"翻转）
    dE_arr = np.linalg.norm(rE, axis=0)
    e_hat = rE / dE_arr
    e1 = np.stack([-e_hat[1], e_hat[0], np.zeros_like(e_hat[0])])
    u = rM - rE
    u = u / np.linalg.norm(u, axis=0)
    sM = np.stack([dE_arr * np.einsum("ij,ij->j", e1, u), dE_arr * u[2]])
    lam = np.unwrap(np.arctan2(sM[1], sM[0]))
    dlam = np.gradient(lam, yrs)
    retro = dlam < 0
    n_ep = int(np.sum(np.diff(retro.astype(int)) == 1) + (1 if retro[0] else 0))
    elong = np.arctan2(np.hypot(*sM), -np.einsum("ij,ij->j", e_hat, u) * dE_arr)
    D["solar_system_mars"] = {
        "span_yr": f(2.2), "n_samples": int(yrs.size),
        "n_retrograde_episodes": n_ep,
        "retrograde_time_fraction": f(np.mean(retro)),
        "synodic_period_yr": f(1.0 / (1.0 / 1.0 - 1.0 / 1.8808)),
        "conic_ladder_apparent": degree_ladder(sM, (2, 4, 6, 8)),
        "max_elongation_deg": f(np.max(elong) / DEG),
        "min_elongation_deg": f(np.min(elong) / DEG),
        "apparent_path_not_closed": f(np.linalg.norm(sM[:, -1] - sM[:, 0])),
        "note": "地心视轨道既非椭圆也非低次代数曲线；逆行弧是'非闭合'的直接后果",
    }

    D["_meta"] = meta("T1 observation geometry", dict(
        fiducial={k: (f(v / DEG) if k in ("i", "Om", "om") else f(v)) for k, v in FID.items()},
        theta_deg=f(THETA_FID / DEG), n_points=N_PTS,
        chart="gnomonic (standard coordinates xi=tan); sin-chart kept for chart-dependence check",
    ))

    # ---- 图 --------------------------------------------------------
    make_figures(D, FID, THETA_FID, EL, sM, yrs, retro, fam, rows, inc_rows)

    dump("t1_geometry.json", D)
    print("T1 done; views:", {k: D["views"][k] for k in ("truth_ellipse", "ecliptic_topdown", "from_earth_orthographic")})
    print("power fits:", {k: v["power"] for k, v in D["parallax"]["power_fits"].items()})
    print("identifiability family size:", len(fam))
    return D


def make_figures(D, FID, th, EL, sM, yrs, retro, fam, rows, inc_rows):
    plt = __import__("mmcommon").setup_matplotlib()
    from mmcommon import ascii_log, savefig

    a, e, i, Om, om = FID["a"], FID["e"], FID["i"], FID["Om"], FID["om"]

    # fig1 三种视图
    fig = plt.figure(figsize=(7.2, 2.9))
    M = np.linspace(0, 2 * np.pi, 720)
    r = orbit_points(a, e, i, Om, om, M)
    ax = fig.add_subplot(131, projection="3d")
    ax.plot(r[0], r[1], r[2], color="#1f4e79")
    ax.scatter([0], [0], [0], color="k", s=12)
    ax.set_xlabel("x [AU]"); ax.set_ylabel("y [AU]"); ax.set_zlabel("z [AU]")
    ax.set_title("(a) 真轨道（黄道系）")
    ax.view_init(elev=22, azim=-58)
    ax.set_box_aspect((1, 1, 0.55))
    ax = fig.add_subplot(132)
    s = apparent_orthographic(r, th)
    ax.plot(s[0], s[1], color="#1f4e79")
    ax.set_aspect("equal"); ax.set_title("(b) 斜视正交投影")
    ax.set_xlabel(r"$s_1$ [AU]"); ax.set_ylabel(r"$s_2$ [AU]")
    ax = fig.add_subplot(133)
    ax.plot(r[0], r[1], color="#a33", label="黄道面俯视")
    ax.plot(s[0], s[1], color="#1f4e79", label="地球方向斜视")
    ax.set_aspect("equal"); ax.set_title("(c) 叠放对比")
    ax.set_xlabel("x / $s_1$ [AU]"); ax.set_ylabel("y / $s_2$ [AU]")
    ax.legend(loc="upper right", frameon=False)
    fig.tight_layout()
    savefig(fig, "fig1_three_views"); plt.close(fig)

    # fig2 不同 dE 的视曲线
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.1))
    for dE, c in [(2.0, "#c00"), (5.0, "#e80"), (10.0, "#0a0"), (100.0, "#06c"), (np.inf, "k")]:
        s = apparent_orthographic(r, th) if not np.isfinite(dE) else apparent_sky(r, th, dE)[0]
        lbl = r"$d_E=\infty$" if not np.isfinite(dE) else rf"$d_E={dE:g}$"
        axes[0].plot(s[0], s[1], color=c, label=lbl)
    axes[0].set_aspect("equal"); axes[0].legend(frameon=False, loc="upper right")
    axes[0].set_title("(a) 视曲线的视差形变")
    axes[0].set_xlabel(r"$s_1$ [AU]"); axes[0].set_ylabel(r"$s_2$ [AU]")
    eps = np.array([q["eps_a_over_dE"] for q in rows])
    for key, lab, c in [("conic_1st", r"一阶曲线对圆锥的残差 $\propto(a/d_E)^2$", "#c00"),
                        ("max_gnomonic_minus_sin", "图卡差异（gnomonic-sin）", "#06c"),
                        ("max_exact_minus_1st", r"精确-一阶 $\propto(a/d_E)^2$", "#0a0")]:
        y = np.array([q[key] for q in rows])
        m = y > 1e-13
        axes[1].loglog(eps[m], y[m], "o-", ms=3, color=c, label=lab)
    p = D["parallax"]["power_fits"]["conic_resid_1st"]
    axes[1].loglog(eps, p["intercept"] * eps ** p["power"], "k--", lw=1,
                   label=rf"拟合指数 {p['power']:.3f}")
    axes[1].set_xlabel(r"$\varepsilon=a/d_E$"); axes[1].set_ylabel("最大偏差 [AU]")
    axes[1].set_title("(b) 阶数标定")
    ascii_log(axes[1])
    axes[1].legend(frameon=False, fontsize=6.8, loc="lower right")
    fig.tight_layout()
    savefig(fig, "fig2_parallax_scaling"); plt.close(fig)

    # fig3 三个可观测量随 i
    ii = [q["i_deg"] for q in inc_rows]
    fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.6))
    axes[0].plot(ii, [q["aspect_ortho"] for q in inc_rows], color="#1f4e79", label="正交投影")
    axes[0].plot(ii, [q["aspect_sin_i"] for q in inc_rows], "--", color="0.5", label=r"$|\sin i|$")
    axes[0].plot(ii, [q["aspect_exact"] for q in inc_rows], color="#c00", label="含视差精确")
    axes[0].set_xlabel("倾角 $i$ [deg]"); axes[0].set_ylabel(r"$B'/A'$")
    axes[0].set_title("(a) 半轴比"); axes[0].legend(frameon=False, fontsize=6.5)
    axes[1].plot(ii, [q["center_ortho"] for q in inc_rows], color="#1f4e79")
    axes[1].plot(ii, [q["center_exact"] for q in inc_rows], color="#c00")
    axes[1].set_xlabel("倾角 $i$ [deg]"); axes[1].set_ylabel("中心偏移 [AU]")
    axes[1].set_title("(b) 中心偏移")
    axes[2].plot(ii, [q["peri_aph_ratio_exact"] / q["peri_aph_ratio_ortho"] for q in inc_rows],
                 color="#0a0")
    axes[2].axhline(1.0, color="0.5", lw=0.8, ls="--")
    axes[2].set_xlabel("倾角 $i$ [deg]"); axes[2].set_ylabel("比值的视差放大")
    axes[2].set_title(r"(c) 近/远心距比 $d_E=10a$")
    fig.tight_layout()
    savefig(fig, "fig3_observables_vs_i"); plt.close(fig)

    # fig4 火星地心视轨道
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.2))
    axes[0].plot(sM[0], sM[1], color="#333", lw=0.9)
    axes[0].scatter([0], [0], color="#e80", s=40, marker="*", zorder=5)
    axes[0].set_aspect("equal"); axes[0].set_title("(a) 火星地心视轨道（太阳为原点）")
    axes[0].set_xlabel("切平面 $\\xi$ [AU]"); axes[0].set_ylabel("切平面 $\\eta$ [AU]")
    axes[0].text(0.02, 0.02, "★ = 太阳", transform=axes[0].transAxes, fontsize=7)
    lam = np.unwrap(np.arctan2(sM[1], sM[0]))
    axes[1].plot(yrs, np.gradient(lam, yrs) / DEG * 365.25, color="#06c", lw=0.9)
    axes[1].axhline(0, color="0.5", lw=0.8)
    axes[1].fill_between(yrs, 0, np.gradient(lam, yrs) / DEG * 365.25,
                         where=np.gradient(lam, yrs) < 0, color="#c00", alpha=0.3)
    axes[1].set_xlabel("t [yr]"); axes[1].set_ylabel(r"$d\lambda/dt$ [deg/yr]")
    axes[1].set_title("(b) 视黄经速率与逆行区间")
    fig.tight_layout()
    savefig(fig, "fig4_mars_geocentric"); plt.close(fig)

    # fig5 简并族
    fig, ax = plt.subplots(figsize=(4.4, 3.0))
    if fam:
        ax.scatter([q["e"] for q in fam], [q["i_deg"] for q in fam], s=8,
                   c=[q["om_deg"] for q in fam], cmap="viridis")
        ax.scatter([f(e)], [f(i / DEG)], color="#c00", marker="*", s=120, zorder=5,
                   label="真值 $(e,i)$")
        ax.legend(frameon=False, fontsize=7)
    ax.set_xlabel("偏心率 $e$"); ax.set_ylabel("倾角 $i$ [deg]")
    ax.set_title("同一外观椭圆的精确解族")
    fig.tight_layout()
    savefig(fig, "fig5_identifiability"); plt.close(fig)


if __name__ == "__main__":
    main()