import sys,io,time
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
sys.path.insert(0,r"E:\数学建模\_swc2026\SWC2026_A\code")
import p4_econ as P
t=time.time(); r=P.scheme("Case3",35,1.0,3000,800,0.5,0); print(r); print("time",time.time()-t)
