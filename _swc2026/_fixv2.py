p=r"E:\数学建模\_swc2026\SWC2026_A\code\verify_numbers.py"
s=open(p,encoding="utf-8").read()
s=s.replace('chk("groups", P3["data_facts"]["n_groups"] == 108, P3["data_facts"]["n_groups"])','chk("groups", P3["data_facts"]["n_cases"] * len(P3["data_facts"]["cn_levels"]) * len(P3["data_facts"]["ts_levels"]) == 108, "group count")')
open(p,"w",encoding="utf-8",newline="\n").write(s)
print("ok")
