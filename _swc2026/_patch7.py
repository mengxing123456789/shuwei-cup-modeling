p=r"E:\数学建模\_swc2026\SWC2026_A\code\make_paper_tables.py"
s=open(p,encoding="utf-8").read()
import re
s2=re.sub(r"\$t_s\^\\ast\$ grid \(d\)", r"$t_s^\\ast$ design grid (d)", s)
print("changed", s2!=s)
open(p,"w",encoding="utf-8",newline="\n").write(s2)
