import json, re
fp=r"E:\数学建模\_swc2026\modex_re\workflow_acceptance.strings.json"
rows=json.load(open(fp,encoding='utf-8'))
seen=set(); out=[]
for r in rows:
    s=r['s']
    if r['sec']!='.rdata': continue
    if len(s)<8: continue
    good=sum(1 for ch in s if 32<=ord(ch)<127 or '\u4e00'<=ch<='\u9fff')
    if good/len(s)<0.92: continue
    if s in seen: continue
    seen.add(s)
    # skip Cython boilerplate
    if re.search(r'PyInit|cp311|\.c$|\.py$|__pyx|coroutine|metaclass|PyObject|%\.|import', s): continue
    out.append(s)
open(r"E:\数学建模\_swc2026\modex_re\acc_strings_clean.txt","w",encoding="utf-8").write("\n".join(out))
print(len(out))
