"""Quick feasibility probe for C / Problem 3 (not a final solver).

Purpose: answer one question with evidence -- can a simple, rule-compliant
policy clear the mandatory floor "mean weighted on-time rate >= 0.50 per case
over 30 nominal trials"?  If yes, C is technically winnable; if no, the floor
itself is the risk.

Implements the protocol in Problem_3_Requirements.pdf:
  s = t + D + 0.5 ; cost = 2 + 0.1b + 0.2D ; C = s + p ; p = alpha*d + beta
  equipment next free at s + max(p, b)
Policy: earliest-due-date among released & predecessor-ready jobs, reservation
b = alpha*d_hat + beta with d_hat = median TRAIN duration of the job's family.
"""
import json, math, random, statistics, sys, os
import pandas as pd

B = r"C:\Users\29900\Downloads\AsterLink\C_Problem_Data\C_Problem_Data\Restocking_Problem_and_Data_EN\Restocking_Problem_and_Data_EN\Restocking_Tasks_and_Constraints"
tasks = pd.read_csv(os.path.join(B, "tasks.csv"))
seg = pd.read_csv(os.path.join(B, "source_segment_index.csv"))
cond = json.load(open(os.path.join(B, "common_conditions.json"), encoding="utf-8"))
Z = {"Z0": (0, 0), "Z1": (1, 0), "Z2": (0, 1), "Z3": (1, 1), "Z4": (2, 0)}

# train-only family medians (fit on train split)
train_d = seg[(seg.split == "train") & (seg.eligible == 1)]
MED = {f: float(train_d[train_d.family_id == f].duration_s.median()) for f in ["P", "A", "L"]}

def sample_pool(split, fam, rng):
    pool = seg[(seg.split == split) & (seg.family_id == fam) & (seg.eligible == 1)]
    return pool.reset_index(drop=True)

def run(case, alpha, beta, seed, split="validation"):
    rng = random.Random(int(seed))
    T = tasks[tasks.case_id == case].sort_values("job_id").reset_index(drop=True)
    pools = {f: sample_pool(split, f, rng) for f in ["P", "A", "L"]}
    dur, fam_of = {}, {}
    for _, r in T.iterrows():
        pool = pools[r.family_id]
        pick = pool.iloc[rng.randrange(len(pool))]      # choice() with replacement
        dur[r.job_id] = float(pick.duration_s); fam_of[r.job_id] = r.family_id
    H = float(cond["cases"][[c["case_id"] for c in cond["cases"]].index(case)]["horizon_s"])
    Bc = float(cond["cases"][[c["case_id"] for c in cond["cases"]].index(case)]["cost_budget"])
    info = {r.job_id: dict(release=float(r.release_s), due=float(r.due_s), w=float(r.priority_weight),
                           zone=r.zone_id, pred=[] if pd.isna(r.predecessors) else str(r.predecessors).split("|"))
            for _, r in T.iterrows()}
    done, cost, t, zone, censored = set(), 0.0, 0.0, "Z0", 0
    comp, ontime, tard, overrun, idle = {}, {}, {}, 0.0, 0.0
    while True:
        avail = [j for j in info if j not in done and info[j]["release"] <= t + 1e-9
                 and all(p in done for p in info[j]["pred"])]
        if not avail:
            # wait to next release if within H, else stop
            nxt = [info[j]["release"] for j in info if j not in done and all(p in done for p in info[j]["pred"])]
            nxt = [x for x in nxt if x > t + 1e-9 and x < H]
            if not nxt: break
            t = min(nxt); continue
        j = min(avail, key=lambda x: (info[x]["due"], -info[x]["w"], x))
        zx, zy = Z[info[j]["zone"]]; cx, cy = Z[zone]
        D = math.hypot(zx - cx, zy - cy)
        s = t + D + 0.5
        d_hat = MED[fam_of[j]]
        b = max(0.2, alpha * d_hat + beta)
        c = 2.0 + 0.1 * b + 0.2 * D
        if s + b > H + 1e-9 or cost + c > Bc + 1e-9:
            done.add(j)                      # cannot schedule; drop from pool (counts as unfinished)
            continue
        cost += c; p = alpha * dur[j] + beta
        C = s + p
        if C <= H + 1e-9:
            comp[j] = C
            if C <= info[j]["due"] + 1e-9: ontime[j] = C
            else: tard[j] = C - info[j]["due"]
            idle += max(b - p, 0.0); overrun += max(min(p, H - s) - b, 0.0)
            t = s + max(p, b); zone = info[j]["zone"]
        else:
            censored += 1; done.add(j); break
    W = sum(v["w"] for v in info.values())
    wc = sum(info[j]["w"] for j in comp) / W
    wo = sum(info[j]["w"] for j in ontime) / W
    wt = sum(info[j]["w"] * tard.get(j, 0.0) for j in info)
    return dict(case=case, alpha=alpha, beta=beta, seed=seed, wc=wc, wo=wo, wt=wt,
                cost=cost, censored=censored, elapsed=t)

def main():
    rows = []
    for case in ["S1", "S2", "S3"]:
        for alpha, beta in [(1.0, 0.5), (0.75, 0.5), (1.5, 0.5), (1.0, 0.0), (1.0, 1.0)]:
            for seed in cond["validation_seeds"]:
                rows.append(run(case, alpha, beta, seed))
    df = pd.DataFrame(rows)
    print("== nominal (alpha=1,beta=0.5) ==")
    nom = df[(df.alpha == 1.0) & (df.beta == 0.5)]
    for case in ["S1", "S2", "S3"]:
        s = nom[nom.case == case]
        print(case, "on_time %.3f  completion %.3f  tardiness %.1f  cost %.1f  censored %d" % (
            s.wo.mean(), s.wc.mean(), s.wt.mean(), s.cost.mean(), s.censored.sum()))
    print("\n== all five mappings (mean on-time rate) ==")
    print(df.groupby(["case", "alpha", "beta"]).wo.mean().round(3).to_string())
    print("\n== worst-case over 30 seeds (nominal) ==")
    print(nom.groupby("case").wo.agg(["min", "mean", "max"]).round(3).to_string())

if __name__ == "__main__":
    main()
