import sys,io,json,os
sys.path.insert(0,r"E:\数学建模\_swc2026\SWC2026_A\code")
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
import p4_econ as PE, mm_common as MC
R=r"E:\数学建模\_swc2026\SWC2026_A"; D3=json.load(open(os.path.join(R,"data","p3_decline.json"),encoding="utf-8"))
prm={c:dict(Ainf=D3['M5_params'][c]['Ainf'],tau=D3['M5_params'][c]['tau'],p=D3['M5_params'][c]['p'],
            a=D3['M5_params'][c]['a'],D=D3['shared_D'][c]['D'],D_sd=D3['shared_D'][c]['D_sd']) for c in MC.CASE_KEYS}
PE.OUT['_prm']=prm
print("=== tau_inj sweep: ts=30, cn=1.0, Vinj=3000, qinj=300, fCO2=0.5 ===")
for c in MC.CASE_KEYS:
    row=[(tau, round(PE.scheme(c,30.0,cn=1.0,Vinj=3000.0,qinj=300.0,fCO2=0.5,tau_inj=float(tau))["npv"],2)) for tau in (0,3,7,15)]
    print("  ",c,row)
print()
print("=== qinj sweep: ts=30, cn=1.0, Vinj=3000, fCO2=0.5, tau=0 ===")
for c in MC.CASE_KEYS:
    row=[]
    for q in (100,200,300,500,800):
        try: row.append((q, round(PE.scheme(c,30.0,cn=1.0,Vinj=3000.0,qinj=float(q),fCO2=0.5,tau_inj=0.0)["npv"],2)))
        except Exception as e: row.append((q,"ERR"))
    print("  ",c,row)
