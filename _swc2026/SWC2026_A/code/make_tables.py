# -*- coding: utf-8 -*-
"""
从 data/*.json 生成 out/03-numbers.md —— 正文里的每个数字都必须能在这里找到键。
本脚本不产生任何新数字，只做格式化（所以这里出现的数值都是 JSON 里的引用）。
"""
import os
import sys
import json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mm_common as MC

CASES = MC.CASE_KEYS
CN = ['0.5', '1.0', '1.5']
L = []


def w(s=''):
    L.append(s)


def row(metric, value, unit, key, fmt='%.4g'):
    if isinstance(value, (int, np.integer)):
        v = '%d' % value
    elif isinstance(value, float):
        v = fmt % value
    else:
        v = str(value)
    w('| %s | %s | %s | `%s` |' % (metric, v, unit, key))


def head(title, intro=None):
    w()
    w('## ' + title)
    w()
    if intro:
        w(intro)
        w()
    w('| 量 | 值 | 单位 | 来源 JSON 键 |')
    w('|---|---|---|---|')


def main():
    D1 = json.load(open(os.path.join(MC.DATA, 'p1_mechanistic.json'), encoding='utf-8'))
    D2 = json.load(open(os.path.join(MC.DATA, 'p2_shape.json'), encoding='utf-8'))
    D3 = json.load(open(os.path.join(MC.DATA, 'p3_decline.json'), encoding='utf-8'))
    D4 = json.load(open(os.path.join(MC.DATA, 'p4_econ.json'), encoding='utf-8'))
    D5 = json.load(open(os.path.join(MC.DATA, 'p5_sobol.json'), encoding='utf-8'))
    DE = json.load(open(os.path.join(MC.DATA, 'verify_env.json'), encoding='utf-8'))

    w('# 03 数字表（唯一来源：data/*.json）')
    w()
    w('本文件的每一行都对应 `data/<script>.json` 里的一个键；正文里出现的任何数字都必须能在此检索到。')
    w('格式约定：量 | 值 | 单位 | JSON 键。键的写法是 `文件:路径.到.字段`，`{case}` 表示三个场景各一行。')
    w()
    w('### 口径声明（先说清，再报数）')
    w()
    w('1. **时间轴**：day 0 = 压裂当天；注入 tinj = Vinj/qinj 天（基准 3000/300 = 10 d）；浸泡 ts 天；生产 360 d。')
    w('2. **折现**：日末折现 (1+r)^(-d/365)，r = 8%/yr，365 d/yr，基准 day 0。')
    w('3. **成本**：压裂 120 万元 day0 一次付；注入期逐日 30 万元/d；浸泡期逐日 3 万元/d；')
    w('   CO2 与纳米材料按 B.2 计算并在 day0 一次付。题面 B.4 检验向量算出小计 848.25 万元，脚本内断言通过。')
    w('4. **产水**：附件C 无产水数据，基线 WOR = 0（待假设），另做 WOR = 0.5 敏感性。')
    w('5. **浸泡时长两套口径**：`ts_data_grid` = 在附件C 的 5,10,…,60 档位上取 NPV 最大；')
    w('   `ts_continuous` = 对 M5 拟合曲线解 dNPV/dts = 0 的驻点。工程决策用前者，后者用来说明曲线形状。')
    w('6. **注入量不可识别**：附件C 不含 Vinj，`S_V = 1-exp(-Vinj/V0)` 依赖 V0 的口径；两种 V0 下推荐的 Vinj 会翻边，')
    w('   故本文只报 ts 与 Cn 的最优，不报 Vinj 的最优值（见 `p4_econ:V0` 与 `pareto_meta`）。')
    w('7. **NPV 的绝对符号**由题面固定成本（压裂 120 万 + 材料 + 注入）与附件C 的井尺度产量共同决定；')
    w('   本文不做井段数缩放，Case1/Case2 的结构性亏损是结论，不是计算错误。')
    w('8. 键里的 `{i}` 表示"该行对应 9 个（场景×浓度）组合里的第 i 个"，顺序为 Case1/Case2/Case3 各 Cn=0.5→1.0→1.5。')

    # ---------------------------------------------------------------- 数据
    head('0  数据概况', '附件C 的规模与结构；组数 = 场景 × 浓度 × 浸泡档。')
    row('总行数', D3['data_facts']['n_rows'], '行', 'p3_decline:data_facts.n_rows', '%d')
    row('场景数', D3['data_facts']['n_cases'], '个', 'p3_decline:data_facts.n_cases', '%d')
    row('浓度档', ' / '.join('%.1f' % v for v in D3['data_facts']['cn_levels']), 'wt%',
        'p3_decline:data_facts.cn_levels')
    row('浸泡档', ' / '.join('%d' % v for v in D3['data_facts']['ts_levels']), 'd',
        'p3_decline:data_facts.ts_levels')
    row('生产日范围', ' / '.join('%d' % v for v in D3['data_facts']['days']), 'd',
        'p3_decline:data_facts.days')
    row('(场景,浓度,浸泡) 组数', D3['n_groups'], '组', 'p3_decline:n_groups', '%d')

    # ---------------------------------------------------------------- P1
    head('1  P1：控制方程的无量纲群（三个场景各一组）',
         '10 个无量纲群的数值；表达式与物理意义见 `out/01-model.md` 表 1-2。')
    keys = [k for k in D1['dimensionless']['Case1'].keys() if not k.startswith('_')]
    for k in keys:
        vals = [D1['dimensionless'][c][k]['v'] for c in CASES]
        row('%s = %s' % (k, D1['dimensionless']['Case1'][k]['expr']),
            ' / '.join('%.3g' % v for v in vals), '—',
            'p1_mechanistic:dimensionless.{case}.%s.v' % k)

    head('1b  P1/P2：改造半径与标度律',
         '数值解 R_p 由压力扰动 5% 判据给出；ν 由 R_p = C·t^ν 的 log-log 斜率（全窗口 5–60 d，n=56）估计。')
    for c in CASES:
        r = D1['radii'][c]
        for t in (5, 20, 60):
            row('%s  R_p(%d d)' % (c, t), r['Rp'][t - 1], 'm',
                'p1_mechanistic:radii.%s.Rp[%d]' % (c, t - 1))
    for c in CASES:
        row('%s  ν（5–60 d，n=56）' % c, D1['scaling'][c]['all']['nu'], '—',
            'p1_mechanistic:scaling.%s.all.nu' % c)
        row('%s  ν 的 R²' % c, D1['scaling'][c]['all']['r2'], '—',
            'p1_mechanistic:scaling.%s.all.r2' % c, '%.6f')
        row('%s  C（R_p = C·t^ν 的系数）' % c, D1['scaling'][c]['all']['C'], 'm·d^-ν',
            'p1_mechanistic:scaling.%s.all.C' % c)
        row('%s  R_p(60 d) 解析/数值比' % c, D1['scaling'][c]['ratio_num_ana'], '—',
            'p1_mechanistic:scaling.%s.ratio_num_ana' % c)
    for c in CASES:
        row('%s  质量相对不平衡' % c, D1['solver_check'][c]['rel_imbalance'], '—',
            'p1_mechanistic:solver_check.%s.rel_imbalance' % c)
        row('%s  网格加密相对差（N=300 vs 600）' % c, D1['grid_convergence'][c]['rel_300'], '—',
            'p1_mechanistic:grid_convergence.%s.rel_300' % c)

    head('1c  P2：饱和时间尺度 τ 的两个机制假设 vs 数据反演',
         'τ_sat 由"扩散到达特征长度"的两种几何给出；数据 τ 由 M5 拟合。')
    for c in CASES:
        row('%s  τ_sat（假设A：基质块半宽 h/2）' % c, D1['scaling'][c]['tau_sat_A_block'], 'd',
            'p1_mechanistic:scaling.%s.tau_sat_A_block' % c)
        row('%s  τ_sat（假设B：缝半长 Lf/2）' % c, D1['scaling'][c]['tau_sat_B_frac'], 'd',
            'p1_mechanistic:scaling.%s.tau_sat_B_frac' % c)
        row('%s  τ（M5 拟合）' % c, D3['M5_params'][c]['tau'], 'd',
            'p3_decline:M5_params.%s.tau' % c)
        row('%s  corr(log A, log R_p)' % c, D1['cross_check'][c]['corr'], '—',
            'p1_mechanistic:cross_check.%s.corr' % c)
        row('%s  ν_data（5–20 d）' % c, D1['cross_check'][c]['nu_data_5_20'], '—',
            'p1_mechanistic:cross_check.%s.nu_data_5_20' % c)

    head('2  P2：浸泡响应的形状判别（三种候选形状 × 9 个组合）',
         '两个 ν 不是一回事：ν=1/2 属于改造半径（前沿位置，见 1b 的数值解），'
         '而产量对 ts 的响应是饱和的。本表用附件C 直接判别，不靠论证。')
    for c in CASES:
        rs = [r for r in D2['rows'] if r['case'] == c]
        for s, nm in (('S1_sqrt', 'R²(A+B·√ts)'), ('S2_exp', 'R²(A(1−e^(−ts/τ)))'),
                      ('S3_power', 'R²(A·ts^ν)')):
            row('%s  %s 区间（Cn=0.5/1.0/1.5）' % (c, nm),
                ' / '.join('%.4f' % r['shapes'][s]['r2'] for r in rs), '—',
                'p2_shape:rows.{i}.shapes.%s.r2' % s, '%s')
        row('%s  τ（S2，Cn=0.5/1.0/1.5）' % c,
            ' / '.join('%.3f' % r['shapes']['S2_exp']['params']['tau'] for r in rs), 'd',
            'p2_shape:rows.{i}.shapes.S2_exp.params.tau', '%s')
        row('%s  ν_data（S3）' % c,
            ' / '.join('%.4f' % r['shapes']['S3_power']['params']['nu'] for r in rs), '—',
            'p2_shape:rows.{i}.shapes.S3_power.params.nu', '%s')
        row('%s  τ 在三个浓度间的相对散布' % c, D2['tau_cn_independence'][c], '—',
            'p2_shape:tau_cn_independence.%s' % c, '%.3g')
        row('%s  ΔR²（指数饱和 − √ts）最小者' % c,
            min(r['dR2_exp_minus_sqrt'] for r in rs), '—', 'p2_shape:rows.{i}.dR2_exp_minus_sqrt', '%.4f')
        row('%s  √ts 形状的残差符号游程（期望 6.5）' % c,
            ' / '.join('%d' % r['shapes']['S1_sqrt']['resid_runs'] for r in rs), '次',
            'p2_shape:rows.{i}.shapes.S1_sqrt.resid_runs', '%s')
        row('%s  指数饱和的残差符号游程（期望 6.5）' % c,
            ' / '.join('%d' % r['shapes']['S2_exp']['resid_runs'] for r in rs), '次',
            'p2_shape:rows.{i}.shapes.S2_exp.resid_runs', '%s')
    row('9 个组合的最佳形状都是指数饱和', D2['decision']['best_shape_all_9'], '—',
        'p2_shape:decision.best_shape_all_9')
    row('ΔR² 的最小值（指数饱和 − √ts）', D2['decision']['min_dR2_exp_minus_sqrt'], '—',
        'p2_shape:decision.min_dR2_exp_minus_sqrt')
    row('自由幂律被否掉（ν_data 偏离 0.5 或跨场景不等）', D2['decision']['nu_single_powerlaw_rejected'],
        '—', 'p2_shape:decision.nu_single_powerlaw_rejected')
    ts_ = D2['tau_scaling_vs_Rp']
    row('τ 与 R_p(60 d) 的 log-log 指数', ts_['loglog_exponent'], '—',
        'p2_shape:tau_scaling_vs_Rp.loglog_exponent')
    row('该指数的 R²（3 个点）', ts_['loglog_r2'], '—', 'p2_shape:tau_scaling_vs_Rp.loglog_r2')
    row('若扩散控制应得的指数', ts_['diffusion_expected_exponent'], '—',
        'p2_shape:tau_scaling_vs_Rp.diffusion_expected_exponent', '%.1f')
    row('实测/扩散预期', ts_['ratio_observed_to_diffusion'], '—',
        'p2_shape:tau_scaling_vs_Rp.ratio_observed_to_diffusion', '%.3f')

    # ---------------------------------------------------------------- P3
    head('3  P3：五个产能模型的比选',
         'BIC 越小越好；逐组自由参数的模型参数最多（M1/M2/M3 各 324/216/324 个），M5 只有 15 个。')
    for k in ('M1', 'M2', 'M3', 'M4', 'M5'):
        m = D3['model_selection'][k]
        row('BIC (%s)' % k, m['bic'], '—', 'p3_decline:model_selection.%s.bic' % k, '%.1f')
        row('参数个数 (%s)' % k, m['kpar'], '个', 'p3_decline:model_selection.%s.kpar' % k, '%d')
        row('残差 RMSE (%s)' % k, m['rmse'], 'm³/d', 'p3_decline:model_selection.%s.rmse' % k)
    for c in CASES:
        row('%s  D（共享，40–330 d 对数斜率中位数）' % c, D3['shared_D'][c]['D'], 'd⁻¹',
            'p3_decline:shared_D.%s.D' % c, '%.6f')
        row('%s  D 在 36 组之间的变异系数' % c, D3['shared_D'][c]['D_cv'], '—',
            'p3_decline:shared_D.%s.D_cv' % c, '%.3g')
        p = D3['M5_params'][c]
        row('%s  A∞（M5）' % c, p['Ainf'], 'm³/d', 'p3_decline:M5_params.%s.Ainf' % c)
        row('%s  τ（M5）' % c, p['tau'], 'd', 'p3_decline:M5_params.%s.tau' % c)
        row('%s  p（M5 饱和指数）' % c, p['p'], '—', 'p3_decline:M5_params.%s.p' % c)
        row('%s  a（M5 浓度敏感度）' % c, p['a'], '—', 'p3_decline:M5_params.%s.a' % c)
        row('%s  R²（M5）' % c, p['r2'], '—', 'p3_decline:M5_params.%s.r2' % c)
        row('%s  相对 RMSE（M5）' % c, p['rel_rmse'], '—', 'p3_decline:M5_params.%s.rel_rmse' % c)
    for c in CASES:
        b = D3['bootstrap'][c]
        row('%s  EUR 的 bootstrap 90%% 区间下界' % c, b['EUR'][0], 'm³',
            'p3_decline:bootstrap.%s.EUR[0]' % c)
        row('%s  EUR 的 bootstrap 90%% 区间上界' % c, b['EUR'][1], 'm³',
            'p3_decline:bootstrap.%s.EUR[1]' % c)
        row('%s  D 的 bootstrap 90%% 区间' % c,
            '[%.4f, %.4f]' % (b['D'][0], b['D'][1]), 'd⁻¹', 'p3_decline:bootstrap.%s.D' % c)
    row('bootstrap 重抽样次数', D3['bootstrap']['Case1']['n_boot'], '次',
        'p3_decline:bootstrap.Case1.n_boot', '%d')
    row('bootstrap 随机种子', D3['bootstrap']['Case1']['seed'], '—',
        'p3_decline:bootstrap.Case1.seed', '%d')

    head('3b  P3：按浸泡档整组留出的交叉验证（5 折，含上下两个外推方向）',
         'M2 是逐组自由指数：被留出的浸泡档没有参数可估，故只在训练组上打分（`M2_train_rmse`），测试档记 NA。')
    for r in D3['cv']:
        row('fold %d 留出档 %s：M2 训练组 RMSE' % (r['fold'], r['held_out_ts']),
            r['M2_train_rmse'], 'm³/d', 'p3_decline:cv[%d].M2_train_rmse' % r['fold'])
        row('fold %d：M4 留出档 RMSE' % r['fold'], r['M4_rmse'], 'm³/d',
            'p3_decline:cv[%d].M4_rmse' % r['fold'])
        row('fold %d：M5 留出档 RMSE' % r['fold'], r['M5_rmse'], 'm³/d',
            'p3_decline:cv[%d].M5_rmse' % r['fold'])
    row('划分合规性审计：全部 PASS', D3['split_audit']['all_pass'], '—',
        'p3_decline:split_audit.all_pass')
    for f in D3['split_audit']['folds']:
        row('fold %d 测试集独有的浸泡档' % f['fold'], f['test_ts_not_in_train'], 'd',
            'p3_decline:split_audit.folds[%d].test_ts_not_in_train' % f['fold'])
        row('fold %d 整组只落在一个 split' % f['fold'], f['PASS_group_whole'], '—',
            'p3_decline:split_audit.folds[%d].PASS_group_whole' % f['fold'])

    head('3c  P3：每组 (场景,浓度,浸泡) 的 qi、D、EUR',
         'qi 为 M5 的第一天产能 A(ts,Cn)·e^-D，EUR 为 360 d 累计；D 按场景共享，故同一场景内 qi 的差异全部来自 A(ts,Cn)。')
    for g in D3['groups']:
        c = g['case']
        row('%s Cn=%.1f ts=%d：q1' % (c, g['cn'], int(g['ts'])), g['qi_shared'], 'm³/d',
            'p3_decline:groups[%d].qi_shared' % D3['groups'].index(g))
        row('%s Cn=%.1f ts=%d：EUR（实测）' % (c, g['cn'], int(g['ts'])), g['EUR_data'], 'm³',
            'p3_decline:groups[%d].EUR_data' % D3['groups'].index(g))
        row('%s Cn=%.1f ts=%d：EUR（M5 拟合）' % (c, g['cn'], int(g['ts'])), g['EUR_shared'], 'm³',
            'p3_decline:groups[%d].EUR_shared' % D3['groups'].index(g))

    # ---------------------------------------------------------------- P4
    head('4  P4：题面 B.4 的官方检验向量',
         '用来锁定成本口径。Vinj=3000、fCO2=0.5、Cn=1.0、注入 10 d、浸泡 30 d。')
    t = D4['test_b4']
    row('水相体积 Vaq', t['Vaq'], 'm³', 'p4_econ:test_b4.Vaq')
    row('纳米材料用量', t['m_nano_t'], 't', 'p4_econ:test_b4.m_nano_t')
    row('纳米材料费', t['cost_nano_wan'], '万元', 'p4_econ:test_b4.cost_nano_wan')
    row('CO2 用量', t['m_co2_t'], 't', 'p4_econ:test_b4.m_co2_t')
    row('CO2 费', t['cost_CO2_wan'], '万元', 'p4_econ:test_b4.cost_CO2_wan')
    row('注入天数', t['tinj_d'], 'd', 'p4_econ:test_b4.tinj_d')
    row('小计（不含生产费）', t['subtotal_wan'], '万元', 'p4_econ:test_b4.subtotal_wan')
    row('断言通过', t['PASS'], '—', 'p4_econ:test_b4.PASS')

    head('4b  P4：最优浸泡时间的两套口径（Cn=1.0）',
         '档位最优是工程可执行的决策值；连续驻点是 dNPV/dts=0 的解。')
    for c in CASES:
        o = D4['optimum_two_calibers']['%s|cn1.0' % c]
        row('%s  ts_data_grid（档位最优）' % c, o['ts_data_grid'], 'd',
            'p4_econ:optimum_two_calibers.%s|cn1.0.ts_data_grid' % c, '%.0f')
        row('%s  ts_continuous（连续驻点）' % c, o['ts_continuous'], 'd',
            'p4_econ:optimum_two_calibers.%s|cn1.0.ts_continuous' % c, '%.2f')
        row('%s  档位最优处的 NPV' % c, o['npv_at_data_grid'] / 1e4, '万元',
            'p4_econ:optimum_two_calibers.%s|cn1.0.npv_at_data_grid' % c, '%.2f')
        row('%s  两口径之差 Δts' % c, o['d_ts'], 'd',
            'p4_econ:optimum_two_calibers.%s|cn1.0.d_ts' % c, '%.2f')
        row('%s  两口径之差 ΔNPV' % c, o['d_npv_wan'], '万元',
            'p4_econ:optimum_two_calibers.%s|cn1.0.d_npv_wan' % c, '%.2f')
        o2 = D4['optimum_ts']['%s|cn1.0' % c]
        row('%s  ±2%% 平台带' % c, '[%.0f, %.0f]' % tuple(o2['band_2pct']), 'd',
            'p4_econ:optimum_ts.%s|cn1.0.band_2pct' % c)
        row('%s  ts=5 d 的 NPV' % c, o2['npv_at_5'] / 1e4, '万元',
            'p4_econ:optimum_ts.%s|cn1.0.npv_at_5' % c, '%.2f')
        row('%s  ts=30 d 的 NPV' % c, o2['npv_at_30'] / 1e4, '万元',
            'p4_econ:optimum_ts.%s|cn1.0.npv_at_30' % c, '%.2f')

    head('4c  P4：盈亏平衡反推（Cn=1.0，ts 取档位最优）',
         'NPV = 0 所需的累计产油与实测之比，即"结构性亏损"的定量表述。')
    for c in CASES:
        b = D4['break_even'][c]
        row('%s  实测累计油' % c, b['EUR_obs'], 'm³', 'p4_econ:break_even.%s.EUR_obs' % c)
        row('%s  NPV=0 所需累计油' % c, b['EUR_required_for_zero'], 'm³',
            'p4_econ:break_even.%s.EUR_required_for_zero' % c)
        row('%s  所需/实测' % c, b['ratio_required_over_observed'], '倍',
            'p4_econ:break_even.%s.ratio_required_over_observed' % c, '%.2f')
        row('%s  NPV=0 所需油价' % c, b['price_required_for_zero'], 'CNY/m³',
            'p4_econ:break_even.%s.price_required_for_zero' % c, '%.0f')
        row('%s  NPV=0 所需的 Cfrac 变化量' % c, b['frac_cost_required_for_zero'] / 1e4, '万元',
            'p4_econ:break_even.%s.frac_cost_required_for_zero' % c, '%.1f')

    head('4d  P4：V0 的两种口径与注入量不可识别',
         'V0_geo 由机理 R_p(60 d) 与缝面面积给出；V0_emp 为经验值 1500 m³。')
    for c in CASES:
        row('%s  R_p(60 d)' % c, D4['V0'][c]['Rp60'], 'm', 'p4_econ:V0.%s.Rp60' % c)
        row('%s  缝面面积 A_face' % c, D4['V0'][c]['A_face'], 'm²', 'p4_econ:V0.%s.A_face' % c)
        row('%s  V0_geo' % c, D4['V0'][c]['geo'], 'm³', 'p4_econ:V0.%s.geo' % c)
        row('%s  V0_emp' % c, D4['V0'][c]['emp'], 'm³', 'p4_econ:V0.%s.emp' % c)
        for tag in ('geo', 'emp'):
            m = D4['pareto_meta']['%s|%s' % (c, tag)]
            row('%s  V0=%s：max-NPV 解的 Vinj' % (c, tag), m['npv_best']['Vinj'], 'm³',
                'p4_econ:pareto_meta.%s|%s.npv_best.Vinj' % (c, tag), '%.0f')
            row('%s  V0=%s：max-NPV' % (c, tag), m['npv_best']['npv'] / 1e4, '万元',
                'p4_econ:pareto_meta.%s|%s.npv_best.npv' % (c, tag), '%.2f')
            row('%s  V0=%s：前沿点数' % (c, tag), m['n_front'], '个',
                'p4_econ:pareto_meta.%s|%s.n_front' % (c, tag), '%d')
            row('%s  V0=%s：膝点的 ts / Vinj' % (c, tag),
                '%.0f / %.0f' % (m['knee']['ts'], m['knee']['Vinj']), 'd / m³',
                'p4_econ:pareto_meta.%s|%s.knee' % (c, tag))
            row('%s  V0=%s：膝点的 EUR / 成本 / NPV' % (c, tag),
                '%.0f / %.0f / %.2f' % (m['knee']['EUR_m3'], m['knee']['cost_nom'] / 1e4,
                                        m['knee']['npv'] / 1e4), 'm³ / 万元 / 万元',
                'p4_econ:pareto_meta.%s|%s.knee' % (c, tag))
        row('%s  NSGA-II 与网格 max-NPV 的相对差' % c,
            D4['pareto_meta']['%s|nsga2_check' % c]['rel_diff'], '—',
            'p4_econ:pareto_meta.%s|nsga2_check.rel_diff' % c)

    head('4e  P4：±15% 扰动的鲁棒性（7 个因子 × 2 个符号 = 14 次）',
         '判据是决策不变性：扰动后档位最优 ts 是否改变。')
    for c in CASES:
        r = D4['robustness'][c]
        row('%s  基准 ts*' % c, r['base_ts'], 'd', 'p4_econ:robustness.%s.base_ts' % c, '%.0f')
        row('%s  基准 NPV' % c, r['base_npv'] / 1e4, '万元',
            'p4_econ:robustness.%s.base_npv' % c, '%.2f')
        row('%s  改变了 ts* 的扰动个数' % c, r['n_changed'], '个（共 14）',
            'p4_econ:robustness.%s.n_changed' % c, '%d')
        row('%s  NPV 相对摆幅' % c, r['npv_span_rel'], '—',
            'p4_econ:robustness.%s.npv_span_rel' % c, '%.3g')

    head('4f  P4：机理-数据差异的归因（方向 + 量级）',
         '每条都可检验：给出"若假设不成立，预测偏高/偏低多少"。')
    a = D4['attribution']
    for c in CASES:
        row('%s  共享 D 的相对散布 ΔD/D' % c, a['shared_D_impact'][c]['rel_dD'], '—',
            'p4_econ:attribution.shared_D_impact.%s.rel_dD' % c, '%.3g')
        row('%s  共享 D 假设失效对 EUR 的相对影响' % c, a['shared_D_impact'][c]['d_EUR_rel'], '—',
            'p4_econ:attribution.shared_D_impact.%s.d_EUR_rel' % c, '%.3g')
    row('实测残差中位相对值（题面声明噪声 ±5%）', a['data_noise']['measured_med_rel_resid'], '—',
        'p4_econ:attribution.data_noise.measured_med_rel_resid')
    row('实测残差相对标准差', a['data_noise']['measured_resid_sd_rel'], '—',
        'p4_econ:attribution.data_noise.measured_resid_sd_rel')
    for c in CASES:
        row('%s  EUR 的 bootstrap 半宽（噪声传播）' % c, a['data_noise']['eur_ci_wan'][c], 'm³',
            'p4_econ:attribution.data_noise.eur_ci_wan.%s' % c)
    row('缝面面积口径', a['A_face_convention']['expression'], '—',
        'p4_econ:attribution.A_face_convention.expression')

    # ---------------------------------------------------------------- P5
    head('5  P5：Sobol 全局敏感性（对 ts*）',
         'N=1024，2k=16 维单一 Sobol 设计前后切分 A/B（实测 max|corr(A,B)| 见下），Jansen 估计量；'
         'S1 之和 ≈ 1、ST 之和 ≈ 1 说明交互项可忽略，模型近似可加。')
    row('A/B 两矩阵列间最大 |corr|', D5['design']['max_abs_corr_A_B'], '—',
        'p5_sobol:design.max_abs_corr_A_B', '%.3g')
    row('模型求值次数', D5['design']['n_eval'], '次', 'p5_sobol:design.n_eval', '%d')
    row('随机种子', D5['design']['seed'], '—', 'p5_sobol:design.seed', '%d')
    for c in CASES:
        r = D5['sobol'][c]['ts']
        row('%s  ΣS1（对 ts*）' % c, r['sum_S1'], '—', 'p5_sobol:sobol.%s.ts.sum_S1' % c)
        row('%s  ΣST（对 ts*）' % c, r['sum_ST'], '—', 'p5_sobol:sobol.%s.ts.sum_ST' % c)
        row('%s  max|S1−ST|（对 ts*）' % c, r['max_abs_S1_minus_ST'], '—',
            'p5_sobol:sobol.%s.ts.max_abs_S1_minus_ST' % c)
        for f in D5['design']['factors']:
            row('%s  S1(%s) 对 ts*' % (c, f), r['S1'][f], '—',
                'p5_sobol:sobol.%s.ts.S1.%s' % (c, f))
            row('%s  ST(%s) 对 ts*' % (c, f), r['ST'][f], '—',
                'p5_sobol:sobol.%s.ts.ST.%s' % (c, f))
        row('%s  因子排序（按 ST）' % c, ', '.join(r['order'][:4]), '—',
            'p5_sobol:sobol.%s.ts.order' % c)
    head('5b  P5：弹性判据与 Sobol 的交叉验证',
         '闭式 ts* = τ·ln(arg) 给出 e(A∞)=e(c_soak)=τ/ts*、e(τ)=(ts*−τ)/ts*；'
         '预测的 S1 比 = (e_i/e_A∞)²，与实测比对照。')
    for c in CASES:
        e = D5['elasticity_check'][c]
        row('%s  ts*/τ' % c, e['ts_over_tau'], '—', 'p5_sobol:elasticity_check.%s.ts_over_tau' % c,
            '%.2f')
        row('%s  主导因子判据' % c, e['regime'], '—', 'p5_sobol:elasticity_check.%s.regime' % c)
        row('%s  e(A∞) = e(c_soak)' % c, e['e_Ainf'], '—',
            'p5_sobol:elasticity_check.%s.e_Ainf' % c, '%.3f')
        row('%s  e(τ)' % c, e['e_tau'], '—', 'p5_sobol:elasticity_check.%s.e_tau' % c, '%.3f')
        row('%s  预测 S1(τ)/S1(A∞)' % c, e['pred_S1_tau_over_Ainf'], '—',
            'p5_sobol:elasticity_check.%s.pred_S1_tau_over_Ainf' % c, '%.3f')
        row('%s  实测 S1(τ)/S1(A∞)' % c, e['obs_S1_tau_over_Ainf'], '—',
            'p5_sobol:elasticity_check.%s.obs_S1_tau_over_Ainf' % c, '%.3f')
        row('%s  实测 S1(c_soak)/S1(A∞)' % c, e['obs_S1_csoak_over_Ainf'], '—',
            'p5_sobol:elasticity_check.%s.obs_S1_csoak_over_Ainf' % c, '%.3f')
        q = D5['sobol'][c]['quantiles']
        row('%s  NPV 的 5/50/95 分位' % c, ' / '.join('%.0f' % (v / 1e4) for v in q['npv']),
            '万元', 'p5_sobol:sobol.%s.quantiles.npv' % c)
        row('%s  ts* 的 5/50/95 分位' % c, ' / '.join('%.1f' % v for v in q['ts']), 'd',
            'p5_sobol:sobol.%s.quantiles.ts' % c)

    head('6  环境与数值对账')
    row('numpy 版本', DE['numpy_version'], '—', 'verify_env:numpy_version')
    row('手写 OLS 与 numpy 的一致性（三场景）',
        ' / '.join('%.1e' % c['rel_diff'] for c in DE['slope_equivalence']), '—',
        'verify_env:slope_equivalence.{i}.rel_diff')
    row('对账通过', DE['PASS'], '—', 'verify_env:PASS')

    path = os.path.join(MC.ROOT, 'out', '03-numbers.md')
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(L) + '\n')
    print('-> out/03-numbers.md  %d 行' % len(L))


if __name__ == '__main__':
    main()