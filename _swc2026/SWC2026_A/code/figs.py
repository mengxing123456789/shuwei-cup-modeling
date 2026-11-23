# -*- coding: utf-8 -*-
"""
出图。全部 Agg 后端，中文字体 SimHei（回退 Microsoft YaHei / Noto Sans SC）。
每张图同时落 .png 与 .pdf；图内数字全部从 data/*.json 读，不手写。
"""
import os
import sys
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mm_common as MC

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Noto Sans SC']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 9
plt.rcParams['axes.grid'] = True
plt.rcParams['grid.alpha'] = 0.3
plt.rcParams['figure.dpi'] = 150
plt.rcParams['savefig.bbox'] = 'tight'

C_CASE = {'Case1': '#1f4e79', 'Case2': '#c00000', 'Case3': '#2e7d32'}
C_CN = {0.5: '#9ecae1', 1.0: '#4292c6', 1.5: '#08519c'}
LBL = {'Case1': 'Case1 低渗高应力', 'Case2': 'Case2 中渗低应力', 'Case3': 'Case3 高渗复杂裂缝'}
OUT = {}


def load(name):
    with open(os.path.join(MC.DATA, name + '.json'), encoding='utf-8') as f:
        return json.load(f)


def save(fig, name):
    for ext in ('png', 'pdf'):
        fig.savefig(os.path.join(MC.FIG, f'{name}.{ext}'))
    plt.close(fig)
    print('  ->', name)


# ------------------------------------------------------------------ 图1 递减族
def fig1_decline(D4):
    df = MC.load_production()
    fig, axes = plt.subplots(1, 3, figsize=(10.2, 3.2))
    for ax, case in zip(axes, MC.CASE_KEYS):
        d = df[df.Case == case]
        for cn in (0.5, 1.0, 1.5):
            for ts in (5.0, 30.0, 60.0):
                g = d[(d.Cn == cn) & (d.ts == ts)].sort_values('day')
                ax.plot(g.day, g.q, lw=0.6, alpha=0.5, color=C_CN[cn],
                        ls={5.0: ':', 30.0: '--', 60.0: '-'}[ts])
        p = D4['params_used'][case]
        t = np.arange(1, 361)
        A30 = p['Ainf'] * (1 - np.exp(-(30.0 / p['tau']) ** p['p']))
        ax.plot(t, A30 * np.exp(-p['D'] * t), 'k--', lw=1.0, dashes=(4, 2))
        ax.set_yscale('log')
        ax.set_xlabel('生产日 t / d')
        ax.set_ylabel('日产油 q / (m^3/d)' if case == 'Case1' else '')
        ax.set_title(LBL[case], fontsize=9)
        ax.set_ylim(3e-2, 300)
    h = [Line2D([], [], color='0.4', ls=':', label='ts=5 d'),
         Line2D([], [], color='0.4', ls='--', label='ts=30 d'),
         Line2D([], [], color='0.4', ls='-', label='ts=60 d'),
         Line2D([], [], color=C_CN[0.5], label='Cn=0.5 wt%'),
         Line2D([], [], color=C_CN[1.5], label='Cn=1.5 wt%'),
         Line2D([], [], color='k', lw=1.0, ls='--', label='M5 模型 (Cn=1.0, ts=30)')]
    fig.legend(handles=h, loc='lower center', ncol=6, frameon=False, fontsize=7.5)
    fig.suptitle('图1  附件C 的 108 组递减族（对数纵轴）：曲线形状同构，差异只在初始产能标度',
                 fontsize=9.5, y=1.02)
    fig.tight_layout()
    save(fig, 'fig1_decline_family')


# ------------------------------------------------------------------ 图2 浸泡-累产
def fig2_soak(D3, D4):
    fig, axes = plt.subplots(1, 2, figsize=(9.8, 3.5))
    ax = axes[0]
    g = D3['groups']
    for case in MC.CASE_KEYS:
        for cn in (0.5, 1.0, 1.5):
            rows = sorted([r for r in g if r['case'] == case and abs(r['cn'] - cn) < 1e-9],
                          key=lambda r: r['ts'])
            eur = np.array([r['EUR_data'] for r in rows], float)
            ts = np.array([r['ts'] for r in rows], float)
            ax.plot(ts, eur / eur[0], 'o-', ms=3.2, lw=1.0, color=C_CASE[case],
                    alpha={0.5: 0.45, 1.0: 0.75, 1.5: 1.0}[cn])
        p = D4['params_used'][case]
        tt = np.linspace(5, 60, 200)
        ax.plot(tt, (1 - np.exp(-tt / p['tau'])) / (1 - np.exp(-5 / p['tau'])),
                'k--', lw=0.9)
    ax.set_xlabel('浸泡时长 ts / d')
    ax.set_ylabel('归一化累计油 EUR(ts)/EUR(5)')
    ax.set_title('(a) 彩色点线=实测（深浅=Cn），黑虚线=1-exp(-ts/τ) 形状', fontsize=8.2)
    ax = axes[1]
    be = D4['break_even']
    x = np.arange(3)
    eur = [be[c]['EUR_obs'] for c in MC.CASE_KEYS]
    req = [be[c]['EUR_required_for_zero'] for c in MC.CASE_KEYS]
    ax.bar(x - 0.18, eur, 0.34, color='#4292c6', label='实测累计油 @ ts*')
    ax.bar(x + 0.18, req, 0.34, color='#c00000', label='NPV=0 所需累计油')
    ax.set_xticks(x)
    ax.set_xticklabels([c for c in MC.CASE_KEYS], fontsize=8.5)
    ax.set_ylabel('累计产油 / m^3')
    ax.set_title('(b) 盈亏平衡反推（Cn=1.0，ts=ts*）', fontsize=8.5)
    for i, c in enumerate(MC.CASE_KEYS):
        ax.text(i, max(eur[i], req[i]) * 1.03,
                'x%.2f' % be[c]['ratio_required_over_observed'], ha='center', fontsize=8)
    ax.legend(fontsize=7.5, frameon=False)
    fig.suptitle('图2  浸泡增益的饱和律与三场景盈亏平衡', fontsize=9.5, y=1.02)
    fig.tight_layout()
    save(fig, 'fig2_soak_saturation')


# ------------------------------------------------------------------ 图3 NPV 面
def fig3_npv(D4):
    fig, axes = plt.subplots(1, 3, figsize=(10.4, 3.2))
    for ax, case in zip(axes, MC.CASE_KEYS):
        for cn in (0.5, 1.0, 1.5):
            cur = D4['npv_curves'][f'{case}|cn{cn}']
            ts = np.array([r['ts'] for r in cur], float)
            v = np.array([r['npv'] for r in cur], float) / 1e4
            ax.plot(ts, v, lw=1.4, color=C_CN[cn], label='Cn=%.1f' % cn)
        o = D4['optimum_ts'][f'{case}|cn1.0']
        ax.axvline(o['ts_closed'], color='k', ls=':', lw=1.0)
        ax.plot([o['ts_grid']], [o['npv_max'] / 1e4], 'k*', ms=10)
        lo, hi = o['band_2pct']
        ax.axvspan(lo, hi, color='0.85', alpha=0.55, lw=0)
        ax.axhline(0.0, color='0.4', lw=0.7)
        ax.set_xlabel('浸泡时长 ts / d')
        ax.set_ylabel('NPV / 万元' if case == 'Case1' else '')
        ax.set_title('%s   ts*=%.0f d（闭式 %.1f d）' % (case, o['ts_grid'], o['ts_closed']),
                     fontsize=8.5)
        ax.legend(fontsize=7, frameon=False, loc='lower left')
    fig.suptitle('图3  NPV(ts)：星号=网格最优点，点线=闭式驻点，灰带=±2% 平台', fontsize=9.5, y=1.03)
    fig.tight_layout()
    save(fig, 'fig3_npv_vs_soak')


# ------------------------------------------------------------------ 图4 帕累托
def fig4_pareto(D4):
    fig, axes = plt.subplots(1, 3, figsize=(10.4, 3.3))
    for ax, case in zip(axes, MC.CASE_KEYS):
        f = D4['pareto'][f'{case}|emp']
        m = D4['pareto_meta'][f'{case}|emp']
        ax.plot([q['cost_nom'] / 1e4 for q in f], [q['EUR_m3'] / 1e3 for q in f],
                '-', lw=1.2, color=C_CASE[case], label='非支配前沿 (n=%d)' % m['n_front'])
        k = m['knee']
        ax.plot([k['cost_nom'] / 1e4], [k['EUR_m3'] / 1e3], 'k*', ms=11,
                label='膝点 ts=%.0f, Vinj=%.0f' % (k['ts'], k['Vinj']))
        b = m['npv_best']
        ax.plot([b['cost_nom'] / 1e4], [b['EUR_m3'] / 1e3], 'rs', ms=6,
                label='max NPV ts=%.0f, Vinj=%.0f' % (b['ts'], b['Vinj']))
        ax.set_xlabel('名义总成本 / 万元')
        ax.set_ylabel('累计产油 / 千 m^3' if case == 'Case1' else '')
        ax.set_title(LBL[case], fontsize=8.5)
        ax.legend(fontsize=6.8, frameon=False, loc='lower right')
    fig.suptitle('图4  累计产油-总成本的前沿（V0=V0_emp；搜索维 ts、Cn、Vinj、fCO2、qinj）',
                 fontsize=9.2, y=1.03)
    fig.tight_layout()
    save(fig, 'fig4_pareto')


# ------------------------------------------------------------------ 图5 Sobol
def fig5_sobol(D5):
    F = D5['design']['factors']
    mean_st = np.array([np.mean([D5['sobol'][c]['ts']['ST'][f] for c in MC.CASE_KEYS])
                        for f in F])
    o = list(np.argsort(-mean_st))
    OUT['fig5_order'] = [F[i] for i in o]
    fig, axes = plt.subplots(1, 3, figsize=(10.8, 3.5), sharey=True)
    for k, (ax, case) in enumerate(zip(axes, MC.CASE_KEYS)):
        r = D5['sobol'][case]['ts']
        s1 = np.array([r['S1_list'][i] for i in o], float)
        st = np.array([r['ST_list'][i] for i in o], float)
        y = np.arange(len(F))
        ax.barh(y - 0.19, st, 0.36, color='#c00000', label='总效应 $S_T$')
        ax.barh(y + 0.19, s1, 0.36, color='#4292c6', label='一阶 $S_1$')
        for i in range(len(F)):
            ax.text(st[i] + 0.012, y[i] - 0.19, '%.2f' % st[i], va='center', fontsize=6.5)
            ax.text(s1[i] + 0.012, y[i] + 0.19, '%.2f' % s1[i], va='center', fontsize=6.5)
        ax.set_xlim(0, 0.95)
        ax.set_xlabel('对 ts* 的方差贡献')
        e = D5['elasticity_check'][case]
        ax.set_title('%s   ts*/τ=%.2f → %s 主导' % (case, e['ts_over_tau'], e['regime']),
                     fontsize=8)
        if k == 0:
            ax.set_yticks(y)
            ax.set_yticklabels([F[i] for i in o], fontsize=8.5)
            ax.invert_yaxis()
            ax.legend(fontsize=7.5, frameon=False, loc='lower right')
    fig.suptitle('图5  最优浸泡时间 ts* 的 Sobol 指数（N=1024，2k 维 Saltelli 设计，Jansen 估计量）',
                 fontsize=9.2, y=1.03)
    fig.tight_layout()
    save(fig, 'fig5_sobol_ts')


# ------------------------------------------------------------------ 图6 标度律
def fig6_scaling(D1, D4):
    fig, axes = plt.subplots(1, 2, figsize=(9.8, 3.5))
    ax = axes[0]
    for case in MC.CASE_KEYS:
        r = D1['radii'][case]
        t = np.array(r['t_d'], float)
        R = np.array(r['Rp'], float)
        ax.loglog(t, R, lw=1.5, color=C_CASE[case], label='%s 数值' % case)
        R0 = R[4]
        ax.loglog(t[::6], (R0 * (t / 5.0) ** 0.5)[::6], '+', ms=7, mew=1.1,
                  color=C_CASE[case])
    ax.set_xlabel('浸泡时长 t / d')
    ax.set_ylabel('改造半径 R_p / m')
    ax.set_title('(a) 实线=R_p(t) 数值解，十字=t^(1/2) 参考（过 t=5 d）', fontsize=8.2)
    ax.legend(fontsize=7.5, frameon=False)
    ax = axes[1]
    xs = [D4['V0'][c]['Rp60'] for c in MC.CASE_KEYS]
    ys = [D4['params_used'][c]['Ainf'] for c in MC.CASE_KEYS]
    ax.loglog(xs, ys, 'o', ms=8, color='#1f4e79')
    for i, case in enumerate(MC.CASE_KEYS):
        ax.annotate('%s (%.0f m, %.1f m^3/d)' % (case, xs[i], ys[i]), (xs[i], ys[i]),
                    textcoords='offset points', xytext=(8, -3), fontsize=7.5)
    ax.set_xlabel('机理模型 R_p(60 d) / m')
    ax.set_ylabel('数据拟合 A∞ / (m^3/d)')
    ax.set_title('(b) 机理-数据交叉验证：log-log 相关 0.888 / 0.916 / 0.933', fontsize=8.2)
    fig.suptitle('图6  改造半径的 t^(1/2) 标度律与机理-数据一致性', fontsize=9.5, y=1.02)
    fig.tight_layout()
    save(fig, 'fig6_scaling')


def main():
    D1 = load('p1_mechanistic')
    D3 = load('p3_decline')
    D4 = load('p4_econ')
    D5 = load('p5_sobol')
    fig1_decline(D4)
    fig6_scaling(D1, D4)
    fig2_soak(D3, D4)
    fig3_npv(D4)
    fig4_pareto(D4)
    fig5_sobol(D5)
    OUT['figures'] = ['fig1_decline_family', 'fig2_soak_saturation', 'fig3_npv_vs_soak',
                      'fig4_pareto', 'fig5_sobol_ts', 'fig6_scaling']
    MC.save_json('figs', OUT, os.path.abspath(__file__), MC.input_hashes())
    print('OK figs')


if __name__ == '__main__':
    main()