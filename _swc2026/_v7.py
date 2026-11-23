import sys,io,os
sys.path.insert(0,r"E:\数学建模\_swc2026\SWC2026_A\code")
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
import p4_econ as PE
import numpy as np
print("=== tau_inj sweep (Case1/2/3, ts=30, Cn=1.0, Vinj=3000, fCO2=0.5) ===")
for c in ("Case1","Case2","Case3"):
    row=[]
    for tau in (0,3,7,15):
        r=PE.scheme(c,30.0,cn=1.0,Vinj=3000.0,qinj=300.0,fCO2=0.5,tau_inj=float(tau))
        row.append((tau, round(r["npv"],2), round(r.get("cost_nom",0),1)))
    print(" ",c,row)
print()
print("=== qinj sweep (Case3, ts=30, Cn=1.0, Vinj=3000, fCO2=0.5) ===")
for c in ("Case1","Case3"):
    row=[]
    for q in (100,200,300,500,800):
        try:
            r=PE.scheme(c,30.0,cn=1.0,Vinj=3000.0,qinj=float(q),fCO2=0.5,tau_inj=0.0)
            row.append((q, round(r["npv"],2)))
        except Exception as e: row.append((q,"ERR "+str(e)[:40]))
    print(" ",c,row)
