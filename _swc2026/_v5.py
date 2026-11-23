import sys,io,json
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
B=r"E:\数学建模\_swc2026\SWC2026_B\data"
d=json.load(open(B+r"\p3.json",encoding="utf-8"))["p3"]
for k,v in d.items():
    if not isinstance(v,(list,dict)): print(k,"=",v)
    else: print(k,type(v).__name__,len(v), (list(v.keys())[:8] if isinstance(v,dict) else ""))
print()
p=json.load(open(B+r"\p2.json",encoding="utf-8"))["p2_1"]
for k,v in p.items():
    if not isinstance(v,(list,dict)): print("p2_1.",k,"=",v)
print()
q=json.load(open(B+r"\p1.json",encoding="utf-8"))["p1_T1"]
for k,v in q.items():
    if not isinstance(v,(list,dict)): print("p1_T1.",k,"=",v)
