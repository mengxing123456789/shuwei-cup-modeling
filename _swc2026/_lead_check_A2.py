# -*- coding: utf-8 -*-
"""A 题附件 C 的二阶透视：浓度效应、浸泡效应、BHP 与产量关系、NPV 曲线形状。"""
import json
import numpy as np
import pandas as pd

XL = (r"E:\数学建模\数维杯\2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）"
      r"赛题\A题\附件C Synthetic_Production_Data（英文版）.xlsx")
OUT = r"E:\数学建模\_swc2026\_lead_check_A2.json"

df = pd.read_excel(XL, engine="openpyxl")
df.columns = ["case", "cn", "ts", "day", "bhp", "rate", "cum"]
res = {}

tot = df.groupby(["case", "cn", "ts"]).cum.max().reset_index()

# 1) 浓度效应：固定 ts=30，各 cn 的 360 天累计
for case in df.case.unique():
    sub = tot[(tot.case == case) & (tot.ts == 30)]
    res[f"cum@{case}@ts30"] = {f"cn{r.cn}": round(float(r.cum), 1) for r in sub.itertuples()}

# 2) 浸泡效应：固定 cn=1.0，各 ts 的累计（min/max/相对增益）
for case in df.case.unique():
    sub = tot[(tot.case == case) & (tot.cn == 1.0)].sort_values("ts")
    lo, hi = sub.iloc[0], sub.iloc[-1]
    res[f"soak@{case}@cn1.0"] = {
        "ts_min": int(lo.ts), "cum_min": round(float(lo.cum), 1),
        "ts_max": int(hi.ts), "cum_max": round(float(hi.cum), 1),
        "rel_gain_pct": round(100 * (hi.cum / lo.cum - 1), 2),
        "curve": {int(r.ts): round(float(r.cum), 1) for r in sub.itertuples()},
        "monotone_increasing": bool(np.all(np.diff(sub.cum.values) > 0)),
    }

# 3) BHP 与日产油的相关（同一曲线内去趋势）
def corr(x, y):
    """手写相关系数：绕开本机 numpy.corrcoef 的 0xC06D007F 原生崩溃（已知环境故障）"""
    x = np.asarray(x, float); y = np.asarray(y, float)
    x = x - x.mean(); y = y - y.mean()
    den = np.sqrt((x * x).sum() * (y * y).sum())
    return float((x * y).sum() / den) if den > 0 else float("nan")


cors = []
for (case, cn, ts), sub in df.groupby(["case", "cn", "ts"]):
    sub = sub.sort_values("day")
    cors.append(corr(sub.bhp.values, sub.rate.values))
res["corr_bhp_rate_median"] = round(float(np.median(cors)), 4)
res["corr_bhp_rate_p10_p90"] = [round(float(np.percentile(cors, 10)), 3),
                                round(float(np.percentile(cors, 90)), 3)]

# 4) 日产量的衰减形态：首日/末日/半衰期（拟合指数）
dec = {}
for case in df.case.unique():
    sub = df[(df.case == case) & (df.cn == 1.0) & (df.ts == 30)].sort_values("day")
    y = sub.rate.values
    q1, q360 = y[0], y[-1]
    # 指数衰减拟合 log y ~ a + b*day（手写二元法方程，避免 np.polyfit 触发同类崩溃）
    d = sub.day.values.astype(float)
    ly = np.log(np.maximum(y, 1e-9))
    dm, lm = d.mean(), ly.mean()
    sxx = ((d - dm) ** 2).sum()
    b = float(((d - dm) * (ly - lm)).sum() / sxx)
    a = float(lm - b * dm)
    dec[case] = {"q_day1": round(float(q1), 3), "q_day360": round(float(q360), 3),
                 "ratio": round(float(q360 / q1), 3),
                 "exp_decay_per_day": round(float(b), 6),
                 "half_life_days": round(float(np.log(2) / -b), 1) if b < 0 else None}
res["decay"] = dec

# 5) NPV 曲线的完整形状（cn=1.0，每场景）
POIL, C_NANO, C_INJ, C_SOAK, C_FRAC, C_PROD, R = 3396.0, 20e4, 30e4, 3e4, 120e4, 0.035e4, 0.08
VINJ, QINJ, FCO2 = 3000.0, 300.0, 0.5
t_inj = VINJ / QINJ
curves = {}
for case in df.case.unique():
    sub = df[(df.case == case) & (df.cn == 1.0)]
    pts = {}
    for ts, s2 in sub.groupby("ts"):
        y = s2.sort_values("day").rate.values
        vaq = VINJ * (1 - FCO2)
        cost = C_FRAC + C_NANO * (1.0 / 100 * vaq) + C_INJ * t_inj + C_SOAK * ts
        disc = (1 + R) ** (-(t_inj + ts + np.arange(1, 361)) / 365.0)
        net = float((POIL - C_PROD) * (y * disc).sum() - cost)
        pts[int(ts)] = round(net / 1e4, 1)
    curves[case] = pts
res["npv_curve_cn1.0_1e4"] = curves

json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))