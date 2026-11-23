import sys,io,os,json
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
R=r"E:\数学建模\_swc2026\SWC2026_A"
for d in ["data","code","problem"]:
    p=os.path.join(R,d)
    if os.path.isdir(p):
        print("##",d)
        for f in sorted(os.listdir(p))[:25]:
            fp=os.path.join(p,f); print("   ",f, os.path.getsize(fp) if os.path.isfile(fp) else "<dir>")
