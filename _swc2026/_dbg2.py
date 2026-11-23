import sys,io,importlib.util as u,pandas as pd
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
spec=u.spec_from_file_location("probe",r"E:\数学建模\_swc2026\_c_p3_probe.py")
m=u.module_from_spec(spec); spec.loader.exec_module(m)
for s in [2026111700,2026111701,2026111702]:
    r=m.run("S1",1.0,0.5,s); print(r)
