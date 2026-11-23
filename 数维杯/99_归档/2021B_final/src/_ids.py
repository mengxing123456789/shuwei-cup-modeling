import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import pandas as pd
import common as C

d = pd.read_csv(C.RESULTS / "q2_city_trends.csv")
print(len(d))
for _, r in d.sort_values("id").iterrows():
    print(f'    "{r["id"]}",  # {r["city"]}')
