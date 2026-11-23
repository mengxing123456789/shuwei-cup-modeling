
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""P3 adaptive: calibrated duration distribution + online alpha/beta + information value.

Information levels (identical scheduler otherwise):
  point_est   : frozen point prediction (compliant)
  point_deb   : same, de-biased by the train-split mean residual (compliant)
  family_dist : train-split family empirical duration distribution (compliant)
  family_pc   : family prior re-weighted by kernel distance on the frozen point
                prediction (prefix-conditioned; selection on validation only)
  unit_resid  : point prediction + train family/prefix residual quantiles (compliant)
  oracle_d    : true d. DIAGNOSTIC ONLY -- violates information_rule; upper bound.

Protocol (corrected): p = alpha*d + beta, C = s + p, next availability = s + max(p,b),
reservation not refunded. Reservation is capped at max(0.2, due-s): a buffer above the
job's own deadline cannot turn lateness into on-time, only delay the next job.

alpha/beta: 'fixed' (information experiment holds the nominal mapping), 'exact'
(two completed jobs with distinct d), or 'bayes' (posterior over the five published
sensitivity mappings in common_conditions.json, updated on each completed job).
"""
import json, math, os, random, time
import numpy as np
import pandas as pd
from common import DATA, load_tasks, load_conditions, load_index, load_zones, write_json
import p3_schedule as old
import p3_stochastic_schedule as st

SEEDS = list(range(2026111700, 2026111730))
PREFIX = [0.2, 0.6, 1.0]
SCEN_Q = np.linspace(0.05, 0.95, 19)
QSEL = np.arange(0.1, 0.91, 0.1)
TASKS, COND, INDEX = st.TASKS, st.COND, st.INDEX
PRED = st.PRED
PREDI = st.PREDI

TR = PRED[PRED.split == "train"].copy()
BIAS = {p: float((TR[TR.prefix == p].pred - TR[TR.prefix == p].duration).mean()) for p in PREFIX}
TRP = {p: TR[TR.prefix == p] for p in PREFIX}
FAM_DUR = {f: np.sort(TR[TR.family == f].duration.values) for f in ("A", "L", "P")}
FAMQ = {f: np.quantile(FAM_DUR[f], SCEN_Q) for f in FAM_DUR}
FP = {}
for f in ("A", "L", "P"):
    for p in PREFIX:
        g = TRP[p][TRP[p].family == f]
        if len(g) < 8:
            g = TRP[p]
        order = np.argsort(g.duration.values)
        durs = g.duration.values[order].astype(float)
        prs = g.pred.values[order].astype(float)
        sd = float(np.std(prs)); n = len(prs)
        FP[(f, p)] = (durs, prs, max(0.7, 1.06 * sd * n ** (-0.2)))
RESID = {}
for p in PREFIX:
    for f in ("A", "L", "P"):
        a = np.sort(TRP[p][TRP[p].family == f].eval("duration - pred").values)
        RESID[(p, f)] = a if len(a) >= 8 else np.sort(TRP[p].eval("duration - pred").values)


def wquant(durs, prs, h, pred_cur, qs):
    w = np.exp(-0.5 * ((pred_cur - prs) / h) ** 2)
    c = np.cumsum(w); c /= c[-1]
    return np.interp(qs, c, durs)


def resid_quantiles(uid, prefix, family, qs):
    return float(PREDI.loc[(uid, prefix), "pred"]) + np.quantile(RESID[(prefix, family)], qs)


# The deployment table already carries train-frozen residual quantiles
# (family shrunk to prefix-global, n/(n+20)): q10..q90 on the duration scale.
QCOLS = [(.1, "q10"), (.25, "q25"), (.5, "q50"), (.6, "q60"),
         (.75, "q75"), (.8, "q80"), (.9, "q90")]
QCACHE = {}
for r in PRED.itertuples():
    QCACHE[(r.unit_id, r.prefix)] = np.array([getattr(r, c) for _, c in QCOLS], float)


def d_quantiles(uid, prefix, family, info):
    if info == "oracle":
        return None
    pr = float(PREDI.loc[(uid, prefix), "pred"])
    if info in ("point_est", "point_deb"):
        v = pr - (BIAS[prefix] if info == "point_deb" else 0.0)
        return np.full(len(SCEN_Q), max(0.5, v))
    if info == "family_dist":
        return FAMQ[family]
    if info == "unit_resid":
        return resid_quantiles(uid, prefix, family, SCEN_Q)
    if info in ("model_quant", "model_quant_deb"):
        v = QCACHE[(uid, prefix)]
        if info == "model_quant_deb":
            v = v - BIAS[prefix]
        return np.interp(SCEN_Q, np.array([q for q, _ in QCOLS]), v)
    d, prs, h = FP[(family, prefix)]
    return wquant(d, prs, h, pr, SCEN_Q)


def pinball(y, qs, qv):
    return float(np.mean([max(q * (y - v), (q - 1) * (y - v)) for q, v in zip(qs, qv)]))


# ---- validation selection between compliant distributions, then frozen
va = PRED[PRED.split == "validation"]
loss = {}
for info in ("family_dist", "family_pc", "unit_resid", "model_quant", "model_quant_deb"):
    loss[info] = float(np.mean([pinball(r.duration, QSEL,
                                        np.quantile(d_quantiles(r.unit_id, r.prefix, r.family, info), QSEL))
                                for r in va.itertuples()]))
CAL_INFO = min(loss, key=loss.get)
test_diag = {}
for info in ("point_est", "point_deb", "family_dist", "family_pc", "unit_resid",
             "model_quant", "model_quant_deb"):
    g = PRED[PRED.split == "test"]; vals, mae = [], []
    for r in g.itertuples():
        qv = d_quantiles(r.unit_id, r.prefix, r.family, info)
        vals.append(pinball(r.duration, QSEL, np.quantile(qv, QSEL)))
        mae.append(abs(float(np.median(qv)) - r.duration))
    test_diag[info] = dict(pinball=float(np.mean(vals)), median_mae=float(np.mean(mae)))
val_diag = {}
for info in test_diag:
    g = PRED[PRED.split == "validation"]; vals, mae = [], []
    for r in g.itertuples():
        qv = d_quantiles(r.unit_id, r.prefix, r.family, info)
        vals.append(pinball(r.duration, QSEL, np.quantile(qv, QSEL)))
        mae.append(abs(float(np.median(qv)) - r.duration))
    val_diag[info] = dict(pinball=float(np.mean(vals)), median_mae=float(np.mean(mae)))

MAPS = [(1.0, 0.5), (0.75, 0.5), (1.5, 0.5), (1.0, 0.0), (1.0, 1.0)]


class Job:
    def __init__(self, row, unit):
        self.jid = row.job_id; self.family = row.family_id
        self.release = float(row.release_s); self.due = float(row.due_s)
        self.w = float(row.priority_weight); self.zone = row.zone_id
        self.preds = [] if pd.isna(row.predecessors) else str(row.predecessors).split("|")
        self.unit = unit.unit_id; self.d = float(unit.duration_s)
        self.prefix = 0.2; self.reviews = 0; self.started = False; self.done = False
        self.dropped = False; self.C = None; self.on_time = False
        self.overrun = 0.; self.idle = 0.; self.b = 0.


def simulate(case, seed, info, alpha=1.0, beta=0.5, reviews=False, alpha_mode="fixed",
             cap=False, tail_guard=False, pressure_pred=False):
    conf = [c for c in COND["cases"] if c["case_id"] == case][0]
    H = float(conf["horizon_s"]); B = float(conf["cost_budget"]); K = int(conf["observation_limit"])
    rng = random.Random(seed)
    jobs = [Job(r, st.sample_unit(r.family_id, rng))
            for _, r in TASKS[TASKS.case_id == case].sort_values("job_id").iterrows()]
    if alpha_mode == "bayes":
        A = [float(a) for a, _ in MAPS]; Bb = [float(b) for _, b in MAPS]
        W = [1.0 / len(MAPS)] * len(MAPS)
    else:
        A = [float(alpha)]; Bb = [float(beta)]; W = [1.0]
    t = 0.; zone = "Z0"; cost = 0.; nrev = 0; done = set(); log = []
    sol = []; n_comp = 0; ident = 0; pin_jobs = None
    while t < H - 1e-9 and len(log) < 200:
        if alpha_mode == "exact" and len(sol) >= 2:
            cand = [(d2, p2) for d2, p2 in sol[1:] if abs(d2 - sol[0][0]) > 1e-9]
            if cand:
                a1 = (cand[0][1] - sol[0][1]) / (cand[0][0] - sol[0][0])
                b1 = sol[0][1] - a1 * sol[0][0]
                if 0.05 < a1 < 20:
                    A, Bb, W = [a1], [b1], [1.0]
                    if ident == 0:
                        ident = n_comp
        elif alpha_mode == "bayes" and sol:
            w = np.array([np.prod([1.0 if abs(p - (ai * d + bi)) < 1e-6 else 0.0
                                   for d, p in sol]) for ai, bi in MAPS])
            if w.sum() <= 0:
                w = np.ones(len(MAPS))
            W = list(w / w.sum())
            if pin_jobs is None and max(W) >= 0.999:
                pin_jobs = n_comp
        feasible = [j for j in jobs if not j.started and j.release <= t + 1e-9
                    and all(p in done for p in j.preds)]
        acts = []
        rem = 0.
        for x in jobs:
            if x.started:
                continue
            if pressure_pred:
                md = float(PREDI.loc[(x.unit, x.prefix), "pred"])
            else:
                md = x.d if info == "oracle" else float(np.median(d_quantiles(x.unit, x.prefix, x.family, info)))
            rem += sum(wi * (ai * md + bi) for ai, bi, wi in zip(A, Bb, W)) + 1.0
        pressure = rem / max(H - t, 1e-6)
        qlev = float(np.clip(.70 - .55 * max(0., pressure - .75), .35, .70))
        for j in feasible:
            dq = np.array([j.d]) if info == "oracle" else d_quantiles(j.unit, j.prefix, j.family, info)
            ph = sum(wi * (ai * float(np.median(dq)) + bi) for ai, bi, wi in zip(A, Bb, W))
            D = st.dist(zone, j.zone); s = t + D + .5
            b = max(.2, sum(wi * (ai * float(np.quantile(dq, qlev)) + bi)
                            for ai, bi, wi in zip(A, Bb, W)))
            if cap:
                b = min(b, max(.2, j.due - s))      # dominated buffer above own deadline
            c = 2 + .1 * b + .2 * D
            if tail_guard:
                q90p = sum(wi * (ai * float(np.quantile(dq, .9)) + bi) for ai, bi, wi in zip(A, Bb, W))
                if s + q90p > H + 1e-9:
                    continue
            if s + b <= H + 1e-9 and cost + c <= B + 1e-9:
                acts.append(dict(j=j, dq=dq, ph=ph, D=D, s=s, b=b, c=c))
        if reviews and nrev < K and cost + 1 <= B and t + 1 < H and info != "oracle":
            best = (None, 0.)
            for a in acts:
                j = a["j"]
                if j.prefix >= 1. or j.reviews >= 2:
                    continue
                nx = PREFIX[j.reviews + 1]
                d0 = a["dq"]; d1 = d_quantiles(j.unit, nx, j.family, info)
                p0 = np.mean([a["s"] + ai * dd + bi <= j.due for ai, bi in zip(A, Bb)
                              for dd in d0])
                p1 = np.mean([a["s"] + 1. + ai * dd + bi <= j.due for ai, bi in zip(A, Bb)
                              for dd in d1])
                gain = j.w * (p1 - p0) - .02
                if gain > best[1]:
                    best = (j, gain)
            if best[0] is not None:
                j = best[0]; j.prefix = PREFIX[j.reviews + 1]; j.reviews += 1
                nrev += 1; cost += 1.; t += 1.
                log.append(dict(action="review", job=j.jid, t=t, voi=best[1]))
                continue
        if not acts:
            nxt = min([j.release for j in jobs if not j.started and j.release > t + 1e-9] + [H])
            if nxt <= t + 1e-9 or nxt >= H:
                break
            t = nxt; continue

        def onprob(a):
            return float(np.mean([a["s"] + ai * dd + bi <= a["j"].due
                                  for ai, bi in zip(A, Bb) for dd in a["dq"]]))

        on = [a for a in acts if onprob(a) >= .5]
        pool = on if on else acts
        a = max(pool, key=lambda x: x["j"].w * max(.03, onprob(x)) / max(.5, x["ph"])
                * math.exp(-max(0., x["j"].due - x["s"] - x["ph"]) / 12.))
        drop = None
        if pressure > 1.05 and onprob(a) < .15:
            drop = min(acts, key=lambda x: x["j"].w * max(.03, onprob(x)) / max(.5, x["ph"]))["j"]
        if drop is not None:
            drop.started = True; drop.dropped = True
            log.append(dict(action="drop", job=drop.jid, t=t)); continue
        j = a["j"]; j.started = True
        p = alpha * j.d + beta
        C = a["s"] + p; j.C = C; j.b = a["b"]
        cost += a["c"]
        j.overrun = max(0., min(p, H - a["s"]) - a["b"])
        j.idle = max(0., a["b"] - p) if C <= H else 0.
        log.append(dict(action="execute", job=j.jid, t=t, s=a["s"], b=a["b"], p=p, C=C))
        if C > H + 1e-9:
            t = H; break
        j.done = True; j.on_time = C <= j.due + 1e-9; done.add(j.jid)
        sol.append((j.d, p)); n_comp += 1
        t = a["s"] + max(p, a["b"]); zone = j.zone
    Wt = sum(j.w for j in jobs)
    comp = sum(j.w for j in jobs if j.done and not j.dropped and j.C <= H)
    ont = sum(j.w for j in jobs if j.done and j.on_time)
    tard = sum(j.w * max(0., (j.C if j.C is not None else H) - j.due) for j in jobs)
    true_idx = MAPS.index((alpha, beta)) if (alpha, beta) in MAPS else -1
    return dict(case=case, seed=seed, info=info, alpha=alpha, beta=beta, reviews=reviews,
                weighted_completion_rate=comp / Wt, weighted_on_time_rate=ont / Wt,
                weighted_tardiness_s=tard, cost=cost, reserved_s=sum(j.b for j in jobs),
                reserved_idle_s=sum(j.idle for j in jobs),
                observed_overrun_s=sum(j.overrun for j in jobs),
                n_reviews=nrev, n_done=int(sum(j.done for j in jobs)),
                n_drop=int(sum(j.dropped for j in jobs)),
                alpha_hat=float(sum(ai * wi for ai, wi in zip(A, W))),
                beta_hat=float(sum(bi * wi for bi, wi in zip(Bb, W))),
                alpha_err=float(abs(sum(ai * wi for ai, wi in zip(A, W)) - alpha)),
                identified_at=int(ident), pinned_at=int(pin_jobs if pin_jobs is not None else -1),
                mass_true=(float(W[true_idx]) if 0 <= true_idx < len(W) else float("nan")))


def ci95(x):
    x = np.asarray(x, float)
    return 1.96 * x.std(ddof=1) / math.sqrt(len(x)) if len(x) > 1 else 0.


def agg(rows, keys):
    out = []; df = pd.DataFrame(rows)
    for k, g in df.groupby(keys):
        k = k if isinstance(k, tuple) else (k,)
        d = dict(zip(keys, k)); d["n"] = len(g)
        for m in ("weighted_on_time_rate", "weighted_completion_rate", "weighted_tardiness_s",
                  "cost", "reserved_s", "reserved_idle_s", "observed_overrun_s",
                  "n_reviews", "n_done", "n_drop", "alpha_err", "mass_true",
                  "pinned_at", "identified_at", "alpha_hat", "beta_hat"):
            d[m] = float(g[m].mean()); d[m + "_ci95"] = float(ci95(g[m]))
        out.append(d)
    return out


def main():
    t0 = time.time()
    # ---------------- A: information levels at the nominal mapping (alpha held fixed)
    rowsA = []
    for case in ("S1", "S2", "S3"):
        for info in ("point_est", "point_deb", "family_dist", "family_pc", "unit_resid",
                     "model_quant", "model_quant_deb", "oracle"):
            for seed in SEEDS:
                rowsA.append(simulate(case, seed, info, alpha_mode="fixed"))
    aggA = agg(rowsA, ["case", "info"])
    base = json.load(open(os.path.join(DATA, "p3_stochastic_schedule.json"), encoding="utf-8"))
    slack = {r["case"]: r["weighted_on_time_rate"] for r in base["summary"] if r["policy"] == "slack_old"}
    risk = {r["case"]: r["weighted_on_time_rate"] for r in base["summary"] if r["policy"] == "risk_fusion"}
    ub = {}
    for case in ("S1", "S2", "S3"):
        e = {r["info"]: r["weighted_on_time_rate"] for r in aggA if r["case"] == case}
        ub[case] = dict(point_est=e["point_est"], point_deb=e["point_deb"],
                        family_dist=e["family_dist"], family_pc=e["family_pc"],
                        unit_resid=e["unit_resid"], model_quant=e["model_quant"],
                        model_quant_deb=e["model_quant_deb"],
                        calibrated=e[CAL_INFO], oracle=e["oracle"],
                        slack_old=slack[case], risk_fusion=risk[case],
                        oracle_minus_family=e["oracle"] - e["family_dist"],
                        oracle_minus_calibrated=e["oracle"] - e[CAL_INFO],
                        oracle_minus_slack=e["oracle"] - slack[case],
                        oracle_minus_point=e["oracle"] - e["point_est"],
                        oracle_minus_model=e["oracle"] - e["model_quant"],
                        calibrated_minus_point=e[CAL_INFO] - e["point_est"],
                        calibrated_minus_model=e[CAL_INFO] - e["model_quant"],
                        model_minus_point=e["model_quant"] - e["point_est"],
                        family_minus_point=e["family_dist"] - e["point_est"],
                        calibrated_minus_slack=e[CAL_INFO] - slack[case])
    # ---------------- B: cross-mapping regret of the final policy (bayes alpha)
    rowsB = []
    for alpha, beta in old.MAPPINGS:
        for case in ("S1", "S2", "S3"):
            for seed in SEEDS:
                rowsB.append(simulate(case, seed, CAL_INFO, alpha, beta, alpha_mode="bayes"))
    aggB = agg(rowsB, ["case", "alpha", "beta"])
    basemap = base["mapping_sensitivity"]
    reg = []
    for alpha, beta in old.MAPPINGS:
        for case in ("S1", "S2", "S3"):
            mine = [r for r in aggB if r["case"] == case and r["alpha"] == alpha and r["beta"] == beta][0]
            cand = {r["policy"]: r["eta"] for r in basemap
                    if r["case"] == case and r["alpha"] == alpha and r["beta"] == beta}
            bp = max(cand, key=cand.get)
            reg.append(dict(alpha=alpha, beta=beta, case=case, mine=mine["weighted_on_time_rate"],
                            best_policy=bp, best=cand[bp], risk_fusion=cand["risk_fusion"],
                            slack_old=cand["slack_old"],
                            regret=cand[bp] - mine["weighted_on_time_rate"],
                            cost=mine["cost"], reserved_s=mine["reserved_s"],
                            mass_true=mine["mass_true"]))
    # ---------------- C: review sign test under the corrected protocol (bayes alpha)
    mappingsC = [(1.0, 0.5), (0.75, 0.5), (1.5, 0.5)]
    rowsC = []
    for alpha, beta in mappingsC:
        for case in ("S1", "S2", "S3"):
            for seed in SEEDS:
                rowsC.append(simulate(case, seed, CAL_INFO, alpha, beta, reviews=True, alpha_mode="bayes"))
    dfC = pd.DataFrame(rowsC); dfB = pd.DataFrame(rowsB)
    rev = []
    for alpha, beta in mappingsC:
        pv = dfC[(dfC.alpha == alpha) & (dfC.beta == beta)].pivot(
            index="seed", columns="case", values="weighted_on_time_rate")
        for case in ("S1", "S2", "S3"):
            m = dfB[(dfB.alpha == alpha) & (dfB.beta == beta) & (dfB.case == case)
                    ].set_index("seed").weighted_on_time_rate
            d = pv[case] - m
            rev.append(dict(alpha=alpha, beta=beta, case=case, mean_diff=float(d.mean()),
                            min_diff=float(d.min()), n_neg=int((d < -1e-9).sum()), n=len(d),
                            review_rate=float(dfC[(dfC.alpha == alpha) & (dfC.case == case)].n_reviews.mean())))
    # ---------------- gates
    cell = {(r["alpha"], r["beta"], r["case"]): r["mine"] for r in reg}
    gates = {}
    gates["upper_bound_number"] = {c: ub[c]["oracle_minus_family"] for c in ub}
    gates["calibrated_vs_point_nominal"] = {c: dict(cal=ub[c]["calibrated"], point=ub[c]["point_est"],
                                                    diff=ub[c]["calibrated_minus_point"],
                                                    pass_=bool(ub[c]["calibrated"] >= ub[c]["point_est"] - 1e-9))
                                            for c in ub}
    gates["calibrated_vs_model_nominal"] = {c: dict(cal=ub[c]["calibrated"], model_quant=ub[c]["model_quant"],
                                                    diff=ub[c]["calibrated_minus_model"],
                                                    pass_=bool(ub[c]["calibrated"] >= ub[c]["model_quant"] - 1e-9))
                                            for c in ub}
    gates["calibrated_vs_slack_nominal"] = {c: dict(cal=ub[c]["calibrated"], slack=ub[c]["slack_old"],
                                                    diff=ub[c]["calibrated_minus_slack"],
                                                    pass_=bool(ub[c]["calibrated"] >= ub[c]["slack_old"] - 1e-9))
                                            for c in ub}
    rmax = max(r["regret"] for r in reg)
    rm = {str(k): float(np.mean([r["regret"] for r in reg if (r["alpha"], r["beta"]) == k]))
          for k in old.MAPPINGS}
    mine_mean = float(np.mean(list(cell.values())))
    risk_mean = float(np.mean([r["risk_fusion"] for r in reg]))
    gates["regret"] = dict(max=rmax, mean_by_mapping=rm,
                           overall_mean=float(np.mean([r["regret"] for r in reg])),
                           max_ok=bool(rmax <= 0.02),
                           mean_vs_risk=dict(mine=mine_mean, risk_fusion=risk_mean,
                                             pass_=bool(mine_mean >= risk_mean)),
                           per_cell=reg)
    gates["review_sign"] = dict(
        s2_negative=int(sum(r["n_neg"] for r in rev if r["case"] == "S2")),
        s3_negative=int(sum(r["n_neg"] for r in rev if r["case"] == "S3")),
        s2_mean=float(np.mean([r["mean_diff"] for r in rev if r["case"] == "S2"])),
        s3_mean=float(np.mean([r["mean_diff"] for r in rev if r["case"] == "S3"])),
        detail=rev)
    gates["alpha_identification"] = dict(
        mean_alpha_err=float(np.mean([r["alpha_err"] for r in aggB])),
        max_alpha_err=float(np.max([r["alpha_err"] for r in aggB])),
        mean_pinned_at=float(np.mean([r["pinned_at"] for r in aggB if r["pinned_at"] > 0])),
        mean_mass_true=float(np.mean([r["mass_true"] for r in aggB])))
    out = dict(_meta=dict(
        protocol="corrected actual p=alpha*d+beta; C=s+p; availability=s+max(p,b); reservation not refunded",
        reservation="b=max(.2, mixture quantile at qlevel); no own-deadline cap (ablation: capping lowers on-time in 6/6 stress cells)",
        seeds=SEEDS,
        info_levels="point_est / point_deb / model_quant / model_quant_deb / family_dist / family_pc / unit_resid / oracle_d(diagnostic only)",
        note="oracle_d violates information_rule; diagnostic upper bound, not used in any model selection",
        info_experiment="alpha held at the nominal mapping, so only d-information varies",
        online_alpha="bayes posterior over the five published mappings, updated on completed (d,p); exact solve is the fallback",
        debias=f"train mean pred-duration by prefix { {str(k): round(v,4) for k,v in BIAS.items()} } (negative = point estimate short)",
        calibrated_info=CAL_INFO, validation_pinball=loss, test_duration_diag=test_diag,
        validation_duration_diag=val_diag,
        baselines_source="data/p3_stochastic_schedule.json summary and mapping_sensitivity (same 30 seeds/sampling)"),
        info_levels=aggA, upper_bound=ub, final_policy=aggB, regret=reg, gates=gates,
        seconds=time.time() - t0)
    write_json("p3_adaptive.json", out)
    print(json.dumps(dict(ub=ub, gates={k: v for k, v in gates.items() if k != "regret"},
                          regret=dict(max=rmax, by_map=rm, overall=gates["regret"]["overall_mean"],
                                      vs_risk=gates["regret"]["mean_vs_risk"]),
                          cal=CAL_INFO, val_pinball=loss, test=test_diag, bias=BIAS),
                     ensure_ascii=False, indent=1))
    print("seconds", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()