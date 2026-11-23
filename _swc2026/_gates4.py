import sys
sys.path.insert(0,r"E:\数学建模\.agents\skills\mathmodeling\scripts")
import pipeline
from pathlib import Path
p=Path(r"E:\数学建模\_swc2026\SWC2026_A")
for g in ["G1","G2","G3","G4","G5","G6","G7","G8","G13","G15","G16","G17","G18","G19","G20"]:
    try:
        r=pipeline.GATES[g][1](p); print(g,r[0],str(r[1])[:90])
    except Exception as e: print(g,"ERR",type(e).__name__,str(e)[:60])
