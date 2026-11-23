import re
s=open(r"E:\数学建模\_swc2026\SWC2026_A\main.tex",encoding="utf-8").read()
bad=sorted({c for c in s if ord(c)>127})
print("NONASCII:", "".join(bad) if bad else "none")
