import io
p=r"E:\数学建模\_swc2026\01-四题第一轮总报告.md"
s=open(p,encoding="utf-8").read()
s=s.replace("data 7 JSON；figures 8 组；tables 12","data 8 JSON；figures 8 组；tables 12")
s=s.replace("data 7 JSON / figures 8 组 / tables 12","data 8 JSON / figures 8 组 / tables 12")
open(p,"w",encoding="utf-8",newline="\n").write(s)
print("ok")
