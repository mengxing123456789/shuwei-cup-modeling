import sys, json
from pathlib import Path
sys.path.insert(0, r"E:\数学建模\数维杯\03_实战演练\2021_B_ExtremeRainfall\01_code")
import common as C
for name in ["q1_results","q2_results","q3_results"]:
    d = C.read_json(C.RESULTS/f"{name}.json")
    print("="*20, name)
    print(json.dumps(d, ensure_ascii=False)[:2600])
