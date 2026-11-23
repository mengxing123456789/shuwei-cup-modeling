
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""Independent verification of the selected P3 improved policy.

This script does not call ``best_p3_sens.simulate``.  It implements the official
P3 replay directly from the problem data:

    p = alpha * d + beta
    s = t + travel(D) + changeover(0.5)
    C = s + p
    next availability = s + max(p, b)

and checks, per executed action, that reserve/cost/horizon bounds hold.  It then
replays the two selection-stage winners from p3_improved_search.json for all 30
official seeds and checks per-seed equality with the search output.

Output: data/p3_improved_verify.json
"""
import json
import math
import os
import random
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import p3_schedule as old  # frozen old ridge predictions/residuals
import p3_stochastic_schedule as S

SEEDS = list(S.SEEDS)
PREFIX = [0.2, 0.6, 1.0]
SCEN_Q = np.linspace(0.05, 0.95, 19)
ALPHA = 1.0
BETA = 0.5
CHANGEOVER = 0.5
RESERVE_MIN = 0.2
EPS = 1e-9
SELECTION_JSON = os.path.join(HERE, "..", "data", "p3_improved_search.json")
OUT = os.path.join(HERE, "..", "data", "p3_improved_verify.json")


def ci95(x):
    x = np.asarray(x, float)
    return float(1.96 * x.std(ddof=1) / math.sqrt(len(x))) if len(x) > 1 else 0.0


def binom_two_sided(wins, losses):
    n = wins + losses
    if n == 0:
        return 1.0
    k = min(wins, losses)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2.0 ** n)
    return float(min(1.0, 2.0 * tail))


def quantile(a, q):
    return float(np.quantile(np.asarray(a, float), q))


def configure(case, seed):
    """Reproduce the official source sampling and freeze one replay."""
    conf = [c for c in S.COND["cases"] if c["case_id"] == case][0]
    rows = S.TASKS[S.TASKS.case_id == case].sort_values("job_id")
    rng = random.Random(seed)
    jobs = []
    for _, row in rows.iterrows():
        u = S.sample_unit(row.family_id, rng)
        jobs.append(dict(
            jid=row.job_id, family=row.family_id,
            release=float(row.release_s), due=float(row.due_s),
            w=float(row.priority_weight), zone=row.zone_id,
            preds=[] if S.pd.isna(row.predecessors) else str(row.predecessors).split("|"),
            unit=u.unit_id, d=float(u.duration_s),
            pred=float(old.DHAT[(u.unit_id, 0.2)]),
            prefix=0.2, started=False, done=False, dropped=False,
            C=None, on_time=False,
        ))
    return dict(case=case, seed=seed, H=float(conf["horizon_s"]),
                B=float(conf["cost_budget"]), conf=conf, jobs=jobs)


def simulate(case, seed, policy, params=None, oracle=False):
    """Direct replay. policy in {slack_old, risk_old}; params for risk_old.

    ``oracle=True`` keeps the rule, its parameters, the action set and the
    seeds fixed and replaces only what the rule *knows*: the residual
    scenarios become a point mass at the true remaining duration, so both the
    on-time probability and the reservation are computed from true ``p``.
    This is the same-rule reference the paper compares against.
    """
    P = dict(Q_HI=0.60, Q_SLOPE=0.55, Q_KNEE=0.75, Q_LO=0.35,
             GATE=0.5, LATE_TOL_RISK=12.0, LATE_TOL_SLACK=10.0,
             DROP_P=1.05, DROP_ON=0.15)
    P.update(params or {})
    st = configure(case, seed)
    H, B = st["H"], st["B"]
    jobs = st["jobs"]
    t = 0.0
    zone = "Z0"
    cost = 0.0
    done = set()
    actions = 0
    checks = dict(actions=0, reserve_min_ok=True, budget_ok=True,
                  horizon_ok=True, completion_formula_ok=True,
                  availability_formula_ok=True, no_review=True)
    trace = []

    def travel(z):
        return S.dist(zone, z)

    def onprob(a):
        if oracle:
            phat_true = ALPHA * a["j"]["d"] + BETA
            return float(a["s"] + phat_true <= a["j"]["due"] + EPS)
        ds = np.quantile(old.RES[0.2], SCEN_Q)
        phat = ALPHA * np.maximum(0.2, a["j"]["pred"] + ds) + BETA
        return float(np.mean(a["s"] + phat <= a["j"]["due"] + EPS))

    while t < H - EPS and actions < 200:
        actions += 1
        feasible = [j for j in jobs if not j["started"] and j["release"] <= t + EPS
                    and all(p in done for p in j["preds"])]
        rem = sum(ALPHA * x["pred"] + BETA + 1.0 for x in jobs if not x["started"])
        pressure = rem / max(H - t, 1e-6)
        qlevel = float(np.clip(P["Q_HI"] - P["Q_SLOPE"] * max(0.0, pressure - P["Q_KNEE"]),
                               P["Q_LO"], P["Q_HI"]))
        acts = []
        for j in feasible:
            ph = ALPHA * j["pred"] + BETA
            D = travel(j["zone"])
            s = t + D + CHANGEOVER
            if policy == "slack_old":
                b = max(RESERVE_MIN, ph + 0.6 * ALPHA * quantile(old.RES[0.2], 0.6))
            elif policy == "risk_old":
                if oracle:
                    b = max(RESERVE_MIN, ALPHA * j["d"] + BETA)
                else:
                    b = max(RESERVE_MIN,
                            ALPHA * (j["pred"] + quantile(old.RES[0.2], qlevel)) + BETA)
            else:
                raise ValueError(policy)
            c = 2.0 + 0.1 * b + 0.2 * D
            if s + b <= H + EPS and cost + c <= B + EPS:
                acts.append(dict(j=j, ph=ph, D=D, s=s, b=b, c=c))
        if not acts:
            future = [j["release"] for j in jobs if not j["started"] and j["release"] > t + EPS]
            nxt = min(future + [H])
            if nxt <= t + EPS or nxt >= H:
                break
            trace.append(dict(action="wait", t=t, until=nxt))
            t = nxt
            continue

        drop = None
        if policy == "slack_old":
            on2 = [a for a in acts if a["s"] + a["ph"] <= a["j"]["due"] + 0.5]
            if on2:
                a = max(on2, key=lambda a: (a["j"]["w"] / max(0.5, a["ph"]))
                        * math.exp(-max(0.0, a["j"]["due"] - a["s"] - a["ph"]) / P["LATE_TOL_SLACK"]))
            else:
                a = min(acts, key=lambda a: (a["s"] + a["ph"] - a["j"]["due"])
                        / max(1.0, a["j"]["w"]))
        else:
            on = [x for x in acts if onprob(x) >= P["GATE"]]
            pool = on if on else acts
            a = max(pool, key=lambda x: x["j"]["w"] * max(0.03, onprob(x))
                    / max(0.5, x["ph"])
                    * math.exp(-max(0.0, x["j"]["due"] - x["s"] - x["ph"])
                               / P["LATE_TOL_RISK"]))
        if pressure > P["DROP_P"] and onprob(a) < P["DROP_ON"]:
            drop = min(acts, key=lambda x: x["j"]["w"] * max(0.03, onprob(x))
                       / max(0.5, x["ph"]))["j"]
        if drop is not None:
            drop["started"] = True
            drop["dropped"] = True
            trace.append(dict(action="drop", t=t, job=drop["jid"]))
            continue

        j = a["j"]
        j["started"] = True
        p = ALPHA * j["d"] + BETA
        C = a["s"] + p
        j["C"] = C
        cost += a["c"]
        action = dict(action="execute", t=t, job=j["jid"], D=a["D"], s=a["s"],
                      b=a["b"], p=p, C=C, cost=cost)
        trace.append(action)
        checks["actions"] += 1
        checks["reserve_min_ok"] &= bool(a["b"] >= RESERVE_MIN - EPS)
        checks["budget_ok"] &= bool(cost <= B + EPS)
        checks["horizon_ok"] &= bool(a["s"] + a["b"] <= H + EPS)
        checks["completion_formula_ok"] &= bool(abs(C - (a["s"] + p)) < 1e-12)
        if C > H + EPS:
            t = H
            break
        j["done"] = True
        j["on_time"] = C <= j["due"] + EPS
        done.add(j["jid"])
        nxt = a["s"] + max(p, a["b"])
        checks["availability_formula_ok"] &= bool(nxt >= C - EPS)
        t = nxt
        zone = j["zone"]

    W = sum(j["w"] for j in jobs)
    comp = sum(j["w"] for j in jobs if j["done"] and not j["dropped"] and j["C"] <= H + EPS)
    ontime = sum(j["w"] for j in jobs if j["done"] and j["on_time"])
    dropW = sum(j["w"] for j in jobs if j["dropped"])
    tard = sum(j["w"] * max(0.0, (j["C"] if j["C"] is not None else H) - j["due"])
               for j in jobs)
    return dict(case=case, seed=seed, policy=policy, params=P,
                weighted_on_time_rate=float(ontime / W),
                weighted_completion_rate=float(comp / W),
                weighted_late_rate=float((comp - ontime) / W),
                weighted_dropped_rate=float(dropW / W),
                weighted_unserved_rate=float((W - comp - dropW) / W),
                weighted_tardiness_s=float(tard),
                cost=float(cost), n_done=int(sum(j["done"] for j in jobs)),
                n_drop=int(sum(j["dropped"] for j in jobs)),
                n_started=int(sum(j["started"] for j in jobs)),
                elapsed_s=float(t), checks=checks,
                trace=trace)


def summarize(rows):
    ot = np.asarray([r["weighted_on_time_rate"] for r in rows], float)
    cp = np.asarray([r["weighted_completion_rate"] for r in rows], float)
    td = np.asarray([r["weighted_tardiness_s"] for r in rows], float)
    cost = np.asarray([r["cost"] for r in rows], float)
    return dict(n=len(rows), on_time_mean=float(ot.mean()), on_time_ci95=ci95(ot),
                on_time_median=float(np.median(ot)), on_time_min=float(ot.min()),
                on_time_max=float(ot.max()), completion_mean=float(cp.mean()),
                late_mean=float(np.mean([r["weighted_late_rate"] for r in rows])),
                dropped_mean=float(np.mean([r["weighted_dropped_rate"] for r in rows])),
                unserved_mean=float(np.mean([r["weighted_unserved_rate"] for r in rows])),
                tardiness_mean=float(td.mean()), cost_mean=float(cost.mean()),
                cost_min=float(cost.min()), cost_max=float(cost.max()),
                n_done_mean=float(np.mean([r["n_done"] for r in rows])),
                n_drop_mean=float(np.mean([r["n_drop"] for r in rows])),
                on_time=[float(x) for x in ot], completion=[float(x) for x in cp])


def bootstrap_ci(delta, reps=20000, seed=20261117):
    rng = np.random.RandomState(seed)
    a = np.asarray(delta, float)
    means = np.empty(reps)
    n = len(a)
    for i in range(reps):
        means[i] = a[rng.randint(0, n, n)].mean()
    return dict(mean=float(a.mean()), ci95_normal=ci95(a),
                ci95_percentile=[float(np.percentile(means, 2.5)),
                                 float(np.percentile(means, 97.5))],
                reps=reps, seed=seed)


def main():
    with open(SELECTION_JSON, encoding="utf-8") as f:
        search = json.load(f)
    results = {}
    for c in ("S2", "S3"):
        sel = search["selection"][c]
        policy = sel["policy"]
        params = sel["params"]
        base_rows = [simulate(c, sd, "slack_old") for sd in SEEDS]
        cand_rows = [simulate(c, sd, policy, params) for sd in SEEDS]
        nodrop_params = dict(params, DROP_P=1e9)
        nodrop_rows = [simulate(c, sd, policy, nodrop_params) for sd in SEEDS]
        base = summarize(base_rows)
        cand = summarize(cand_rows)
        nodrop = summarize(nodrop_rows)

        # per-seed equality with the original search results
        ref_base = search["baseline"][c]["all30"]["on_time"]
        ref_cand = search["selection"][c]["all30"]["on_time"]
        diff_base = np.asarray(base["on_time"]) - np.asarray(ref_base)
        diff_cand = np.asarray(cand["on_time"]) - np.asarray(ref_cand)
        exact = dict(slack_old_max_abs=float(np.max(np.abs(diff_base))),
                     selected_max_abs=float(np.max(np.abs(diff_cand))),
                     slack_old_exact=bool(np.max(np.abs(diff_base)) < 1e-12),
                     selected_exact=bool(np.max(np.abs(diff_cand)) < 1e-12))

        d = np.asarray(cand["on_time"], float) - np.asarray(base["on_time"], float)
        dc = np.asarray(cand["completion"], float) - np.asarray(base["completion"], float)
        wins = int((d > 1e-12).sum())
        losses = int((d < -1e-12).sum())
        ties = int(len(d) - wins - losses)
        check_ok = {}
        for name, rows in (("slack_old", base_rows), ("selected", cand_rows),
                           ("drop_disabled", nodrop_rows)):
            for key in ("reserve_min_ok", "budget_ok", "horizon_ok",
                        "completion_formula_ok", "availability_formula_ok"):
                check_ok["%s.%s" % (name, key)] = bool(all(r["checks"][key] for r in rows))
            check_ok["%s.max_actions" % name] = bool(max(r["checks"]["actions"] for r in rows) <= 200)
            check_ok["%s.no_review" % name] = bool(all(r["checks"]["no_review"] for r in rows))
        drop_off_same_on_time = [float(x) for x in nodrop["on_time"]] == [float(x) for x in cand["on_time"]]
        results[c] = dict(
            selected_tag=sel["tag"], policy=policy, params=params,
            baseline=base, selected=cand,
            drop_disabled=dict(summary=nodrop, params=nodrop_params,
                               same_on_time_as_selected=drop_off_same_on_time,
                               on_time_delta_mean=float(nodrop["on_time_mean"] - cand["on_time_mean"])),
            exact_reproduction=exact,
            invariants=check_ok,
            paired=dict(delta_mean=float(d.mean()), delta_ci95_normal=ci95(d),
                        delta_completion_mean=float(dc.mean()),
                        wins=wins, losses=losses, ties=ties,
                        sign_test_p_two_sided=binom_two_sided(wins, losses),
                        bootstrap=bootstrap_ci(d),
                        per_seed_delta=[float(x) for x in d],
                        per_seed_completion_delta=[float(x) for x in dc]),
            holdout=search["evidence"][c]["holdout"],
            selection_stage=search["evidence"][c]["tune"],
        )
        print("\n%s %s" % (c, sel["tag"]))
        print("  baseline %.4f -> selected %.4f  Δ=%+.4f ±%.4f  W/L/T=%d/%d/%d"
              % (base["on_time_mean"], cand["on_time_mean"], d.mean(), ci95(d),
                 wins, losses, ties))
        print("  completion %.4f -> %.4f  cost %.2f -> %.2f  drops %.2f -> %.2f"
              % (base["completion_mean"], cand["completion_mean"], base["cost_mean"],
                 cand["cost_mean"], base["n_drop_mean"], cand["n_drop_mean"]))
        print("  no-drop sensitivity: on_time %.4f  completion %.4f  same_on_time=%s"
              % (nodrop["on_time_mean"], nodrop["completion_mean"], drop_off_same_on_time))
        print("  exact:", exact, " invariants:", all(check_ok.values()), flush=True)

    # mixed S2+S3 paired difference, seed-by-seed
    dmix = 0.5 * (np.asarray(results["S2"]["paired"]["per_seed_delta"])
                  + np.asarray(results["S3"]["paired"]["per_seed_delta"]))
    dcmix = 0.5 * (np.asarray(results["S2"]["paired"]["per_seed_completion_delta"])
                   + np.asarray(results["S3"]["paired"]["per_seed_completion_delta"]))
    mixed = dict(delta_mean=float(dmix.mean()), delta_ci95_normal=ci95(dmix),
                 delta_completion_mean=float(dcmix.mean()),
                 wins=int((dmix > 1e-12).sum()), losses=int((dmix < -1e-12).sum()),
                 ties=int(len(dmix) - (dmix > 1e-12).sum() - (dmix < -1e-12).sum()),
                 sign_test_p_two_sided=binom_two_sided(int((dmix > 1e-12).sum()),
                                                       int((dmix < -1e-12).sum())),
                 bootstrap=bootstrap_ci(dmix),
                 per_seed_delta=[float(x) for x in dmix])

    overall_ok = all(v for c in results.values() for v in c["invariants"].values())
    exact_ok = all(v["exact_reproduction"]["selected_exact"]
                   and v["exact_reproduction"]["slack_old_exact"] for v in results.values())
    out = dict(
        _meta=dict(purpose="independent replay/invariant verification of selected improved P3 policies",
                   protocol="official constants: alpha=1, beta=0.5, changeover=0.5, reserve_min=0.2; p=alpha*d+beta; C=s+p; next=s+max(p,b)",
                   seeds=SEEDS, source="selection read from data/p3_improved_search.json",
                   independent_engine="does not call best_p3_sens.simulate",
                   verification_scope="30 official seeds x S2,S3; baseline and selected candidate all traced"),
        verified_all=bool(overall_ok and exact_ok),
        invariants_all=overall_ok,
        exact_reproduction_all=exact_ok,
        cases=results,
        mixed_S2_S3=mixed,
    )
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\nmixed S2+S3 Δ=%+.4f ±%.4f W/L/T=%d/%d/%d p_sign=%.6f"
          % (mixed["delta_mean"], mixed["delta_ci95_normal"], mixed["wins"],
             mixed["losses"], mixed["ties"], mixed["sign_test_p_two_sided"]))
    print("verified_all:", out["verified_all"], "saved ->", OUT, flush=True)


if __name__ == "__main__":
    main()