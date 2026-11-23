import sys,io,json,os
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
R=r"E:\数学建模\_swc2026\SWC2026_D\data"
def flat(o,p="",d=0):
    if d>2: return
    if isinstance(o,dict):
        for k,v in list(o.items())[:20]:
            if isinstance(v,(dict,list)): flat(v,p+k+".",d+1)
            else: print(" ",p+k,"=",v)
    elif isinstance(o,list):
        if o and not isinstance(o[0],(dict,list)): print(" ",p[:-1],"=",o[:6])
        elif o and isinstance(o[0],dict): print(" ",p[:-1],f"[{len(o)} rows]",list(o[0].keys())[:7])
t2=json.load(open(os.path.join(R,"t2_resonance.json"),encoding="utf-8"))
print("### t2_resonance"); flat(t2)
print("\n### t3 verdict"); flat(json.load(open(os.path.join(R,"t3_kepler.json"),encoding="utf-8"))["verdict"])
