import os,glob,json
root=r"C:\modex-mh-agent\resources\app\backend"
hits={}
for p in glob.glob(root+r"\**\*.pyd",recursive=True):
    data=open(p,'rb').read()
    # utf8 decode already done separately; quick search both utf8/utf16
    for kw in [b"PROBLEM_FACTS",b"CROSS_PROBLEM_LEDGER",b"FIGURE_MANIFEST",b"artifact_context"]:
        if kw in data:
            hits.setdefault(os.path.basename(p),[]).append(kw.decode())
print(hits)
