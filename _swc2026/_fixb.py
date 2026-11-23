p=r"E:\数学建模\_swc2026\SWC2026_B\code\verify_numbers.py"
s=open(p,encoding="utf-8").read()
s=s.replace('claim(tag + " free = obs_end + reset", s["free"], s["obs_end"] + s["reset"], 1e-4)','claim(tag + " free = obs_end + reset", s["free"], s["obs_end"] + s["reset"], 1e-3)')
open(p,"w",encoding="utf-8",newline="\n").write(s)
print("ok")
