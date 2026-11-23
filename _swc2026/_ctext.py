import fitz,io,sys,re
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
p=r"E:\数学建模\数维杯\2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）赛题\C题\2026_“ShuWei Cup”C_Problem.pdf"
t="".join(x.get_text() for x in fitz.open(p))
print("chars",len(t))
for kw in ["Data_Documentation","file_manifest","missing_observation","tasks_and_evaluation","attachment_guide","record_index"]:
    for m in re.finditer(kw,t):
        s=max(0,m.start()-120); print("---",kw,":",t[s:m.start()+160].replace("\n"," "))
        break
print("\n\n=== masking paragraph ===")
i=t.find("defensible")
print(t[max(0,i-700):i+400].replace("\n"," ") if i>0 else "not found")
