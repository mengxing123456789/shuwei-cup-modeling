import sys,io,importlib.util as u
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
spec=u.spec_from_file_location("p2",r"E:\数学建模\_swc2026\_c_p3_probe2.py")
m=u.module_from_spec(spec); spec.loader.exec_module(m)
# monkeypatch: replicate with logging
import math,random,pandas as pd
def trace(case,alpha,beta,seed,q):
    rng=random.Random(int(seed)); T=m.tasks[m.tasks.case_id==case].sort_values("job_id").reset_index(drop=True)
    pools={f:m.seg[(m.seg.split=="validation")&(m.seg.family_id==f)&(m.seg.eligible==1)].reset_index(drop=True) for f in ["P","A","L"]}
    dur={};fam={}
    for _,r in T.iterrows():
        pool=pools[r.family_id];dur[r.job_id]=float(pool.iloc[rng.randrange(len(pool))].duration_s);fam[r.job_id]=r.family_id
    C_={c["case_id"]:c for c in m.cond["cases"]}[case];H=float(C_["horizon_s"]);Bc=float(C_["cost_budget"])
    info={r.job_id:dict(release=float(r.release_s),due=float(r.due_s),w=float(r.priority_weight),zone=r.zone_id,pred=[] if pd.isna(r.predecessors) else str(r.predecessors).split("|")) for _,r in T.iterrows()}
    done=set();cost=0.;t=0.;zone="Z0"
    while True:
        avail=[j for j in info if j not in done and info[j]["release"]<=t+1e-9 and all(p in done for p in info[j]["pred"])]
        if not avail:
            nxt=[info[j]["release"] for j in info if j not in done and all(p in done for p in info[j]["pred"]) and info[j]["release"]>t+1e-9]
            if not nxt or min(nxt)>=H: print("  stop: no avail, t=%.1f"%t); break
            t=min(nxt); continue
        j=min(avail,key=lambda x:(info[x]["due"],-info[x]["w"],x))
        zx,zy=m.Z[info[j]["zone"]];cx,cy=m.Z[zone];D=math.hypot(zx-cx,zy-cy);s=t+D+0.5
        b=max(0.2,alpha*m.q_dur(fam[j],q)+beta);c=2.0+0.1*b+0.2*D
        print("  t=%.1f avail=%d pick=%s due=%.0f w=%d D=%.1f b=%.2f c=%.2f s=%.2f s+b=%.2f cost=%.1f dur=%.2f"%(t,len(avail),j,info[j]["due"],info[j]["w"],D,b,c,s,s+b,cost,dur[j]))
        if s+b>H+1e-9 or cost+c>Bc+1e-9:
            print("    -> skip infeasible"); done.add(j); continue
        cost+=c;p=alpha*dur[j]+beta;Ce=s+p
        if Ce<=H+1e-9:
            print("    -> done C=%.2f"%Ce); t=s+max(p,b);zone=info[j]["zone"];done.add(j)
        else:
            print("    -> CENSOR C=%.1f > H"%Ce);break
print("=== S1 q=0.95 ===")
trace("S1",1,0.5,2026111700,0.95)
