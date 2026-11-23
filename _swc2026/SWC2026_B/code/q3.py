# -*- coding: utf-8 -*-
"""P3：定位误差 + 云台指向误差的方位传导与概率约束。"""
from __future__ import annotations

import math

import numpy as np
from scipy.stats import norm

import common as C

NAME = "p3.json"
SEED = 20261120
R_FIX = 40.0            # 题面：水平距离固定 40 m
SIG_ZERO = 0.8          # deg，云台零偏
SIG_CTRL = 0.6          # deg，云台控制
A0, B0 = 0.3, 0.02      # 题面 sigma(s)=0.3+0.02 s
TOL_DEG = 5.0
PROB = 0.95


def sig_loc_deg(s, a=A0, b=B0, r=R_FIX):
    return (a + b * s) / r * 180.0 / math.pi


def sig_total_deg(s, a=A0, b=B0, r=R_FIX):
    return math.hypot(sig_loc_deg(s, a, b, r), math.hypot(SIG_ZERO, SIG_CTRL))


def mc_p(s, n, a=A0, b=B0, r=R_FIX, seed=SEED, exact=True):
    """精确几何（由估计位置算指令方位）与线性化的对比。"""
    rng = np.random.default_rng(seed)
    sig_s = a + b * s
    d = rng.normal(0.0, sig_s, (2, n))
    e0 = np.radians(rng.normal(0.0, SIG_ZERO, n))
    e1 = np.radians(rng.normal(0.0, SIG_CTRL, n))
    if exact:
        # T 在 (r,0)，估计位置 P̂=(r,0)+(dx,dy)
        # 真实方位：P=(0,0) -> T=(r,0) 为 0；估计位置 P̂=(dx,dy)，T-P̂=(r-dx,-dy)
        psi_cmd = np.arctan2(-d[1], r - d[0])
    else:
        psi_cmd = -d[1] / r
    dpsi = (psi_cmd + e0 + e1)
    dpsi = np.angle(np.exp(1j * dpsi))           # wrap 到 [-pi,pi)
    return float(np.mean(np.abs(dpsi) <= math.radians(TOL_DEG)))


def main():
    out = {"_meta": C.meta("q3.py")}
    z = float(norm.ppf(0.5 + PROB / 2.0))
    budget = TOL_DEG / z
    sig_g2 = SIG_ZERO**2 + SIG_CTRL**2
    sig_loc_max = math.sqrt(max(budget**2 - sig_g2, 0.0))
    sig_s_max = sig_loc_max / 180.0 * math.pi * R_FIX
    s_max = (sig_s_max - A0) / B0
    # 数值求根（用解析式反解作对照，另一路径：对 P(s) 数值单调搜索）
    lo, hi = 0.0, 500.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if sig_total_deg(mid) <= budget:
            lo = mid
        else:
            hi = mid
    s_max_bisect = lo

    mc_at = mc_p(s_max, 100000)
    mc_at_minus = mc_p(s_max * 0.98, 100000, seed=SEED + 1)

    # 三源贡献（方差份额）
    s_list = [0.0, 10.0, 20.0, 40.0, s_max, 80.0]
    contrib = []
    for s in s_list:
        loc = sig_loc_deg(s) ** 2
        tot = loc + sig_g2
        contrib.append(dict(
            s=round(float(s), 4), sigma_loc_deg=round(sig_loc_deg(s), 6),
            sigma_total_deg=round(math.sqrt(tot), 6),
            share_loc=round(loc / tot, 6), share_zero=round(SIG_ZERO**2 / tot, 6),
            share_ctrl=round(SIG_CTRL**2 / tot, 6),
            p_within_5=round(2 * norm.cdf(TOL_DEG / math.sqrt(tot)) - 1, 8),
        ))
    # 定位与云台合成误差相等的交叉点
    s_cross = (math.sqrt(sig_g2) / 180.0 * math.pi * R_FIX - A0) / B0

    # s=80 的 a,b 约束
    b_max_at_a0 = sig_s_max / 80.0
    b_at_a03 = (sig_s_max - A0) / 80.0
    ab = dict(
        s=80.0, sigma_s_allow=round(sig_s_max, 6),
        constraint="a + 80 b <= %.6f  (a>=0, b>=0)" % sig_s_max,
        a_max=round(sig_s_max, 6), b_max=round(b_max_at_a0, 6),
        b_at_a_eq_03=round(b_at_a03, 6),
        shortfall_b=round(B0 - b_at_a03, 6),
        b_ok_at_a0=bool(B0 <= b_max_at_a0 + 1e-12),
        vertices=[[0.0, round(b_max_at_a0, 6)], [round(sig_s_max, 6), 0.0]],
        iso_line="a/%.6f + b/%.6f = 1" % (sig_s_max, b_max_at_a0),
    )
    mc80 = mc_p(80.0, 100000, seed=SEED + 2)
    mc80_ok = mc_p(80.0, 100000, a=0.0, b=b_max_at_a0, seed=SEED + 3)

    # 线性化误差：精确 MC 与闭式在同一 s 的差
    lin_check = []
    for s in (20.0, 40.0, 60.0, 80.0, 120.0, 200.0):
        lin_check.append(dict(s=s, closed=round(float(2 * norm.cdf(TOL_DEG / sig_total_deg(s)) - 1), 8),
                              mc_exact=round(mc_p(s, 200000, seed=SEED + int(s)), 8)))

    out["p3"] = dict(
        z975=round(z, 8), budget_deg=round(budget, 8), sigma_gimbal_deg=round(math.sqrt(sig_g2), 8),
        sigma_loc_allow_deg=round(sig_loc_max, 8), sigma_s_allow_m=round(sig_s_max, 8),
        s_max=round(s_max, 6), s_max_bisect=round(s_max_bisect, 6),
        closed_form="s_max = [ r * sqrt((5/z)^2 - 0.8^2 - 0.6^2) * pi/180 - a ] / b",
        mc_at_s_max=mc_at, mc_at_098_s_max=mc_at_minus,
        contributions=contrib, s_cross_loc_vs_gimbal=round(s_cross, 6),
        ab_constraint=ab, mc_at_80=mc80, mc_at_80_tight=mc80_ok,
        linearization_check=lin_check,
        calibers=dict(
            sigma_total="三分量独立同向叠加后的标准差（角度）",
            p_within="正态近似 2Φ(5/σ)-1；MC 用精确反正切几何",
            share="方差份额，非标准差份额",
        ),
        findings=["定位项在 s>20 m 后成为主导（方差份额>50%）",
                  "s=80 时可行域是 a+80b<=%.4f 的三角形；a=0.3 时 b 上限只有 %.5f，题面的 b=0.02 超 %.5f" % (sig_s_max, b_at_a03, B0 - b_at_a03),
                  "若把 0.3 m 的系统项压到 0，b=0.02 恰好落在可行域内（%.5f < %.5f）" % (B0, b_max_at_a0)],
    )
    C.dump(NAME, out)
    print(f"s_max={s_max:.4f} m (bisect {s_max_bisect:.4f})  sigma_s<= {sig_s_max:.4f} m")
    print(f"MC@ s_max: {mc_at:.5f}   MC@0.98s_max: {mc_at_minus:.5f}   MC@80: {mc80:.5f}")
    print("MC@80 tight:", mc80_ok, " cross s =", round(s_cross, 3))
    for r in contrib:
        print(r)


if __name__ == "__main__":
    main()