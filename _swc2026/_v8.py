import sys,io,json,os
sys.path.insert(0,r"E:\数学建模\_swc2026\SWC2026_A\code")
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
import p4_econ as PE, p3_decline as P3, mm_common as MC
R=r"E:\数学建模\_swc2026\SWC2026_A"
d3=json.load(open(os.path.join(R,"data","p3_decline.json"),encoding="utf-8"))
prm={}
for c in MC.CASE_KEYS:
    m=d3["M5_params"][c]
    prm[c]=dict(Ainf=m["Ainf"],tau=m["tau"],p=m["p"],a=m["a"],
                D=d3["shared_D"][c]["D"], **{k:v for k,v in PE.__dict__.items() if False})
# need full param set like main(); instead call main-lite: replicate lines 279-299
for c in MC.CASE_KEYS:
    m=d3["M5_params"][c]
    prm[c].update(dict(**(d3.get("case_params",{}) or {})))
print("keys:",list(prm["Case1"].keys()))
