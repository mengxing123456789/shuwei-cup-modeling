import py_compile, os, pandas as pd

DATA = r"E:\数学建模\_swc2026\SWC2026_C\data"
for f in ("p3_duration_predictions.csv", "p3_duration_predictions_v2.csv"):
    d = pd.read_csv(os.path.join(DATA, f), nrows=3)
    print(f, d.shape, list(d.columns))

src = r"E:\数学建模\_swc2026\SWC2026_C\code\p3_stochastic_schedule.py"
dst = r"E:\数学建模\_swc2026\SWC2026_C\code\p3_schedule_v2.py"
t = open(src, encoding="utf-8").read()
a = 'PRED = pd.read_csv(os.path.join(DATA,"p3_duration_predictions.csv"))'
b = 'PRED = pd.read_csv(os.path.join(DATA,"p3_duration_predictions_v2.csv"))'
assert a in t
t = t.replace(a, b, 1)
t = t.replace('write_json("p3_stochastic_schedule.json",out)', 'write_json("p3_schedule_v2.json",out)', 1)
t = t.replace("p3_stochastic_trials.csv", "p3_v2_trials.csv").replace("p3_stochastic_summary.csv", "p3_v2_summary.csv")
open(dst, "w", encoding="utf-8", newline="\n").write(t)
py_compile.compile(dst, doraise=True)
print("v2 schedule copy ready (non-destructive)")