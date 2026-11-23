import sys,io
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
sys.path.insert(0,r"E:\数学建模\.agents\skills\mathmodeling\scripts")
import mmkit.crew as crew
for k,v in crew.OUTPUT_OF.items():
    if "总编" in k or "评审" in k or "review" in str(v): print(repr(k),"=>",v)
