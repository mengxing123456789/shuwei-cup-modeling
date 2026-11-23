import sys,io,random,pandas as pd
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
sys.path.insert(0,r"E:\数学建模\_swc2026")
import importlib.util as u
spec=u.spec_from_file_location("probe",r"E:\数学建模\_swc2026\_c_p3_probe.py")
m=u.module_from_spec(spec); spec.loader.exec_module(m)
seg=m.seg
v=seg[(seg.split=="validation")&(seg.eligible==1)]
print(v.groupby("family_id").duration_s.describe())
T=m.tasks[m.tasks.case_id=="S1"]
rng=random.Random(2026111700)
pools={f:m.sample_pool("validation",f,rng) for f in ["P","A","L"]}
for _,r in T.sort_values("job_id").iterrows():
    pool=pools[r.family_id]; pick=pool.iloc[rng.randrange(len(pool))]
    print(r.job_id,r.family_id,"->",float(pick.duration_s), "due",r.due_s,"w",r.priority_weight)
