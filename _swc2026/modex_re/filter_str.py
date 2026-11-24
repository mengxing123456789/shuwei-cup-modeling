import json, re, sys
files = [r"E:\数学建模\_swc2026\modex_re\ckpt_runtime.strings.json", r"E:\数学建模\_swc2026\modex_re\ckpt_router.strings.json"]
for fp in files:
    print("="*20, fp)
    rows=json.load(open(fp,encoding='utf-8'))
    seen=set()
    for r in rows:
        s=r['s']
        if r['sec']!='.rdata': continue
        if len(s)<6: continue
        # printable ascii or CJK
        good=sum(1 for ch in s if 32<=ord(ch)<127 or '\u4e00'<=ch<='\u9fff')
        if good/len(s)<0.9: continue
        if s in seen: continue
        seen.add(s)
        if re.search(r'checkpoint|approve|pause|timeout|resolve|conflict|expire|token|decision|action|wait|identity|round|human|status', s, re.I) or any('\u4e00'<=ch<='\u9fff' for ch in s):
            print(r['sec'], hex(r['off']), repr(s)[:300])
