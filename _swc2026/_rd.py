import io,sys
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
for p in [r"E:\数学建模\_swc2026\01-四题第一轮总报告.md", r"E:\数学建模\_swc2026\02-选题建议与评分矩阵.md"]:
    s=open(p,encoding="utf-8").read()
    print("=====",p,len(s),"chars")
    print(s[:1200].replace("\n"," | "))
    print("...TAIL...")
    print(s[-600:].replace("\n"," | "))
