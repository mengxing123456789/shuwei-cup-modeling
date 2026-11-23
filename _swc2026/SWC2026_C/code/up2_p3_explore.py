# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""up2_p3_explore.py -- train/val search for the P3 dispatch v2 upgrade.

Three pre-registered strategy classes (data/up2_p3_prereg.json):

  A  parametric rule search -- random factorial over selector, reservation rule,
     reserve quantile, EDF/ATC mix, lookahead, review hurdle, blocking weight.
  B  learned context policy -- linear-in-features reserve multiplier
     k(pressure, budget) = ksk + ksp*max(0, pressure-0.75) + ksb*(1-cost/B),
     trained by the cross-entropy method on train seeds, stopped on val seeds.
  C  distributionally robust choice -- min-max and CVaR over the five official
     (alpha,beta) mappings, using the class-A candidate table.

No test seed is touched: ``SEEDS_TRAIN`` and ``SEEDS_VAL`` only. The frozen
picks are written to data/up2_p3_search.json for up2_p3_final.py.
"""
import argparse
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import up_p3_vectorized as V
import up2_p3_engine as E
from common import DATA

TRAIN = [2026111700 + i for i in range(15)]
VAL = [2026111715 + i for i in range(10)]
SEARCH_SEEDS = TRAIN + VAL
CASES = ("S2", "S3")
MAPPINGS = [(1.0, 0.5), (0.75, 0.5), (1.5, 0.5), (1.0, 0.0), (1.0, 1.0)]
MAP_KEYS = ["a%.2f_b%.2f" % m for m in MAPPINGS]
N_TRAIN = len(TRAIN)

BASELINE = dict(SEL=1, RULE=E.RULE_SLACK, q_hi=0.60, gate=0.50, late_tol=12.0,
                REVIEW=False, name="slack_old")
V1_S2 = dict(SEL=0, RULE=E.RULE_ABS, q_hi=0.50, gate=0.60, late_tol=12.0,
             REVIEW=False, name="v1_improved_S2")
V1_S3 = dict(SEL=0, RULE=E.RULE_ABS, q_hi=0.60, gate=0.50, late_tol=20.0,
             REVIEW=False, name="v1_improved_S3")
EDF = dict(SEL=0, RULE=E.RULE_ABS, q_hi=0.30, gate=1.01, late_tol=1e6, mix=1.0,
           REVIEW=False, name="edf_ref")
RULE_NAMES = {E.RULE_ABS: "abs", E.RULE_ADD: "add", E.RULE_SLACK: "slack",
              E.RULE_FIX: "fix"}
CHUNK = 120
KEY_METRICS = ("weighted_on_time_rate", "weighted_completion_rate",
               "weighted_tardiness_s", "cost", "n_reviews")


# --------------------------------------------------------------------------- #
class Runner(object):
    """Evaluate a candidate list on (case, mapping) with the train+val seed block."""

    def __init__(self, seeds=SEARCH_SEEDS):
        self.seeds = list(seeds)
        self.spec = {}
        self.cfg = {}
        self.scen = {}

    def case_data(self, case, alpha, beta):
        if case not in self.spec:
            self.spec[case] = V.build_spec(case)
            self.cfg[case] = V.build_configs(self.spec[case], self.seeds)
        k = (case, alpha, beta)
        if k not in self.scen:
            self.scen[k] = V._scen(self.spec[case], self.cfg[case], alpha, beta)
        return self.spec[case], self.cfg[case], self.scen[k]

    def run(self, cands, cases=CASES, mappings=MAPPINGS):
        out = {}
        for case in cases:
            for (alpha, beta) in mappings:
                sp, cfg, scen = self.case_data(case, alpha, beta)
                n = len(cands)
                res = {k: np.zeros((n, len(self.seeds))) for k in KEY_METRICS}
                res["budget_ok"] = np.ones((n, len(self.seeds)), bool)
                for i0 in range(0, n, CHUNK):
                    sub = cands[i0:i0 + CHUNK]
                    ca = V._cand_arrays(sub)
                    for k in ("ksk", "qsl", "mix", "gam", "tau", "pw", "po", "pp",
                              "ksp", "ksb"):
                        if any(c.get(k) is not None for c in sub):
                            dflt = E.DEFAULTS.get(k, 0.0)
                            ca[k] = np.array([dflt if c.get(k) is None else
                                              float(c[k]) for c in sub], np.float64)
                    r = E.simulate_batch2(sp, cfg, alpha, beta, ca,
                                         n_seeds=len(self.seeds), scen=scen)
                    for k in KEY_METRICS:
                        res[k][i0:i0 + CHUNK] = r[k]
                    res["budget_ok"][i0:i0 + CHUNK] = r["budget_ok"]
                out[(case, alpha, beta)] = res
        return out


def summarise(res, cands):
    """train / val means over mappings for every candidate, per case."""
    tab = {}
    for case in CASES:
        M = np.stack([res[(case, a, b)]["weighted_on_time_rate"] for a, b in MAPPINGS])
        C = np.stack([res[(case, a, b)]["weighted_completion_rate"] for a, b in MAPPINGS])
        K = np.stack([res[(case, a, b)]["cost"] for a, b in MAPPINGS])
        R = np.stack([res[(case, a, b)]["n_reviews"] for a, b in MAPPINGS])
        tab[case] = dict(
            train_by_map=M[:, :, :N_TRAIN].mean(2), val_by_map=M[:, :, N_TRAIN:].mean(2),
            comp_train=C[:, :, :N_TRAIN].mean(2), comp_val=C[:, :, N_TRAIN:].mean(2),
            cost_train=K[:, :, :N_TRAIN].mean(2), rev_train=R[:, :, :N_TRAIN].mean(2),
            train=M[:, :, :N_TRAIN].mean(2).mean(0),
            val=M[:, :, N_TRAIN:].mean(2).mean(0),
            n=len(cands),
        )
    return tab


# --------------------------------------------------------------------------- #
def build_stage_a(n_random=480, seed=20261121):
    rng = np.random.RandomState(seed)
    cands = [dict(BASELINE), dict(V1_S2), dict(V1_S3), dict(EDF)]
    sel_grid = [0, 1]
    rule_grid = [E.RULE_ABS, E.RULE_SLACK, E.RULE_ADD, E.RULE_FIX]
    q_grid = [round(0.30 + 0.05 * i, 2) for i in range(9)]
    gate_grid = [0.35, 0.45, 0.55, 0.65, 0.75]
    late_grid = [8.0, 12.0, 20.0, 30.0]
    ksk_grid = [0.25, 0.40, 0.55, 0.70, 0.85]
    qsl_grid = [0.45, 0.55, 0.65, 0.75]
    mix_grid = [0.0, 0.15, 0.35, 0.60, 1.0]
    gam_grid = [0.0, 0.10, 0.25]
    tau_grid = [0.02, 0.06]
    seen = set()
    for _ in range(n_random):
        sel = int(rng.choice(sel_grid))
        rule = int(rng.choice(rule_grid))
        q = float(rng.choice(q_grid))
        g = float(rng.choice(gate_grid))
        lt = float(rng.choice(late_grid))
        mix = float(rng.choice(mix_grid))
        gam = float(rng.choice(gam_grid))
        ksk = float(rng.choice(ksk_grid)) if rule == E.RULE_SLACK else 0.60
        qsl = float(rng.choice(qsl_grid)) if rule == E.RULE_SLACK else 0.60
        rv = bool(rng.rand() < 0.35)
        tau = float(rng.choice(tau_grid)) if rv else 0.02
        key = (sel, rule, q, g, lt, mix, gam, ksk, qsl, rv, tau)
        if key in seen:
            continue
        seen.add(key)
        cands.append(dict(SEL=sel, RULE=rule, q_hi=q, gate=g, late_tol=lt, mix=mix,
                          gam=gam, ksk=ksk, qsl=qsl, REVIEW=rv, tau=tau,
                          name="A_s%d_r%s_q%.2f_g%.2f_l%g_m%.2f_G%.2f_k%.2f_%0.2f%s%s"
                               % (sel, RULE_NAMES[rule], q, g, lt, mix, gam, ksk, qsl,
                                  "_rev" if rv else "", ("_t%.2f" % tau) if rv else "")))
    return cands


def select_A(tab, cands):
    """train top-5 -> val re-rank -> one policy per case."""
    picks = {}
    for case in CASES:
        t = tab[case]["train"]
        v = tab[case]["val"]
        order = np.argsort(-t)
        order = [i for i in order if i != 0][:5]          # exclude baseline row 0
        best = max(order, key=lambda i: v[i])
        picks[case] = dict(index=int(best), name=cands[best]["name"],
                           params={k: cands[best][k] for k in
                                   ("SEL", "RULE", "q_hi", "gate", "late_tol", "mix",
                                    "gam", "ksk", "qsl", "REVIEW", "tau")
                                   if k in cands[best]},
                           train_top5=[dict(index=int(i), name=cands[i]["name"],
                                            train=float(t[i]), val=float(v[i]))
                                       for i in order],
                           train=float(t[best]), val=float(v[best]),
                           baseline_train=float(t[0]), baseline_val=float(v[0]))
    return picks


# --------------------------------------------------------------------------- #
CEM_NAMES = ["q_hi", "mix", "gam", "ksk", "ksp", "ksb"]
CEM_LO = np.array([0.30, 0.00, 0.00, 0.20, -0.60, -0.50])
CEM_HI = np.array([0.70, 0.60, 0.30, 0.90, 0.60, 0.50])


def _to_cand(theta, tag=""):
    x = np.clip(theta, CEM_LO, CEM_HI)
    return dict(SEL=0, RULE=E.RULE_SLACK, q_hi=float(x[0]), gate=0.50, late_tol=12.0,
                ksk=float(x[3]), qsl=0.60, ksp=float(x[4]), ksb=float(x[5]),
                mix=float(x[1]), gam=float(x[2]), tau=0.02, REVIEW=False,
                name="B_cem%s_q%.2f_m%.2f_G%.2f_k%.2f_p%+.2f_b%+.2f"
                     % (tag, x[0], x[1], x[2], x[3], x[4], x[5]))


def stage_B(runner, iters=18, pop=20, elite=5, seed=20261121, log=print):
    rng = np.random.RandomState(seed)
    out = {}
    for case in CASES:
        mu = np.array([0.52, 0.10, 0.05, 0.55, 0.15, 0.10])
        sd = np.array([0.09, 0.12, 0.07, 0.16, 0.20, 0.18])
        best = None
        curve = []
        for it in range(iters):
            X = np.clip(mu + sd * rng.randn(pop, len(mu)), CEM_LO, CEM_HI)
            while len({tuple(np.round(x, 6)) for x in X}) < pop:
                X = np.vstack([X, np.clip(mu + sd * rng.randn(1, len(mu)), CEM_LO, CEM_HI)])
            cands = [_to_cand(X[i], tag="_i%02d_%02d" % (it, i)) for i in range(pop)]
            res = runner.run(cands, cases=(case,))
            ok = res[(case,) + MAPPINGS[0]]["weighted_on_time_rate"]
            M = np.stack([res[(case, a, b)]["weighted_on_time_rate"] for a, b in MAPPINGS])
            tr = M[:, :, :N_TRAIN].mean(2).mean(0)
            order = np.argsort(-tr)
            el = order[:elite]
            mu_new = 0.6 * X[el].mean(0) + 0.4 * mu
            sd_new = 0.6 * X[el].std(0) + 0.4 * sd + 1e-3
            mu, sd = mu_new, np.maximum(sd_new, 0.01)
            # val check of this iteration's elite leader (early stopping criterion)
            leaders = [i for i in el[:3]]
            vres = runner.run([cands[i] for i in leaders], cases=(case,))
            VM = np.stack([vres[(case, a, b)]["weighted_on_time_rate"]
                           for a, b in MAPPINGS])
            vsc = VM[:, :, N_TRAIN:].mean(2).mean(0)
            j = int(np.argmax(vsc))
            curve.append(dict(iter=it, best_train=float(tr[order[0]]),
                              leader_val=float(vsc[j]), leader=int(leaders[j]),
                              leader_name=cands[leaders[j]]["name"],
                              mu=[float(x) for x in mu], sd=[float(x) for x in sd]))
            if best is None or vsc[j] > best["val"]:
                best = dict(val=float(vsc[j]), train=float(tr[leaders[j]]),
                            cand=cands[leaders[j]], iter=it)
            log("  B %s it%02d train=%.4f val_best=%.4f mu=%s"
                % (case, it, float(tr[order[0]]), best["val"],
                   np.round(mu, 3).tolist()))
        out[case] = dict(name=best["cand"]["name"],
                         params={k: best["cand"][k] for k in
                                 ("SEL", "RULE", "q_hi", "gate", "late_tol", "ksk",
                                  "qsl", "ksp", "ksb", "mix", "gam", "REVIEW")},
                         train=best["train"], val=best["val"], iter=best["iter"],
                         curve=curve)
    return out


def select_C(tab, cands):
    """min-max and CVaR(0.4) over the five mappings, on train means."""
    out = {}
    for case in CASES:
        T = tab[case]["train_by_map"]     # (5, nC)
        Vv = tab[case]["val_by_map"]
        nC = T.shape[1]
        pool = [i for i in range(nC)
                if not cands[i].get("name", "").startswith(("A_s1_rfix", "edf_ref"))]
        worst = np.min(T, axis=0)
        k2 = int(math.ceil(0.4 * T.shape[0]))
        cvar = np.sort(T, axis=0)[:k2].mean(0)
        best_mm = max([i for i in pool if i != 0], key=lambda i: worst[i])
        best_cv = max([i for i in pool if i != 0], key=lambda i: cvar[i])
        def blk(i, tag):
            return dict(tag=tag, index=int(i), name=cands[i]["name"],
                        params={k: cands[i][k] for k in
                                ("SEL", "RULE", "q_hi", "gate", "late_tol", "mix",
                                 "gam", "ksk", "qsl", "REVIEW", "tau") if k in cands[i]},
                        train_by_map=[float(x) for x in T[:, i]],
                        val_by_map=[float(x) for x in Vv[:, i]],
                        train_mean=float(T[:, i].mean()), val_mean=float(Vv[:, i].mean()),
                        train_min=float(T[:, i].min()), train_cvar40=float(cvar[i]),
                        baseline_train_mean=float(T[:, 0].mean()),
                        baseline_val_mean=float(Vv[:, 0].mean()))
        out[case] = dict(minimax=blk(best_mm, "min-max over mappings"),
                         cvar=blk(best_cv, "CVaR(0.4) over mappings"))
        # robust winner = the one with the better val mean among the two
        w = ("minimax" if out[case]["minimax"]["val_mean"]
             >= out[case]["cvar"]["val_mean"] else "cvar")
        out[case]["robust_pick"] = w
        out[case]["chosen"] = out[case][w]
    return out


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(DATA, "up2_p3_search.json"))
    ap.add_argument("--stage", default="all", choices=["all", "a", "b", "c"])
    ap.add_argument("--n-random", type=int, default=480)
    args = ap.parse_args()
    t0 = time.time()
    logf = open(os.path.join(os.path.dirname(DATA), "logs", "up2_p3_explore.log"),
                "w", encoding="utf-8")
    def log(msg):
        print(msg, flush=True)
        logf.write(msg + "\n")
        logf.flush()

    runner = Runner()
    log("split: train %d seeds, val %d seeds, mappings %s"
        % (len(TRAIN), len(VAL), MAP_KEYS))
    log("baseline = %s" % BASELINE["name"])

    cands = build_stage_a(args.n_random)
    log("stage A: %d candidates (%d random + 4 anchors)" % (len(cands), args.n_random))
    cache = os.path.join(DATA, "up2_p3_poolA.json")
    names = [c["name"] for c in cands]
    tab = None
    if os.path.exists(cache):
        with open(cache, encoding="utf-8") as f:
            old = json.load(f)
        if old.get("names") == names:
            tab = {}
            for case in CASES:
                d = old["cases"][case]
                tab[case] = {k: np.array(v, np.float64) for k, v in d.items() if k != "n"}
                tab[case]["n"] = len(cands)
            log("stage A: reusing cached pool table %s" % cache)
    if tab is None:
        res = runner.run(cands)
        tab = summarise(res, cands)
        with open(cache, "w", encoding="utf-8", newline="\n") as f:
            json.dump(dict(names=names, cases={case: {
                k: np.asarray(v).tolist() for k, v in tab[case].items()} for case in CASES}),
                f, ensure_ascii=False)
    for case in CASES:
        log("  A %s baseline train=%.4f val=%.4f"
            % (case, tab[case]["train"][0], tab[case]["val"][0]))
    picksA = select_A(tab, cands)
    for case in CASES:
        p = picksA[case]
        log("  A pick %s -> %s train=%.4f val=%.4f (delta_val %+.4f)"
            % (case, p["name"], p["train"], p["val"], p["val"] - p["baseline_val"]))

    picksB = stage_B(runner, log=log)
    for case in CASES:
        p = picksB[case]
        log("  B pick %s -> %s train=%.4f val=%.4f"
            % (case, p["name"], p["train"], p["val"]))

    picksC = select_C(tab, cands)
    for case in CASES:
        c = picksC[case]["chosen"]
        log("  C pick %s (%s) train_min=%.4f train_mean=%.4f val=%.4f"
            % (case, c["tag"], c["train_min"], c["train_mean"], c["val_mean"]))

    # frozen choice per case: best val among the three classes, with the shortfall
    # rule pre-registered (if none reaches +1.5pp on val, the best val candidate is
    # still frozen and the shortfall is reported).
    frozen = {}
    for case in CASES:
        arms = [("A", picksA[case]["val"], picksA[case]["params"], picksA[case]["name"]),
                ("B", picksB[case]["val"], picksB[case]["params"], picksB[case]["name"]),
                ("C", picksC[case]["chosen"]["val_mean"],
                 picksC[case]["chosen"]["params"], picksC[case]["chosen"]["name"])]
        b0 = tab[case]["val"][0]
        arms.sort(key=lambda z: -z[1])
        tag, val, params, name = arms[0]
        frozen[case] = dict(class_=tag, name=name, params=params, val=float(val),
                            val_delta=float(val - b0), baseline_val=float(b0),
                            by_class={a[0]: float(a[1]) for a in arms},
                            val_gain_ok=bool(val - b0 >= 0.015))
        log("  frozen %s: class %s %s val=%.4f delta=%+.4f ok=%s"
            % (case, tag, name, val, val - b0, frozen[case]["val_gain_ok"]))

    out = dict(
        _meta=dict(script="code/up2_p3_explore.py",
                   prereg="data/up2_p3_prereg.json",
                   engine="code/up2_p3_engine.py (bit-exact superset of "
                          "code/up_p3_vectorized.py)",
                   seeds_train=TRAIN, seeds_val=VAL,
                   cases=list(CASES), mappings=MAP_KEYS,
                   n_candidates_A=len(cands),
                   stageA_authored_at=time.strftime("%Y-%m-%dT%H:%M:%S")),
        stage_A=dict(picks=picksA,
                     top20={case: [dict(index=int(i), name=cands[i]["name"],
                                        train=float(tab[case]["train"][i]),
                                        val=float(tab[case]["val"][i]))
                                   for i in np.argsort(-tab[case]["train"])[:20]]
                            for case in CASES}),
        stage_B=picksB,
        stage_C=picksC,
        frozen=frozen,
        pool=dict(candidates=[{k: c.get(k) for k in
                               ("name", "SEL", "RULE", "q_hi", "gate", "late_tol",
                                "mix", "gam", "ksk", "qsl", "ksp", "ksb", "REVIEW",
                                "tau")} for c in cands],
                  train_by_map={case: [[float(x) for x in row]
                                       for row in tab[case]["train_by_map"]]
                                for case in CASES},
                  val_by_map={case: [[float(x) for x in row]
                                     for row in tab[case]["val_by_map"]]
                              for case in CASES}),
        wall_clock_s=float(time.time() - t0),
    )
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    log("saved -> %s  (%.1fs)" % (args.out, time.time() - t0))
    logf.close()


if __name__ == "__main__":
    main()