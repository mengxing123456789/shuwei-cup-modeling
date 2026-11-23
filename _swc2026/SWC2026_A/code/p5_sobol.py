# -*- coding: utf-8 -*-
"""
Problem 4 的全局敏感性：Sobol（自实现 Saltelli 2010 估计量）。

因子（8 个，乘性缩放，区间见 RANGES）：
  Ainf 增产幅度、tau 浸泡饱和时间、D 递减率、Poil 油价、cprod 处理费、
  csoak 浸泡日费、Cfrac 压裂费、a 浓度敏感度
输出（2 个）：NPV_max（12 档浸泡时长上的最大 NPV）、ts_star（闭式驻点）
采样：scipy.stats.qmc.Sobol(scramble=True, seed=20261120)，N=1024 → 1024*(2*8+2)=18432 次模型求值
"""
import os
import sys
import numpy as np
from scipy.stats.qmc import Sobol

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mm_common as MC
import p4_econ as P4

OUT = {}
FACTORS = ['Ainf', 'tau', 'D', 'Poil', 'cprod', 'csoak', 'Cfrac', 'a']
RANGES = {'Ainf': (0.70, 1.30), 'tau': (0.70, 1.30), 'D': (0.85, 1.15),
          'Poil': (0.85, 1.15), 'cprod': (0.85, 1.15), 'csoak': (0.70, 1.30),
          'Cfrac': (0.70, 1.30), 'a': (0.50, 1.50)}
N = 1024
SEED = 20261120
TS_GRID = np.arange(5, 61, 5, dtype=float)


def npv_matrix(P, case, prm0, cn=1.0):
    """P: (n,8) 乘性因子 → (n, len(TS_GRID)) 的 NPV 矩阵（基线 Vinj=3000）。"""
    n = P.shape[0]
    Ainf = prm0['Ainf'] * P[:, 0]
    tau = prm0['tau'] * P[:, 1]
    p = prm0['p']
    D = prm0['D'] * P[:, 2]
    Poil = P4.E['Poil'] * P[:, 3]
    cprod = P4.E['cprod'] * P[:, 4]
    csoak = P4.E['csoak'] * P[:, 5]
    Cfrac = P4.E['Cfrac'] * P[:, 6]
    a = prm0['a'] * P[:, 7]

    t = np.arange(1, 361, dtype=float)
    r = P4.E['r']
    net = Poil - cprod
    tinj = 3000.0 / 300.0
    S = float(P4.sv(3000.0, 1500.0))
    mat = P4.materials(3000.0, 0.5, cn)
    fixed = Cfrac + mat[3] + mat[4]
    c_inj = float(np.sum(P4.E['cinj'] * P4.disc(np.arange(tinj), r)))

    out = np.empty((n, len(TS_GRID)))
    expD = np.exp(-D[:, None] * t[None, :])            # (n,360)
    enet = net[:, None] * expD                          # (n,360)
    for j, ts in enumerate(TS_GRID):
        df = P4.disc(tinj + ts + t, r)                  # (360,)
        G = enet @ df                                   # (n,)
        A = Ainf * (1.0 - np.exp(-np.power(ts / tau, p))) * (1.0 + a * (cn - 1.0)) * S
        c_soak = np.sum(csoak[:, None] *
                        P4.disc(tinj + np.arange(ts), r)[None, :], axis=1)
        out[:, j] = A * G - (fixed + c_inj + c_soak)
    return out


def ts_closed(P, case, prm0, cn=1.0):
    """闭式驻点 ts* = tau·ln(P_net·Ainf(1+a(cn−1))·S·F/(c_soak·tau))^(1/p)，F 取 20 d。"""
    Ainf = prm0['Ainf'] * P[:, 0]
    tau = prm0['tau'] * P[:, 1]
    p = prm0['p']
    D = prm0['D'] * P[:, 2]
    Poil = P4.E['Poil'] * P[:, 3]
    cprod = P4.E['cprod'] * P[:, 4]
    csoak = P4.E['csoak'] * P[:, 5]
    a = prm0['a'] * P[:, 7]
    t = np.arange(1, 361, dtype=float)
    F = np.sum(np.exp(-D[:, None] * t[None, :]) *
               P4.disc(3000.0 / 300.0 + 20.0 + t, P4.E['r'])[None, :], axis=1)
    S = float(P4.sv(3000.0, 1500.0))
    arg = (Poil - cprod) * Ainf * (1.0 + a * (cn - 1.0)) * S * F / (csoak * tau)
    ts = np.where(arg > 1.0, tau * np.power(np.log(np.maximum(arg, 1.0)), 1.0 / p), 0.0)
    return np.clip(ts, 0.0, 60.0)


def saltelli(fA, fB, fAB):
    """S1/ST 估计量。S1 用 Jansen (1999)：1 − mean((fB−fABi)²)/(2V)，
    ST 用 Jansen：mean((fA−fABi)²)/(2V)。两者同一族，权重一致、无 S1>1 的偏。
    同时保留 Saltelli 2010 的 S1 版本作交叉核对。"""
    k = len(fAB)
    V = np.var(np.concatenate([fA, fB]), ddof=1)
    S1, S1_salt, ST = np.zeros(k), np.zeros(k), np.zeros(k)
    for i in range(k):
        d2 = np.mean((fB - fAB[i]) ** 2)
        S1[i] = 1.0 - d2 / (2.0 * V)
        ST[i] = np.mean((fA - fAB[i]) ** 2) / (2.0 * V)
        S1_salt[i] = np.mean(fB * (fAB[i] - fA)) / V
    return S1, ST, V, S1_salt


def analyse(name, fA, fB, fAB):
    S1, ST, V, S1_salt = saltelli(fA, fB, fAB)
    S1 = np.clip(S1, 0.0, None)
    order = np.argsort(-ST)
    return dict(name=name, V=V,
                S1=dict((FACTORS[i], float(S1[i])) for i in range(len(FACTORS))),
                ST=dict((FACTORS[i], float(ST[i])) for i in range(len(FACTORS))),
                order=[FACTORS[i] for i in order],
                sum_S1=float(S1.sum()), sum_ST=float(ST.sum()),
                S1_list=[float(v) for v in S1], ST_list=[float(v) for v in ST],
                S1_saltelli=[float(v) for v in S1_salt],
                max_abs_S1_minus_ST=float(np.max(np.abs(S1 - ST))))


def main():
    import json
    with open(os.path.join(MC.DATA, 'p3_decline.json'), encoding='utf-8') as f:
        D3 = json.load(f)
    with open(os.path.join(MC.DATA, 'p4_econ.json'), encoding='utf-8') as f:
        D4 = json.load(f)
    prm = {c: D4['params_used'][c] for c in MC.CASE_KEYS}

    OUT['design'] = dict(factors=FACTORS, ranges=RANGES, N=N, seed=SEED,
                         n_eval=int(N * (2 * len(FACTORS) + 2)),
                         ts_grid=[float(v) for v in TS_GRID],
                         estimator='Jansen: S1=1-mean((fB-fABi)^2)/(2V); ST=mean((fA-fABi)^2)/(2V); 附 Saltelli2010 的 S1 作核对')

    # 单一 2k 维 Sobol 设计，前后各取 k 列作 A / B —— 两个独立 Sobol 实例的列
    # 会高度相关（实测 max|corr|=0.94），使估计量有偏
    sobol = Sobol(d=2 * len(FACTORS), scramble=True, seed=SEED)
    U = sobol.random(N)
    def to_factors(cols):
        out = np.zeros_like(cols)
        for j, f in enumerate(FACTORS):
            lo = 1.0 - (1.0 - RANGES[f][0])
            hi = 1.0 + (RANGES[f][1] - 1.0)
            out[:, j] = lo + cols[:, j] * (hi - lo)
        return out
    A = to_factors(U[:, :len(FACTORS)])
    B = to_factors(U[:, len(FACTORS):])
    OUT['design']['max_abs_corr_A_B'] = float(np.max(np.abs([
        np.corrcoef(A[:, i], B[:, j])[0, 1]
        for i in range(len(FACTORS)) for j in range(len(FACTORS))])))

    res = {}
    for case in MC.CASE_KEYS:
        prm0 = prm[case]
        MA = npv_matrix(A, case, prm0)
        MB = npv_matrix(B, case, prm0)
        fA = MA.max(axis=1)
        fB = MB.max(axis=1)
        fAB, gAB = [], []
        tA = ts_closed(A, case, prm0)
        tB = ts_closed(B, case, prm0)
        for i in range(len(FACTORS)):
            AB = A.copy()
            AB[:, i] = B[:, i]
            fAB.append(npv_matrix(AB, case, prm0).max(axis=1))
            gAB.append(ts_closed(AB, case, prm0))
        r_npv = analyse('NPV_max', fA, fB, fAB)
        r_ts = analyse('ts_star', tA, tB, gAB)
        res[case] = dict(
            npv=r_npv, ts=r_ts,
            quantiles=dict(
                npv=[float(np.quantile(np.concatenate([fA, fB]), q)) for q in (0.05, 0.5, 0.95)],
                ts=[float(np.quantile(np.concatenate([tA, tB]), q)) for q in (0.05, 0.5, 0.95)]),
            argmax_ts_at_median=[float(TS_GRID[np.argsort(npv_matrix(
                np.ones((1, len(FACTORS))), case, prm0)[0])[::-1][0]])],
        )
    OUT['sobol'] = res

    # ---- 与 p4 的基线一致性检查（因子全取 1 时 NPV_max 与 ts* 应复现 p4）
    ones = np.ones((1, len(FACTORS)))
    chk = {}
    for case in MC.CASE_KEYS:
        m = npv_matrix(ones, case, prm[case])[0]
        chk[case] = dict(npv_max=float(m.max()), ts_at_max=float(TS_GRID[int(np.argmax(m))]),
                         ts_closed=float(ts_closed(ones, case, prm[case])[0]),
                         p4_npv_max=D4['optimum_ts'][f'{case}|cn1.0']['npv_max'],
                         p4_ts=D4['optimum_ts'][f'{case}|cn1.0']['ts_grid'],
                         p4_ts_closed=D4['optimum_ts'][f'{case}|cn1.0']['ts_closed'])
    OUT['consistency_check'] = chk

    # ---- 解析核对：闭式 ts*=τ·ln(arg) 的半弹性
    # e(Ainf)=e(csoak)=τ/ts*，e(τ)=(ts*−τ)/ts* → 预测的 S1 比 = (e_i/e_Ainf)^2
    ela = {}
    for case in MC.CASE_KEYS:
        prm0 = prm[case]
        ts0 = float(ts_closed(ones, case, prm0)[0])
        tau0 = prm0['tau']
        eA = tau0 / ts0
        etau = (ts0 - tau0) / ts0
        S1 = res[case]['ts']['S1']
        ela[case] = dict(ts_star=ts0, tau=tau0, ts_over_tau=ts0 / tau0,
                         e_Ainf=eA, e_csoak=eA, e_tau=etau,
                         criterion='ts*/τ > 2 (等价 ln(arg)>2) 时 τ 主导，否则 Ainf/csoak 主导',
                         pred_S1_tau_over_Ainf=(etau / eA) ** 2,
                         obs_S1_tau_over_Ainf=S1['tau'] / S1['Ainf'],
                         obs_S1_csoak_over_Ainf=S1['csoak'] / S1['Ainf'],
                         regime=('tau' if ts0 / tau0 > 2.0 else 'Ainf/csoak'))
    OUT['elasticity_check'] = ela
    MC.save_json('p5_sobol', OUT, os.path.abspath(__file__), MC.input_hashes())

    for case in MC.CASE_KEYS:
        r = res[case]['npv']
        print(case, 'NPV  S1:', {k: round(v, 3) for k, v in r['S1'].items()},
              'ST:', {k: round(v, 3) for k, v in r['ST'].items()})
        print('     sumS1=%.3f sumST=%.3f  order=%s' % (r['sum_S1'], r['sum_ST'],
                                                        r['order'][:4]))
        r2 = res[case]['ts']
        print('     ts*  S1:', {k: round(v, 3) for k, v in r2['S1'].items()},
              'ST:', {k: round(v, 3) for k, v in r2['ST'].items()})
        print('     consistency:', {k: round(v, 3) for k, v in chk[case].items()})
    print('OK p5')


if __name__ == '__main__':
    main()