import json,sys
from pathlib import Path
sys.path.insert(0, str(Path(r"E:\数学建模\数维杯\03_实战演练\2021_B_ExtremeRainfall\01_code")))
import common as C
d = C.read_json(C.RESULTS/"q4_results.json")
print(json.dumps(d["decomposition"], ensure_ascii=False, indent=1))
print(json.dumps(d["type_criteria"], indent=1))
print("same:", d["same_storm_type"])
