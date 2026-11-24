import json
out=[]
for fn,kws in [("artifact_context",["get_artifact_context","artifact","context","workflow","node","edge","preview","read","path","kind","label"]),("workflow_engine",["PROBLEM_FACTS","CROSS_PROBLEM_LEDGER","FIGURE_MANIFEST"])]:
    rows=json.load(open(rf"E:\数学建模\_swc2026\modex_re\{fn}.strings.json",encoding='utf-8'))
    out.append(f"==== {fn} rows={len(rows)}")
    for r in rows:
        s=r['s']
        if any(k in s for k in kws) and len(s)>15:
            # only human-readable: ratio of printable/CJK
            good=sum(1 for ch in s if 32<=ord(ch)<127 or '\u4e00'<=ch<='\u9fff')
            if good/len(s)>0.85:
                out.append(s)
open(r"E:\数学建模\_swc2026\modex_re\ctx_strings.txt","w",encoding="utf-8").write("\n---\n".join(out))
print(len(out))
