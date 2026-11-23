import re
p=r"E:\数学建模\_swc2026\SWC2026_A\main.tex"
t=open(p,encoding="utf-8").read()
# strip preamble
body=t.split(r"\begin{document}")[1].split(r"\end{document}")[0]
# rough sentence split
sents=[s.strip() for s in re.split(r"(?<=[.!?])\s+",re.sub(r"\s+"," ",body)) if len(s.strip())>20]
print("sentences",len(sents))
from collections import Counter
starts=Counter(s.split()[0] for s in sents if s.split())
print("top starts",starts.most_common(8))
pats=["not only","crucial","delve","robust","novel","it is worth","In this paper","This paper","plays a key role","significant","Moreover","Furthermore","Therefore"]
for q in pats:
    c=sum(1 for s in sents if q.lower() in s.lower())
    print(q,c)
# long sentences
ls=[len(s.split()) for s in sents]
print("mean len",sum(ls)/len(ls),"max",max(ls),"cv", (sum((x-sum(ls)/len(ls))**2 for x in ls)/len(ls))**.5/(sum(ls)/len(ls)))
