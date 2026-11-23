import sys,io,json,os,glob
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
B=r"E:\数学建模\_swc2026\SWC2026_B\data"
for f in sorted(glob.glob(os.path.join(B,"*.json"))):
    print("##",os.path.basename(f),os.path.getsize(f))
    try: d=json.load(open(f,encoding="utf-8"))
    except Exception as e: print("  parse err"); continue
    if isinstance(d,dict):
        for k in list(d.keys())[:12]:
            v=d[k]
            if not isinstance(v,(dict,list)): print("   ",k,"=",v)
            else: print("   ",k,type(v).__name__,len(v))
