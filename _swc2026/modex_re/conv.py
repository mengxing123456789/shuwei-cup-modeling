# -*- coding: utf-8 -*-
base = "E:/数学建模/_swc2026/modex_re/"
for n in ["qctx_out.txt","qpre_out.txt","eng_ctx.txt","ctx_strings.txt"]:
    p=base+n
    d=open(p,"rb").read()
    best=None
    for enc in ("utf-8","utf-16","gbk","latin1"):
        try:
            t=d.decode(enc)
        except Exception:
            continue
        score=sum(1 for c in t if "\u4e00"<=c<="\u9fff")
        if best is None or score>best[0]: best=(score,enc,t)
    score,enc,t=best
    open(p+".u8","w",encoding="utf-8").write(t)
    print(n,enc,len(t),score)
