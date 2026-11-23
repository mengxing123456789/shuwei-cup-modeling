import sys,io
sys.path.insert(0,r"E:\数学建模\_swc2026\SWC2026_A\code")
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
import mm_common as MC
print("CASE_KEYS",MC.CASE_KEYS)
for k,v in MC.GEO.items():
    print("GEO",k,{kk:vv for kk,vv in v.items() if not isinstance(vv,(list,dict))})
print()
for k,v in MC.FRAC.items():
    print("FRAC",k,v)
