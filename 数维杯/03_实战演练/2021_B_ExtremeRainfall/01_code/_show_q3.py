import json,sys
from pathlib import Path
sys.path.insert(0, str(Path(r"E:\数学建模\数维杯\03_实战演练\2021_B_ExtremeRainfall\01_code")))
import common as C
d=C.read_json(C.RESULTS/"q3_results.json")
print("n_test_years dist:", d["n_test_years"])
print("mle_unstable:", d["mle_unstable_cities"])
for r in d["record_breakers"]:
    print(f'  {r["city"]:12s} train_max {r["max_rx1day_train"]:6.1f}  test_max {r["obs_max_rx1day"]:6.1f} in {r["obs_max_year"]}  (T={r["n_test"]})')
print("best reg:", d["best_regression"], "| best cls:", d["best_classification"])
