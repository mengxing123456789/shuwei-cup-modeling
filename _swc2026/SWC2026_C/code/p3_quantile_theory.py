# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""Is the reservation level a quantile?  Empirical curve + structural check.

Claim tested here:  the adaptive-quantile policy's reservation is one number, a
quantile level q of the service-time law.  Two things follow without any cost
exchange rate:

  (i)  the on-time rate as a function of q is unimodal, because raising q
       monotonically reduces overrun (good) and monotonically eats capacity
       (bad); hence the argmax is interior and a single sign change in the
       first differences is expected;
  (ii) the argmax moves up when the instance is more heavily loaded, because
       the marginal price of one second of delay rises with utilisation while
       the price of idle capacity is fixed by the protocol.

Both are checkable on the 121-candidate sweep already on disk, plus the job
table and the duration law.  No new simulation, no invented cm-to-cost rate.

Output: data/p3_quantile_theory.json
"""
import csv
import json
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
CONS = r"Restocking_Problem_and_Data_EN\Restocking_Tasks_and_Constraints"


def load_json(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    sweep = load_json("p3_improved_search.json")
    seeds = sweep["_meta"]["seeds"]
    n_tune = 15

    jobs = read_csv(os.path.join(CONS, "tasks.csv"))
    segs = read_csv(os.path.join(CONS, "source_segment_index.csv"))

    # --- duration law per family, from the eligible units only -------------
    fam_dur = {}
    for r in segs:
        if str(r.get("eligible", "")).strip().lower() not in ("true", "1", "yes"):
            continue
        fam = r["family_id"] if "family_id" in r else r.get("family")
        try:
            d = float(r["duration_s"] if "duration_s" in r else r["duration"])
        except (KeyError, ValueError):
            continue
        fam_dur.setdefault(fam, []).append(d)
    if not fam_dur:  # fall back: any duration column we can find
        keys = list(segs[0].keys())
        raise SystemExit("no durations parsed; columns are %s" % keys)

    fam_p = {k: np.asarray(v, float) + 0.5 for k, v in fam_dur.items()}  # p = 1.0*d + 0.5

    # --- utilisation per case ---------------------------------------------
    H = {"S1": 100.0, "S2": 100.0, "S3": 125.0}
    cases = {}
    for case in ("S1", "S2", "S3"):
        rows = [r for r in jobs if r["case_id"] == case]
        ep = []
        for r in rows:
            fam = r["family_id"]
            if fam not in fam_p:
                raise SystemExit("family %r missing from segment index" % fam)
            ep.append(float(np.mean(fam_p[fam])))
        pool = np.concatenate([fam_p[r["family_id"]] for r in rows])
        cases[case] = dict(
            n_jobs=len(rows),
            horizon_s=H[case],
            utilisation=float(np.sum(ep) / H[case]),
            expected_service_sum=float(np.sum(ep)),
            p_median=float(np.median(pool)),
            p_q40=float(np.quantile(pool, 0.40)),
            p_q50=float(np.quantile(pool, 0.50)),
            p_q60=float(np.quantile(pool, 0.60)),
        )

    # --- empirical on-time rate as a function of the reservation quantile --
    def curve(case):
        buckets = {}
        for cand in sweep["candidates"]:
            if cand["family"] != "adaptive_quantile":
                continue
            q = cand["params"].get("Q_HI")
            if q is None:
                continue
            tune = cand["tune"].get(case)
            if not tune or "on_time" not in tune:
                continue
            vals = np.asarray(tune["on_time"][:n_tune], float)
            buckets.setdefault(round(float(q), 4), []).append(float(np.mean(vals)))
        qs = sorted(buckets)
        out = {
            "q": qs,
            "max_on_time": [max(buckets[q]) for q in qs],
            "mean_on_time": [float(np.mean(buckets[q])) for q in qs],
            "n_configs": [len(buckets[q]) for q in qs],
        }
        best = out["max_on_time"]
        d = np.diff(best)
        sign_changes = int(np.sum(np.sign(d[1:]) != np.sign(d[:-1]))) if len(d) > 1 else 0
        return dict(
            out,
            argmax_q=qs[int(np.argmax(best))],
            argmax_value=max(best),
            sign_changes_in_first_differences=sign_changes,
            unimodal=bool(sign_changes <= 1),
            spread_at_best=float(max(best) - min(best)),
        )

    curves = {c: curve(c) for c in ("S2", "S3")}

    # median of p, and where the empirical argmax sits relative to it
    for c in curves:
        info = cases[c]
        q_emp = curves[c]["argmax_q"]
        curves[c]["p_level_at_q_emp"] = float(np.quantile(
            np.concatenate([fam_p[r["family_id"]] for r in jobs if r["case_id"] == c]), q_emp))
        curves[c]["q_of_median_p"] = None
        # percentile of the mixture that the median covers
        curves[c]["median_covers_fraction"] = float(np.mean(
            np.concatenate([fam_p[r["family_id"]] for r in jobs if r["case_id"] == c]) <= info["p_median"]))

    order_util = [cases[c]["utilisation"] for c in ("S2", "S3")]
    order_q = [curves[c]["argmax_q"] for c in ("S2", "S3")]
    prediction_holds = bool(
        (order_util[1] > order_util[0] and order_q[1] >= order_q[0])
        or (order_util[1] < order_util[0] and order_q[1] <= order_q[0])
    )

    out = dict(
        _meta=dict(
            script="p3_quantile_theory.py",
            question="is the reservation level one quantile of the service-time law?",
            sources=["p3_improved_search.json", "tasks.csv", "source_segment_index.csv"],
            seeds_selection=int(n_tune),
            protocol="p=alpha*d+beta with alpha=1, beta=0.5; C=s+p; next=s+max(p,b)",
            note="no cm-to-cost rate is invented; only the shape and the ordering are claimed",
        ),
        cases=cases,
        curves=curves,
        structural_check=dict(
            utilisation_order=[round(x, 6) for x in order_util],
            argmax_q_order=order_q,
            median_p_order=[cases[c]["p_median"] for c in ("S2", "S3")],
            higher_load_pushes_quantile_up=prediction_holds,
            both_unimodal=bool(all(curves[c]["unimodal"] for c in curves)),
        ),
    )

    dst = os.path.join(DATA, "p3_quantile_theory.json")
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print("written", dst, os.path.getsize(dst), "B")
    print("cases:", json.dumps(cases, ensure_ascii=False))
    for c in curves:
        print(c, "q grid", curves[c]["q"])
        print(c, "max  ", [round(x, 4) for x in curves[c]["max_on_time"]])
        print(c, "argmax q", curves[c]["argmax_q"], "unimodal", curves[c]["unimodal"],
              "sign changes", curves[c]["sign_changes_in_first_differences"],
              "spread", round(curves[c]["spread_at_best"], 4))
    print("structural:", json.dumps(out["structural_check"], ensure_ascii=False))


if __name__ == "__main__":
    main()