import sys,io,importlib.util as u,math,random,pandas as pd
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
spec=u.spec_from_file_location("p2",r"E:\数学建模\_swc2026\_c_p3_probe2.py")
m=u.module_from_spec(spec); spec.loader.exec_module(m)
def run_oracle(case,alpha,beta,seed,split="validation"):
    rng=random.Random(int(seed));T=m.tasks[m.tasks.case_id==case].sort_values("job_id").reset_index(drop=True)
    pools={f:m.seg[(m.seg.split==split)&(m.seg.family_id==f)&(m.seg.eligible==1)].reset_index(drop=True) for f in ["P","A","L"]}
    dur={};fam={}
    for _,r in T.iterrows():
        pool=pools[r.family_id];dur[r.job_id]=float(pool.iloc[rng.randrange(len(pool))].duration_s);fam[r.job_id]=r.family_id
    C_={c["case_id"]:c for c in m.cond["cases"]}[case];H=float(C_["horizon_s"]);Bc=float(C_["cost_budget"])
    info={r.job_id:dict(release=float(r.release_s),due=float(r.due_s),w=float(r.priority_weight),zone=r.zone_id,pred=[] if pd.isna(r.predecessors) else str(r.predecessors).split("|")) for _,r in T.iterrows()}
    done=set();cost=0.;t=0.;zone="Z0";comp={};ontime={};tard={}
    while True:
        avail=[j for j in info if j not in done and info[j]["release"]<=t+1e-9 and all(p in done for p in info[j]["pred"])]
        if not avail:
            nxt=[info[j]["release"] for j in info if j not in done and all(p in done for p in info[j]["pred"]) and info[j]["release"]>t+1e-9]
            if not nxt or min(nxt)>=H: break
            t=min(nxt);continue
        j=min(avail,key=lambda x:(info[x]["due"],-info[x]["w"],x))
        zx,zy=m.Z[info[j]["zone"]];cx,cy=m.Z[zone];D=math.hypot(zx-cx,zy-cy);s=t+D+0.5
        p=alpha*dur[j]+beta;b=max(0.2,p);c=2.0+0.1*b+0.2*D
        if s+b>H+1e-9 or cost+c>Bc+1e-9: done.add(j);continue
        cost+=c;Ce=s+p
        if Ce<=H+1e-9:
            comp[j]=Ce
            if Ce<=info[j]["due"]+1e-9: ontime[j]=Ce
            else: tard[j]=Ce-info[j]["due"]
            done.add(j);t=s+max(p,b);zone=info[j]["zone"]
        else: break
    W=sum(v["w"] for v in info.values())
    return dict(case=case,wo=sum(info[j]["w"] for j in ontime)/W,wc=sum(info[j]["w"] for j in comp)/W,wt=sum(info[j]["w"]*tard.get(j,0) for j in info),cost=cost)
rows=[run_oracle(c,1,0.5,s) for c in ["S1","S2","S3"] for s in m.cond["validation_seeds"]]
df=pd.DataFrame(rows); print("ORACLE (true p reserved): mean over 30 seeds")
print(df.groupby("case")[["wo","wc","wt","cost"]].mean().round(3).to_string())
print("\nmin on-time:",df.groupby("case").wo.min().round(3).to_dict())
