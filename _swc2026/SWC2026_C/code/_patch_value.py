from pathlib import Path
p = Path(r"code\make_value_figure.py")
t = p.read_text(encoding="utf-8")
t = t.replace('p3 = json.loads((DATA / "p3_scheduling.json").read_text(encoding="utf-8"))',
              'p3 = json.loads((DATA / "p3_stochastic_schedule.json").read_text(encoding="utf-8"))')
t = t.replace('rows = [r for r in p3["summary"] if r["alpha"] == 1.0 and r["beta"] == 0.5]\nrate = {(r["case"], r["policy"]): r["weighted_on_time_rate"] for r in rows}',
              'rows = p3["summary"]\nrate = {(r["case"], r["policy"]): r["weighted_on_time_rate"] for r in rows}')
t = t.replace('rule = 100.0 * (rate[(case, "slack")] - rate[(case, "edf")])',
              'rule = 100.0 * (rate[(case, "slack_old")] - rate[(case, "edf_old")])')
p.write_text(t, encoding="utf-8")
print("patched")
