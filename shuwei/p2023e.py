
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

﻿import zipfile,io,re,sys
from pypdf import PdfReader
sys.stdout.reconfigure(encoding='utf-8',errors='ignore')
def clean(t):
    t=re.sub(r'[\ud800-\udfff]','',t)
    return re.sub(r'[ \t]+',' ',t)
zp=_corpus_root() + r'\2023第九届数维杯国际赛优秀论文.zip'
z=zipfile.ZipFile(zp)
p=[n for n in z.namelist() if n.endswith('D2023091419459.pdf')][0]
r=PdfReader(io.BytesIO(z.read(p)))
print('='*25,'2023 D')
for i in range(2,min(8,len(r.pages))):
    t=clean(r.pages[i].extract_text() or '')
    if len(t)>300 and re.search(r'question|Problem|Background|laundry|Laundry',t,re.I):
        print('--- page',i+1); print(t[:3200]); break
