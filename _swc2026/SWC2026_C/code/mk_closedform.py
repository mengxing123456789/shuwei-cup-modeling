
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""Generate an instrumented copy of the corrected scheduler.

The scheduler is the one artefact that must stay untouched: every number in the
frozen submission comes from it.  So instead of editing it, this script reads it and
writes a sibling with one addition, a per-job record at the moment a job completes.

What the record is for
----------------------
Line 182 of the scheduler sets the realised service time to `p = alpha*j.d + beta`,
and line 189 decides on time as `C <= j.due`.  Substituting gives an exact condition,

    on time  <=>  s + alpha*d + beta <= due  <=>  d <= (due - s - beta)/alpha

so the probability that a job with a released prefix of length s meets its due date is

    P(on time | s, due, alpha) = F_d( (due - s - beta)/alpha ),

where F_d is the predictive law of the source duration, conditional on the family.
Note that the reservation b does not appear: it buys starts, not punctuality.  And
alpha enters only as the scale 1/alpha inside the argument, which is why the whole
mapping-sensitivity table should collapse onto one curve F_d((due-s-beta)/alpha).  The
per-job dump lets us test that against realised outcomes instead of asserting it.

Output
    code/p3_closedform.py   instrumented copy, writes data/p3_jobs.csv
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "code", "p3_stochastic_schedule.py")
DST = os.path.join(ROOT, "code", "p3_closedform.py")

ANCHOR = "        j.done=True; j.on_time=C<=j.due+1e-9; done.add(j.jid)"
INJECT = """        j.done=True; j.on_time=C<=j.due+1e-9; done.add(j.jid)
        JOBROWS.append(dict(case=case,seed=seed,policy=policy,alpha=alpha,beta=beta,
                            jid=j.jid,s=a["s"],b=a["b"],p=p,d=j.d,due=j.due,
                            family=j.family,prefix=j.prefix,on_time=bool(j.on_time),
                            C=C,w=j.w))
"""

MAIN_OLD = """    policies=["edf_old","slack_old","edf_fusion","slack_fusion","risk_fusion","rollout_fusion"]
    for case in ("S1","S2","S3"):
        for policy in policies+["oracle"]:
            for seed in SEEDS:
                r=simulate(case,seed,policy,reviews_allowed=(policy in ("risk_fusion","rollout_fusion")))
                r.pop("log"); rows.append(r)"""
MAIN_NEW = """    policies=["edf_old","slack_old","oracle"]
    for case in ("S1","S2","S3"):
        for policy in policies:
            for al in (0.75,1.0,1.5):
                for seed in SEEDS:
                    r=simulate(case,seed,policy,alpha=al,beta=0.5,
                               reviews_allowed=False)
                    r.pop("log"); rows.append(r)"""


def main():
    with open(SRC, "r", encoding="utf-8") as f:
        src = f.read()
    if ANCHOR not in src:
        raise SystemExit("anchor not found, scheduler changed; re-read it first")
    if MAIN_OLD not in src:
        raise SystemExit("main loop not found, scheduler changed; re-read it first")
    src = src.replace("import time", "import time\nJOBROWS=[]", 1)
    src = src.replace(ANCHOR, INJECT, 1)
    src = src.replace(MAIN_OLD, MAIN_NEW, 1)
    # dump the per-job rows next to the trial table
    TRIALS_OLD = ('trials=pd.DataFrame(rows); '
                  'trials.to_csv(os.path.join(DATA,"p3_stochastic_trials.csv"),index=False)')
    TRIALS_NEW = ('trials=pd.DataFrame(rows); '
                  'trials.to_csv(os.path.join(DATA,"p3_closedform_trials.csv"),index=False)\n'
                  '    pd.DataFrame(JOBROWS).to_csv(os.path.join(DATA,"p3_jobs.csv"),index=False)')
    if TRIALS_OLD not in src:
        raise SystemExit("trial dump line not found")
    src = src.replace(TRIALS_OLD, TRIALS_NEW, 1)
    src = src.replace('"p3_stochastic_schedule.json"', '"p3_closedform.json"')
    with open(DST, "w", encoding="utf-8") as f:
        f.write(src)
    print("wrote", DST, len(src), "bytes")


if __name__ == "__main__":
    main()