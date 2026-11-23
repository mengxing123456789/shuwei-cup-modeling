# -*- coding: utf-8 -*-
import sys, traceback
import pandas as pd, numpy as np

P = r'E:\数学建模\数维杯\2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）赛题\A题\附件C Synthetic_Production_Data（英文版）.xlsx'


def main():
    df = pd.read_excel(P)
    df['Case'] = df.Case_ID.str.slice(0, 5)
    for c in ['Case1', 'Case2', 'Case3']:
        s = df[df.Case == c]
        piv = s.pivot_table(index=['Nano_Concentration_wt%', 'Soak_Time_Days'],
                            columns='Production_Day', values='Oil_Rate_m3_d')
        # normalise by q at day 30 (well inside decline)
        norm = piv.div(piv[30], axis=0)
        cv = (norm.std() / norm.mean())
        print('==', c, 'shape collapse CV by day')
        print('  d1..d12 :', np.round(cv.values[:12], 3))
        print('  d15,d20,d30,d60,d120,d240,d360:',
              [round(float(cv[k]), 3) for k in [15, 20, 30, 60, 120, 240, 360]])
        # exponential fit over 30..330 on the mean shape
        m = norm.mean(axis=0)
        t = np.array(m.index, float)
        sel = (t >= 30) & (t <= 330)
        D = -np.polyfit(t[sel], np.log(m.values[sel]), 1)[0]
        print('  fitted D on mean shape (30-330):', round(float(D), 5),
              ' implied 1/D days:', round(1 / D, 2))
        # implied qi at t=0 from the fit
        a, b = np.polyfit(t[sel], np.log(m.values[sel]), 1)
        print('  shape at t=0 ->', round(float(np.exp(a)), 4),
              '| mean shape day1/30:', round(float(m[1]), 4))
        print('  mean shape:', [(k, round(float(m[k]), 3)) for k in [1, 2, 3, 4, 5, 7, 10, 15, 20, 30, 60, 120, 240, 360]])
    print('OK')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(2)