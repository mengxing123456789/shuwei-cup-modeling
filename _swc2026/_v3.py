import sys,io,json
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
d=json.load(open(r"E:\数学建模\_swc2026\SWC2026_A\data\p3_decline.json",encoding="utf-8"))
def walk(o,p="",depth=0):
    if depth>2: return
    if isinstance(o,dict):
        for k,v in list(o.items())[:14]:
            if isinstance(v,(dict,list)): print(" "*depth,p+k,type(v).__name__); walk(v,p+k+".",depth+1)
            else: print(" "*depth,p+k,"=",v)
    elif isinstance(o,list):
        print(" "*depth,p,"list len",len(o))
        if o and isinstance(o[0],dict): print(" "*depth,"  keys:",list(o[0].keys())[:10])
walk(d)
