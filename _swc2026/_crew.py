import sys
sys.path.insert(0,r"E:\数学建模\.agents\skills\mathmodeling\scripts")
import mmkit.crew as crew
for k,v in crew.OUTPUT_OF.items():
    if "总编" in k or "审阅" in k: print(k,v)
