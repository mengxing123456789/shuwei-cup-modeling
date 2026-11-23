import json
rows=json.load(open(r"E:\数学建模\_swc2026\modex_re\step_review_report.strings.json",encoding='utf-8')) if __import__('os').path.exists(r"E:\数学建模\_swc2026\modex_re\step_review_report.strings.json") else []
print(len(rows))
for r in rows:
    s=r['s']
    if any(k in s for k in ["snapshot","added","removed","changes","files","notes","summary","count","vision","precompile"]):
        print(repr(s[:300]))
