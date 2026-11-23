# -*- coding: utf-8 -*-
"""Lead 独立复核 A 题附件 C：数据完整性 + NPV 最优浸泡时间（不看 mm-a 的结论先算一遍）。

产出 _lead_check_A.json，用于与 mm-a 的数字对账。
"""
import json, hashlib, os
import numpy as np
import pandas as pd

XL = (r"E:\数学建模\数维杯\2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）"
      r"赛题\A题\附件C Synthetic_Production_Data（英文版）.xlsx")
OUT = r"E:\数学建模\_swc2026\_lead_check_A.json"

# ---- 经济参数（题面 B.1，单位 10^4 CNY）----
POIL = 3396.0            # CNY/m3
C_NANO = 20e4            # CNY/t
C_INJ = 30e4             # CNY/d 注入期
C_SOAK = 3e4             # CNY/d 浸泡期
C_FRAC = 120e4           # CNY/井 day0
C_PROD = 0.035e4         # CNY/m3 产液
R_YEAR = 0.08
VINJ, QINJ, FCO2 = 3000.0, 300.0, 0.5

def npv(prod_rate_daily, t_inj, ts, cn, n_prod=360):
    """日末折现、day0 基准。成本在 day0 一次付清（按题面：压裂 day0，注入与浸泡在注入/浸泡期）"""
    vaq = VINJ * (1 - FCO2)
    m_nano = cn / 100.0 * vaq          # t
    cost = C_FRAC + C_NANO * m_nano + C_INJ * t_inj + C_SOAK * ts
    disc = np.array([(1 + R_YEAR) ** (-(t_inj + ts + d) / 365.0) for d in range(1, n_prod + 1)])
    rev = POIL * prod_rate_daily * disc
    # 生产期操作成本（产液处理）也折现
    op = C_PROD * prod_rate_daily * disc
    return float(rev.sum() - op.sum() - cost), float(cost), float(rev.sum())

def main():
    print("reading xlsx ...", flush=True)
    df = pd.read_excel(XL, engine="openpyxl")
    print(df.shape, list(df.columns), flush=True)
    df.columns = ["case", "cn", "ts", "day", "bhp", "rate", "cum"]
    rep = {"file_sha256": hashlib.sha256(open(XL, "rb").read()).hexdigest(),
           "shape": list(df.shape)}

    # ---- 完整性 1：Cum 是否恰好等于 rate 的累加 ----
    g = df.groupby(["case", "cn", "ts"], sort=True)
    resid = []
    for k, sub in g:
        sub = sub.sort_values("day")
        resid.append(np.abs(np.cumsum(sub.rate.values) - sub.cum.values).max())
    rep["cum_eq_cumsum_max_abs_dev"] = float(np.max(resid))
    rep["cum_eq_cumsum_all_exact"] = bool(np.max(resid) < 1e-9)

    # ---- 完整性 2：每个 (case,cn,ts) 是否 360 天连续无缺 ----
    lens = g.size()
    rep["groups"] = int(len(lens))
    rep["group_len_min_max"] = [int(lens.min()), int(lens.max())]
    rep["cn_levels"] = sorted(df.cn.unique().tolist())
    rep["ts_levels"] = sorted(df.ts.unique().tolist())

    # ---- 噪声水平：对每条曲线做 15 点滑动中位平滑，残差/均值 ----
    rel = []
    for k, sub in g:
        y = sub.sort_values("day").rate.values.astype(float)
        sm = pd.Series(y).rolling(15, center=True, min_periods=5).median().values
        m = np.nanmean(sm)
        rel.append(np.nanstd(y - sm) / m)
    rep["noise_rel_sigma_median"] = float(np.median(rel))
    rep["noise_rel_sigma_p10_p90"] = [float(np.percentile(rel, 10)), float(np.percentile(rel, 90))]

    # ---- 产量随浸泡时间：末期 360 天累计 ----
    tot = df.groupby(["case", "cn", "ts"]).cum.max().reset_index()
    rep["cum_by_case_cn_ts"] = {f"{r.case}|cn{r.cn}|ts{r.ts}": float(r.cum) for r in tot.itertuples()}

    # ---- NPV：固定 Vinj/qinj=10d 注入，扫 ts ----
    t_inj = VINJ / QINJ
    rows = []
    for (case, cn, ts), sub in g:
        y = sub.sort_values("day").rate.values.astype(float)
        v, cost, rev = npv(y, t_inj, ts, cn)
        rows.append({"case": case, "cn": cn, "ts": ts, "npv_1e4": v / 1e4,
                     "cost_1e4": cost / 1e4, "rev_1e4": rev / 1e4})
    t = pd.DataFrame(rows)
    best = t.loc[t.groupby(["case", "cn"]).npv_1e4.idxmax()]
    rep["npv_opt_ts"] = {f"{r.case}|cn{r.cn}": {"ts": int(r.ts), "npv_1e4": round(r.npv_1e4, 1)}
                         for r in best.itertuples()}
    # 每场景（三个浓度取最优）的最佳 ts
    b2 = t.loc[t.groupby("case").npv_1e4.idxmax()]
    rep["npv_opt_per_case"] = {r.case: {"ts": int(r.ts), "cn": float(r.cn), "npv_1e4": round(r.npv_1e4, 1)}
                               for r in b2.itertuples()}

    # ---- 数据驱动 vs 机理：单调性检查（产量是否随 ts 单调增）----
    mono = {}
    for (case, cn), sub in t.groupby(["case", "cn"]):
        s = sub.sort_values("ts")
        mono[f"{case}|cn{cn}"] = bool(np.all(np.diff(s.npv_1e4.values) > 0))
    rep["npv_monotone_in_ts"] = mono

    # ---- 浓度效应：同一 case、同一 ts 下 cum 与 cn 的关系 ----
    pivot = tot.pivot_table(index=["case", "ts"], columns="cn", values="cum")
    rep["cum_pivot_head"] = {str(k): {str(cc): float(v) for cc, v in row.items()}
                             for k, row in pivot.head(6).round(2).to_dict("index").items()}

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(rep, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n=== 复核结果 ===")
    for k in ["cum_eq_cumsum_all_exact", "cum_eq_cumsum_max_abs_dev", "groups",
              "group_len_min_max", "noise_rel_sigma_median", "noise_rel_sigma_p10_p90",
              "npv_opt_per_case", "npv_monotone_in_ts"]:
        print(k, "=", rep[k])
    print("\n每 (场景,浓度) 最优 ts:", rep["npv_opt_ts"])

if __name__ == "__main__":
    main()