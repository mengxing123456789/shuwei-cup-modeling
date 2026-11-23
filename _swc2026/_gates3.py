import sys,time
sys.path.insert(0,r"E:\数学建模\.agents\skills\mathmodeling\scripts")
import pipeline
from pathlib import Path
p=Path(r"E:\数学建模\_swc2026\SWC2026_A")
for g in ["G6","G7","G8","G10","G12","G14","G15","G17","G18"]:
    print(">>>",g,flush=True)
    t=time.time()
    try:
        r=pipeline.GATES[g][1](p); print(g,r[0],str(r[1])[:100],"%.1fs"%(time.time()-t),flush=True)
    except Exception as e:
        print(g,"ERR",type(e).__name__,str(e)[:80],flush=True)
