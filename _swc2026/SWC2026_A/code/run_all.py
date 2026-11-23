#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""一键复跑全部建模计算与图表。

用法（在任意目录）：
    E:\\Mini\\envs\\mathmodel\\python.exe code\\run_all.py

链条：p3（附件C 产能）→ p1（机理/无量纲）→ p2_shape（P2 形状判别）→ p4（经济/优化）
      → p5（Sobol）→ verify_env（环境对账）→ figs（7 张图）→ make_tables（03-numbers.md）

每一步都核对：退出码 0、预期打印标记、产物文件存在且 mtime 晚于本步开始时间
（防止"文件在、但是上一版"）。全部通过后打印 PASS 汇总并以 0 退出。
"""
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = os.path.join(ROOT, 'code')
PY = sys.executable
DAY = 86400.0

STEPS = [
    ('p3_decline.py',    ['OK p3'],                    ['data/p3_decline.json']),
    ('p1_mechanistic.py', ['OK p1'],                   ['data/p1_mechanistic.json']),
    ('p2_shape.py',      ['decision:'],            ['data/p2_shape.json',
                                                        'figures/fig7_shape_discrimination.png']),
    ('p4_econ.py',       ['PASS 848.25', 'OK p4'],      ['data/p4_econ.json']),
    ('p5_sobol.py',      ['OK p5'],                    ['data/p5_sobol.json']),
    ('verify_env.py',    [],                           ['data/verify_env.json']),
    ('figs.py',          ['OK figs'],                  ['figures/fig1_decline_family.png',
                                                        'figures/fig2_soak_saturation.png',
                                                        'figures/fig3_npv_vs_soak.png',
                                                        'figures/fig4_pareto.png',
                                                        'figures/fig5_sobol_ts.png',
                                                        'figures/fig6_scaling.png']),
    ('make_tables.py',   ['-> out/03-numbers.md'],      ['out/03-numbers.md']),
]


def run_step(script, markers, outputs):
    path = os.path.join(CODE, script)
    t0 = time.time()
    wall0 = time.time()
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    p = subprocess.run([PY, path], cwd=ROOT, env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = p.stdout.decode('utf-8', 'replace')
    dt = time.time() - t0
    if p.returncode != 0:
        raise SystemExit('[FAIL] %s 退出码 %d\n%s' % (script, p.returncode, out[-4000:]))
    for m in markers:
        if m not in out:
            raise SystemExit('[FAIL] %s 缺少标记 %r\n%s' % (script, m, out[-4000:]))
    for rel in outputs:
        ap = os.path.join(ROOT, rel.replace('/', os.sep))
        if not os.path.isfile(ap):
            raise SystemExit('[FAIL] %s 未生成 %s' % (script, rel))
        if os.path.getmtime(ap) < wall0 - 2.0:
            raise SystemExit('[FAIL] %s 的产物 %s 早于本步开始（旧文件）' % (script, rel))
        if os.path.getsize(ap) == 0:
            raise SystemExit('[FAIL] %s 的产物 %s 为空' % (script, rel))
    return dt, out


def load(name):
    with open(os.path.join(ROOT, 'data', name), encoding='utf-8') as f:
        return json.load(f)


def check_all():
    """跨文件断言：任何一条不成立就退出 1。"""
    errs = []

    p1 = load('p1_mechanistic.json')
    for c in ('Case1', 'Case2', 'Case3'):
        rp = p1['radii'][c]['Rp']
        if len(rp) != 60 or rp[59] is None or rp[0] is None:
            errs.append('p1 %s Rp 长度/空值异常' % c)
    if not (0.49 < p1['scaling']['Case1']['all']['nu'] < 0.51):
        errs.append('p1 Case1 nu 偏离 1/2')

    p3 = load('p3_decline.json')
    if p3.get('n_groups') != 108:
        errs.append('p3 n_groups != 108')
    if not p3.get('split_audit', {}).get('all_pass'):
        errs.append('p3 split_audit.all_pass != true')
    for c in ('Case1', 'Case2', 'Case3'):
        if abs(p3['M5_params'][c]['p'] - 1.0) > 0.05:
            errs.append('p3 %s 的 p 偏离 1（饱和律形状）' % c)

    p2 = load('p2_shape.json')
    if len(p2.get('rows', [])) != 9:
        errs.append('p2 rows 数 != 9')
    if not p2.get('decision', {}).get('best_shape_all_9'):
        errs.append('p2 不是 9/9 组合都以指数饱和为最优')
    if not p2.get('decision', {}).get('nu_single_powerlaw_rejected'):
        errs.append('p2 未拒绝单一幂律')

    p4 = load('p4_econ.json')
    if not p4['test_b4'].get('PASS'):
        errs.append('p4 test_b4 未 PASS')
    if abs(p4['test_b4']['subtotal_wan'] - 848.25) > 0.01:
        errs.append('p4 B.4 小计 %.4f != 848.25' % p4['test_b4']['subtotal_wan'])

    p5 = load('p5_sobol.json')
    if p5['design']['max_abs_corr_A_B'] > 0.05:
        errs.append('p5 A/B 相关 %.3f 过大' % p5['design']['max_abs_corr_A_B'])
    for c in ('Case1', 'Case2', 'Case3'):
        for out in ('ts', 'npv'):
            s = p5['sobol'][c][out]
            if abs(s['sum_S1'] - 1.0) > 0.08 or abs(s['sum_ST'] - 1.0) > 0.08:
                errs.append('p5 %s/%s sumS1=%.3f sumST=%.3f 超界' % (c, out, s['sum_S1'], s['sum_ST']))

    v = load('verify_env.json')
    if not v.get('PASS'):
        errs.append('verify_env PASS != true')

    # 每个 data/*.json 必须带 _meta（脚本名、运行时间、输入哈希）
    for fn in sorted(os.listdir(os.path.join(ROOT, 'data'))):
        if not fn.endswith('.json'):
            continue
        d = load(fn)
        m = d.get('_meta') if isinstance(d, dict) else None
        if not isinstance(m, dict) or not {'script', 'run_at', 'inputs'} <= set(m):
            errs.append('data/%s 缺 _meta(script/run_at/inputs)' % fn)

    # 03-numbers.md 规模与图
    nt = os.path.join(ROOT, 'out', '03-numbers.md')
    with open(nt, encoding='utf-8') as f:
        nline = sum(1 for _ in f)
    if nline < 400:
        errs.append('out/03-numbers.md 只有 %d 行' % nline)

    return errs


def main():
    t_start = time.time()
    print('=' * 72)
    print('run_all：2026 数维杯 A 题 前期建模稿全链路')
    print('工作目录：%s' % ROOT)
    print('解释器：%s' % PY)
    print('=' * 72)
    total = 0.0
    for script, markers, outputs in STEPS:
        print('[run] %-20s ...' % script, end='', flush=True)
        dt, out = run_step(script, markers, outputs)
        total += dt
        tail = [l for l in out.strip().splitlines() if l.strip()][-1:] or ['']
        print('\r[ok ] %-20s %6.1f s   %s' % (script, dt, tail[0][:80]))

    print('-' * 72)
    print('跨文件断言 ...')
    errs = check_all()
    if errs:
        for e in errs:
            print('  [FAIL] %s' % e)
        raise SystemExit(1)
    print('  全部通过（108 组 / split_audit / B.4 / Sobol / _meta / 表）')

    print('-' * 72)
    print('产物清单：')
    for sub in ('data', 'figures'):
        d = os.path.join(ROOT, sub)
        fs = sorted(f for f in os.listdir(d) if os.path.isfile(os.path.join(d, f)))
        print('  %-8s %2d 个  %s' % (sub, len(fs), ', '.join(fs[:6]) + (' ...' if len(fs) > 6 else '')))
    print('  out/03-numbers.md  %d 行' % sum(1 for _ in open(os.path.join(ROOT, 'out', '03-numbers.md'), encoding='utf-8')))
    print('=' * 72)
    print('PASS 全部 %d 步完成，累计 %.1f s（墙钟 %.1f s）' % (len(STEPS), total, time.time() - t_start))


if __name__ == '__main__':
    main()
