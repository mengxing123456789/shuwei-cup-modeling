import sys
sys.path.insert(0,r"E:\数学建模\.agents\skills\mathmodeling\scripts")
import pipeline
from pathlib import Path
p=Path(r"E:\数学建模\_swc2026\SWC2026_A")
for g in ["G1","G2","G20","G3","G4","G5","G16"]:
    fn=pipeline.GATES[g][1]
    try:
        print(g, fn(p))
    except Exception as e:
        print(g,"ERR",type(e).__name__,e)
