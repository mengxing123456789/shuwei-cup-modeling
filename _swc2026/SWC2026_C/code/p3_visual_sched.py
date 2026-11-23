
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""P3 v4: protocol-correct, distribution-driven stochastic MPC.

Important correction to p3_schedule.py: actual service is p=alpha*d+beta, hence
C=s+p and next availability=s+max(p,b). The old script accidentally used C=s+d
and t=s+max(d,b), which made its alpha/beta sensitivity incomplete.

Policies compared with identical source samples:
  edf_old / slack_old       : old 8-feature ridge
  edf_fusion / slack_fusion : validation-selected old+phase-TCN fusion
  risk_fusion              : chance-constrained reservation + expected on-time ATC
  rollout_fusion           : two-stage scenario model-predictive control
  oracle                   : nondeployable upper reference, corrected protocol

Review decisions use expected reduction in lateness probability, including the
1-second delay and unit observation cost. No review is forced.
"""
import copy
import json
import math
import os
import random
import time
import numpy as np
import pandas as pd
from common import DATA, ATT, load_tasks, load_zones, load_conditions, load_index, write_json
import p3_schedule as old

SEEDS = list(range(2026111700, 2026111730))
PREFIX = [0.2, 0.6, 1.0]
TASKS = load_tasks(); COND = load_conditions(); INDEX = load_index()
ZONES = {r.zone_id:(float(r.x),float(r.y)) for _,r in load_zones().iterrows()}
PRED = pd.read_csv(os.path.join(DATA,"p3_duration_predictions_v2.csv"))
PREDI = PRED.set_index(["unit_id","prefix"])
UNIT = INDEX[INDEX.eligible==1].reset_index(drop=True)
OLDHAT = old.DHAT.copy()
TR = PRED[PRED.split=="train"].copy(); TR["resid"] = TR.duration-TR.pred
RES = {}
for p in PREFIX:
    for f in ("A","L","P"):
        a = np.sort(TR[(TR.prefix==p)&(TR.family==f)].resid.values)
        RES[(p,f)] = a if len(a)>=8 else np.sort(TR[TR.prefix==p].resid.values)
SCEN_Q = np.linspace(0.05,0.95,19)


def dist(a,b): return math.hypot(ZONES[a][0]-ZONES[b][0],ZONES[a][1]-ZONES[b][1])
def sample_unit(f,rng):
    pool=UNIT[(UNIT.split=="validation")&(UNIT.family_id==f)]
    return pool.iloc[rng.randrange(len(pool))]
def pred(uid,p,f,model):
    if model=="old": return OLDHAT[(uid,p)]
    return float(PREDI.loc[(uid,p),"pred"])
def residuals(uid,p,f,model):
    if model=="old":
        a=old.RES[p]
        return a
    return RES[(p,f)]
def quant(uid,p,f,model,q):
    r=residuals(uid,p,f,model)
    return float(np.quantile(r,q))
def scenarios(uid,p,f,model,alpha,beta):
    r=residuals(uid,p,f,model)
    ds=np.quantile(r,SCEN_Q)
    return alpha*np.maximum(p,pred(uid,p,f,model)+ds)+beta


class Job:
    def __init__(self,row,unit):
        self.jid=row.job_id; self.family=row.family_id; self.release=float(row.release_s)
        self.due=float(row.due_s); self.w=float(row.priority_weight); self.zone=row.zone_id
        self.preds=[] if pd.isna(row.predecessors) else str(row.predecessors).split("|")
        self.unit=unit.unit_id; self.d=float(unit.duration_s); self.prefix=.2
        self.reviews=0; self.started=False; self.done=False; self.dropped=False
        self.C=None; self.on_time=False; self.overrun=0.; self.idle=0.


def simulate(case,seed,policy="risk_fusion",alpha=1.,beta=.5,reviews_allowed=False):
    model="old" if policy.endswith("old") else "fusion"
    conf=[c for c in COND["cases"] if c["case_id"]==case][0]
    H=float(conf["horizon_s"]); B=float(conf["cost_budget"]); K=int(conf["observation_limit"])
    rng=random.Random(seed)
    jobs=[Job(r,sample_unit(r.family_id,rng)) for _,r in TASKS[TASKS.case_id==case].sort_values("job_id").iterrows()]
    t=0.; zone="Z0"; cost=0.; nreview=0; done=set(); log=[]
    while t<H-1e-9 and len(log)<200:
        feasible=[j for j in jobs if not j.started and j.release<=t+1e-9 and all(p in done for p in j.preds)]
        acts=[]
        # Capacity pressure determines the chance level: slack capacity buys insurance,
        # overloaded capacity cannot afford large unused reservations.
        rem=sum(pred(x.unit,x.prefix,x.family,model)*alpha+beta+1.0 for x in jobs if not x.started)
        pressure=rem/max(H-t,1e-6)
        qlevel=float(np.clip(.70-.55*max(0.,pressure-.75),.35,.70))
        for j in feasible:
            ph=alpha*pred(j.unit,j.prefix,j.family,model)+beta
            D=dist(zone,j.zone); s=t+D+.5
            if policy.startswith("risk") or policy.startswith("rollout"):
                b=max(.2,alpha*(pred(j.unit,j.prefix,j.family,model)+quant(j.unit,j.prefix,j.family,model,qlevel))+beta)
            else:
                b=max(.2,ph+.6*alpha*quant(j.unit,j.prefix,j.family,model,.6))
            c=2+.1*b+.2*D
            if s+b<=H+1e-9 and cost+c<=B+1e-9:
                acts.append(dict(j=j,ph=ph,D=D,s=s,b=b,c=c))
        # Expected value of information: only pay if the next prefix improves the
        # probability of on-time completion enough to cover delay and opportunity cost.
        if reviews_allowed and nreview<K and cost+1<=B and t+1<H:
            best=(None,0.)
            for a in acts:
                j=a["j"]
                if j.prefix>=1. or j.reviews>=2: continue
                nx=PREFIX[j.reviews+1]
                ds0=scenarios(j.unit,j.prefix,j.family,model,alpha,beta)
                ds1=scenarios(j.unit,nx,j.family,model,alpha,beta)
                p0=np.mean(a["s"]+ds0<=j.due)
                p1=np.mean(a["s"]+1.+ds1<=j.due)
                gain=j.w*(p1-p0)-.02 # observation fee and delay shadow price
                if gain>best[1]: best=(j,gain)
            if best[0] is not None:
                j=best[0]; j.prefix=PREFIX[j.reviews+1]; j.reviews+=1
                nreview+=1; cost+=1.; t+=1.
                log.append(dict(action="review",job=j.jid,t=t,voi=best[1],cost=cost))
                continue
        if not acts:
            nxt=min([j.release for j in jobs if not j.started and j.release>t+1e-9]+[H])
            if nxt<=t+1e-9 or nxt>=H: break
            log.append(dict(action="wait",t=t,dt=nxt-t)); t=nxt; continue

        def onprob(a):
            if policy=="oracle": return float(a["s"]+alpha*a["j"].d+beta<=a["j"].due)
            ds=scenarios(a["j"].unit,a["j"].prefix,a["j"].family,model,alpha,beta)
            return float(np.mean(a["s"]+ds<=a["j"].due))

        drop=None
        if policy.startswith("edf"):
            a=min(acts,key=lambda a:(a["j"].due,-a["j"].w))
        elif policy=="oracle":
            on=[a for a in acts if a["s"]+alpha*a["j"].d+beta<=a["j"].due+.5]
            if on: a=max(on,key=lambda a:a["j"].w/max(.5,alpha*a["j"].d+beta)*math.exp(-max(0.,a["j"].due-a["s"]-alpha*a["j"].d-beta)/10))
            else: a=max(acts,key=lambda a:a["j"].w/max(.5,alpha*a["j"].d+beta))
        elif policy.startswith("rollout"):
            # Two-stage scenario MPC. Each candidate is evaluated over common duration
            # quantiles; the second stage chooses the best currently feasible successor.
            bestscore=-1e100; a=None
            for cand in acts:
                j=cand["j"]; ds=scenarios(j.unit,j.prefix,j.family,model,alpha,beta)
                total=0.
                for p in ds:
                    C=cand["s"]+p
                    immediate=j.w*float(C<=j.due and C<=H)
                    tn=cand["s"]+max(p,cand["b"])
                    nxt=[x for x in jobs if x is not j and not x.started and x.release<=tn+1e-9 and all(q in done or q==j.jid for q in x.preds)]
                    future=0.
                    for k in nxt:
                        sk=tn+dist(j.zone,k.zone)+.5
                        dk=np.median(scenarios(k.unit,k.prefix,k.family,model,alpha,beta))
                        future=max(future,k.w*float(sk+dk<=k.due and sk+dk<=H))
                    total+=immediate+.65*future-.015*j.w*max(0.,C-j.due)
                score=total/len(ds)-.01*cand["c"]
                if score>bestscore: bestscore=score; a=cand
            # Capacity relief: dropping is a real action only when expected overload
            # makes the lowest-value job harmful to the remaining weighted jobs.
            if pressure>1.0:
                vals=[(x["j"].w*onprob(x)/max(.5,x["ph"]),x) for x in acts]
                worst=min(vals,key=lambda z:z[0])[1]
                if onprob(a)<.20 and worst["j"].w<=a["j"].w: drop=worst["j"]
        else:
            # Risk-sensitive ATC / old slack under the corrected protocol.
            on=[x for x in acts if onprob(x)>=.5]
            if policy.startswith("risk"):
                pool=on if on else acts
                a=max(pool,key=lambda x:x["j"].w*max(.03,onprob(x))/max(.5,x["ph"])*math.exp(-max(0.,x["j"].due-x["s"]-x["ph"])/12.))
            else:
                on2=[x for x in acts if x["s"]+x["ph"]<=x["j"].due+.5]
                if on2:
                    a=max(on2,key=lambda x:x["j"].w/max(.5,x["ph"])*math.exp(-max(0.,x["j"].due-x["s"]-x["ph"])/10.))
                else:
                    a=min(acts,key=lambda x:(x["s"]+x["ph"]-x["j"].due)/max(1.,x["j"].w))
            if pressure>1.05 and onprob(a)<.15:
                drop=min(acts,key=lambda x:x["j"].w*max(.03,onprob(x))/max(.5,x["ph"]))["j"]
        if drop is not None:
            drop.started=True; drop.dropped=True
            log.append(dict(action="drop",job=drop.jid,t=t)); continue
        j=a["j"]; j.started=True
        p=alpha*j.d+beta
        C=a["s"]+p; j.C=C
        cost+=a["c"]
        j.overrun=max(0.,min(p,H-a["s"])-a["b"])
        j.idle=max(0.,a["b"]-p) if C<=H else 0.
        log.append(dict(action="execute",job=j.jid,t=t,s=a["s"],b=a["b"],p=p,C=C,cost=cost))
        if C>H+1e-9: t=H; break
        j.done=True; j.on_time=C<=j.due+1e-9; done.add(j.jid)
        t=a["s"]+max(p,a["b"]); zone=j.zone
    W=sum(j.w for j in jobs)
    comp=sum(j.w for j in jobs if j.done and not j.dropped and j.C<=H)
    ont=sum(j.w for j in jobs if j.done and j.on_time)
    tard=sum(j.w*max(0.,(j.C if j.C is not None else H)-j.due) for j in jobs)
    return dict(case=case,seed=seed,policy=policy,alpha=alpha,beta=beta,
                weighted_completion_rate=comp/W,weighted_on_time_rate=ont/W,
                weighted_tardiness_s=tard,cost=cost,reviews=nreview,elapsed_s=t,
                observed_overrun_s=sum(j.overrun for j in jobs),reserved_idle_s=sum(j.idle for j in jobs),
                censored_units=int(any(j.started and not j.done and not j.dropped for j in jobs)),
                n_done=sum(j.done for j in jobs),n_drop=sum(j.dropped for j in jobs),log=log)


def ci95(x):
    x=np.asarray(x,float); return 1.96*x.std(ddof=1)/math.sqrt(len(x)) if len(x)>1 else 0.


def main():
    t0=time.time(); rows=[]
    policies=["edf_old","slack_old","edf_fusion","slack_fusion","risk_fusion","rollout_fusion"]
    for case in ("S1","S2","S3"):
        for policy in policies+["oracle"]:
            for seed in SEEDS:
                r=simulate(case,seed,policy,reviews_allowed=(policy in ("risk_fusion","rollout_fusion")))
                r.pop("log"); rows.append(r)
    trials=pd.DataFrame(rows); trials.to_csv(os.path.join(DATA,"p3_stochastic_trials.csv"),index=False)
    agg=[]
    for (case,policy),g in trials.groupby(["case","policy"]):
        d=dict(case=case,policy=policy,n=len(g))
        for m in ("weighted_on_time_rate","weighted_completion_rate","weighted_tardiness_s","cost","reviews","reserved_idle_s","observed_overrun_s"):
            d[m]=float(g[m].mean()); d[m+"_ci95"]=float(ci95(g[m]))
        agg.append(d)
    summary=pd.DataFrame(agg); summary.to_csv(os.path.join(DATA,"p3_stochastic_summary.csv"),index=False)
    paired=[]
    for case in ("S1","S2","S3"):
        p=trials[trials.case==case].pivot(index="seed",columns="policy",values="weighted_on_time_rate")
        for pol in policies:
            if pol=="slack_old": continue
            d=p[pol]-p.slack_old
            paired.append(dict(case=case,policy=pol,mean_diff=float(d.mean()),ci95=float(ci95(d))))
    mappings=[]
    for alpha,beta in old.MAPPINGS:
        for case in ("S1","S2","S3"):
            for policy in ("slack_old","slack_fusion","risk_fusion"):
                g=[simulate(case,s,policy,alpha,beta) for s in SEEDS]
                mappings.append(dict(case=case,policy=policy,alpha=alpha,beta=beta,
                    eta=float(np.mean([r["weighted_on_time_rate"] for r in g])),
                    completion=float(np.mean([r["weighted_completion_rate"] for r in g])),
                    cost=float(np.mean([r["cost"] for r in g]))))
    out=dict(_meta=dict(protocol="corrected actual p=alpha*d+beta; C=s+p; availability=s+max(p,b)",
                        source="official validation eligible units; 30 common seeds; sorted jobs",
                        model="visual_a300 duration model (v2 table); conditional family/prefix train residual distributions",
                        risk="capacity-pressure chance reservation q=clip(.70-.55*max(pressure-.75),.35,.70)",
                        rollout="19 common duration quantiles, two-stage stochastic MPC, no future true duration",
                        reviews="expected lateness-probability gain net of 1s delay and cost shadow price"),
             summary=agg,paired_vs_slack_old=paired,mapping_sensitivity=mappings,seconds=time.time()-t0)
    write_json("p3_visual_schedule.json",out)
    print(summary[["case","policy","weighted_on_time_rate","weighted_completion_rate","weighted_tardiness_s","cost","reviews","reserved_idle_s"]].round(4).to_string(index=False))
    print("PAIRED",json.dumps(paired,ensure_ascii=False))
    print("seconds",round(time.time()-t0,1))


if __name__=="__main__": main()