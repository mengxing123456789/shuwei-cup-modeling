import sys,io,json,os,glob
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
R=r"E:\数学建模\_swc2026\SWC2026_D"
for f in sorted(glob.glob(os.path.join(R,"data","*.json"))):
    print("##",os.path.basename(f),os.path.getsize(f))
    d=json.load(open(f,encoding="utf-8"))
    if isinstance(d,dict):
        for k,v in list(d.items())[:14]:
            if not isinstance(v,(dict,list)): print("   ",k,"=",v)
            else: print("   ",k,type(v).__name__,len(v))
print()
for p in ["out\\01-model.md","out\\03-numbers.md"]:
    fp=os.path.join(R,p)
    if os.path.exists(fp): print("##",p,os.path.getsize(fp),"B")
