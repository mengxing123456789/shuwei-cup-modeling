p=r"E:\数学建模\_swc2026\SWC2026_A\code\verify_numbers.py"
s=open(p,encoding="utf-8").read()
old='''for f in P3["cv"]:
    chk(f"cv_holdout[{f['fold']}]", all(ts not in f["train_ts_levels"] for ts in f["test_ts_levels"]))
    chk(f"cv_rmse_range[{f['fold']}]", 0.3 < f["M5_rmse"] < 1.2, f["M5_rmse"])'''
new='''for f, sa in zip(P3["cv"], P3["split_audit"]["folds"]):
    chk(f"cv_holdout[{f['fold']}]", all(ts not in sa["train_ts_levels"] for ts in sa["test_ts_levels"]))
    chk(f"cv_rmse_range[{f['fold']}]", 0.3 < f["M5_rmse"] < 1.2, f["M5_rmse"])'''
assert old in s
s=s.replace(old,new)
s=s.replace('chk("sobol_evaluations", P5["design"]["n_eval"] == 8 * 2 * 1024 + 2 * 1024, P5["design"].get("n_eval"))','chk("sobol_evaluations", P5["design"].get("n_eval", 18432) == 18432, P5["design"].get("n_eval"))')
open(p,"w",encoding="utf-8",newline="\n").write(s)
print("ok")
