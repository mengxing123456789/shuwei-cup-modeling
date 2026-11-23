import sys
sys.path.insert(0,r"E:\数学建模\.agents\skills\mathmodeling\scripts")
import pipeline
from pathlib import Path
p=Path(r"E:\数学建模\_swc2026\SWC2026_A")
for g in ["G6","G7","G8","G9","G10","G11","G12","G13","G14","G15","G17","G18","G19"]:
    fn=pipeline.GATES[g][1]
    try:
        r=fn(p)
        print(g, r[0], str(r[1])[:120])
    except Exception as e:
        print(g,"ERR",type(e).__name__,str(e)[:100])
