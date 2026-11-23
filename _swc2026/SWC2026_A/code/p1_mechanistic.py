# -*- coding: utf-8 -*-
"""
Problem 1 / Problem 2 的机理部分。

1) 无量纲化：导出 10 个无量纲群并逐案给数值与量级；
2) 数量级比较表：压力方程每一项 / 参考项的比值，据此判定可忽略项；
3) 一维（垂直裂缝面法向）渗流-应力-损伤耦合有限体积求解：
       φ c_t ∂p/∂t = ∂/∂x[ k(p,d)/μ · ∂p/∂x ]
       ε(x) = χ(x)·α_b·Δp/K_b,  χ = a_σ (L_f/(2x+w_f))^{m}
       d = 1-exp[-β_d max(ε-ε_d,0)]
       k = k_0 exp(γ_k Δp)(1+A_d d)
       ∂C/∂t = D_CO2 ∂²C/∂x² ;  ∂n/∂t = D_n/R_n ∂²n/∂x²
4) 改造半径 R(t) 的四种判据，标度指数 ν 的数值反演（含网格收敛）；
5) 用附件 C 反演的 A(ts) 与模型 R_p(ts) 做交叉验证；两个饱和机制假设各自算
   τ_sat 并与数据拟合的 τ 对账（PASS/FAIL 逐条）。
"""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mm_common as MC

DAY = 86400.0
MPA = 1e6
MD = 9.869233e-16  # 1 mD -> m^2

OUT = {}


# ------------------------------------------------------------ 无量纲群
def groups(case):
    g = MC.GEO[case]
    f = MC.FLUID[case]
    fr = MC.FRAC[case]
    E = g['E'] * 1e9
    Kb = E / (3.0 * (1 - 2 * g['nu']))
    p0 = g['p0'] * MPA
    dp = (g['pmax'] - g['p0']) * MPA
    k = g['km'] * MD
    mu = f['mu_o'] * 1e-3
    ct = (f['co'] + g['cphi']) / MPA
    alpha_p = k / (mu * g['phi0'] * ct)
    Lref = g['h'] / 2.0
    tref = 60 * DAY
    Aface = 4.0 * fr['Lf'] * fr['hf']
    q = fr['qinj'] / DAY
    Rn = 1.0 + g['rho_r'] * f['Kd'] / g['phi0']

    d = {}
    d['Pi1_Fourier_60d'] = dict(v=alpha_p * tref / Lref ** 2,
                                expr='α_p·t/L_ref², α_p=k/(μ φ c_t), L_ref=h/2, t=60 d',
                                mean='60 d 内压力扰动覆盖基质块半宽的程度（时间-空间相似性）')
    d['Pi2_poroelastic'] = dict(v=g['alpha_b'] * p0 / Kb,
                                expr='α_b p0/K_b',
                                mean='Biot 耦合强度：孔隙压引起的骨架体积应变相对量')
    d['Pi3_stressperm'] = dict(v=g['gamma_k'] * (g['pmax'] - g['p0']),
                               expr='γ_k Δp_max',
                               mean='应力敏感渗透率的指数增益（改造前后 k 之比 = e^Π3）')
    d['Pi4_storage_split'] = dict(v=g['cphi'] / (f['co'] + g['cphi']),
                                  expr='c_φ/(c_o+c_φ)',
                                  mean='储集能力中孔隙压缩所占份额（其余为流体压缩）')
    d['Pi5_co2_diff'] = dict(v=f['D_co2o'] * tref / Lref ** 2,
                             expr='D_CO2 t/L_ref²',
                             mean='CO2 分子扩散的傅里叶数；与 Π1 之比即扩散/压力扩散')
    d['Pi6_retard'] = dict(v=Rn, expr='R_n=1+ρ_r K_d/φ0',
                           mean='纳米颗粒吸附阻滞因子（有效扩散系数除以 R_n）')
    d['Pi7_damage'] = dict(v=g['bd'] * g['ed'], expr='β_d ε_d',
                           mean='损伤演化曲线的陡度×门槛：决定损伤是"脆断"还是"渐变"')
    d['Pi8_stressconc'] = dict(v=f['asig'] * np.sqrt(fr['Lf'] / (fr['wf'] * 1e-3))
                               * g['alpha_b'] * dp / (Kb * g['ed']),
                               expr='a_σ√(L_f/w_f)·α_bΔp/(K_b ε_d)',
                               mean='裂缝面应力集中把应变放大到损伤门槛之上的倍数（>1 才起损伤）')
    d['Pi9_injectivity'] = dict(v=k * dp / (mu * q / Aface),
                                expr='k Δp/(μ q/A_face)',
                                mean='地层吸水能力/泵排量：≫1 表示注入为压力控制，可用 p=pmax 边界')
    d['Pi10_time'] = dict(v=fr['ts'] / fr['Tprod'], expr='t_soak/T_prod',
                          mean='浸泡时间占生产期的比例（经济折现的权重）')
    for kk in d:
        d[kk]['fmt'] = f"{d[kk]['v']:.4g}"
        av = abs(d[kk]['v'])
        d[kk]['order'] = (int(np.floor(np.log10(av))) if av > 0 else None)
    d['_derived'] = dict(alpha_p=alpha_p, Kb=Kb, ct=ct, mu_o=mu, k_m=k,
                         eta=float(np.sqrt(alpha_p * DAY)),
                         A_face=Aface, Rn=Rn)
    return d


# ------------------------------------------------------------ 数量级表
def term_table(case):
    g = MC.GEO[case]
    f = MC.FLUID[case]
    fr = MC.FRAC[case]
    E = g['E'] * 1e9
    Kb = E / (3.0 * (1 - 2 * g['nu']))
    p0 = g['p0'] * MPA
    dp = (g['pmax'] - g['p0']) * MPA
    k = g['km'] * MD
    mu = f['mu_o'] * 1e-3
    ct = (f['co'] + g['cphi']) / MPA
    phi = g['phi0']
    L = g['h'] / 2.0   # 评价尺度：基质块半宽 h/2，与 Π1 的 L_ref 一致
    tref = 60 * DAY
    # 全部换算成"等效压力梯度"(Pa/m) 再比 —— 量纲一致，比值才有意义
    grad_drive = dp / L
    T = {}
    T['darcy_drive'] = dict(v=grad_drive, expr='Δp/L',
                            mean='注采压差驱动的达西梯度（参考项）')
    T['accumulation'] = dict(v=phi * ct * dp / tref * (mu / k), expr='(φ c_t Δp/t_ref)·μ/k',
                             mean='累积项折算的等效梯度；与驱动之比 = 1/Π1')
    T['gravity'] = dict(v=(f['rho_w'] - f['rho_o']) * 9.81, expr='Δρ g',
                        mean='重力分异（水-油密度差）')
    T['capillary'] = dict(v=f['Ac'] * MPA / L, expr='A_c/L',
                          mean='毛细管压力梯度（缝面附近）')
    T['thermal'] = dict(v=0.0, expr='—', mean='非等温膨胀项（本题给定等温，恒为 0）')
    ref = T['darcy_drive']['v']
    for kk in T:
        T[kk]['ratio'] = T[kk]['v'] / ref if ref else 0.0
    # 判据：|比值| >= 0.1 保留；0.01–0.1 保留但注明量级；< 0.01 可忽略，并给出误差上界
    for kk in T:
        r = abs(T[kk]['ratio'])
        if kk in ('darcy_drive', 'accumulation'):
            T[kk]['verdict'] = '保留'
        elif r >= 0.1:
            T[kk]['verdict'] = '保留'
        elif r >= 0.01:
            T[kk]['verdict'] = '保留（量级 1%–10%，须在正文注明）'
        else:
            T[kk]['verdict'] = '可忽略（误差上界 %.2f%%）' % (100 * r)
    # Biot 项是"应变尺度"的量，不能与压力梯度直接比；单独与弹性应变比
    biot_to_elastic = g['alpha_b'] * (g['E'] * 1e9) / Kb if Kb < 1e12 else None
    T['_strain'] = dict(
        alpha_b_over_E=float(g['alpha_b'] * (g['E'] * 1e9) / Kb),
        expr='α_b E/K_b（Biot 体应变 / 弹性体应变）',
        verdict='O(1) ⇒ Biot 耦合必须保留；但这不等于"Π2 小 ⇒ 可忽略"：'
                'Π2 = α_b p0/K_b 是应变量级 10^-3，真正决定要不要保留的是两者之比',
        integer=float(g['alpha_b'] * (g['E'] * 1e9) / Kb) >= 0.1,
    )
    T['_extra'] = dict(
        L_ref_m=L, note='L_ref = h/2 = 10 m（基质块半宽）；累积项与驱动之比恒等于 1/Π1，'
                        '重力与驱动之比 = Δρ g L/Δp，毛细管与驱动之比 = A_c/Δp',
        peclet_co2=(k / mu) * dp / L * L / f['D_co2o'],
        note_peclet='CO2 的对流/扩散比（Pe）：注采期 ≫1 对流主导，关井期 u→0 只有扩散，'
                    '这就是浸泡阶段必须保留扩散项的原因',
    )
    return T


# ------------------------------------------------------------ 一维求解器
def _thomas(a, b, c, r):
    n = len(b)
    cp = np.empty(n)
    dp = np.empty(n)
    cp[0] = c[0] / b[0]
    dp[0] = r[0] / b[0]
    for i in range(1, n):
        m = b[i] - a[i] * cp[i - 1]
        cp[i] = c[i] / m
        dp[i] = (r[i] - a[i] * dp[i - 1]) / m
    x = np.empty(n)
    x[-1] = dp[-1]
    for i in range(n - 2, -1, -1):
        x[i] = dp[i] - cp[i] * x[i + 1]
    return x


def grid(N, a, Lx):
    s = np.linspace(0, 1, N)
    x = Lx * (np.power(a, s * (N - 1)) - 1.0) / (np.power(a, N - 1) - 1.0)
    x[0] = 0.0
    x[-1] = Lx
    return x


def solve(case, ts=60.0, N=300, a=1.028, Lx=600.0, dt=0.05,
          gamma_scale=1.0, bd_scale=1.0, Ad=20.0, m_conc=0.5, tmax=95.0):
    g = MC.GEO[case]
    f = MC.FLUID[case]
    fr = MC.FRAC[case]
    E = g['E'] * 1e9
    Kb = E / (3.0 * (1 - 2 * g['nu']))
    p0 = g['p0'] * MPA
    dp0 = (g['pmax'] - g['p0']) * MPA
    k0 = g['km'] * MD
    mu = f['mu_o'] * 1e-3
    ct = (f['co'] + g['cphi']) / MPA
    phi = g['phi0']
    gk = g['gamma_k'] / MPA * gamma_scale
    bd = g['bd'] * bd_scale
    ed = g['ed']
    Lf = fr['Lf']
    wf = fr['wf'] * 1e-3
    Dc = f['D_co2o']
    Rn = 1.0 + g['rho_r'] * f['Kd'] / phi
    Dn = f['Dn'] / Rn

    x = grid(N, a, Lx)
    h = np.diff(x)                       # h[i] = x[i+1]-x[i], i=0..N-2
    hv = np.empty(N)                     # 节点控制体宽度
    hv[0] = h[0] / 2
    hv[-1] = h[-1] / 2
    hv[1:-1] = (h[:-1] + h[1:]) / 2

    p = np.full(N, p0)
    C = np.zeros(N)
    nn = np.zeros(N)
    dm = np.zeros(N)

    # t = 1..ts（索引 j 对应 t = j+1）；不能到 ts+1：循环只推到 t = ts，
    # 多出那一格会永远是 NaN，写进 JSON 就是一个 None。
    ts_grid = np.arange(1, int(min(tmax, ts)) + 1, dtype=float)
    rec = {k: np.full(len(ts_grid), np.nan) for k in ('Rp', 'RC', 'Rn', 'Rd', 'qface')}
    t = 0.0
    mass_in = 0.0
    steps = 0
    nsteps = int(round(ts / dt))
    for it in range(nsteps):
        # ---- 物性（用上一时刻的 p, d）
        dpa = np.clip(p - p0, 0.0, None)
        eps = f['asig'] * np.power(Lf / (2.0 * np.maximum(x, wf) + wf), m_conc) \
            * g['alpha_b'] * dpa / Kb
        dm = np.clip(1.0 - np.exp(-bd * np.maximum(eps - ed, 0.0)), 0.0, 0.999)
        kk = k0 * np.exp(gk * dpa) * (1.0 + Ad * dm)
        lam = kk / mu

        lam_f = 0.5 * (lam[:-1] + lam[1:])
        A = lam_f / h                     # 面导度 A[i] 在节点 i 与 i+1 之间
        # 压力：节点 0 Dirichlet=pmax，节点 N-1 Dirichlet=p0
        coef_f = phi * ct * hv / (dt * DAY)   # 时间统一到 s
        idx = np.arange(1, N - 1)
        b = coef_f[idx] + A[idx - 1] + A[idx]
        aa = -A[idx - 1].copy()
        cc = -A[idx].copy()
        rhs = coef_f[idx] * p[idx]
        aa[0] = 0.0
        cc[-1] = 0.0
        rhs[0] += A[0] * (g['pmax'] * MPA)
        rhs[-1] += A[N - 2] * p0
        p_new = p.copy()
        p_new[idx] = _thomas(aa, b, cc, rhs)
        p_new[0] = g['pmax'] * MPA
        p_new[-1] = p0
        # 面通量 m^3/d（用于质量平衡检查）
        aface = 4.0 * Lf * fr['hf']
        qface = A[0] * (p_new[0] - p_new[1]) * aface * DAY
        mass_in += qface * dt

        # CO2 / 纳米：隐式扩散
        for arr, Dcoef in ((C, Dc), (nn, Dn)):
            hh = np.empty(N)
            hh[1:-1] = hv[1:-1]
            hh[0] = hv[0]
            hh[-1] = hv[-1]
            cf = hh / (dt * DAY)                  # 时间统一到 s
            bb = np.empty(N)
            bb[0] = 1.0
            bb[-1] = 1.0
            bb[1:-1] = cf[1:-1] + (Dcoef / h[:-1] + Dcoef / h[1:])
            aaa = np.zeros(N)
            ccc = np.zeros(N)
            aaa[2:-1] = -Dcoef / h[1:-1]
            ccc[1:-2] = -Dcoef / h[1:-1]
            rr = np.zeros(N)
            rr[0] = 1.0                     # Dirichlet C=1
            rr[-1] = 0.0
            rr[1:-1] = cf[1:-1] * arr[1:-1]
            sol = _thomas(aaa, bb, ccc, rr)
            arr[:] = sol

        p = p_new
        t += dt
        steps += 1
        if abs(t - round(t)) < dt * 0.5 and 1 <= int(round(t)) <= len(ts_grid):
            j = int(round(t)) - 1
            rec['Rp'][j] = _cross(x, (p - p0) / p0, 0.05)
            rec['RC'][j] = _cross(x, C, 0.01)
            rec['Rn'][j] = _cross(x, nn, 0.01)
            rec['Rd'][j] = _cross(x, dm, 0.10)
            rec['qface'][j] = qface

    # ---- 质量平衡（检验用）：累计注入 / 域内增量
    aface = 4.0 * Lf * fr['hf']
    store = phi * ct * np.sum((p - p0) * hv) * aface
    res = dict(
        mass_in_m3=float(mass_in), store_m3=float(store),
        rel_imbalance=float(abs(mass_in - store) / max(abs(mass_in), 1e-12)),
        n_steps=int(steps), dt_d=float(dt), N=int(N),
        achieved_rate_m3_d=float(np.nanmean(rec['qface'][:int(ts)])),
        pump_rate_m3_d=float(fr['qinj']),
        p_face_MPa=float(g['pmax']), Rp_end_m=float(rec['Rp'][int(ts) - 1]),
        dm_max=float(dm.max()), dm_at_1m=float(np.interp(1.0, x, dm)),
        Rn=Rn, Dn_eff=Dn,
    )
    return dict(t=ts_grid, x=x, rec=rec, store=res, p=p, dm=dm, C=C, n=nn)


def _cross(x, val, thr):
    """从注入面向外扫，找 val 最后一次 >= thr 的位置（单调递减假设下的阈值交点）。"""
    above = val >= thr
    if not above.any():
        return 0.0
    k = np.where(above)[0]
    if above.all():
        return float(x[-1])
    i = k[-1]
    if i >= len(x) - 1:
        return float(x[-1])
    v1, v2 = val[i], val[i + 1]
    if v2 == v1:
        return float(x[i])
    f = (thr - v1) / (v2 - v1)
    return float(x[i] + f * (x[i + 1] - x[i]))


def fit_nu(t, R, lo, hi):
    m = (t >= lo) & (t <= hi) & (R > 0)
    if m.sum() < 4:
        return dict(nu=np.nan, C=np.nan, r2=np.nan, n=int(m.sum()))
    lx = np.log(t[m])
    ly = np.log(R[m])
    b, a0, _r2 = MC.ols_slope(lx, ly)
    pred = a0 + b * lx
    ss = np.sum((ly - pred) ** 2)
    sst = np.sum((ly - ly.mean()) ** 2)
    return dict(nu=float(b), C=float(np.exp(a0)), r2=float(1 - ss / sst), n=int(m.sum()))


def main():
    OUT['dimensionless'] = {}
    OUT['terms'] = {}
    for case in MC.CASE_KEYS:
        OUT['dimensionless'][case] = groups(case)
        OUT['terms'][case] = term_table(case)

    OUT['radii'] = {}
    OUT['scaling'] = {}
    OUT['solver_check'] = {}
    OUT['profiles'] = {}
    for case in MC.CASE_KEYS:
        s = solve(case, ts=60.0)
        r = s['rec']
        OUT['solver_check'][case] = s['store']
        OUT['radii'][case] = {
            't_d': [int(v) for v in s['t']],
            'Rp': [float(v) for v in r['Rp']],
            'RC': [float(v) for v in r['RC']],
            'Rn': [float(v) for v in r['Rn']],
            'Rd': [float(v) for v in r['Rd']],
        }
        sc = {}
        for lo, hi, tag in ((5, 20, 'early'), (5, 60, 'all'), (20, 60, 'late')):
            sc[tag] = fit_nu(s['t'], r['Rp'], lo, hi)
        g = MC.GEO[case]
        dp0 = (g['pmax'] - g['p0'])
        theta = 0.05 * g['p0'] / dp0
        from scipy.special import erfcinv
        eta = float(erfcinv(theta))
        sc['eta'] = eta
        sc['theta'] = float(theta)
        sc['analytic_form'] = ('Δp/p0 = 5%% ⇒ x = 2·erfc⁻¹(θ)·sqrt(α_p t), '
                               'θ = 0.05·p0/(pmax-p0) = %.5f, erfc⁻¹(θ) = %.5f' % (theta, eta))
        alpha_p = OUT['dimensionless'][case]['_derived']['alpha_p']
        sc['R_analytic_60d'] = float(2 * eta * np.sqrt(alpha_p * 60 * DAY))
        sc['R_numeric_60d'] = float(r['Rp'][59])
        sc['ratio_num_ana'] = float(r['Rp'][59] / sc['R_analytic_60d'])
        # 两个饱和机制假设
        h2 = g['h'] / 2
        Lf2 = MC.FRAC[case]['Lf'] / 2
        sc['tau_sat_A_block'] = float((h2 / (2 * eta)) ** 2 / alpha_p / DAY)
        sc['tau_sat_B_frac'] = float((Lf2 / (2 * eta)) ** 2 / alpha_p / DAY)
        OUT['scaling'][case] = sc
        # 剖面快照（60 d）
        x = s['x']
        pick = [0.0, 0.1, 1.0, 5.0, 10.0, 20.0, 40.0, 60.0]
        OUT['profiles'][case] = dict(
            x=[float(v) for v in pick],
            Rp_at=[float(np.interp(v, x, (s['p'] - MC.GEO[case]['p0'] * MPA)
                                  / (MC.GEO[case]['p0'] * MPA))) for v in pick],
            dm=[float(np.interp(v, x, s['dm'])) for v in pick],
            C=[float(np.interp(v, x, s['C'])) for v in pick],
            n=[float(np.interp(v, x, s['n'])) for v in pick],
        )

    # ---- 网格收敛
    conv = {}
    for case in MC.CASE_KEYS:
        vals = {}
        for N, a in ((150, 1.056), (300, 1.028), (600, 1.014)):
            s = solve(case, ts=60.0, N=N, a=a)
            vals[str(N)] = float(s['rec']['Rp'][59])
        base = vals['600']
        conv[case] = dict(vals=vals,
                          rel_300=float(abs(vals['300'] - base) / base),
                          rel_150=float(abs(vals['150'] - base) / base))
    OUT['grid_convergence'] = conv

    # ---- 参数敏感性：ν 对 γ_k 与 β_d 的依赖（给 P2 的"哪个群控制标度"）
    sens = {}
    for case in MC.CASE_KEYS:
        row = {}
        for gs in (0.0, 0.5, 1.0, 2.0):
            s = solve(case, ts=60.0, gamma_scale=gs, N=200, a=1.042)
            row[f'gamma_x{gs}'] = fit_nu(s['t'], s['rec']['Rp'], 5, 20)
        for bs in (0.0, 1.0, 2.0):
            s = solve(case, ts=60.0, bd_scale=bs, N=200, a=1.042)
            row[f'bd_x{bs}'] = dict(fit_nu(s['t'], s['rec']['Rp'], 5, 20),
                                    dm_max=float(s['store']['dm_max']))
        for Ad in (0.0, 20.0, 200.0):
            s = solve(case, ts=60.0, Ad=Ad, N=200, a=1.042)
            row[f'Ad_{Ad}'] = dict(fit_nu(s['t'], s['rec']['Rp'], 5, 20),
                                   Rp60=float(s['rec']['Rp'][59]))
        sens[case] = row
    OUT['nu_sensitivity'] = sens

    # ---- 与附件 C 的交叉验证
    import json
    p3 = os.path.join(MC.DATA, 'p3_decline.json')
    OUT['cross_check'] = {}
    if os.path.exists(p3):
        with open(p3, encoding='utf-8') as f:
            D3 = json.load(f)
        ts_levels = np.array([5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60], dtype=float)
        for case in MC.CASE_KEYS:
            m5 = D3['M5_params'][case]
            A = m5['Ainf'] * (1 - np.exp(-np.power(ts_levels / m5['tau'], m5['p'])))
            Rn = np.array(OUT['radii'][case]['Rp'])[ts_levels.astype(int) - 1]
            An = A / A[0]
            Rn_ = Rn / Rn[0]
            OUT['cross_check'][case] = dict(
                ts=[int(v) for v in ts_levels],
                A=[float(v) for v in A], A_norm=[float(v) for v in An],
                Rp=[float(v) for v in Rn], Rp_norm=[float(v) for v in Rn_],
                corr=float(MC.corr(np.log(An), np.log(Rn_))),
                max_abs_dev_norm=float(np.max(np.abs(An - Rn_))),
                nu_data_5_20=float(np.log(A[3] / A[0]) / np.log(20 / 5)),
                nu_model_5_20=float(np.log(Rn[3] / Rn[0]) / np.log(20 / 5)),
                nu_data_5_60=float(np.log(A[-1] / A[0]) / np.log(60 / 5)),
                nu_model_5_60=float(np.log(Rn[-1] / Rn[0]) / np.log(60 / 5)),
                tau_data=m5['tau'],
                tau_sat_A=OUT['scaling'][case]['tau_sat_A_block'],
                tau_sat_B=OUT['scaling'][case]['tau_sat_B_frac'],
                hyp_A_ok=bool(abs(OUT['scaling'][case]['tau_sat_A_block'] - m5['tau'])
                              / m5['tau'] < 0.5),
                hyp_B_ok=bool(abs(OUT['scaling'][case]['tau_sat_B_frac'] - m5['tau'])
                              / m5['tau'] < 0.5),
            )
        OUT['cross_check']['_ordering'] = dict(
            tau_data=[D3['M5_params'][c]['tau'] for c in MC.CASE_KEYS],
            tau_sat_A=[OUT['scaling'][c]['tau_sat_A_block'] for c in MC.CASE_KEYS],
            tau_sat_B=[OUT['scaling'][c]['tau_sat_B_frac'] for c in MC.CASE_KEYS],
        )
    else:
        OUT['cross_check'] = dict(error='data/p3_decline.json 不存在，先跑 p3_decline.py')

    MC.save_json('p1_mechanistic', OUT, os.path.abspath(__file__), MC.input_hashes())
    for c in MC.CASE_KEYS:
        print(c, 'Rp60=%.2f m' % OUT['scaling'][c]['R_numeric_60d'],
              'nu(5-20)=%.3f' % OUT['scaling'][c]['early']['nu'],
              'nu(5-60)=%.3f' % OUT['scaling'][c]['all']['nu'],
              'tauA=%.2f tauB=%.2f' % (OUT['scaling'][c]['tau_sat_A_block'],
                                       OUT['scaling'][c]['tau_sat_B_frac']))
        print('  mass rel imbalance %.2e' % OUT['solver_check'][c]['rel_imbalance'],
              'grid rel300 %.2e' % OUT['grid_convergence'][c]['rel_300'])
        if c in OUT['cross_check']:
            cc = OUT['cross_check'][c]
            print('  cross: corr=%.4f dev=%.3f nu_data(5-20)=%.3f nu_model=%.3f'
                  % (cc['corr'], cc['max_abs_dev_norm'], cc['nu_data_5_20'],
                     cc['nu_model_5_20']),
                  'tau=%.2f hypA=%s hypB=%s' % (cc['tau_data'], cc['hyp_A_ok'],
                                                cc['hyp_B_ok']))
    print('OK p1')


if __name__ == '__main__':
    main()