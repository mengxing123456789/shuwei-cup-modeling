import sys
sys.path.insert(0,r"E:\数学建模\.agents\skills\mathmodeling\scripts")
import pipeline
from pathlib import Path
p=Path(r"E:\数学建模\_swc2026\SWC2026_A")
for g in ["G6","G7","G8","G9","G12","G16","G18","G19","G20"]:
    try:
        r=pipeline.GATES[g][1](p); print(g,r[0],str(r[1])[:80])
    except Exception as e: print(g,"ERR",type(e).__name__)
