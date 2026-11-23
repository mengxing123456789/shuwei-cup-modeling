"""P3: restocking scheduling under duration uncertainty.

Protocol (Restocking_Tasks_and_Constraints + C_Problem3_Requirements.txt):
  one equipment unit, actions wait / review / execute, at most 200 actions.
  source units sampled from the VALIDATION split, uniformly within family, with
  replacement, Python random.Random(seed).choice in sorted job order, generator
  reinitialised per case.  Public seeds 2026111700..2026111729.
  p = alpha*d + beta, execution costs 2 + 0.1b + 0.2D, starts at t + D + 0.5,
  next availability s + max(p,b), completion s + p.
No source identifiers or prefix matching are used by any policy: only the
released numerical prefix features and a frozen duration regression.
"""

# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
import os, json, math, copy
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from scipy.stats import spearmanr

from common import DATA, FIG, ATT, load_tasks, load_zones, load_conditions, load_index, write_json

SEEDS = list(range(2026111700, 2026111730))
FEATS = ["speed_mean", "speed_std", "speed_max", "acc_mean",
         "aperture_mean", "aperture_std", "depth_mean", "depth_std"]
PREFIX = [0.2, 0.6, 1.0]
ZONES = {r.zone_id: (float(r.x), float(r.y)) for _, r in load_zones().iterrows()}
TASKS = load_tasks()
COND = load_conditions()
INDEX = pd.read_csv(os.path.join(ATT, "source_segment_index.csv"))
PREF = pd.read_csv(os.path.join(DATA, "prefix_features.csv"))


def dist(a, b):
    return math.hypot(ZONES[a][0] - ZONES[b][0], ZONES[a][1] - ZONES[b][1])


# ---------------- duration model (fit on training split only) -------------
def design(df):
    fam = pd.get_dummies(df.family).reindex(columns=["A", "L", "P"], fill_value=0).astype(float)
    return np.hstack([df[FEATS].values, fam.values, df.prefix.values[:, None]])


tr = PREF[PREF.split == "train"].copy()
sc = StandardScaler().fit(design(tr))
mdl = Ridge(alpha=3.0).fit(sc.transform(design(tr)), np.log(tr.duration.values))
tr["pred"] = np.exp(mdl.predict(sc.transform(design(tr))))
tr["resid"] = tr.duration - tr.pred
Q = tr.groupby("prefix").resid.quantile([0.5, 0.6, 0.7, 0.8, 0.9]).unstack()
va = PREF[PREF.split == "validation"].copy()
va["pred"] = np.exp(mdl.predict(sc.transform(design(va))))
dur_eval = {}
for pre in PREFIX:
    g = va[va.prefix == pre]
    dur_eval[str(pre)] = dict(n=int(len(g)), mae=float(np.abs(g.duration - g.pred).mean()),
                              rmse=float(np.sqrt(((g.duration - g.pred) ** 2).mean())),
                              spearman=float(spearmanr(g.pred, g.duration).statistic),
                              mean_baseline_mae=float(np.abs(g.duration - tr.duration.mean()).mean()))

PREF_I = PREF.set_index(["unit_id", "prefix"])
UNIT = INDEX[INDEX.eligible == 1].reset_index(drop=True)
# precompute frozen duration predictions once (pandas filtering per action was the bottleneck)
PREF["dhat"] = np.exp(mdl.predict(sc.transform(design(PREF))))
DHAT = {(r.unit_id, r.prefix): float(r.dhat) for r in PREF.itertuples()}


def sample_unit(family, rng):
    pool = UNIT[(UNIT.split == "validation") & (UNIT.family_id == family)]
    return pool.iloc[rng.randrange(len(pool))]


def pfeat(unit_id, prefix):
    return PREF_I.loc[(unit_id, prefix)]


def predict(unit_id, prefix, alpha, beta):
    dhat = DHAT[(unit_id, prefix)]
    q = Q.loc[prefix]
    return alpha * dhat + beta, alpha * float(q[0.6]), alpha * float(q[0.8])


# ---------------- simulator -------------------------------------------------
class Job:
    __slots__ = ("jid", "family", "release", "due", "w", "zone", "preds", "unit", "d",
                 "prefix", "reviews", "started", "done", "on_time", "C", "dropped", "overrun", "idle")

    def __init__(self, row, unit):
        self.jid = row.job_id; self.family = row.family_id
        self.release = row.release_s; self.due = row.due_s; self.w = row.priority_weight
        self.zone = row.zone_id
        self.preds = [] if pd.isna(row.predecessors) else str(row.predecessors).split("|")
        self.unit = unit.unit_id; self.d = float(unit.duration_s)
        self.prefix = 0.2; self.reviews = 0; self.started = False; self.done = False
        self.on_time = False; self.C = None; self.dropped = False; self.overrun = 0.0; self.idle = 0.0


# ---------------------------------------------------------------- value of information
# No constant "seconds saved by a prefix" is assumed. The empirical residual
# distribution of the training split gives it directly:
#   P(late | prefix) = P(d > due - s | residual distribution of that prefix)
# and we then measure how far one more released prefix moves that quantity.
RES = {p: np.sort(tr.loc[tr.prefix == p, "resid"].values) for p in PREFIX}


def p_late(prefix, x):
    """P(resid > x): empirical survival function, no parameters, no assumed family."""
    a = RES[prefix]
    if len(a) == 0:
        return 0.0
    return float(np.mean(a > x))


REVIEW_BAR = 0.02   # expected gain in weighted on-time probability that pays 1 cost + 1 s


def simulate(case, seed, policy, alpha=1.0, beta=0.5, review_gate=True, qbuf=0.6,
             late_tol=0.0, oracle=False, review_bar=REVIEW_BAR):
    conf = [c for c in COND["cases"] if c["case_id"] == case][0]
    H, B, K = conf["horizon_s"], conf["cost_budget"], conf["observation_limit"]
    rows = TASKS[TASKS.case_id == case].sort_values("job_id")
    rng = __import__("random").Random(seed)
    jobs = [Job(r, sample_unit(r.family_id, rng)) for _, r in rows.iterrows()]
    byid = {j.jid: j for j in jobs}
    t, zone, cost, reviews = 0.0, "Z0", 0.0, 0
    log = []
    done = set()
    while t < H - 1e-9 and len(log) < 200:
        feasible = [j for j in jobs if (not j.started) and j.release <= t + 1e-9
                    and all(p in done for p in j.preds)]
        actionable = []
        for j in feasible:
            p_hat, q60, q80 = predict(j.unit, j.prefix, alpha, beta)
            if oracle:
                p_hat, q60, q80 = alpha * j.d + beta, 0.0, 0.0
            D = dist(zone, j.zone)
            b = max(0.2, p_hat + qbuf * q60)
            s = t + D + 0.5
            if s + b <= H + 1e-9 and cost + 2 + 0.1 * b + 0.2 * D <= B + 1e-9:
                actionable.append((j, p_hat, q60, q80, D, b, s))
        # ---- paid re-observation: the criterion is endogenous to the residual distribution
        if review_gate and reviews < K and cost + 1 <= B + 1e-9 and t + 1 <= H - 1e-9:
            cand = [a for a in actionable if a[0].prefix < 1.0 and a[0].reviews < 2]
            pick, best_gain = None, -1.0
            for a in cand:
                j0 = a[0]
                pf, nx = j0.prefix, PREFIX[j0.reviews + 1]
                s0 = a[6] + 1.0                      # start time after the 1.0 s observation delay
                ph = alpha * DHAT[(j0.unit, pf)] + beta
                pn = alpha * DHAT[(j0.unit, nx)] + beta
                if s0 + max(0.2, pn) > H + 1e-9:
                    continue
                pc = p_late(pf, j0.due - s0 - ph)
                pnn = p_late(nx, j0.due - s0 - pn)
                if pc < 0.25:                        # not at risk anyway, so a look cannot help
                    continue
                gain = j0.w * (pc - pnn)
                if gain > best_gain:
                    pick, best_gain = j0, gain
            if pick is not None and best_gain >= review_bar:
                pick.prefix = PREFIX[pick.reviews + 1]; pick.reviews += 1
                cost += 1.0; reviews += 1; t += 1.0
                log.append(dict(t=t, action="review", job=pick.jid, prefix=pick.prefix,
                                voi=round(best_gain, 4), cost=cost))
                continue
        if not actionable:
            # wait to the next release, otherwise stop
            nxt = min([j.release for j in jobs if not j.started and j.release > t + 1e-9] + [H])
            if nxt <= t + 1e-9 or nxt >= H:
                break
            log.append(dict(t=t, action="wait", dt=nxt - t))
            t = nxt
            continue
        # ---- choose job
        if policy in ("slack", "voi", "oracle"):
            kap = 10.0
            ontime = [a for a in actionable if a[6] + a[1] <= a[0].due + late_tol]
            if ontime:
                j, p_hat, q60, q80, D, b, s = max(
                    ontime, key=lambda a: (a[0].w / max(0.5, a[1])) *
                    math.exp(-max(0.0, a[0].due - (a[6] + a[1])) / kap))
            else:
                # capacity relief only when the remaining workload cannot fit
                rem = sum(predict(x.unit, x.prefix, alpha, beta)[0] + 1.1
                          for x in jobs if not x.started) + dist(zone, "Z0")
                if rem > H - t + 2.0:
                    worst = max(actionable, key=lambda a: ((a[6] + a[1] - a[0].due) / max(1, a[0].w)))
                    worst[0].started = True; worst[0].dropped = True
                    log.append(dict(t=t, action="drop", job=worst[0].jid))
                    continue
                j, p_hat, q60, q80, D, b, s = min(
                    actionable, key=lambda a: ((a[6] + a[1] - a[0].due) / max(1, a[0].w)))
        else:
            if policy in ("edf", "edf_rev"):
                key = lambda a: (a[0].due, -a[0].w)
            elif policy == "now":
                key = lambda a: (-a[0].w / max(0.5, a[0].due - t), a[0].due)
            else:  # atc / voi: weight per unit predicted occupancy, discounted by lateness risk
                kap = 10.0
                key = lambda a: (-(a[0].w / max(0.5, a[1])) *
                                 math.exp(-max(0.0, a[0].due - (t + a[4] + 0.5 + a[1])) / kap), a[0].due)
            j, p_hat, q60, q80, D, b, s = sorted(actionable, key=key)[0]
            # drop jobs that cannot be on time and have low weight density (capacity relief)
            if policy in ("atc", "voi") and s + p_hat > j.due + 1.0 and j.w <= 1 and (s + p_hat - j.due) > 0.5 * p_hat:
                j.started = True; j.dropped = True  # never executed
                log.append(dict(t=t, action="drop", job=j.jid))
                continue
        c = 2 + 0.1 * b + 0.2 * D
        cost += c
        C = s + j.d
        j.started = True; j.C = C
        j.overrun = max(0.0, min(j.d, H - s) - b)
        j.idle = max(0.0, b - j.d) if C <= H else 0.0
        log.append(dict(t=t, action="execute", job=j.jid, b=b, s=s, C=C, cost=cost))
        if C > H + 1e-9:
            # censored: trial terminates at H, job unfinished
            t = H
            break
        j.done = True; j.on_time = C <= j.due + 1e-9; done.add(j.jid)
        t = s + max(j.d, b); zone = j.zone
    W = sum(j.w for j in jobs)
    comp = sum(j.w for j in jobs if j.done and not j.dropped and j.C is not None and j.C <= H)
    ontime = sum(j.w for j in jobs if j.done and j.on_time)
    tard = sum(j.w * max(0.0, (j.C if j.C is not None else H) - j.due) for j in jobs)
    over = sum(j.overrun for j in jobs)
    idle = sum(j.idle for j in jobs)
    return dict(case=case, seed=seed, policy=policy, alpha=alpha, beta=beta,
                weighted_completion_rate=comp / W, weighted_on_time_rate=ontime / W,
                weighted_tardiness_s=tard, cost=cost, reviews=reviews,
                elapsed_s=t, observed_overrun_s=over, reserved_idle_s=idle,
                censored_units=int(any(j.started and not j.done and not j.dropped for j in jobs)),
                n_done=sum(j.done for j in jobs), n_drop=sum(j.dropped for j in jobs),
                log=log)


POLICIES = ["edf", "edf_rev", "now", "slack", "voi", "oracle"]
MAPPINGS = [(1.0, 0.5), (0.75, 0.5), (1.5, 0.5), (1.0, 0.0), (1.0, 1.0)]
METRICS = ["weighted_completion_rate", "weighted_on_time_rate", "weighted_tardiness_s",
           "cost", "reviews", "elapsed_s", "observed_overrun_s", "reserved_idle_s",
           "censored_units", "n_done", "n_drop"]


def ci95(x):
    x = np.asarray(x, float)
    return 1.96 * x.std(ddof=1) / math.sqrt(len(x)) if len(x) > 1 else 0.0


if __name__ == "__main__":
    rows = []
    for case in ["S1", "S2", "S3"]:
        for alpha, beta in MAPPINGS:
            for pol in POLICIES:
                if pol == "oracle" and (alpha, beta) != (1.0, 0.5):
                    continue
                for seed in SEEDS:
                    r = simulate(case, seed, pol, alpha=alpha, beta=beta,
                                 review_gate=(pol in ("voi", "edf_rev")),
                                 late_tol=(0.5 if pol in ("slack", "voi", "oracle") else 0.0),
                                 oracle=(pol == "oracle"))
                    r.pop("log")
                    rows.append(r)
    trials = pd.DataFrame(rows)
    trials.to_csv(os.path.join(DATA, "p3_trials.csv"), index=False)

    agg = []
    for (case, alpha, beta, pol), g in trials.groupby(["case", "alpha", "beta", "policy"]):
        d = dict(case=case, alpha=alpha, beta=beta, policy=pol, n=len(g))
        for m in METRICS:
            d[m] = float(g[m].mean()); d[m + "_ci95"] = float(ci95(g[m]))
        agg.append(d)
    pd.DataFrame(agg).to_csv(os.path.join(DATA, "p3_summary.csv"), index=False)

    # paired difference vs EDF, same seeds
    paired = []
    for (case, alpha, beta), g in trials.groupby(["case", "alpha", "beta"]):
        piv = g.pivot_table(index="seed", columns="policy", values="weighted_on_time_rate")
        base = piv["edf"]
        for pol in piv.columns:
            if pol == "edf":
                continue
            diff = piv[pol] - base
            paired.append(dict(case=case, alpha=alpha, beta=beta, policy=pol,
                               mean_diff=float(diff.mean()), ci95=float(ci95(diff.values))))

    nominal = trials[(trials.alpha == 1.0) & (trials.beta == 0.5)]
    constraint = []
    for (case, pol), g in nominal.groupby(["case", "policy"]):
        constraint.append(dict(case=case, policy=pol, mean_eta=float(g.weighted_on_time_rate.mean()),
                               met=bool(g.weighted_on_time_rate.mean() >= 0.5)))

    # capacity diagnostic: nearest-neighbour route + mean service / horizon
    cap = []
    for case in ["S1", "S2", "S3"]:
        conf = [c for c in COND["cases"] if c["case_id"] == case][0]
        js = TASKS[TASKS.case_id == case].sort_values("job_id")
        units = [sample_unit(f, __import__("random").Random(1)) for f in js.family_id]
        pbar = float(np.mean([u.duration_s + 0.5 for u in units]))
        route, cur, left = 0.0, "Z0", set(js.zone_id)
        while left:
            nxt = min(left, key=lambda z: dist(cur, z))
            route += dist(cur, nxt); cur = nxt; left.remove(nxt)
        cap.append(dict(case=case, n_jobs=len(js), mean_p_s=pbar, nn_route_s=route,
                        capacity_ratio=(route + len(js) * pbar) / conf["horizon_s"],
                        horizon_s=conf["horizon_s"], budget=conf["cost_budget"]))
    # analytic capacity: train family means + MST route lower bound + 0.5 s changeover/job
    idx = load_index(); tr = idx[(idx.split == "train") & (idx.eligible)]
    fam = tr.groupby("family_id").duration_s.mean().to_dict()
    def mst(ids):
        pts = [ZONES[z] for z in ids]; n = len(pts)
        if n < 2: return 0.0
        used, dd = {0}, 0.0
        while len(used) < n:
            step = min((math.hypot(pts[i][0]-pts[j][0], pts[i][1]-pts[j][1]), j)
                       for i in used for j in range(n) if j not in used)
            dd += step[0]; used.add(step[1])
        return dd
    cap_analytic = []
    for case in ["S1", "S2", "S3"]:
        conf = [c for c in COND["cases"] if c["case_id"] == case][0]
        js = TASKS[TASKS.case_id == case]
        sp = float(sum(fam[f] for f in js.family_id))
        r = mst(list(js.zone_id)); H = float(conf["horizon_s"])
        cap_analytic.append(dict(case=case, n_jobs=len(js), sum_family_mean_p_s=round(sp, 2),
                                 mst_route_s=round(r, 2), capacity_ratio_analytic=round((sp + r + 0.5*len(js))/H, 3),
                                 horizon_s=H))

    out = dict(_meta=dict(protocol="C_Problem3_Requirements.txt; source pool=validation split, "
                          "eligible only; random.Random(seed).choice per family, sorted job order",
                          seeds=[SEEDS[0], SEEDS[-1]], n_seeds=len(SEEDS),
                          n_trials_per_policy=int(len(trials[trials.policy == "slack"])),
                          mappings=MAPPINGS, policies=POLICIES,
                          review_voi=dict(
                              method="empirical residual survival function per prefix",
                              rule="P(late|prefix)>0.25 and w*(P_late(cur)-P_late(next))>=bar, "
                                   "cost 1.0 and delay 1.0 s as specified",
                              bar=REVIEW_BAR, max_per_job=2, obs_limit={c["case_id"]: c["observation_limit"] for c in COND["cases"]}),
                          note="oracle knows true p; upper bound for the same scheduler, not deployable; oracle runs nominal mapping only (90 trials); capacity uses seed-1 nearest-neighbour route, capacity_analytic uses train family means + MST"),
               duration_model=dur_eval, residuals=Q.round(3).to_dict(),
               capacity=cap, capacity_analytic=cap_analytic, summary=agg, paired_vs_edf=paired,
               constraint_nominal=constraint)

    # review-bar sensitivity: how much expected weighted on-time gain must an observation
    # promise before it pays for its own 1 cost + 1 s
    sens_rev = []
    for bar in [0.0, 0.01, 0.02, 0.05, 0.10, 1.0]:
        for case in ["S1", "S2", "S3"]:
            g = [simulate(case, sd, "edf_rev", review_gate=True, review_bar=bar)
                 for sd in SEEDS[:10]]
            sens_rev.append(dict(case=case, review_bar=bar, n_seeds=10,
                                 eta=float(np.mean([x["weighted_on_time_rate"] for x in g])),
                                 reviews=float(np.mean([x["reviews"] for x in g])),
                                 cost=float(np.mean([x["cost"] for x in g])),
                                 idle=float(np.mean([x["reserved_idle_s"] for x in g]))))
    out["review_bar_sensitivity"] = sens_rev
    write_json("p3_scheduling.json", out)

    # figures
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.5))
    for case, g in pd.DataFrame(agg).query("alpha==1.0 and beta==0.5").groupby("case"):
        ax[0].bar(np.arange(len(g)) + {"S1": -0.25, "S2": 0, "S3": 0.25}[case], g.weighted_on_time_rate,
                  width=0.22, label=case)
    ax[0].set_xticks(np.arange(len(POLICIES))); ax[0].set_xticklabels(POLICIES, fontsize=8)
    ax[0].axhline(0.5, color="k", ls="--", lw=.8); ax[0].set_ylabel("weighted on-time rate")
    ax[0].legend(fontsize=7); ax[0].set_title("nominal mapping")
    for pol, g in pd.DataFrame(agg).query("case=='S3'").groupby("policy"):
        ax[1].plot(g.alpha.astype(str) + "/" + g.beta.astype(str), g.weighted_on_time_rate, "o-", ms=3, label=pol)
    ax[1].set_ylabel("S3 weighted on-time rate"); ax[1].tick_params(axis="x", labelsize=6)
    ax[1].legend(fontsize=6); ax[1].set_title("S3 mapping sensitivity")
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig6_p3_policy.png"), dpi=180); plt.close(fig)

    print(pd.DataFrame(agg).query("alpha==1.0 and beta==0.5")[
        ["case", "policy", "weighted_on_time_rate", "weighted_completion_rate", "cost", "reviews"]].round(3).to_string(index=False))
    print("constraint", constraint)
    print("capacity", cap)
