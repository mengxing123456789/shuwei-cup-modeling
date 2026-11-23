# Inspection only: dump structure of p3_improved_search.json and the job tables.
import json
import os

D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

j = json.load(open(os.path.join(D, "p3_improved_search.json"), encoding="utf-8"))
print("=== p3_improved_search.json ===")
print("KEYS:", list(j.keys()))
for k, v in j.items():
    if isinstance(v, list):
        print(" ", k, "list len", len(v))
        if v and isinstance(v[0], dict):
            print("    first keys:", list(v[0].keys()))
            print("    first item:", json.dumps(v[0], ensure_ascii=False)[:400])
    elif isinstance(v, dict):
        print(" ", k, "dict keys", list(v.keys())[:12])
        for kk, vv in list(v.items())[:3]:
            print("    ", kk, "->", json.dumps(vv, ensure_ascii=False)[:300] if not isinstance(vv, (int, float, str)) else vv)
    else:
        print(" ", k, type(v).__name__, str(v)[:80])

print()
print("=== tasks.csv ===")
p = os.path.join(r"Restocking_Problem_and_Data_EN\Restocking_Tasks_and_Constraints\tasks.csv")
print(open(p, encoding="utf-8").read()[:600])

print()
print("=== p3_duration_predictions.csv head ===")
p2 = os.path.join(D, "p3_duration_predictions.csv")
with open(p2, encoding="utf-8") as f:
    for i, line in enumerate(f):
        print(line.rstrip())
        if i > 4:
            break