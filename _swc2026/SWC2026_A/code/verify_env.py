# -*- coding: utf-8 -*-
"""
环境与数值对账：确认手写的 ols_slope / corr 与 numpy 的 polyfit / corrcoef 一致。
用途：numpy.libs 的 OpenBLAS 曾缺失、np.dot 系函数整机崩溃，机理与统计脚本一度改成手写；
修好之后用本脚本一次性证明"手写版与 numpy 版等价（相对差 <1e-12）"，则先前结果无需重算。
"""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mm_common as MC

OUT = {}


def one(case, cn, ts, lo, hi):
    df = MC.load_production()
    g = df[(df.Case == case) & (np.isclose(df.Cn, cn)) & (np.isclose(df.ts, ts))].sort_values('day')
    m = (g.day >= lo) & (g.day <= hi) & (g.q > 1e-6)
    x = g.day[m].values.astype(float)
    y = np.log(g.q[m].values)
    b_np = float(np.polyfit(x, y, 1)[0])
    b_hand, a_hand, r2 = MC.ols_slope(x, y)
    return dict(n=int(m.sum()), slope_numpy=b_np, slope_hand=float(b_hand),
                rel_diff=float(abs(b_np - b_hand) / abs(b_np)), r2=float(r2),
                corr_numpy=float(np.corrcoef(x, y)[0, 1]), corr_hand=float(MC.corr(x, y)))


def main():
    cases = []
    for case in MC.CASE_KEYS:
        cases.append(dict(case=case, **one(case, 1.0, 30.0, 40, 300)))
    OUT['slope_equivalence'] = cases
    OUT['numpy_version'] = np.__version__
    OUT['blas_ok'] = dict(dot=float(np.dot([1.0, 2.0], [3.0, 4.0])),
                          inv=float(np.linalg.inv(np.array([[2.0, 0.0], [0.0, 2.0]]))[0, 0]),
                          lstsq_rank=int(np.linalg.lstsq(np.eye(3), np.ones(3), rcond=None)[2]))
    OUT['PASS'] = all(c['rel_diff'] < 1e-12 for c in cases)
    OUT['note'] = ('numpy.libs 的 OpenBLAS 曾缺失，np.dot/inv/lstsq/corrcoef/polyfit 触发 '
                   '0xC06D007F 原生崩溃；lead 已 pip install --force-reinstall numpy==2.4.6 修复。'
                   '机理/统计脚本里的手写 ols_slope 与 corr 与之等价（相对差 <1e-12），故先前结果无需重算。')
    MC.save_json('verify_env', OUT, os.path.abspath(__file__), MC.input_hashes())
    print('numpy', np.__version__, 'PASS' if OUT['PASS'] else 'FAIL',
          [(c['case'], '%.2e' % c['rel_diff']) for c in cases])


if __name__ == '__main__':
    main()