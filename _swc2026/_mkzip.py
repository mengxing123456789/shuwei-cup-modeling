import zipfile,os
base=r"E:\数学建模\_swc2026\SWC2026_A"
out=os.path.join(base,"ASWBMCM2634892fj.zip")
include_dirs=["code","data","figures","tables","out","review"]
with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
    for f in ["main.tex","main.pdf","ASWBMCM2634892cns.tex","ASWBMCM2634892cns.pdf","swmcmthesis.cls","swmcmthesis.cfg"]:
        p=os.path.join(base,f)
        if os.path.exists(p): z.write(p,f)
    for d in include_dirs:
        for root,_,files in os.walk(os.path.join(base,d)):
            for fn in files:
                p=os.path.join(root,fn)
                z.write(p,os.path.relpath(p,base))
print(out,round(os.path.getsize(out)/1024/1024,2),"MB")
