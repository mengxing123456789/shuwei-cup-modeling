
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

﻿import zipfile,io,re,glob,os
from pypdf import PdfReader
zp=_corpus_root() + r'\2023年数维杯国际赛优秀论文.zip'
if not os.path.exists(zp):
    cands=[f for f in glob.glob(_corpus_root() + r'\*2023*')]
    print('CAND',cands); zp=cands[0] if cands else None
z=zipfile.ZipFile(zp)
names=[n for n in z.namelist() if n.lower().endswith('.pdf')]
print('pdf count',len(names))
# group by problem letter from path
groups={}
for n in names:
    m=re.search(r'([ABCD])[^/\\]*$',n) or re.search(r'([ABCD])',n.split('/')[1] if len(n.split('/'))>1 else n)
    if m: groups.setdefault(m.group(1),[]).append(n)
for k in sorted(groups):
    print(k,len(groups[k]))
    print('   ',groups[k][0])
