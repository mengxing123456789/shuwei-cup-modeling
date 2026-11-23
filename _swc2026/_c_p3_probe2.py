"""Feasibility probe for C / Problem 3: how hard is the mandatory 0.50 floor?

Sweeps the reservation quantile q (reserve b = quantile_q of TRAIN durations for
the job's family, mapped through p = alpha*d + beta) and reports the mean
weighted on-time rate over the 30 nominal validation seeds.

Policy: earliest due date among released & predecessor-ready jobs; skip a job
only when its cheapest possible action cannot fit the remaining budget/horizon.
"""
import json, math, random, os
import pandas as pd

B = r"C:\Users\29900\Downloads\AsterLink\C_Problem_Data\C_Problem_Data\Restocking_Problem_and_Data_EN\Restocking_Problem_and_Data_EN\Restocking_Tasks_and_Constraints"
tasks = pd.read_csv(os.path.join(B, "tasks.csv"))
seg = pd.read_csv(os.path.join(B, "source_segment_index.csv"))
cond = json.load(open(os.path.join(B, "common_conditions.json"), encoding="utf-8"))
Z = {"Z0": (0, 0), "Z1": (1, 0), "Z2": (0, 1), "Z3": (1, 1), "Z4": (2, 0)}
train_d = seg[(seg.split == "train") & (seg.eligible == 1)]

def q_dur(fam, q):
    return float(train_d[train_d.family_id == fam].duration_s.quantile(q))

def run(case, alpha, beta, seed, q, split="validation"):
    rng = random.Random(int(seed))
    T = tasks[tasks.case_id == case].sort_values("job_id").reset_index(drop=True)
    pools = {f: seg[(seg.split == split) & (seg.family_id == f) & (seg.eligible == 1)].reset_index(drop=True)
             for f in ["P", "A", "L"]}
    dur, fam_of = {}, {}
    for _, r in T.iterrows():
        pool = pools[r.family_id]
        dur[r.job_id] = float(pool.iloc[rng.randrange(len(pool))].duration_s)
        fam_of[r.job_id] = r.family_id
    C_ = {c["case_id"]: c for c in cond["cases"]}[case]
    H, Bc = float(C_["horizon_s"]), float(C_["cost_budget"])
    info = {r.job_id: dict(release=float(r.release_s), due=float(r.due_s), w=float(r.priority_weight),
                           zone=r.zone_id,
                           pred=[] if pd.isna(r.predecessors) else str(r.predecessors).split("|"))
            for _, r in T.iterrows()}
    done, cost, t, zone, censored = set(), 0.0, 0.0, "Z0", 0
    comp, ontime, tard = {}, {}, {}
    while True:
        avail = [j for j in info if j not in done and info[j]["release"] <= t + 1e-9
                 and all(p in done for p in info[j]["pred"])]
        if not avail:
            nxt = [info[j]["release"] for j in info if j not in done
                   and all(p in done for p in info[j]["pred"]) and info[j]["release"] > t + 1e-9]
            if not nxt or min(nxt) >= H: break
            t = min(nxt); continue
        j = min(avail, key=lambda x: (info[x]["due"], -info[x]["w"], x))
        zx, zy = Z[info[j]["zone"]]; cx, cy = Z[zone]
        D = math.hypot(zx - cx, zy - cy)
        s = t + D + 0.5
        b = max(0.2, alpha * q_dur(fam_of[j], q) + beta)
        c = 2.0 + 0.1 * b + 0.2 * D
        if s + b > H + 1e-9 or cost + c > Bc + 1e-9:
            done.add(j); continue
        cost += c
        p = alpha * dur[j] + beta
        Cend = s + p
        if Cend <= H + 1e-9:
            comp[j] = Cend
            if Cend <= info[j]["due"] + 1e-9: ontime[j] = Cend
            else: tard[j] = Cend - info[j]["due"]
            done.add(j); t = s + max(p, b); zone = info[j]["zone"]
        else:
            censored += 1; done.add(j); break
    W = sum(v["w"] for v in info.values())
    return dict(case=case, q=q, wc=sum(info[j]["w"] for j in comp) / W,
                wo=sum(info[j]["w"] for j in ontime) / W,
                wt=sum(info[j]["w"] * tard.get(j, 0.0) for j in info),
                cost=cost, censored=censored, elapsed=t)

if __name__ == "__main__":
    rows = []
    for q in [0.5, 0.7, 0.8, 0.9, 0.95, 1.0]:
        for case in ["S1", "S2", "S3"]:
            for sd in cond["validation_seeds"]:
                rows.append(run(case, 1.0, 0.5, sd, q))
    df = pd.DataFrame(rows)
    print("== nominal alpha=1 beta=0.5 : mean weighted on-time rate by reservation quantile ==")
    print(df.pivot_table(index="q", columns="case", values="wo", aggfunc="mean").round(3).to_string())
    print("\n== censored trials (out of 30) ==")
    print(df.pivot_table(index="q", columns="case", values="censored", aggfunc="sum").to_string())
    print("\n== mean cost (budget S1=32 S2=34 S3=40) ==")
    print(df.pivot_table(index="q", columns="case", values="cost", aggfunc="mean").round(1).to_string())
