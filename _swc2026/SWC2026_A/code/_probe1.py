# -*- coding: utf-8 -*-
import sys, traceback
import pandas as pd, numpy as np

P = r'E:\数学建模\数维杯\2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）赛题\A题\附件C Synthetic_Production_Data（英文版）.xlsx'


def main():
    df = pd.read_excel(P)
    df['Case'] = df.Case_ID.str.slice(0, 5)
    rows = []
    for k, d in df.groupby(['Case', 'Nano_Concentration_wt%', 'Soak_Time_Days']):
        d = d.sort_values('Production_Day')
        q = d.Oil_Rate_m3_d.values
        t = d.Production_Day.values
        m = (t >= 40) & (t <= 300) & (q > 0.05)
        D = -np.polyfit(t[m], np.log(q[m]), 1)[0]
        rows.append((k[0], k[1], k[2], q[0], q[4], q[9], D))
    r = pd.DataFrame(rows, columns=['case', 'cn', 'ts', 'q1', 'q5', 'q10', 'D'])
    for c in ['Case1', 'Case2', 'Case3']:
        s = r[r.case == c]
        print('==', c)
        print('D  (log-slope 40-300d)')
        print(s.pivot_table(index='cn', columns='ts', values='D').round(4).to_string())
        print('q1')
        print(s.pivot_table(index='cn', columns='ts', values='q1').round(2).to_string())
        print('q1/q1(ts=5)')
        piv = s.pivot_table(index='cn', columns='ts', values='q1')
        print((piv.div(piv[5], axis=0)).round(3).to_string())
    print('OK')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(2)