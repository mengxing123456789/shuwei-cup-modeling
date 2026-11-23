p=r"C:\modex-mh-agent\resources\app\backend\services\workflow_engine.cp311-win_amd64.pyd"
d=open(p,'rb').read()
out=[]
for kw in [b"PROBLEM_FACTS",b"FIGURE_MANIFEST"]:
    out.append("="*30+" "+kw.decode())
    start=0
    for i in range(4):
        idx=d.find(kw,start)
        if idx<0: break
        seg=d[max(0,idx-900):idx+900]
        txt=seg.decode('utf-8','ignore')
        txt=''.join(ch if (32<=ord(ch)<127 or '\u4e00'<=ch<='\u9fff' or ch=='\n') else ' ' for ch in txt)
        out.append(txt)
        start=idx+1
open(r"E:\数学建模\_swc2026\modex_re\ctx_around_utf8.txt","w",encoding="utf-8").write("\n\n".join(out))
print("ok")
