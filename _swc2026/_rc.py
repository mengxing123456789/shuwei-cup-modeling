import sys,io
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
sys.path.insert(0,r"E:\数学建模\.agents\skills\mathmodeling\scripts")
import mmkit.review_crew as rc
print([ (k,v) for k,v in getattr(rc,"OUTPUT_OF",{}).items() if "总编" in k])
