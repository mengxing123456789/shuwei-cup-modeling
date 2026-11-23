import py_compile, hashlib, re

dst = r"E:\数学建模\_swc2026\SWC2026_C\code\p3_online_alpha2.py"
t = open(dst, encoding="utf-8").read()

# idempotent: only apply if absent
if "alpha_true=None" not in t:
    a = 'def simulate(case,seed,policy="risk_fusion",alpha=1.,beta=.5,reviews_allowed=False):'
    assert a in t
    t = t.replace(a, a[:-2] + ",alpha_true=None):", 1)
if "TRUE_A=alpha if alpha_true is None else alpha_true" not in t:
    a = "TRUE_A,TRUE_B=alpha,beta; EA=[alpha]; EB=[beta]; OBS=[]"
    assert a in t, "TRUE_A line missing"
    t = t.replace(a, "TRUE_A=alpha if alpha_true is None else alpha_true; TRUE_B=beta; EA=[alpha]; EB=[beta]; OBS=[]", 1)

head = t.split("def main():")[0]

new_main = '''def main():
    t0=time.time(); rows=[]
    policies=["slack_old","slack_old_online"]
    TRUE_A_LIST=[0.75,1.0,1.25,1.5]
    for atrue in TRUE_A_LIST:
        for case in ("S1","S2","S3"):
            for policy in policies:
                for seed in SEEDS:
                    r=simulate(case,seed,policy,alpha=1.0,beta=0.5,alpha_true=atrue)
                    r.pop("log",None); r["alpha_true"]=atrue; rows.append(r)
    trials=pd.DataFrame(rows)
    trials.to_csv(os.path.join(DATA,"p3_online2_trials.csv"),index=False)
    agg=[]
    for (atrue,case,policy),g in trials.groupby(["alpha_true","case","policy"]):
        d=dict(alpha_true=float(atrue),case=case,policy=policy,n=len(g))
        for m in ("weighted_on_time_rate","weighted_completion_rate","weighted_tardiness_s",
                  "cost","reserved_idle_s","observed_overrun_s"):
            d[m]=float(g[m].mean()); d[m+"_ci95"]=float(ci95(g[m]))
        agg.append(d)
    summary=pd.DataFrame(agg)
    summary.to_csv(os.path.join(DATA,"p3_online2_summary.csv"),index=False)
    paired=[]
    for atrue in TRUE_A_LIST:
        for case in ("S1","S2","S3"):
            s=trials[(trials.alpha_true==atrue)&(trials.case==case)]
            p=s.pivot(index="seed",columns="policy",values="weighted_on_time_rate")
            d=p["slack_old_online"]-p["slack_old"]
            paired.append(dict(alpha_true=atrue,case=case,
                               old=float(p["slack_old"].mean()),
                               online=float(p["slack_old_online"].mean()),
                               mean_diff=float(d.mean()),ci95=float(ci95(d))))
    out=dict(_meta=dict(
                protocol="corrected actual p=alpha_true*d+beta; C=s+p; availability=s+max(p,b)",
                design=("planner starts from alpha_hat=1.0 in every series; slack_old never updates; "
                        "slack_old_online refits alpha/beta by least squares after each completed job"),
                source="official validation eligible units; 30 common seeds",
                alpha_true_list=TRUE_A_LIST,beta=0.5,
                note="alpha_true=1.0 is the sanity check: both policies must coincide"),
             summary=agg,paired=paired,seconds=time.time()-t0)
    write_json("p3_online_alpha2.json",out)
    print(summary[["alpha_true","case","policy","weighted_on_time_rate",
                   "weighted_completion_rate","reserved_idle_s"]].round(4).to_string(index=False))
    print("PAIRED",json.dumps(paired,ensure_ascii=False))
    print("seconds",round(time.time()-t0,1))


if __name__=="__main__": main()
'''

out = head + new_main
open(dst, "w", encoding="utf-8", newline="\n").write(out)
py_compile.compile(dst, doraise=True)
print("compile ok; TRUE_A_LIST in file:", "TRUE_A_LIST" in open(dst, encoding="utf-8").read())
print("sha256:", hashlib.sha256(open(dst, "rb").read()).hexdigest()[:16])