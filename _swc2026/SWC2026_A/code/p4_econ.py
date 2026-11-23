# -*- coding: utf-8 -*-
"""
Problem 3 / Problem 4 的经济与优化部分。

口径（同时写进 out/03-numbers.md 的口径段）：
  时间轴      day 0 = 压裂当天；注入 tinj=Vinj/qinj 天；浸泡 ts 天；生产 360 天
  折现        日末折现 (1+r)^(-d/365)，r=8%/yr，365 d/yr，基准 day 0
  收入        Σ q(t)·(P_oil − c_prod − WOR·c_water)，逐日折现
  成本        压裂 day0 一次付；注入期逐日 c_inj；浸泡期逐日 c_soak；
              材料（CO2+纳米）day0 一次付 —— 与题面 B.4 检验向量一致
  产水        附件 C 无产水数据 → 基线 WOR=0（待假设），另做 WOR=0.5 敏感性
  基线 B1     "只压裂" A_B1=0（外推，单列）；主基线取 ts=5（数据支撑内最保守）
  注入量耦合  附件 C 不含 Vinj → S_V=1−exp(−Vinj/V0)，V0 两口径：
              V0_geo=φ0·A_face·R_p(60 d)（机理推导）、V0_emp=1500（经验）
              两种口径下推荐 Vinj 会翻边，故 Vinj 只报"不可识别"，不报最优值
"""
import os
import sys
import math
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mm_common as MC

E = MC.ECON
OUT = {}
DAY = 365.0
V0_EMP = 1500.0


# ------------------------------------------------------------------ 基本量
def materials(Vinj, fCO2, Cn):
    """题面 B.1/B.4 口径。返回 (Vaq, m_nano_t, m_CO2_t, cost_nano, cost_CO2)。"""
    rho_ref = 850.0
    Vaq = Vinj * (1.0 - fCO2)
    m_nano = (Cn / 100.0) * 1000.0 * Vaq / 1000.0          # t
    m_co2 = rho_ref * fCO2 * Vinj / 1000.0                 # t
    return Vaq, m_nano, m_co2, m_nano * 1000.0 * E['cnano'], m_co2 * E['cCO2']


def test_b4():
    """B.4 官方检验向量：Vinj=3000, fCO2=0.5, Cn=1.0 → 848.25 万（不含生产费）。"""
    Vaq, mn, mc, c_nano, c_co2 = materials(3000.0, 0.5, 1.0)
    tinj = 3000.0 / 300.0
    sub = c_nano + c_co2 + E['cinj'] * tinj + E['csoak'] * 30.0 + E['Cfrac']
    val = sub / 1e4
    assert abs(val - 848.25) < 0.01, f'B.4 检验失败: {val}'
    return dict(Vaq=Vaq, m_nano_t=mn, m_co2_t=mc, cost_nano_wan=c_nano / 1e4,
                cost_CO2_wan=c_co2 / 1e4, tinj_d=tinj, subtotal_wan=val, PASS=True)


def disc(d, r=None):
    r = E['r'] if r is None else r
    return np.power(1.0 + r, -np.asarray(d, dtype=float) / DAY)


def A_scale(ts, cn, prm):
    return (prm['Ainf'] * (1.0 - np.exp(-np.power(np.asarray(ts, float) / prm['tau'],
                                                  prm['p'])))
            * (1.0 + prm['a'] * (np.asarray(cn, float) - 1.0)))


def sv(Vinj, V0):
    f = lambda v: 1.0 - np.exp(-np.asarray(v, float) / V0)
    return f(Vinj) / f(3000.0)


def scheme(case, ts, cn=1.0, Vinj=3000.0, qinj=300.0, fCO2=0.5, tau_inj=0.0,
           prm=None, V0=None, WOR=0.0, r=None, cost_day0=False,
           P_oil=None, c_prod=None, c_soak=None, c_frac=None, D=None):
    prm = prm or OUT['_prm'][case]
    P = E['Poil'] if P_oil is None else P_oil
    cp = E['cprod'] if c_prod is None else c_prod
    cs = E['csoak'] if c_soak is None else c_soak
    cf = E['Cfrac'] if c_frac is None else c_frac
    r = E['r'] if r is None else r
    D = D if D is not None else prm['D']
    tinj = Vinj / qinj + tau_inj

    A = float(A_scale(ts, cn, prm))
    if V0 is not None:
        A *= float(sv(Vinj, V0))
    t = np.arange(1, 361, dtype=float)
    q = A * np.exp(-D * t)
    EUR = float(q.sum())
    df = disc(tinj + ts + t, r)
    rev = float(np.sum(q * df) * (P - cp - WOR * E['cwater']))

    _, mn, mc, c_nano, c_co2 = materials(Vinj, fCO2, cn)
    if cost_day0:
        c_inj = E['cinj'] * tinj
        c_soak = cs * ts
    else:
        c_inj = float(np.sum(E['cinj'] * disc(tau_inj + np.arange(tinj), r))) if tinj > 0 else 0.0
        c_soak = float(np.sum(cs * disc(tau_inj + tinj + np.arange(ts), r)))
    cost_nom = cf + c_nano + c_co2 + E['cinj'] * tinj + cs * ts
    cost_pv = cf + c_nano + c_co2 + c_inj + c_soak
    return dict(ts=float(ts), cn=float(cn), Vinj=float(Vinj), qinj=float(qinj),
                fCO2=float(fCO2), tinj_d=float(tinj), A_m3d=A, EUR_m3=EUR,
                rev=rev, cost_nom=cost_nom, cost_pv=cost_pv, npv=rev - cost_pv,
                c_nano=c_nano, c_co2=c_co2, m_nano_t=mn, m_co2_t=mc)


# ------------------------------------------------------------------ 非支配
def dominates(a, b):
    return (a[0] >= b[0] and a[1] <= b[1]) and (a[0] > b[0] or a[1] < b[1])


def nds(F):
    n = len(F)
    S = [[] for _ in range(n)]
    nd = [0] * n
    fronts = [[]]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if dominates(F[i], F[j]):
                S[i].append(j)
            elif dominates(F[j], F[i]):
                nd[i] += 1
        if nd[i] == 0:
            fronts[0].append(i)
    k = 0
    while fronts[k]:
        nxt = []
        for i in fronts[k]:
            for j in S[i]:
                nd[j] -= 1
                if nd[j] == 0:
                    nxt.append(j)
        fronts.append(nxt)
        k += 1
    return [f for f in fronts if f]


def crowding(F, idx):
    d = {i: 0.0 for i in idx}
    for m in range(len(F[0])):
        order = sorted(idx, key=lambda i: F[i][m])
        d[order[0]] = d[order[-1]] = 1e9
        lo, hi = F[order[0]][m], F[order[-1]][m]
        if hi == lo:
            continue
        for k in range(1, len(order) - 1):
            d[order[k]] += (F[order[k + 1]][m] - F[order[k - 1]][m]) / (hi - lo)
    return d


def nsga2(case, V0, pop=64, gens=120, seed=20261120):
    rng = np.random.default_rng(seed)
    lb = np.array([5.0, 0.5, 1000.0, 100.0, 0.2])
    ub = np.array([60.0, 1.5, 5000.0, 800.0, 0.8])
    X = lb + rng.random((pop, 5)) * (ub - lb)
    cache = {}

    def evaluate(x):
        ts, cn, Vinj, qinj, fCO2 = x
        pen = 0.0
        tinj = Vinj / qinj
        _, mn, _, _, _ = materials(Vinj, fCO2, cn)
        if mn > MC.NANO_LIMIT_T:
            pen += (mn - MC.NANO_LIMIT_T) * 1e6
        if tinj + ts > MC.DUR_LIMIT:
            pen += (tinj + ts - MC.DUR_LIMIT) * 1e6
        s = scheme(case, ts, cn, Vinj, qinj, fCO2, V0=V0)
        return (s['EUR_m3'] - pen, s['cost_nom'] + pen), s

    def ev(x):
        k = tuple(np.round(np.asarray(x, float), 6))
        if k not in cache:
            cache[k] = evaluate(np.asarray(x, float))
        return cache[k]

    for _ in range(gens):
        F = [ev(x)[0] for x in X]
        fronts = nds(F)
        rank = np.empty(pop)
        crowd = np.empty(pop)
        for r, f in enumerate(fronts):
            cd = crowding(F, f)
            for i in f:
                rank[i] = r
                crowd[i] = cd[i]
        newX = []
        while len(newX) < pop:
            i, j = rng.integers(0, pop, 2)
            pi = i if (rank[i], -crowd[i]) <= (rank[j], -crowd[j]) else j
            i2, j2 = rng.integers(0, pop, 2)
            pj = i2 if (rank[i2], -crowd[i2]) <= (rank[j2], -crowd[j2]) else j2
            u = rng.random(5)
            beta = np.where(u < 0.5, (2 * u) ** (1 / 16), (1 / (2 * (1 - u))) ** (1 / 16))
            for c in (0.5 * ((1 + beta) * X[pi] + (1 - beta) * X[pj]),
                      0.5 * ((1 - beta) * X[pi] + (1 + beta) * X[pj])):
                mut = rng.random(5) < 0.2
                c[mut] += (rng.random(int(mut.sum())) - 0.5) * (ub - lb)[mut] * 0.15
                newX.append(np.clip(c, lb, ub))
        allX = np.vstack([X, np.array(newX[:pop])])
        Fall = [ev(x)[0] for x in allX]
        sel = []
        for f in nds(Fall):
            if len(sel) + len(f) <= pop:
                sel += f
            else:
                cd = crowding(Fall, f)
                sel += sorted(f, key=lambda i: -cd[i])[:pop - len(sel)]
                break
        X = allX[sel]
    F = [ev(x)[0] for x in X]
    pts = []
    for i in nds(F)[0]:
        s = ev(X[i])[1]
        pts.append(dict(ts=s['ts'], cn=s['cn'], Vinj=s['Vinj'], qinj=s['qinj'],
                        fCO2=s['fCO2'], EUR_m3=s['EUR_m3'], cost_nom=s['cost_nom'],
                        npv=s['npv']))
    return sorted(pts, key=lambda p: p['cost_nom']), len(cache)


def front_grid(case, V0, ts_qinj=800.0):
    """精确前沿：ts × Vinj × Cn × fCO2 全网格（qinj 取上界 800，tinj 因此最短）。"""
    pts = []
    for ts in range(5, 61):
        for Vinj in range(1000, 5001, 100):
            for cn in (0.5, 1.0, 1.5):
                for fCO2 in (0.2, 0.5, 0.8):
                    if Vinj / ts_qinj + ts > MC.DUR_LIMIT:
                        continue
                    s = scheme(case, ts, cn, Vinj, ts_qinj, fCO2, V0=V0)
                    if s['m_nano_t'] > MC.NANO_LIMIT_T:
                        continue
                    pts.append(s)
    # 双目标（max EUR, min cost）的非支配集：按成本升序扫一遍，只保留产量创新高的点
    pts.sort(key=lambda p: (p['cost_nom'], -p['EUR_m3']))
    out = []
    best = -1.0
    for p in pts:
        if p['EUR_m3'] > best + 1e-12:
            out.append(p)
            best = p['EUR_m3']
    return out


def knee(pts, trim=0.05):
    """归一化 (EUR, −cost) 空间里到两端连线距离最大的点；两端各裁掉 trim 分位。"""
    if len(pts) < 5:
        return pts[0] if pts else None, 0.0
    C = np.array([p['cost_nom'] for p in pts], float)
    Q = np.array([p['EUR_m3'] for p in pts], float)
    lo, hi = np.quantile(C, trim), np.quantile(C, 1 - trim)
    m = (C >= lo) & (C <= hi)
    sub = [p for p, mm in zip(pts, m) if mm]
    if len(sub) < 5:
        sub = pts
    C2 = np.array([p['cost_nom'] for p in sub], float)
    Q2 = np.array([p['EUR_m3'] for p in sub], float)
    Cn = (C2 - C2.min()) / max(C2.max() - C2.min(), 1e-12)
    Qn = (Q2 - Q2.min()) / max(Q2.max() - Q2.min(), 1e-12)
    p1 = np.array([Cn[np.argmin(C2)], Qn[np.argmin(C2)]])
    p2 = np.array([Cn[np.argmax(C2)], Qn[np.argmax(C2)]])
    v = p2 - p1
    nv = np.linalg.norm(v)
    if nv < 1e-12:
        return sub[int(np.argmax(Q2))], 0.0
    v = v / nv
    d = np.abs((Cn - p1[0]) * v[1] - (Qn - p1[1]) * v[0])
    k = int(np.argmax(d))
    return sub[k], float(d[k])


def main():
    b4 = test_b4()
    print('PASS %.2f' % b4['subtotal_wan'])
    OUT['test_b4'] = b4

    import json
    with open(os.path.join(MC.DATA, 'p3_decline.json'), encoding='utf-8') as f:
        D3 = json.load(f)
    prm = {}
    for c in MC.CASE_KEYS:
        m = D3['M5_params'][c]
        prm[c] = dict(Ainf=m['Ainf'], tau=m['tau'], p=m['p'], a=m['a'],
                      D=D3['shared_D'][c]['D'], D_sd=D3['shared_D'][c]['D_sd'])
    OUT['_prm'] = prm
    OUT['params_used'] = prm

    # V0 两口径（几何推导用 p1 的 R_p(60)）
    with open(os.path.join(MC.DATA, 'p1_mechanistic.json'), encoding='utf-8') as f:
        D1 = json.load(f)
    V0 = {}
    for c in MC.CASE_KEYS:
        Rp = D1['scaling'][c]['R_numeric_60d']
        aface = 4.0 * MC.FRAC[c]['Lf'] * MC.FRAC[c]['hf']
        V0[c] = dict(geo=float(MC.GEO[c]['phi0'] * aface * Rp), emp=V0_EMP,
                     Rp60=float(Rp), A_face=float(aface))
    OUT['V0'] = V0

    # ---------------- 1) NPV(ts) 曲线（cn 三档，基线 Vinj=3000, qinj=300, fCO2=0.5）
    curves = {}
    for c in MC.CASE_KEYS:
        for cn in (0.5, 1.0, 1.5):
            curves[f'{c}|cn{cn}'] = [
                scheme(c, ts, cn) for ts in range(1, 61)]
    OUT['npv_curves'] = curves

    # ---------------- 2) 最优浸泡时间：网格 argmax + 闭式驻点
    opt = {}
    for c in MC.CASE_KEYS:
        for cn in (0.5, 1.0, 1.5):
            rows = curves[f'{c}|cn{cn}']
            npv = np.array([r['npv'] for r in rows])
            ts = np.array([r['ts'] for r in rows], float)
            i = int(np.argmax(npv))
            p = prm[c]
            Pnet = E['Poil'] - E['cprod']
            ts0 = 20.0
            arg = 1.0
            for _ in range(200):
                F = float(np.sum(np.exp(-p['D'] * np.arange(1, 361))
                                 * disc(10.0 + ts0 + np.arange(1, 361))))
                arg = (Pnet * p['Ainf'] * (1 + p['a'] * (cn - 1.0)) * F
                       / (E['csoak'] * p['tau']))
                ts_new = 0.0 if arg <= 1.0 else p['tau'] * math.log(arg) ** (1.0 / p['p'])
                ts_new = min(max(ts_new, 0.0), 60.0)
                if abs(ts_new - ts0) < 1e-7:
                    ts0 = ts_new
                    break
                ts0 = 0.5 * (ts0 + ts_new)
            band = npv >= npv.max() - 0.02 * abs(npv.max())
            opt[f'{c}|cn{cn}'] = dict(
                ts_grid=float(ts[i]), npv_max=float(npv[i]),
                ts_closed=float(ts0), arg_closed=float(arg),
                band_2pct=[float(ts[band][0]), float(ts[band][-1])],
                npv_at_5=float(npv[4]), npv_at_30=float(npv[29]))
    OUT['optimum_ts'] = opt

    # ---------------- 2b) 两套口径：附件C 档位上的最优（工程可执行）vs 连续驻点（曲线形状）
    dat_grid = {}
    for c in MC.CASE_KEYS:
        for cn in (0.5, 1.0, 1.5):
            rows = curves[f'{c}|cn{cn}']
            lv = [r for r in rows if abs(r['ts'] - round(r['ts'] / 5.0) * 5.0) < 1e-9]
            best = max(lv, key=lambda r: r['npv'])
            o = opt[f'{c}|cn{cn}']
            dat_grid[f'{c}|cn{cn}'] = dict(
                ts_data_grid=float(best['ts']), npv_at_data_grid=float(best['npv']),
                ts_continuous=o['ts_closed'], npv_at_continuous=float(o['npv_max']),
                d_ts=float(o['ts_closed'] - best['ts']),
                d_npv_wan=float((o['npv_max'] - best['npv']) / 1e4),
                same_level=bool(abs(o['ts_closed'] - best['ts']) < 2.5),
                note='工程上浸泡天数只能取 5,10,...,60 档；连续驻点只用来说明曲线形状与灵敏度')
    OUT['optimum_two_calibers'] = dat_grid
    OUT['note_two_calibers'] = ('决策值取 ts_data_grid（附件C 只在 5,10,...,60 给出实测）；'
                                'ts_continuous 为 dNPV/dts=0 的驻点，用于 P5 的弹性分析')

    # ---------------- 2c) 数据驱动 vs 机理 的差异归因（每条给方向与量级）
    att = {}
    att['A_face_convention'] = dict(
        expression='A_face = 4·Lf·hf = 2(条缝翼) × 2(个面) × Lf × hf',
        value={c: float(OUT['V0'][c]['A_face']) for c in MC.CASE_KEYS},
        Lf_hf={c: [MC.FRAC[c]['Lf'], MC.FRAC[c]['hf']] for c in MC.CASE_KEYS},
        note='Lf 取半长口径；若按"缝面面积=2·Lf·hf（Lf 为全长）"读表，V0_geo 与等效注入面积同比减半')
    # 共享 D 假设：D 的组间散布 → 累计产油的相对偏移 = D_sd × (Σt·q/Σq) = D_sd / D
    att['shared_D_impact'] = {}
    for c in MC.CASE_KEYS:
        p_ = prm[c]
        att['shared_D_impact'][c] = dict(
            D=float(p_['D']), D_sd=float(p_.get('D_sd', 0.0)),
            rel_dD=float(p_.get('D_sd', 0.0) / p_['D']),
            d_EUR_rel=float(p_.get('D_sd', 0.0) / p_['D']),
            direction='若真实 D 大于共享值，累计产油偏低（D 越大衰减越快）',
            note='指数律下 ∂lnEUR/∂D = −Σt·q/Σq = −1/D，故累计产油相对偏移 = ΔD/D')
    # 数值误差：网格收敛只影响 R_p 与 V0_geo，不进入 NPV（NPV 用数据拟合的 A）
    att['numerical_error'] = dict(
        source='data/p1_mechanistic.json: grid_convergence、solver_check',
        note='网格加密的相对差在 1e-5 量级；且 R_p 不进入 NPV 计算（NPV 用附件C 拟合的 A），'
             '只影响 P2 的 R_p 与 V0_geo，故对 NPV 的影响可忽略、对 V0 的影响与 R_p 同比')
    # 数据噪声：题面声明 ±5%，实测残差（相对）的中位数
    with open(os.path.join(MC.DATA, 'p3_decline.json'), encoding='utf-8') as f:
        D3 = json.load(f)
    att['data_noise'] = dict(
        declared='附件C 声明 ±5% 高斯噪声（题面 Attachment C 说明）',
        measured_med_rel_resid=float(D3['noise_check']['med_rel_resid']),
        measured_resid_sd_rel=float(D3['noise_check']['resid_sd_rel']),
        direction='若把残差全部当噪声，会高估噪声、低估模型形式误差；实测中位相对残差高于 5%，'
                  '差额归因于"产量按 2 位小数截断 + A 的乘法结构放大相对误差"',
        eur_ci_wan={c: float((D3['bootstrap'][c]['EUR'][1] - D3['bootstrap'][c]['EUR'][0]) / 2.0)
                    for c in MC.CASE_KEYS})
    OUT['attribution'] = att

    # ---------------- 3) 盈亏平衡反推
    be = {}
    for c in MC.CASE_KEYS:
        rows = curves[f'{c}|cn1.0']
        i = int(np.argmax([r['npv'] for r in rows]))
        s = scheme(c, rows[i]['ts'], 1.0)
        net = E['Poil'] - E['cprod']
        be[c] = dict(
            ts_opt=int(rows[i]['ts']), npv=s['npv'], EUR_obs=s['EUR_m3'],
            cost_pv=s['cost_pv'], rev=s['rev'],
            EUR_required_for_zero=float(s['cost_pv'] / net),
            ratio_required_over_observed=float(s['cost_pv'] / net / s['EUR_m3']),
            frac_cost_required_for_zero=float(s['rev'] - (s['cost_pv'] - E['Cfrac'])),
            price_required_for_zero=float(s['cost_pv'] / s['EUR_m3'] + E['cprod']))
    OUT['break_even'] = be

    # ---------------- 4) 前沿：网格（精确）+ NSGA-II（独立对账），V0 两口径
    fronts, meta = {}, {}
    for c in MC.CASE_KEYS:
        for tag in ('geo', 'emp'):
            key = f'{c}|{tag}'
            fp = front_grid(c, V0[c][tag])
            kn, kd = knee(fp)
            best = max(fp, key=lambda p: p['npv'])
            fronts[key] = [dict(ts=p['ts'], cn=p['cn'], Vinj=p['Vinj'], fCO2=p['fCO2'],
                                qinj=p['qinj'], EUR_m3=p['EUR_m3'],
                                cost_nom=p['cost_nom'], npv=p['npv'],
                                m_nano_t=p['m_nano_t']) for p in fp]
            meta[key] = dict(n_front=len(fp), knee=dict(kn, knee_dist=kd),
                             npv_best=best, min_cost=fp[0], max_EUR=max(fp, key=lambda p: p['EUR_m3']))
        g, _neval = nsga2(c, V0[c]['emp'])
        meta[f'{c}|nsga2_check'] = dict(
            n_front=len(g), npv_best=max(g, key=lambda p: p['npv']),
            npv_best_grid=meta[f'{c}|emp']['npv_best']['npv'],
            rel_diff=float((max(g, key=lambda p: p['npv'])['npv']
                            - meta[f'{c}|emp']['npv_best']['npv'])
                           / abs(meta[f'{c}|emp']['npv_best']['npv'])))
    OUT['pareto'] = fronts
    OUT['pareto_meta'] = meta

    # ---------------- 5) 鲁棒性：±15% 扰动下 argmax ts 是否变（决策不变性）
    rob = {}
    factors = ('Ainf', 'tau', 'D', 'Poil', 'cprod', 'csoak', 'Cfrac')
    for c in MC.CASE_KEYS:
        base = curves[f'{c}|cn1.0']
        base_npv = np.array([r['npv'] for r in base])
        ts_ax = np.array([r['ts'] for r in base], float)
        base_ts = float(ts_ax[int(np.argmax(base_npv))])
        rows = {}
        for fac in factors:
            for sgn in (+1, -1):
                sc = 1.0 + sgn * 0.15
                p2 = dict(prm[c])
                kw = {}
                if fac == 'Ainf':
                    p2['Ainf'] = prm[c]['Ainf'] * sc
                elif fac == 'tau':
                    p2['tau'] = prm[c]['tau'] * sc
                elif fac == 'D':
                    p2['D'] = prm[c]['D'] * sc
                elif fac == 'Poil':
                    kw['P_oil'] = E['Poil'] * sc
                elif fac == 'cprod':
                    kw['c_prod'] = E['cprod'] * sc
                elif fac == 'csoak':
                    kw['c_soak'] = E['csoak'] * sc
                elif fac == 'Cfrac':
                    kw['c_frac'] = E['Cfrac'] * sc
                vals = np.array([scheme(c, ts, 1.0, prm=p2, **kw)['npv'] for ts in ts_ax])
                i = int(np.argmax(vals))
                rows[f'{fac}{"+" if sgn > 0 else "-"}'] = dict(
                    ts=float(ts_ax[i]), npv=float(vals[i]),
                    d_ts=float(ts_ax[i] - base_ts), d_npv=float(vals[i] - base_npv.max()),
                    changed=bool(abs(ts_ax[i] - base_ts) > 2.5))
        nch = sum(1 for v in rows.values() if v['changed'])
        rob[c] = dict(base_ts=base_ts, base_npv=float(base_npv.max()), cases=rows,
                      n_perturb=len(rows), n_changed=nch,
                      dominated_factor=[k for k, v in rows.items() if v['changed']],
                      npv_min=float(min(v['npv'] for v in rows.values())),
                      npv_max=float(max(v['npv'] for v in rows.values())),
                      npv_span_rel=float((max(v['npv'] for v in rows.values())
                                          - min(v['npv'] for v in rows.values()))
                                         / max(abs(base_npv.max()), 1e-9)))
    OUT['robustness'] = rob

    # ---------------- 6) 机理通道（数据驱动模型对这些量严格不敏感）
    OUT['mechanism_channel'] = dict(
        note='A(ts,Cn) 不含 k_m/σ 特征 → 数据驱动模型对二者不敏感；机理通道 R_p∝√k_m',
        Rp_ratio_low=float(math.sqrt(0.85)), Rp_ratio_high=float(math.sqrt(1.15)),
        ts_equiv=float(math.sqrt(1.15 / 0.85)))

    OUT['design_space'] = dict(
        note='P4 精确前沿的网格与约束；qinj 取上限 800 m³/d 使注入期最短',
        ts_range=[5, 60, 1], Vinj_range=[1000, 5000, 100],
        Cn_levels=[0.5, 1.0, 1.5], fCO2_levels=[0.2, 0.5, 0.8], qinj=800.0,
        n_candidates=56 * 41 * 3 * 3,
        constraints=['m_nano = (Cn/100)*1000*Vaq/1000 <= 30 t/井',
                     'tinj + ts <= 90 d，tinj = Vinj/qinj'],
        n_front=dict((c, int(meta[f'{c}|emp']['n_front'])) for c in MC.CASE_KEYS))

    # ---------------- 7) 与 lead 对照
    OUT['lead_reconcile'] = dict(
        note='lead 对照值不含 CO2 材料费；其余口径相同（日末折现、成本 day0、处理费折现）',
        co2_cost_wan=float(materials(3000.0, 0.5, 1.0)[4] / 1e4),
        my_npv_cn1=dict((c, {int(r['ts']): round(r['npv'] / 1e4, 2)
                             for r in curves[f'{c}|cn1.0'] if r['ts'] in (5, 10, 20, 30, 40, 60)})
                        for c in MC.CASE_KEYS),
        diff_note='我的口径 = lead 口径 − 38.25 万元（CO2 材料费），逐点常数')
    MC.save_json('p4_econ', OUT, os.path.abspath(__file__), MC.input_hashes())

    for c in MC.CASE_KEYS:
        o = opt[f'{c}|cn1.0']
        m = meta[f'{c}|emp']
        print(c, 'ts*=%d npv=%.2f万 closed=%.1f band=%s 盈亏比=%.2f'
              % (o['ts_grid'], o['npv_max'] / 1e4, o['ts_closed'], o['band_2pct'],
                 be[c]['ratio_required_over_observed']))
        print('   front(emp) n=%d knee ts=%d Vinj=%d npv=%.1f万 | npv_best ts=%d Vinj=%d npv=%.1f万'
              % (m['n_front'], m['knee']['ts'], m['knee']['Vinj'], m['knee']['npv'] / 1e4,
                 m['npv_best']['ts'], m['npv_best']['Vinj'], m['npv_best']['npv'] / 1e4))
        print('   front(geo) npv_best ts=%d Vinj=%d npv=%.1f万 | nsga2 rel_diff=%.3f'
              % (meta[f'{c}|geo']['npv_best']['ts'], meta[f'{c}|geo']['npv_best']['Vinj'],
                 meta[f'{c}|geo']['npv_best']['npv'] / 1e4,
                 meta[f'{c}|nsga2_check']['rel_diff']))
        print('   robust %d/%d 变 ts; npv span %.1f%%'
              % (rob[c]['n_changed'], rob[c]['n_perturb'], 100 * rob[c]['npv_span_rel']))
    print('OK p4')


if __name__ == '__main__':
    main()