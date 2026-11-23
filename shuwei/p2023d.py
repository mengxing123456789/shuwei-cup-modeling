
def _corpus_root():
    """语料根：MM_CORPUS_ROOT > 向上找含 corpus/problems 的一级 > 旧 AsterLink 兜底。"""
    import os as _os
    from pathlib import Path as _P
    env = _os.environ.get("MM_CORPUS_ROOT")
    if env:
        return env
    for _probe in _P(__file__).resolve().parents:
        if (_probe / "corpus" / "problems").is_dir():
            return str(_probe / "corpus")
    return r"C:\Users\29900\Downloads\AsterLink"

﻿import zipfile,io,re
from pypdf import PdfReader
zp=_corpus_root() + r'\2023第九届数维杯国际赛优秀论文.zip'
z=zipfile.ZipFile(zp)
for k,f in [('C','C2023091819503.pdf'),('D','D2023091419459.pdf')]:
    p=[n for n in z.namelist() if n.endswith(f)][0]
    r=PdfReader(io.BytesIO(z.read(p)))
    print('='*25,k)
    for i in range(2,min(7,len(r.pages))):
        t=re.sub(r'[ \t]+',' ',(r.pages[i].extract_text() or ''))
        if re.search(r'Restatement|Problem|Background|question|Problem Description',t,re.I) and len(t)>200:
            print('--- page',i+1)
            print(t[:2600])
