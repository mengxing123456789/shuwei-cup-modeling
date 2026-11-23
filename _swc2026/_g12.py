import sys
sys.path.insert(0,r"<skill>\scripts")
import pipeline
from pathlib import Path
p=Path(r"E:\数学建模\_swc2026\SWC2026_A")
print(pipeline.GATES["G12"][1](p))
