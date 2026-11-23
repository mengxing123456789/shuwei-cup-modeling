import io,sys,os
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
d=r"E:\数学建模\_swc2026\SWC2026_C\code"
for f in sorted(os.listdir(d)):
    print(f, os.path.getsize(os.path.join(d,f)))
s=open(os.path.join(d,"build_panel.py"),encoding="utf-8").read() if os.path.exists(os.path.join(d,"build_panel.py")) else ""
import re
for m in re.finditer(r"Q\[|Q =|head|headcam|quat", s):
    pass
print("---- Q construction ----")
i=s.find("Q")
print(s[max(0,i-200):i+700] if s else "no file")
