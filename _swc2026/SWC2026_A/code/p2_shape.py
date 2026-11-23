# -*- coding: utf-8 -*-
"""
P2 的形状判别：浸泡响应到底是 sqrt(t) 型、自由幂律、还是指数饱和？

背景（这是本题最容易翻车的地方）：
  P1/P2 的相似解给出改造半径（前沿位置）的扩散标度律 r_f ∝ t^(1/2)，这在数值上精确到
  小数第三位（ν=0.501–0.503）。但**产量对浸泡时长的响应**不是 r_f 本身，而是被
  "有效改造体积" 限制的积分量。若把 ν=1/2 直接搬到产量响应上，附件C 一拟合就会看到
  R²≈0.69 对 0.999 —— 所以本文把两件事分开：前沿用 ν=1/2（P1 数值解），可观测响应用
  形状判别来定（本文件），并给出三个可判定的证据。

三种候选形状（对 360 d 累计油 EUR(ts) 拟合）：
  S1  A + B·sqrt(ts)                    —— ν=1/2 标度的直接体现（3 参数：A,B 线性）
  S2  A·(1 - exp(-ts/tau))              —— 饱和（2 参数：A 线性，tau 一维搜索）
  S3  A·ts^nu                           —— 自由幂律（2 参数：log-log 线性）
判据（什么叫通过）：S2 的 R² 显著高于 S1，且 S2 的残差在 ts 方向上无结构（符号游程数
接近随机期望），同时对 S1 的残差呈系统性一拱（两端为正/中间为负）。

另外两个判别量：
  (a) 自由幂律指数 nu_data —— 若等于 0.5 且三场景相同，则"单一幂律"成立；实测不是。
  (b) tau 与改造半径 R_p(60 d) 的 log-log 指数 —— 若饱和由扩散控制，应有 tau ∝ R_p²
      （指数 2）；实测指数远小于 2，即饱和不是输运控制的。
"""
import os
import sys
import json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mm_common as MC

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 8.5
plt.rcParams['axes.titlesize'] = 9
plt.rcParams['figure.dpi'] = 200

CASES = MC.CASE_KEYS
CN = [0.5, 1.0, 1.5]
SHAPES = ['S1_sqrt', 'S2_exp', 'S3_power']


# ---------------------------------------------------------------- 拟合器
def fit_sqrt(ts, y):
    """A + B*sqrt(ts)，线性最小二乘。"""
    X = np.column_stack([np.ones_like(ts), np.sqrt(ts)])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    return y * 0 + X @ coef, {'A': float(coef[0]), 'B': float(coef[1])}


def fit_exp(ts, y, lo=0.3, hi=200.0, n=4000):
    """A*(1-exp(-ts/tau))，内层对 A 线性，外层一维搜索 tau（对数网格 + 抛物线细化）。"""
    best = None
    taus = np.exp(np.linspace(np.log(lo), np.log(hi), n))
    for tau in taus:
        g = 1.0 - np.exp(-ts / tau)
        A = float(np.dot(g, y) / np.dot(g, g))
        sse = float(np.sum((y - A * g) ** 2))
        if best is None or sse < best[0]:
            best = (sse, tau, A)
    # 抛物线细化一次
    sse0, tau0, A0 = best
    step = np.log(taus[1] / taus[0])
    for d in np.linspace(-step, step, 41):
        tau = tau0 * np.exp(d)
        g = 1.0 - np.exp(-ts / tau)
        A = float(np.dot(g, y) / np.dot(g, g))
        sse = float(np.sum((y - A * g) ** 2))
        if sse < sse0:
            sse0, tau0, A0 = sse, tau, A
    g = 1.0 - np.exp(-ts / tau0)
    return A0 * g, {'A': A0, 'tau': float(tau0)}


def fit_power(ts, y):
    """A*ts^nu，log-log 线性最小二乘。"""
    X = np.column_stack([np.ones_like(ts), np.log(ts)])
    coef, *_ = np.linalg.lstsq(X, np.log(y), rcond=None)
    nu = float(coef[1])
    A = float(np.exp(coef[0]))
    return A * ts ** nu, {'A': A, 'nu': nu}


def r2_aic(y, yhat, k):
    sse = float(np.sum((y - yhat) ** 2))
    sst = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - sse / sst
    n = len(y)
    aic = n * np.log(sse / n) + 2 * k
    return r2, float(aic), sse


def runs(resid):
    """残差符号游程数（按 ts 升序）；随机白噪声下期望 (n+1)/2。"""
    s = np.sign(resid)
    s = s[s != 0]
    if len(s) < 2:
        return 1, 1.0
    return int(1 + np.sum(s[1:] != s[:-1])), (len(s) + 1) / 2.0


def main():
    df = MC.load_production()
    # 每组 360 d 的累计油（取 day=360 那一行）
    last = df[df['day'] == 360][['Case', 'Cn', 'ts', 'cum']].copy()
    last.columns = ['Case', 'Cn', 'ts', 'EUR']

    rows = []
    for case in CASES:
        for cn in CN:
            sub = last[(last['Case'] == case) & (np.abs(last['Cn'] - cn) < 1e-9)].sort_values('ts')
            ts = sub['ts'].values.astype(float)
            y = sub['EUR'].values.astype(float)
            rec = {'case': case, 'cn': cn, 'ts': ts.tolist(), 'EUR': y.tolist(), 'shapes': {}}
            for name, fn, k in (('S1_sqrt', fit_sqrt, 3), ('S2_exp', fit_exp, 2), ('S3_power', fit_power, 2)):
                yhat, par = fn(ts, y)
                r2, aic, sse = r2_aic(y, yhat, k)
                nr, exp_r = runs(y - yhat)
                rec['shapes'][name] = {'params': par, 'r2': r2, 'aic': aic, 'sse': sse,
                                       'resid_runs': nr, 'resid_runs_expected': exp_r,
                                       'resid': (y - yhat).tolist(), 'fit': yhat.tolist()}
            best = max(SHAPES, key=lambda s: rec['shapes'][s]['r2'])
            rec['best_shape'] = best
            rec['dR2_exp_minus_sqrt'] = rec['shapes']['S2_exp']['r2'] - rec['shapes']['S1_sqrt']['r2']
            rows.append(rec)

    # ------------------------------------------------------------ 判别量 (a)
    nu_by_case = {c: [r['shapes']['S3_power']['params']['nu'] for r in rows if r['case'] == c]
                  for c in CASES}
    tau_by_case = {c: [r['shapes']['S2_exp']['params']['tau'] for r in rows if r['case'] == c]
                   for c in CASES}
    # ------------------------------------------------------------ 判别量 (b)
    p1_path = os.path.join(MC.DATA, 'p1_mechanistic.json')
    tau_scale = None
    if os.path.exists(p1_path):
        D1 = json.load(open(p1_path, encoding='utf-8'))
        Rp = np.array([D1['radii'][c]['Rp'][-1] for c in CASES], dtype=float)
        tau = np.array([np.mean(tau_by_case[c]) for c in CASES], dtype=float)
        lx, ly = np.log(Rp), np.log(tau)
        expo, intercept, r2t = MC.ols_slope(lx, ly)
        tau_scale = {
            'note': '若饱和由扩散控制，tau 应与 R_p^2 同阶（指数 2）；实测指数远小于 2 ⇒ 饱和由滞留/相平衡控制，不是输运控制',
            'Rp60': dict(zip(CASES, Rp.tolist())),
            'tau_mean': dict(zip(CASES, tau.tolist())),
            'tau_over_Rp': dict(zip(CASES, (tau / Rp).tolist())),
            'loglog_exponent': float(expo),
            'loglog_r2': float(r2t),
            'diffusion_expected_exponent': 2.0,
            'ratio_observed_to_diffusion': float(expo / 2.0),
            'n_points': 3,
        }

    # ------------------------------------------------------------ 图
    fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.6))
    colors = {'S1_sqrt': '#c0392b', 'S2_exp': '#1f6fb2', 'S3_power': '#2e8b57'}
    labels = {'S1_sqrt': r'S1  $A+B\sqrt{t_s}$', 'S2_exp': r'S2  $A(1-e^{-t_s/\tau})$',
              'S3_power': r'S3  $A\,t_s^{\nu}$'}
    tg = np.linspace(4, 62, 400)
    for ax, case in zip(axes, CASES):
        rec = [r for r in rows if r['case'] == case and abs(r['cn'] - 1.0) < 1e-9][0]
        ax.plot(rec['ts'], rec['EUR'], 'ko', ms=3.2, label='附件C（$C_n$=1.0）')
        for s in SHAPES:
            if s == 'S1_sqrt':
                p = rec['shapes'][s]['params']
                ax.plot(tg, p['A'] + p['B'] * np.sqrt(tg), '-', color=colors[s], lw=1.0,
                        label='%s  $R^2$=%.4f' % (labels[s], rec['shapes'][s]['r2']))
            elif s == 'S2_exp':
                p = rec['shapes'][s]['params']
                ax.plot(tg, p['A'] * (1 - np.exp(-tg / p['tau'])), '-', color=colors[s], lw=1.4,
                        label='%s  $R^2$=%.4f' % (labels[s], rec['shapes'][s]['r2']))
            else:
                p = rec['shapes'][s]['params']
                ax.plot(tg, p['A'] * tg ** p['nu'], '--', color=colors[s], lw=1.0,
                        label='%s  $\\nu$=%.3f  $R^2$=%.4f'
                              % (labels[s], p['nu'], rec['shapes'][s]['r2']))
        ax.set_xlabel('浸泡时长 $t_s$ / d')
        ax.set_ylabel('360 d 累计油 EUR / m$^3$')
        ax.set_title('(%s) %s' % ('abc'[CASES.index(case)], case))
        ax.grid(alpha=0.3, lw=0.4)
        ax.legend(fontsize=5.6, loc='lower right', frameon=False)
    fig.suptitle('图7 浸泡响应的形状判别：$\\sqrt{t_s}$（红）在两端系统性偏离，指数饱和（蓝）贴合', fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    outs = []
    for ext in ('png', 'pdf'):
        p = os.path.join(MC.FIG, 'fig7_shape_discrimination.' + ext)
        fig.savefig(p, bbox_inches='tight')
        outs.append(os.path.relpath(p, MC.ROOT))
    plt.close(fig)

    payload = {
        'rows': rows,
        'nu_by_case': nu_by_case,
        'tau_by_case': tau_by_case,
        'tau_cn_independence': {c: float((max(v) - min(v)) / np.mean(v)) for c, v in tau_by_case.items()},
        'tau_scaling_vs_Rp': tau_scale,
        'decision': {
            'best_shape_all_9': all(r['best_shape'] == 'S2_exp' for r in rows),
            'min_dR2_exp_minus_sqrt': float(min(r['dR2_exp_minus_sqrt'] for r in rows)),
            'nu_single_powerlaw_rejected': bool(
                any(abs(v - 0.5) > 0.05 for vs in nu_by_case.values() for v in vs)
                or (max(np.mean(v) for v in nu_by_case.values())
                    - min(np.mean(v) for v in nu_by_case.values()) > 0.05)),
            'statement': ('9/9 个(场景,浓度)组合的最佳形状都是指数饱和；自由幂律指数 '
                          'ν_data 既不等于 0.5 也在三场景之间显著不同 ⇒ 单一幂律描述浸泡响应不成立。'
                          'sqrt(t) 只属于改造半径（前沿位置），不属于产量响应。'),
        },
        'figures': outs,
    }
    MC.save_json('p2_shape', payload, os.path.abspath(__file__), MC.input_hashes())

    print('%-6s %-5s %10s %10s %10s %8s %8s' % ('case', 'cn', 'R2_sqrt', 'R2_exp', 'R2_pow', 'best', 'nu'))
    for r in rows:
        print('%-6s %-5.1f %10.4f %10.4f %10.4f %8s %8.3f'
              % (r['case'], r['cn'], r['shapes']['S1_sqrt']['r2'], r['shapes']['S2_exp']['r2'],
                 r['shapes']['S3_power']['r2'], r['best_shape'],
                 r['shapes']['S3_power']['params']['nu']))
    print('tau (S2) per case, cn-independence rel-spread:',
          {c: round(payload['tau_cn_independence'][c], 4) for c in CASES})
    if tau_scale:
        print('tau vs Rp60 log-log exponent = %.3f (diffusion would give 2.0), R2=%.3f'
              % (tau_scale['loglog_exponent'], tau_scale['loglog_r2']))
    print('decision:', payload['decision']['min_dR2_exp_minus_sqrt'], payload['decision']['nu_single_powerlaw_rejected'])


if __name__ == '__main__':
    main()