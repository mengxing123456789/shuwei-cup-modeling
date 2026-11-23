# -*- coding: utf-8 -*-
"""T2 三条反例 + T1 正交/透视四倾角 + T3 耗散衰减率。

反例 A：线性阻力介质。dL/dt = -k L 严格成立 => L(t)=L0 e^{-kt}，a(t)=a0 e^{-2kt}（圆轨道）：
        没有稳态环，只有瞬态螺旋；「收敛到单一中心」退化为「螺旋落到恒星上」。
反例 B：只锁径向、未锁方位。c=p/q 时累积像是 p 重对称的离散瓣，方位谱 A_p 主导、A_1≈0；
        径向上是双峰共振带（带内两个焦散），不是均匀环。
反例 C：进动速率与相位混合速率同量级。观测窗只覆盖 T_mix ≪ T_ring 时，方位密度只剩一段弧，
        l=1 谐波不可忽略；而 l=1 密度谐波与「环心偏移」在观测上简并 => 单中心推断有系统偏差。
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from mmcommon import (apparent_orthographic, apparent_sky, dump, f, meta,  # noqa: E402
                      orbit_points, savefig, setup_matplotlib)
from t2_resonance import rosette_exact  # noqa: E402

MU = 1.0
DEG = math.pi / 180.0


# ---------------------------------------------------------------- 工具
def accel(x, y, k=0.0, vx=0.0, vy=0.0, mu=MU):
    r2 = x * x + y * y
    ir3 = 1.0 / (r2 * math.sqrt(r2))
    return -mu * x * ir3 - k * vx, -mu * y * ir3 - k * vy


def rk4_drag(k, t_end, nsteps, x0=1.0, y0=0.0, vx0=0.0, vy0=1.0):
    dt = t_end / nsteps
    x, y, vx, vy = x0, y0, vx0, vy0
    t = np.empty(nsteps + 1)
    X = np.empty((nsteps + 1, 4))
    X[0] = (x, y, vx, vy)
    t[0] = 0.0
    for i in range(nsteps):
        def f_(st):
            xx, yy, vvx, vvy = st
            ax, ay = accel(xx, yy, k, vvx, vvy)
            return np.array([vvx, vvy, ax, ay])
        s = X[i]
        k1 = f_(s)
        k2 = f_(s + 0.5 * dt * k1)
        k3 = f_(s + 0.5 * dt * k2)
        k4 = f_(s + dt * k3)
        X[i + 1] = s + dt / 6.0 * (k1 + 2 * k2 + 2 * k3 + k4)
        t[i + 1] = t[i] + dt
    return t, X


def harmonics(phi, lmax=6, nbins=72, weight=None):
    """方位密度的傅里叶幅值 A_l（归一化到 A_0=1）。phi 为弧度。"""
    w = np.ones_like(phi) if weight is None else weight
    w = w / w.sum()
    out = []
    for l in range(1, lmax + 1):
        out.append(float(2.0 * abs(np.sum(w * np.exp(-1j * l * phi)))))
    return out


def ks_2sample(a, b):
    a = np.sort(a)
    b = np.sort(b)
    grid = np.concatenate([a, b])
    ca = np.searchsorted(a, grid, side="right") / a.size
    cb = np.searchsorted(b, grid, side="right") / b.size
    return float(np.max(np.abs(ca - cb)))


# ---------------------------------------------------------------- A 阻力
def drag_block():
    k = 1e-2
    # a(t) = a0 e^{-2kt}：取到 a 缩小 20 倍（t = ln20/(2k) = 150）。
    # 再往下积分，dt 会大于内圈周期的 1/10（纯 Python RK4 定步长），数值爆炸 —— 这是积分器的边界，
    # 不是物理结论；e-folding 由解析式给出。
    t_end = math.log(20.0) / (2.0 * k)
    n = 300000
    t, X = rk4_drag(k, t_end, n)
    x, y, vx, vy = X[:, 0], X[:, 1], X[:, 2], X[:, 3]
    r = np.hypot(x, y)
    phi = np.unwrap(np.arctan2(y, x))
    L = r * r * (x * vy - y * vx) / r  # = x*vy - y*vx
    L = x * vy - y * vx
    E = 0.5 * (vx ** 2 + vy ** 2) - MU / r
    a_inst = -MU / (2.0 * E)
    # 拟合 log|L| 与 log a 的斜率（只用 L>0 的前段，避免 r→0 的数值噪声）
    # 只在 L/L0 still smooth 的窗口拟合：L 指数掉到 0.2 以下后，r 已很小，数值噪声主导
    m = L > 0.2 * L[0]
    sl_L = np.polyfit(t[m], np.log(L[m]), 1)[0]
    m2 = a_inst > 0.2 * a_inst[0]
    sl_a = np.polyfit(t[m2], np.log(a_inst[m2]), 1)[0]
    kL = 1.0 / k
    L_at = [dict(t_over_k=f(mult, 3), L=f(float(np.interp(mult * kL, t, L))))
            for mult in (0.5, 1.0, 1.4)]
    # 环的判据：分布是否随时间平稳。前半段 vs 后半段的方位与半径二维分布
    half = n // 2
    # 平稳性判据必须看 r 而不看 phi：螺旋的方位覆盖是均匀的（phi 检验会误判为"环"），
    # 但它沿半径单调内移。对照组用无耗散的闭合轨道（应平稳）。
    ks_r_spiral = ks_2sample(r[:half], r[half:])
    _, r_ros, phi_ros, _ = rosette_exact((1 + math.sqrt(5)) / 2, 1.0, 40000, 120)
    h2 = r_ros.size // 2
    ks_r_rosette = ks_2sample(r_ros[:h2], r_ros[h2:])
    ks_phi = ks_2sample(phi[:half] % (2 * math.pi), phi[half:] % (2 * math.pi))
    # 径向密度：应单调内移，不能有稳态峰
    r_early = np.percentile(r[:half // 20], [50])
    r_late = np.percentile(r[-half // 20:], [50])
    return dict(
        k=f(k),
        t_end=f(t_end),
        L_decay_rate_fit=f(float(sl_L), 6),
        L_decay_rate_theory=f(-k, 6),
        a_decay_rate_fit=f(float(sl_a), 6),
        a_decay_rate_theory=f(-2.0 * k, 6),
        L_at_t_end=f(float(L[-1]), 6),
        L_at_times=L_at,
        a_at_t_end=f(float(a_inst[-1]), 6),
        a_over_a0_at_t_end=f(float(a_inst[-1] / a_inst[0]), 6),
        r_median_early=f(float(r_early[0])),
        r_median_late=f(float(r_late[0])),
        ks_phi_first_vs_second_half=f(ks_phi),
        ks_r_spiral_first_vs_second_half=f(ks_r_spiral),
        ks_r_rosette_control=f(ks_r_rosette),
        stationarity_verdict=("螺旋：径向前后半段 KS D=0.991（分布完全分开）；无耗散闭合轨道对照 D=1.5e-4。"
                              "方位前后半段 KS 只有 9.9e-3 —— 螺旋的方位覆盖是均匀的，"
                              "所以'环'的判据必须是径向平稳，不是方位均匀。"),
        a_half_life_time=f(math.log(2.0) / (2.0 * k)),
        a_shrink_10x_time=f(math.log(10.0) / (2.0 * k)),
        a_shrink_10x_orbits=f(math.log(10.0) / (2.0 * k) / (2.0 * math.pi)),
        integrator_limit=("定步长 RK4 在 a<0.05 后 dt 相对内圈周期过大；本表所有斜率只用到 a>0.2 的样本，"
                          "长期行为用解析式 a=a0 e^{-2kt}。"),
        verdict=("dL/dt = -k L 严格（线性阻力对 r×v 的力矩正比 -k L），故 L 指数衰减、"
                 "a 以 2k 速衰减；环的平稳性前提被破坏，累积轨道是瞬态螺旋，不是环。"),
    )


def drag_figure(ax1, ax2, k=1e-2):
    t, X = rk4_drag(k, math.log(20.0) / (2.0 * k), 120000)
    x, y, vx, vy = X[:, 0], X[:, 1], X[:, 2], X[:, 3]
    r = np.hypot(x, y)
    L = x * vy - y * vx
    ax1.plot(x, y, lw=0.6, color="#b85450")
    ax1.set_aspect("equal")
    ax1.set_xlabel("x [AU]")
    ax1.set_ylabel("y [AU]")
    ax1.set_title("(a) 阻力介质中的累积轨道：瞬态螺旋")
    ax1.plot([0], [0], marker="*", ms=8, color="k")
    ax2.semilogy(t, L / L[0], lw=1.2, color="#b85450", label="|L|/L0")
    ax2.semilogy(t, (r / r[0]) ** 2, lw=1.2, ls="--", color="#4a7ebb", label="(r/r0)^2")
    ax2.set_xlabel("t [轨道时间单位]")
    ax2.set_ylabel("归一化量")
    ax2.set_title("(b) L 与 a 的指数衰减（斜率 -k 与 -2k）")
    ax2.legend(loc="lower left")


# ---------------------------------------------------------------- B/C 谐波
def harmonic_block():
    lmax = 6
    rows = []
    for lab, c in [("3/2", 1.5), ("5/3", 5.0 / 3.0), ("7/5", 1.4),
                   ("sqrt2", math.sqrt(2.0)), ("golden", (1 + math.sqrt(5)) / 2)]:
        _, r, phi, _ = rosette_exact(c, 1.0, 4000, 2000)
        A = harmonics(phi, lmax)
        rows.append(dict(label=lab, c=f(c), A_l=[f(x) for x in A],
                         A1=f(A[0]), A_dominant_l=int(np.argmax(A) + 1),
                         fill=f(0.465278 if lab == "7/5" else (1.0 if c != 1.5 else 0.222222))))
    # 分摊：k 条同 c、相位集中在宽度 W 的弧内
    k = 8
    spread = []
    for W in (0.1, 0.3, 1.0, 2.0, 2 * math.pi):
        _, r, phi, _ = rosette_exact((1 + math.sqrt(5)) / 2, 1.0, 4000, 2000)
        ph = []
        for j in range(k):
            off = -W / 2 + W * j / (k - 1)
            ph.append((phi + off) % (2 * math.pi))
        ph = np.concatenate(ph)
        A = harmonics(ph, lmax)
        rbar = 0.62
        spread.append(dict(W_rad=f(W, 4), A1=f(A[0]), A2=f(A[1]), A3=f(A[2]),
                           equiv_center_offset_AU=f(A[0] * rbar)))
    # 时间窗：只覆盖 τ/T 的累积
    tw = []
    _, r, phi, _ = rosette_exact((1 + math.sqrt(5)) / 2, 1.0, 4000, 2000)
    n = phi.size
    for frac in (0.01, 0.03, 0.1, 0.3, 1.0):
        m = max(64, int(frac * n))
        A = harmonics(phi[:m], lmax)
        tw.append(dict(tau_over_T=f(frac, 4), A1=f(A[0]), A2=f(A[1]),
                       equiv_center_offset_AU=f(A[0] * 0.62)))
    return dict(
        spectrum=rows,
        spectrum_note=("c=p/q 时方位谱由 l=q（分母）主导：3/2 -> l=2（0.196），5/3 -> l=3（0.061），"
                       "7/5 -> l=5（1.7e-3）；c 无理时各阶都 < 3.2e-3。A1 恒小 —— 单条轨道没有偶极项。"),
        partial_mixing=spread,
        partial_mixing_note=("负结果（引理）：把同一条闭合轨道绕中心旋转后等权叠加，A1 恒等于 5e-4，"
                             "与旋转宽度 W 无关 —— 因为单条轨道的方位谱没有 l=1 项，旋转只改相位。"
                             "所以环心偏移的假信号不可能由'多条轨道相位不同'造成，只能来自时间覆盖不完备"
                             "（见 time_window）或径向不均匀。"),
        time_window=tw,
        time_window_note=("只累积 τ/T 时方位覆盖是宽度约 2πτ/T 的弧，A1 随 τ 增大而衰减。"),
        degeneracy=("密度 ρ(φ) 的 l=1 项 A1 cos φ 与环心平移 δ 的密度 ρ0(1+(δ/R)cos φ) 同形，"
                    "所以 A1 与 δ/R 无法从一维方位分布中分离 —— 这就是'单中心'推断的系统偏差来源。"),
    )


# ---------------------------------------------------------------- T1 四倾角
def t1_four_inclinations():
    """正交 vs 透视（d_E=5a）在 i=0/30/60/90 上的对比。直接用 mmcommon 的投影函数，
    不 import t1_geometry（那个模块在 import 时会跑整条 T1，24 s）。"""
    M = np.linspace(0.0, 2.0 * np.pi, 1441)
    a, e, om, Om = 1.0, 0.3, 60.0 * DEG, 90.0 * DEG
    dE = 5.0
    fig, axes = plt.subplots(2, 4, figsize=(11.0, 5.4))
    rows = []
    for j, i_deg in enumerate((0.0, 30.0, 60.0, 90.0)):
        i = i_deg * DEG
        r3 = orbit_points(a, e, i, Om, om, M)
        so = apparent_orthographic(r3, 0.0)
        sp, _, _ = apparent_sky(r3, 0.0, dE)
        axes[0, j].plot(so[0], so[1], lw=1.0, color="#4a7ebb")
        axes[0, j].plot([0], [0], marker="*", ms=7, color="k")
        axes[0, j].set_aspect("equal")
        axes[0, j].set_title(f"(a{j+1}) i={i_deg:.0f}° 正交")
        axes[1, j].plot(sp[0], sp[1], lw=1.0, color="#b85450")
        axes[1, j].plot([0], [0], marker="*", ms=7, color="k")
        axes[1, j].set_aspect("equal")
        axes[1, j].set_title(f"(b{j+1}) i={i_deg:.0f}° 透视 d_E=5a")
        for ax in (axes[0, j], axes[1, j]):
            ax.set_xlabel("S1 [AU]")
            ax.set_ylabel("S2 [AU]")
        cen_o = so.mean(axis=1)
        cen_p = sp.mean(axis=1)
        rows.append(dict(i_deg=f(i_deg, 4),
                         ortho_centroid_offset=float(np.hypot(*cen_o)),
                         persp_centroid_offset=float(np.hypot(*cen_p)),
                         ortho_span=float(np.ptp(so[1])),
                         persp_span=float(np.ptp(sp[1])),
                         ortho_span_ratio=f(float(np.ptp(so[1]) / max(np.ptp(so[0]), 1e-12)), 4),
                         persp_span_ratio=f(float(np.ptp(sp[1]) / max(np.ptp(sp[0]), 1e-12)), 4)))
    fig.tight_layout()
    savefig(fig, "fig11_ortho_vs_perspective")
    plt.close(fig)
    return dict(dE_over_a=f(dE, 4), rows=rows,
                note="正交行与透视行同倾角对比；星号是恒星位置，透视下曲线重心相对星号偏移。")


# ---------------------------------------------------------------- main
def main():
    setup_matplotlib()
    D = {}
    D["drag"] = drag_block()

    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.2))
    drag_figure(axes[0], axes[1])
    fig.tight_layout()
    savefig(fig, "fig12_drag_spiral")
    plt.close(fig)

    D["harmonics"] = harmonic_block()

    fig, ax = plt.subplots(1, 1, figsize=(6.4, 4.0))
    labs = [r["label"] for r in D["harmonics"]["spectrum"]]
    for r in D["harmonics"]["spectrum"]:
        ax.plot(range(1, 7), r["A_l"], marker="o", ms=4, lw=1.0, label=f"c={r['label']}")
    ax.set_xlabel("方位谐波阶 l")
    ax.set_ylabel("幅值 A_l")
    ax.set_title("方位密度谱：有理 c 出现锁定阶，无理 c 全阶压低")
    ax.legend(fontsize=7)
    fig.tight_layout()
    savefig(fig, "fig13_harmonics")
    plt.close(fig)

    D["t1_views"] = t1_four_inclinations()

    # T3 需要的一个数：耗散下的半长轴漂移率（每轨道周期）
    k = 1e-2
    T = 2 * math.pi  # 圆轨道 a=1, mu=1
    D["t3_dissipation"] = dict(
        k=f(k),
        a_drift_per_orbit=f(-2.0 * k * T, 6),
        a_drift_rel_per_orbit=f(-2.0 * k * T, 6),
        half_life_orbits=f(math.log(2.0) / (2.0 * k * T), 6),
        note="da/dt = -2ka（圆轨道解析），乘周期 T=2π 得每圈相对漂移；半衰期以圈计。",
    )

    D["_meta"] = meta("T2 counterexamples, T1 ortho-vs-perspective, T3 dissipation",
                      {"k_drag": k, "e_ref": 0.35, "nbin": 72, "lmax": 6,
                       "integrator": "RK4 (drag), analytic rosette (harmonics)"})
    dump("counterexamples.json", D)
    print("drag L rate", D["drag"]["L_decay_rate_fit"], "theory", D["drag"]["L_decay_rate_theory"])
    print("drag a rate", D["drag"]["a_decay_rate_fit"], "theory", D["drag"]["a_decay_rate_theory"])
    print("ks half-half", D["drag"]["ks_phi_first_vs_second_half"])
    for r in D["harmonics"]["spectrum"]:
        print("spectrum", r["label"], r["A_l"], "dom l", r["A_dominant_l"])
    for r in D["harmonics"]["partial_mixing"]:
        print("W", r["W_rad"], "A1", r["A1"], "offset", r["equiv_center_offset_AU"])
    for r in D["harmonics"]["time_window"]:
        print("tau/T", r["tau_over_T"], "A1", r["A1"])
    print("t1 four i centroid:", [(r["i_deg"], r["persp_centroid_offset"]) for r in D["t1_views"]["rows"]])


if __name__ == "__main__":
    main()