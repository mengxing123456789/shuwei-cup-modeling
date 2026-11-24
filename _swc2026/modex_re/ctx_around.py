import re
p=r"C:\modex-mh-agent\resources\app\backend\services\workflow_engine.cp311-win_amd64.pyd"
d=open(p,'rb').read()
for kw in [b"PROBLEM_FACTS",b"CROSS_PROBLEM_LEDGER",b"FIGURE_MANIFEST"]:
    print("="*20,kw.decode())
    start=0
    for i in range(6):
        idx=d.find(kw,start)
        if idx<0: break
        seg=d[max(0,idx-600):idx+600]
        txt=seg.decode('utf-8','ignore')
        # keep printable/CJK chars
        txt=''.join(ch if (32<=ord(ch)<127 or '\u4e00'<=ch<='\u9fff' or ch in '\n') else ' ' for ch in txt)
        print("---off",idx)
        print(txt[-900:])
        start=idx+1
