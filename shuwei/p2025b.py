
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
zp=_corpus_root() + r'\2025年数维杯秋季赛优秀论文.zip'
z=zipfile.ZipFile(zp)
targets={
 'B':'2025年数维杯秋季赛优秀论文/B题/BSHUWEICUP2549191/BSHUWEICUP2549191.pdf',
 'C':'2025年数维杯秋季赛优秀论文/C题/CSHUWEICUP2551760/CSHUWEICUP2551760.pdf',
}
def clean(t):
    t=re.sub(r'[\ud800-\udfff]','',t); return re.sub(r'[ \t]+',' ',t)
for k,f in targets.items():
    r=PdfReader(io.BytesIO(z.read(f)))
    print('='*25,k,len(r.pages))
    hit=False
    for i in range(1,min(8,len(r.pages))):
        t=clean(r.pages[i].extract_text() or '')
        if re.search(r'Restatement|Background|Problem Description|Task',t,re.I) and len(t)>500:
            print('--- page',i+1); print(t[:3300]); hit=True; break
    if not hit: print('  no restatement page found')
