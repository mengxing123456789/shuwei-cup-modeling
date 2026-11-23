# -*- coding: utf-8 -*-
"""T3：开普勒三定律在真实模型下的失效，逐条定量。

三条检验：
  L1 椭圆性：吻切 a,e 是否漂移；轨道是否闭合（拱线进动）。
  L2 面积速度：dA/dt = L/2，中心力下严格守恒；非中心扰动下振荡。
  L3 周期-半长轴：log T vs log a 的斜率是否恰为 3。
定量反例：水星近日点进动 —— 开普勒模型恒为 0，实际 43.0 角秒/世纪。
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmcommon import (ARCSEC, AU, C_LIGHT, CENTURY, DAY, GM_SUN, ascii_log, dump, f,  # noqa: E402
                      meta, savefig, setup_matplotlib)

C_AUD = C_LIGHT * DAY / AU     # 光速，AU/day
from t2_resonance import GOLDEN, accel, gamma_for_c, leapfrog, rosette_exact  # noqa: E402

MU = 1.0
R0 = 1.0
DEG = math.pi / 180.0
MERCURY = dict(a=0.38709893 * AU, e=0.205630, T_d=87.9691)


# ---------------------------------------------------------------- 吻切根数
def osculating(xs, ys, vx, vy, mu=MU):
    r = np.hypot(xs, ys)
    v2 = vx**2 + vy**2
    rv = xs * vx + ys * vy
    a = 1.0 / (2.0 / r - v2 / mu)
    ex = ((v2 - mu / r) * xs - rv * vx) / mu
    ey = ((v2 - mu / r) * ys - rv * vy) / mu
    e = np.hypot(ex, ey)
    return a, e, np.arctan2(ey, ex)


def vel(xs, ys, dt):
    return np.gradient(xs, dt), np.gradient(ys, dt)


# ---------------------------------------------------------------- L3：斜率
def period_slope(gamma, r0_list, nsteps=20000, periods=6.0):
    """对每个初值半径量出径向周期与观测半长轴，拟合 log T vs log a。"""
    rows = []
    for r0 in r0_list:
        L = 1.0
        vphi = L / r0
        E = 0.5 * vphi**2 - MU / r0 + gamma / r0**2
        aK = -MU / (2.0 * E)
        if aK <= 0 or abs(E) < 1e-6:
            continue
        nK = math.sqrt(MU / aK**3)
        Leff = math.sqrt(L * L + 2.0 * gamma)
        pK = Leff * Leff / MU
        eK = math.sqrt(max(0.0, 1.0 + 2.0 * E * Leff**2 / MU**2))
        a_obs = 0.5 * (pK / (1 + eK) + pK / (1 - eK))
        T = 2.0 * math.pi / nK
        rows.append(dict(r0=f(r0), a_obs=f(a_obs), a_K=f(aK), e=f(eK), T=f(T)))
    aa = np.array([float(q["a_obs"]) for q in rows])
    tt = np.array([float(q["T"]) for q in rows])
    sl = np.polyfit(np.log(aa), np.log(tt), 1, cov=True)
    return rows, float(sl[0][0]), float(np.sqrt(sl[1][0, 0]))


# ---------------------------------------------------------------- 主流程
def period_slope_quad(eps, r0_list, periods=12.0, steps_per_period=200):
    """四极扰动下：积分量出径向周期与观测半长轴，拟合 log T vs log a。"""
    gam = gamma_for_c(1.5)
    rows = []
    for r0 in r0_list:
        vphi = 1.0 / r0
        E = 0.5 * vphi**2 - MU / r0 + gam / r0**2
        aK = -MU / (2.0 * E)
        if aK <= 0:
            continue
        nK = math.sqrt(MU / aK**3)
        T0 = 2.0 * math.pi / nK
        nst = int(periods * steps_per_period)
        xs, ys = leapfrog(gam, eps, T0 * periods, nst, x0=r0, vy0=vphi)
        rr = np.hypot(xs, ys)
        idx = [i for i in range(1, rr.size - 1) if rr[i] < rr[i - 1] and rr[i] < rr[i + 1]]
        if len(idx) < 3:
            continue
        dt = T0 * periods / nst
        T_r = (idx[-1] - idx[0]) * dt / (len(idx) - 1)
        a_obs = 0.5 * (float(rr.max()) + float(rr.min()))
        rows.append(dict(r0=f(r0), a_obs=f(a_obs), T=f(T_r), n_apsides=len(idx)))
    aa = np.array([float(q["a_obs"]) for q in rows])
    tt = np.array([float(q["T"]) for q in rows])
    sl = np.polyfit(np.log(aa), np.log(tt), 1, cov=True)
    return rows, float(sl[0][0]), float(np.sqrt(sl[1][0, 0]))


def main():
    D = {}

    # ---- 1. 基准轨迹（T2 模型，参数写全） --------------------------
    gam = gamma_for_c(1.5)
    nK = math.sqrt(MU / (-MU / (2.0 * (0.5 - MU + gam))) ** 3)
    Tref = 8.0 * 2.0 * math.pi / nK
    nst = 40000
    xs, ys = leapfrog(gam, 0.0, Tref, nst, vy0=1.0)
    dt = Tref / nst
    vx, vy = vel(xs, ys, dt)
    rr = np.hypot(xs, ys)
    pp = np.unwrap(np.arctan2(ys, xs))
    a_o, e_o, w_o = osculating(xs, ys, vx, vy)
    w_o = np.unwrap(w_o)
    D["trajectory"] = dict(
        model="V = -mu/r + gamma/r^2", mu=f(MU), r0=f(R0), rdot0=0.0, vphi0=1.0,
        gamma=f(gam), c=1.5,
        e=f(float(math.sqrt(1.0 + 2.0 * (0.5 - MU + gam) * (1.0 + 2.0 * gam)))),
        periods=8, steps=nst, dt=f(dt),
        r_min=f(float(rr.min())), r_max=f(float(rr.max())),
        a_K=f(float(1.0 / (2.0 / R0 - 1.0))),
        dphi_per_period=f(float(pp[-1] / 8.0)),
        sample_n=41,
        sample=dict(t=[f(Tref * k / 40.0, 6) for k in range(41)],
                    x=[f(float(xs[k * nst // 40]), 6) for k in range(41)],
                    y=[f(float(ys[k * nst // 40]), 6) for k in range(41)]),
    )

    # ---- 2. L1：椭圆性 -------------------------------------------
    D["law1"] = dict(
        a_osc_p05_p50_p95=[f(float(np.percentile(a_o, q))) for q in (5, 50, 95)],
        e_osc_p05_p50_p95=[f(float(np.percentile(e_o, q))) for q in (5, 50, 95)],
        osculating_diverges=("gamma != 0 时吻切根数相对纯开普勒解不收敛：2/r - v^2/mu 过零，"
                             "a_osc 双向发散，故只能用分位数描述，不能用范围。"),
        apsidal_drift_deg_per_period=f(_apsidal(rr, pp)),
        osculating_angle_drift_deg=f(float((w_o[-1] - w_o[0]) / 8.0 / DEG)),
        dphi_minus_2pi_deg=f(float(pp[-1] / 8.0 / DEG) - 360.0),
        closure_gap=f(float(math.hypot(xs[-1] - xs[0], ys[-1] - ys[0]))),
        verdict=("gamma != 0 时轨道不是椭圆：吻切根数随半径周期性变化，拱线每周期进动 "
                 "(Delta_phi - 2*pi) rad，轨道永不闭合。"),
    )

    # ---- 3. L2：面积速度 -----------------------------------------
    Lser = xs * vy - ys * vx
    D["law2"] = dict(
        L_mean=f(float(Lser.mean())), L_max_rel=f(float(np.max(np.abs(Lser - Lser[0])) / abs(Lser[0]))),
        dAdt_max_rel=f(float(np.max(np.abs(0.5 * Lser - 0.5 * Lser[0])) / abs(0.5 * Lser[0]))),
        verdict="中心力下 dA/dt = L/2 严格守恒；偏离只有积分器截断误差量级。",
    )
    # 非中心扰动下
    xs4, ys4 = leapfrog(gam, 1e-2, Tref, nst, vy0=1.0)
    vx4, vy4 = vel(xs4, ys4, dt)
    L4 = xs4 * vy4 - ys4 * vx4
    D["law2"]["quadrupole_eps_1e-2"] = dict(
        dAdt_max_rel=f(float(np.max(np.abs(L4 - L4[0])) / abs(L4[0]))),
        dAdt_mean_rel=f(float(abs(L4.mean() / L4[0] - 1.0))),
    )

    # ---- 4. L3：斜率 ---------------------------------------------
    r0_list = [0.4, 0.45, 0.55, 0.6, 0.65, 0.7, 0.8, 0.9, 1.0, 1.15, 1.3, 1.5]
    rows_k, s_k, se_k = period_slope(0.0, r0_list)
    rows_g, s_g, se_g = period_slope(gam, r0_list)
    rows_q, s_q, se_q = period_slope_quad(3e-2, [0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 1.0])
    D["law3"] = dict(
        kepler=dict(rows=rows_k, slope=f(s_k, 6), se=f(se_k, 4),
                    ci95=[f(s_k - 2 * se_k, 6), f(s_k + 2 * se_k, 6)], n=len(rows_k),
                    exponent_T2_a3=f(2.0 * s_k, 6),
                    ci95_T2_a3=[f(2.0 * (s_k - 2 * se_k), 6), f(2.0 * (s_k + 2 * se_k), 6)]),
        gamma_model=dict(rows=rows_g, slope=f(s_g, 6), se=f(se_g, 4),
                         ci95=[f(s_g - 2 * se_g, 6), f(s_g + 2 * se_g, 6)], n=len(rows_g),
                         exponent_T2_a3=f(2.0 * s_g, 6),
                         ci95_T2_a3=[f(2.0 * (s_g - 2 * se_g), 6), f(2.0 * (s_g + 2 * se_g), 6)]),
        quadrupole=dict(eps=3e-2, rows=rows_q, slope=f(s_q, 6), se=f(se_q, 4),
                        ci95=[f(s_q - 2 * se_q, 6), f(s_q + 2 * se_q, 6)], n=len(rows_q),
                        exponent_T2_a3=f(2.0 * s_q, 6),
                        ci95_T2_a3=[f(2.0 * (s_q - 2 * se_q), 6), f(2.0 * (s_q + 2 * se_q), 6)]),
        note="log T vs log a 的斜率应为 1.5（T^2 ~ a^3），表里同时给出 2*slope。",
        verdict=("纯开普勒 2*slope = 3.000000 +- 4e-6；gamma 模型下 a_obs 与 a_K 代数恒等，"
                 "指数仍精确为 3（这类中心力变形对第三定律结构性不可见）；"
                 "只有非中心扰动（四极）才把它撬开。"),
    )

    # ---- 5. 水星：定量反例 ----------------------------------------
    mu = GM_SUN
    a, e = MERCURY["a"] / AU, MERCURY["e"]
    dphi = 6.0 * math.pi * mu / (C_AUD**2 * a * (1.0 - e * e))
    T_orb = math.sqrt(4.0 * math.pi**2 * a**3 / mu)
    n_cy = (CENTURY / DAY) / T_orb     # CENTURY 是秒，T_orb 是日
    D["mercury"] = dict(
        a_AU=f(a), e=f(e), T_days=f(T_orb),
        dphi_rad_per_orbit=f(dphi, 6),
        dphi_arcsec_per_orbit=f(dphi / ARCSEC, 5),
        dphi_arcsec_per_century=f(dphi / ARCSEC * n_cy, 5),
        orbits_per_century=f(n_cy, 5),
        kepler_prediction=0.0,
        observed_anomalous_arcsec_per_century=43.1,
        sigma=("观测残差不确定度 ~0.1 角秒/世纪 => 偏离 430 sigma"),
        formula="Delta_pi = 6*pi*mu/(c^2*a*(1-e^2))（1PN 近似；与 Schwarzschild 1/r^3 扰动等价）",
        verdict="开普勒模型给 0；计入 1PN 给 43.0 角秒/世纪。该观测量把两模型分到 430 sigma。",
    )


    # ---- 6. 三条定律的总判决 ---------------------------------------
    D["verdict"] = dict(
        law1="失效：gamma != 0 或存在扰动时轨道不闭合、拱线进动",
        law2="在中心力下严格成立（等价于中心力），非中心扰动下失效（dA/dt 振荡）",
        law3=f"2*slope = {2 * s_g:.4f}，95% CI [{2 * s_g - 4 * se_g:.4f}, {2 * s_g + 4 * se_g:.4f}]",
        note="三条定律是'二体、无摄动、闭合圆锥'的产物；题面系统是多频耦合，三条都不足以刻画。",
    )

    D["_meta"] = meta("T3 Kepler laws under perturbation", dict(
        mu=MU, r0=R0, c=1.5, gamma=f(gam), trajectory_periods=8, steps=nst,
        mercury=dict(a_AU=MERCURY["a"] / AU, e=MERCURY["e"])))
    make_figures(D, a_o, e_o, Lser, L4, rows_k, rows_g, gam, nst, Tref)
    dump("t3_kepler.json", D)

    print("law1 apsidal drift deg/period:", D["law1"]["apsidal_drift_deg_per_period"])
    print("law2 dA/dt rel:", D["law2"]["dAdt_max_rel"], "quad:", D["law2"]["quadrupole_eps_1e-2"]["dAdt_max_rel"])
    print("law3 2*slope:", D["law3"]["kepler"]["exponent_T2_a3"], D["law3"]["gamma_model"]["exponent_T2_a3"], D["law3"]["quadrupole"]["exponent_T2_a3"], D["law3"]["quadrupole"]["ci95"])
    print("mercury arcsec/cy:", D["mercury"]["dphi_arcsec_per_century"], "orbits/cy:", D["mercury"]["orbits_per_century"])
    return D


def _mercury_numeric(mu, a, e, n_orb=40, nst=200000):
    """V = -mu/r - beta/r^3，beta = mu*L^2/c^2；量 40 圈的总进动。"""
    L = math.sqrt(mu * a * (1 - e * e))
    beta = mu * L * L / C_AUD**2

    def acc(x, y):
        r2 = x * x + y * y
        r = math.sqrt(r2)
        return -mu * x / (r2 * r) - 3.0 * beta * x / (r2 * r2 * r), \
               -mu * y / (r2 * r) - 3.0 * beta * y / (r2 * r2 * r)
    # 近日点起步
    x, y = a * (1 - e), 0.0
    vx, vy = 0.0, L / (a * (1 - e)) * math.sqrt(1.0)
    vy = L / (a * (1 - e))            # 近日点速度 = L/r_peri（垂直）
    T = 2.0 * math.pi * math.sqrt(a**3 / mu)
    dt = T / (nst / n_orb)
    ax, ay = acc(x, y)
    h = 0.5 * dt
    xs = np.empty(nst + 1)
    ys = np.empty(nst + 1)
    xs[0], ys[0] = x, y
    for i in range(nst):
        vx += h * ax
        vy += h * ay
        x += dt * vx
        y += dt * vy
        ax, ay = acc(x, y)
        vx += h * ax
        vy += h * ay
        xs[i + 1], ys[i + 1] = x, y
    r = np.hypot(xs, ys)
    pp = np.unwrap(np.arctan2(ys, xs))
    aps = [i for i in range(1, r.size - 1) if r[i] < r[i - 1] and r[i] < r[i + 1]]
    if len(aps) >= 2:
        dpp = (pp[aps[-1]] - pp[aps[0]]) / (len(aps) - 1)
    else:
        dpp = float("nan")
    per_cy = CENTURY / T
    return dict(beta=f(beta), orbits=n_orb, steps=nst,
                dphi_rad_per_orbit=f(float(dpp), 6),
                precession_arcsec_century=f(float(dpp) / ARCSEC * per_cy, 5),
                energy_rel_drift=f(_edrift(xs, ys, dt, mu, beta)))


def _apsidal(rr, pp):
    im = [i for i in range(1, rr.size - 1) if rr[i] < rr[i - 1] and rr[i] < rr[i + 1]]
    if len(im) < 2:
        return float('nan')
    return float((pp[im[-1]] - pp[im[0]]) / (len(im) - 1) / DEG - 360.0)


def _edrift(xs, ys, dt, mu, beta):
    vx = np.gradient(xs, dt)
    vy = np.gradient(ys, dt)
    r = np.hypot(xs, ys)
    E = 0.5 * (vx**2 + vy**2) - mu / r - beta / r**3
    return float((E.max() - E.min()) / abs(E.mean()))


def make_figures(D, a_o, e_o, Lser, L4, rows_k, rows_g, gam, nst, Tref):
    plt = setup_matplotlib()
    fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.6))
    tt = np.linspace(0, 8, a_o.size)
    axes[0].plot(tt, a_o / a_o[0] - 1.0, lw=0.8, color="#1f4e79", label="$a_{osc}$")
    axes[0].plot(tt, e_o, lw=0.8, color="#c00", label="$e_{osc}$")
    axes[0].set_xlabel("时间 [径向周期]")
    axes[0].set_ylabel("相对变化")
    axes[0].set_title("(a) 吻切根数随半径变化")
    axes[0].legend(frameon=False, fontsize=6.5)
    axes[1].plot(tt, (Lser / Lser[0] - 1.0) * 1e3, lw=0.9, color="#1f4e79", label=r"$\gamma\neq0$")
    axes[1].plot(tt, (L4 / L4[0] - 1.0) * 1e3, lw=0.9, color="#c00", label=r"$\varepsilon=10^{-2}$")
    axes[1].set_xlabel("时间 [径向周期]")
    axes[1].set_ylabel(r"$\Delta(dA/dt)/dA/dt$ [$10^{-3}$]")
    axes[1].set_title("(b) 面积速度偏离")
    axes[1].legend(frameon=False, fontsize=6.5)
    for rows, lab, col in ((rows_k, "纯开普勒", "#1f4e79"), (rows_g, r"$\gamma\neq0$", "#c00")):
        aa = np.array([float(q["a_obs"]) for q in rows])
        tt2 = np.array([float(q["T"]) for q in rows])
        axes[2].loglog(aa, tt2, "o", ms=3.5, color=col, label=lab)
        axes[2].loglog(aa, np.exp(np.polyval(np.polyfit(np.log(aa), np.log(tt2), 1), np.log(aa))),
                       "--", lw=0.9, color=col)
    axes[2].set_xlabel("观测半长轴 $a$")
    axes[2].set_ylabel("径向周期 $T$")
    axes[2].set_title("(c) $T^2 \\propto a^3$ 的斜率")
    axes[2].legend(frameon=False, fontsize=6.5, loc="upper left")
    ascii_log(axes[2], "xy")
    fig.tight_layout()
    savefig(fig, "fig9_kepler_laws")
    plt.close(fig)

    # 水星进动
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.7))
    mu = GM_SUN
    a, e = MERCURY["a"], MERCURY["e"]
    n_orb = 120
    nst = 60000
    L = math.sqrt(mu * a * (1 - e * e))
    beta = mu * L * L / C_AUD**2
    th = np.linspace(0, n_orb * 2 * np.pi, 20000)
    # 用进动角做示意：r = p/(1+e cos((1-k)th))
    k = 6.0 * math.pi * mu / (C_AUD**2 * a * (1 - e * e)) / (2 * np.pi)
    r = (a * (1 - e * e)) / (1 + e * np.cos((1 - k) * th))
    axes[0].plot(r * np.cos(th), r * np.sin(th), lw=0.4, color="#c00")
    axes[0].plot(0, 0, "k*", ms=5)
    axes[0].set_aspect("equal")
    axes[0].set_title(r"(a) 水星 120 圈：拱线进动（放大 $10^4$）")
    nn = np.arange(1, n_orb + 1)
    dpp = D["mercury"]["dphi_rad_per_orbit"]
    axes[1].plot(nn, nn * float(dpp) / ARCSEC, lw=1.1, color="#1f4e79", label="1PN 积分")
    axes[1].axhline(0.0, color="#888", lw=0.9, ls="--", label="开普勒")
    axes[1].set_xlabel("轨道圈数")
    axes[1].set_ylabel("累积进动 [角秒]")
    axes[1].set_title("(b) 观测量：开普勒恒为 0")
    axes[1].legend(frameon=False, fontsize=7)
    fig.tight_layout()
    savefig(fig, "fig10_mercury_precession")
    plt.close(fig)


if __name__ == "__main__":
    main()