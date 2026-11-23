import io,sys
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
p=r"E:\数学建模\_swc2026\SWC2026_C\out\03-numbers.md"
s=open(p,encoding="utf-8").read()
print("chars",len(s)); print(s[:3000])
