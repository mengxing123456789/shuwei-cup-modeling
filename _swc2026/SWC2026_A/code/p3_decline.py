# -*- coding: utf-8 -*-
"""
Problem 4 的数据驱动部分：附件 C 上的产能模型比较与参数估计。

候选模型（全部按"场景×浓度×浸泡"整组拟合/整组划分，绝不切同一组内的相邻生产日）：
  M1 Arps 双曲（qi, Di, b）        逐组 3 参数
  M2 Arps 指数（qi, Di）            逐组 2 参数
  M3 拉伸指数（qi, tau, n）         逐组 3 参数
  M4 分层指数：Di 按场景共享、qi 逐组
  M5 分层+参数化：Di 按场景共享，qi = A(ts, Cn) 显式饱和律
选择：BIC（主）+ 按浸泡档整组留出的 5 折交叉验证（次）。
"""
import os
import sys
import itertools
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mm_common as MC

OUT = {}


def _fit(fun, t, q, p0, bounds):
    try:
        popt, pcov = curve_fit(fun, t, q, p0=p0, bounds=bounds, maxfev=20000)
        return popt, pcov
    except Exception:
        return None, None


def fit_group(t, q):
    """逐组四类拟合，返回 dict。"""
    res = {}
    # M2 exponential
    p, c = _fit(MC.arps_exp, t, q, [q[0], 0.03], ([0, 1e-4], [np.inf, 1.0]))
    res['exp'] = (p, c)
    # M1 hyperbolic
    p, c = _fit(MC.arps_hyp, t, q, [q[0], 0.03, 0.5],
                ([0, 1e-4, 1e-3], [np.inf, 1.0, 2.0]))
    res['hyp'] = (p, c)
    # M3 stretched exponential
    p, c = _fit(MC.arps_stretch, t, q, [q[0], 40.0, 0.8],
                ([0, 1.0, 0.2], [np.inf, 1e4, 3.0]))
    res['stretch'] = (p, c)
    return res


def rss_of(fun, p, t, q):
    r = q - fun(t, *p)
    return float(np.sum(r * r))


def main():
    df = MC.load_production()
    t_all = np.arange(1, 361, dtype=float)
    n_obs = len(df)

    # ---------------- per-group fits
    rows = []
    for gid, d in df.groupby('gid'):
        d = d.sort_values('day')
        case, cn, ts = gid.split('|')
        t = d.day.values.astype(float)
        q = d.q.values
        f = fit_group(t, q)
        e = {}
        for k, npar in [('exp', 2), ('hyp', 3), ('stretch', 3)]:
            p, c = f[k]
            if p is None:
                e[k] = dict(ok=False)
                continue
            pred = {'exp': MC.arps_exp, 'hyp': MC.arps_hyp,
                    'stretch': MC.arps_stretch}[k](t, *p)
            sse = float(np.sum((q - pred) ** 2))
            e[k] = dict(ok=True, p=[float(v) for v in p], sse=sse, npar=npar,
                        bic=float(n_obs and (n_obs * np.log(sse / len(t)) + npar * np.log(len(t)))))
        rows.append(dict(gid=gid, case=case, cn=float(cn), ts=int(ts), **e))
    R = pd.DataFrame(rows)

    # ---------------- case-level shared D (M4)
    pooled = {}
    for case, s in R.groupby('case'):
        # pooled log-linear slope on all groups, 40..330 d (avoid end effects)
        d = df[df.Case == case]
        # robust: median of per-group log-linear slopes
        slopes = []
        for gid, dd in d.groupby('gid'):
            dd = dd.sort_values('day')
            mm = (dd.day >= 40) & (dd.day <= 330) & (dd.q > 0.05)
            if mm.sum() > 20:
                slopes.append(-MC.ols_slope(dd.day[mm].values, np.log(dd.q[mm].values))[0])
        D = float(np.median(slopes))
        pooled[case] = dict(D=D, D_sd=float(np.std(slopes, ddof=1)),
                            D_cv=float(np.std(slopes, ddof=1) / np.mean(slopes)))

    # ---------------- M4 fit quality (shared D, per-group qi)
    m4 = {'sse': 0.0, 'n': 0}
    for _, r in R.iterrows():
        d = df[df.gid == r.gid].sort_values('day')
        q = d.q.values
        D = pooled[r.case]['D']
        # qi = argmin ||q - qi e^{-Dt}||, closed form
        e = np.exp(-D * d.day.values)
        qi = float(np.dot(q, e) / np.dot(e, e))
        m4['sse'] += float(np.sum((q - qi * e) ** 2))
        m4['n'] += len(q)

    # ---------------- M5: qi = A_inf (1-exp(-(ts/tau)^p)) (1+a (Cn-1))
    def A_of(ts, cn, Ainf, tau, pw, a):
        return Ainf * (1.0 - np.exp(-np.power(ts / tau, pw))) * (1.0 + a * (cn - 1.0))

    m5 = {}
    for case in MC.CASE_KEYS:
        s = R[R.case == case]
        D = pooled[case]['D']
        E = np.array([np.exp(-D * np.arange(1, 361)).sum() for _ in s.iterrows()])
        # A_g = EUR_g / sum(exp) ; fit A_g(ts,cn)
        Ag = s.apply(lambda r: float(df[df.gid == r.gid].q.sum()) / E[0], axis=1).values
        ts = s.ts.values.astype(float)
        cn = s.cn.values.astype(float)

        def f(p):
            return A_of(ts, cn, *p) - Ag

        from scipy.optimize import least_squares
        best = None
        for p0 in ([Ag.max(), 15.0, 0.5, 0.1], [Ag.max(), 30.0, 0.4, 0.1],
                   [Ag.max() * 0.8, 8.0, 0.7, 0.2]):
            sol = least_squares(f, p0, bounds=([0, 1, 0.05, -2], [1e4, 500, 3, 2]))
            if best is None or sol.cost < best.cost:
                best = sol
        p = best.x
        pred = A_of(ts, cn, *p) * E[0]
        obs = Ag * E[0]
        sse = float(np.sum((obs - pred) ** 2))
        sst = float(np.sum((obs - obs.mean()) ** 2))
        m5[case] = dict(Ainf=float(p[0]), tau=float(p[1]), p=float(p[2]), a=float(p[3]),
                        sse=sse, r2=float(1 - sse / sst), npar=4,
                        rmse=float(np.sqrt(sse / len(obs))),
                        rel_rmse=float(np.sqrt(sse / len(obs)) / obs.mean()))

    # ---------------- CV: leave 3 soak levels out (整组留出)
    levels = sorted(df.ts.unique())
    folds = [levels[i::3] for i in range(3)]  # 3 folds x 4 levels held out
    cv = []
    for fi, hold in enumerate(folds + [levels[:6], levels[6:]]):
        tr = ~df.ts.isin(hold)
        te = df.ts.isin(hold)
        errs = {'M2_train': [], 'M4': [], 'M5': []}
        # M2（逐组自由双参数指数）：只能在自己的训练组上打分。
        # 被留出的整档浸泡时长没有对应组的参数可估 → 测试档上是 NA，不是 0 也不是差分数。
        for gid in df[tr].gid.unique():
            d = df[(df.gid == gid) & tr].sort_values('day')
            if len(d) < 30:
                continue
            p, _ = _fit(MC.arps_exp, d.day.values.astype(float), d.q.values,
                        [d.q.values[0], 0.03], ([0, 1e-4], [np.inf, 1.0]))
            if p is None:
                continue
            errs['M2_train'].append(d.q.values - MC.arps_exp(d.day.values.astype(float), *p))
        # M4/M5: shared D and A(ts,cn) from training only
        for case in MC.CASE_KEYS:
            dtr = df[(df.Case == case) & tr]
            slopes = []
            for gid, dd in dtr.groupby('gid'):
                dd = dd.sort_values('day')
                mm = (dd.day >= 40) & (dd.day <= 330) & (dd.q > 0.05)
                if mm.sum() > 20:
                    slopes.append(-MC.ols_slope(dd.day[mm].values, np.log(dd.q[mm].values))[0])
            D = float(np.median(slopes))
            s = dtr.groupby('gid').agg({'Cn': 'first', 'ts': 'first'})
            s['cn'] = s.Cn.astype(float)
            Esum = np.exp(-D * np.arange(1, 361)).sum()
            Ag = []
            for gid in s.index:
                Ag.append(df[df.gid == gid].q.sum() / Esum)
            Ag = np.array(Ag)
            ts_ = s.ts.values.astype(float)
            cn_ = s.cn.values.astype(float)
            # M4: A_g interpolated on ts grid via monotone piecewise-linear in sqrt(ts)
            dd_te = df[(df.Case == case) & te]
            for gid, dd in dd_te.groupby('gid'):
                tsq = float(dd.ts.iloc[0])
                order = np.argsort(ts_)
                Ahat = float(np.interp(np.sqrt(tsq), np.sqrt(ts_[order]),
                                       Ag[order] * (1 + 0.0)))
                errs['M4'].append(dd.q.values - Ahat * np.exp(-D * dd.day.values))
            # M5
            from scipy.optimize import least_squares as LS
            def f5(p):
                return A_of(ts_, cn_, *p) - Ag
            sol = LS(f5, [Ag.max(), 20.0, 0.5, 0.1],
                     bounds=([0, 1, 0.05, -2], [1e4, 500, 3, 2]))
            for gid, dd in dd_te.groupby('gid'):
                tsq = float(dd.ts.iloc[0])
                cnq = float(dd.Cn.iloc[0])
                Ahat = float(A_of(np.array([tsq]), np.array([cnq]), *sol.x)[0])
                errs['M5'].append(dd.q.values - Ahat * np.exp(-D * dd.day.values))
        row = dict(fold=fi, held_out_ts=[int(v) for v in hold],
                   M2_test='NA（逐组模型对未训练的浸泡档没有可估参数，不做外推打分）')
        for k, v in errs.items():
            if v:
                e = np.concatenate(v)
                row[k + '_rmse'] = float(np.sqrt(np.mean(e ** 2)))
                row[k + '_n'] = int(len(e))
        cv.append(row)

    # ---------------- 划分合规性审计（题面 Attachment C 使用规则 1–2 的硬要求）
    audit = []
    for fi, hold in enumerate(folds + [levels[:6], levels[6:]]):
        trm = ~df.ts.isin(hold)
        tem = df.ts.isin(hold)
        tr_ts = sorted({int(v) for v in df.ts[trm].unique()})
        te_ts = sorted({int(v) for v in df.ts[tem].unique()})
        test_groups = sorted({(r.Case, round(float(r.Cn), 1), int(r.ts))
                              for r in df[tem].itertuples()})
        train_groups = {(r.Case, round(float(r.Cn), 1), int(r.ts))
                        for r in df[trm].itertuples()}
        # 1) 每个 (场景,浓度,浸泡) 组是否整组只落在一个 split 里
        whole = True
        for case in MC.CASE_KEYS:
            for cn in (0.5, 1.0, 1.5):
                for tsq in levels:
                    g = df[(df.Case == case) & (df.Cn == cn) & (df.ts == tsq)]
                    n_tr = int(trm[g.index].sum())
                    whole = whole and (n_tr == 0 or n_tr == len(g))
        # 2) 测试集至少含一个训练里没出现过的浸泡档
        unseen = sorted(set(te_ts) - set(tr_ts))
        audit.append(dict(
            fold=fi, held_out_ts=[int(v) for v in hold],
            n_train_rows=int(trm.sum()), n_test_rows=int(tem.sum()),
            n_train_groups=len(train_groups), n_test_groups=len(test_groups),
            train_ts_levels=tr_ts, test_ts_levels=te_ts,
            test_ts_not_in_train=unseen,
            test_groups=[[c, float(cn), int(tsq)] for (c, cn, tsq) in test_groups],
            PASS_group_whole=bool(whole),
            PASS_test_has_unseen_ts=len(unseen) > 0,
            FAIL_note=('' if whole and len(unseen) > 0 else
                       '整组划分/未训练档位之一不满足，该 fold 的 CV 数不可用于外推口径')))

    # ---------------- bootstrap on 9 representative groups (Cn=1.0, ts=30)
    rng = np.random.default_rng(20261120)
    boot = {}
    for case in MC.CASE_KEYS:
        d = df[(df.Case == case) & (df.Cn == 1.0) & (df.ts == 30)].sort_values('day')
        t = d.day.values.astype(float)
        q = d.q.values
        p_hat = R[(R.case == case) & (R.cn == 1.0) & (R.ts == 30)].iloc[0]
        qi0, D0 = p_hat['exp']['p']
        res = q - MC.arps_exp(t, qi0, D0)
        B = 400
        qs, Ds, Es = [], [], []
        idx = np.arange(len(t))
        for b in range(B):
            i = rng.choice(idx, size=len(idx), replace=True)
            qb = MC.arps_exp(t, qi0, D0) + res[i]
            p, _ = _fit(MC.arps_exp, t, qb, [qi0, D0], ([0, 1e-4], [np.inf, 1.0]))
            if p is None:
                continue
            qs.append(p[0]); Ds.append(p[1])
            Es.append(p[0] * (1 - np.exp(-p[1] * 360)) / p[1])
        boot[case] = dict(qi=[float(np.percentile(qs, 2.5)), float(np.percentile(qs, 97.5))],
                          D=[float(np.percentile(Ds, 2.5)), float(np.percentile(Ds, 97.5))],
                          EUR=[float(np.percentile(Es, 2.5)), float(np.percentile(Es, 97.5))],
                          n_boot=int(B), seed=20261120)

    # ---------------- export tables
    tab = []
    for _, r in R.iterrows():
        case, cn, ts = r.gid.split('|')
        d = df[df.gid == r.gid].sort_values('day')
        q = d.q.values
        D = pooled[case]['D']
        e = np.exp(-D * d.day.values)
        qi_sh = float(np.dot(q, e) / np.dot(e, e))
        ex = r['exp']['p'] if r['exp']['ok'] else [np.nan, np.nan]
        hyp = r['hyp']['p'] if r['hyp']['ok'] else [np.nan, np.nan, np.nan]
        tab.append(dict(case=case, cn=float(cn), ts=int(ts),
                        EUR_data=float(q.sum()),
                        qi_shared=qi_sh, D_shared=D,
                        EUR_shared=float(qi_sh * (1 - np.exp(-D * 360)) / D),
                        qi_free=float(ex[0]), D_free=float(ex[1]),
                        b_hyp=float(hyp[2]) if len(hyp) > 2 else None,
                        EUR_free=float(ex[0] * (1 - np.exp(-ex[1] * 360)) / ex[1]),
                        rmse_free=float(np.sqrt(r['exp']['sse'] / len(q))),
                        rmse_shared=float(np.sqrt(np.mean((q - qi_sh * e) ** 2)))))

    # ---------------- information criteria over the whole dataset
    ic = {}
    sse = {'M1': 0.0, 'M2': 0.0, 'M3': 0.0, 'M4': m4['sse']}
    for _, r in R.iterrows():
        for k, key in [('hyp', 'M1'), ('exp', 'M2'), ('stretch', 'M3')]:
            if r[k]['ok']:
                sse[key] += r[k]['sse']
    kpar = {'M1': 3 * len(R), 'M2': 2 * len(R), 'M3': 3 * len(R), 'M4': len(R) + 3,
            'M5': 3 * (len(R) // 36) * 4}
    for k in ['M1', 'M2', 'M3', 'M4']:
        n = n_obs
        ic[k] = dict(sse=float(sse[k]), kpar=int(kpar[k]),
                     rmse=float(np.sqrt(sse[k] / n)),
                     aic=float(n * np.log(sse[k] / n) + 2 * kpar[k]),
                     bic=float(n * np.log(sse[k] / n) + kpar[k] * np.log(n)))
    s5 = sum(v['sse'] for v in m5.values())
    ic['M5'] = dict(sse=float(s5), kpar=int(3 * 4 + 3),
                    rmse=float(np.sqrt(s5 / n_obs)),
                    aic=float(n_obs * np.log(s5 / n_obs) + 2 * (3 * 4 + 3)),
                    bic=float(n_obs * np.log(s5 / n_obs) + (3 * 4 + 3) * np.log(n_obs)))

    OUT['model_selection'] = ic
    OUT['shared_D'] = pooled
    OUT['M5_params'] = m5
    OUT['cv'] = cv
    OUT['split_audit'] = dict(
        rule='题面：按场景×浓度×浸泡时长整组划分；禁止同组内随机切相邻生产日；测试集至少含 1 个未训练的浸泡档',
        folds=audit,
        all_pass=bool(all(a['PASS_group_whole'] and a['PASS_test_has_unseen_ts'] for a in audit)),
        M2_note='M2（逐组自由指数）没有跨档外推能力，故只在训练组上打分（M2_train_rmse），测试档记 NA')

    OUT['bootstrap'] = boot
    OUT['groups'] = tab
    OUT['n_groups'] = int(len(R))
    OUT['noise_check'] = dict(
        resid_sd_rel=float(np.std([
            (df[df.gid == g].q.values - tab[i]['qi_shared'] *
             np.exp(-tab[i]['D_shared'] * df[df.gid == g].day.values)).std() /
            df[df.gid == g].q.values.mean()
            for i, g in enumerate(df.gid.unique())])),
        note='附件C 声明 ±5% 高斯噪声；该值即逐组相对残差标准差的中位数口径见 med_rel_resid',
        med_rel_resid=float(np.median([
            (df[df.gid == g].q.values - tab[i]['qi_shared'] *
             np.exp(-tab[i]['D_shared'] * df[df.gid == g].day.values)).std() /
            df[df.gid == g].q.values.mean()
            for i, g in enumerate(df.gid.unique())])),
    )
    OUT['data_facts'] = dict(
        n_rows=int(len(df)), n_cases=int(df.Case.nunique()),
        cn_levels=sorted(float(v) for v in df.Cn.unique()),
        ts_levels=sorted(int(v) for v in df.ts.unique()),
        days=[1, 360],
    )
    MC.save_json('p3_decline', OUT, os.path.abspath(__file__), MC.input_hashes())
    print('M5', {k: {kk: round(vv, 4) for kk, vv in v.items()} for k, v in m5.items()})
    print('BIC', {k: round(v['bic'], 1) for k, v in ic.items()})
    print('CV', [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()} for r in cv])
    print('OK p3')


if __name__ == '__main__':
    main()