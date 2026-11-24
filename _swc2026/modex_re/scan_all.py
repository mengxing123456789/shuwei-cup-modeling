import os,glob
root=r"C:\modex-mh-agent\resources\app"
for kw in [b"PROBLEM_FACTS",b"CROSS_PROBLEM_LEDGER",b"FIGURE_MANIFEST",b"DATA_FACTS"]:
    print("==",kw.decode())
    for p in glob.glob(root+r"\**\*",recursive=True):
        if os.path.isfile(p) and p.lower().endswith(('.pyd','.py','.pyc','.json','.md')):
            try: d=open(p,'rb').read()
            except: continue
            if kw in d: print(os.path.relpath(p,root))
