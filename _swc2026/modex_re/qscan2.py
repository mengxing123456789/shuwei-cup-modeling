# -*- coding: utf-8 -*-
import os,glob
root=r"C:\modex-mh-agent\resources\app\backend"
for kw in [b"resume_error_code",b"resume_strategy",b"same_session",b"fresh_context",b"auto_resume_count"]:
    print("==",kw.decode())
    for p in glob.glob(root+r"\**\*.pyd",recursive=True):
        d=open(p,"rb").read()
        if kw in d: print(" ",os.path.relpath(p,root))
