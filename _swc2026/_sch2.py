import sys,io,time,json
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
sys.path.insert(0,r"E:\数学建模\_swc2026\SWC2026_A\code")
import p4_econ as P
P.OUT["_prm"]=json.load(open(r"E:\数学建模\_swc2026\SWC2026_A\data\p4_econ.json",encoding="utf-8"))["_prm"]
t=time.time(); r=P.scheme("Case3",35,1.0,3000,800,0.5,0); print({k:r[k] for k in list(r)[:12]}); print("time",time.time()-t)
