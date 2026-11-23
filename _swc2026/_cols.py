
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

﻿import zipfile,io,sys,pandas as pd
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
p=_corpus_root() + r"\C_Problem_Data\C_Problem_Data\Restocking_Problem_and_Data_EN\Restocking_Problem_and_Data_EN\Raw_Data\EgoPro.zip"
zf=zipfile.ZipFile(p)
names=[n for n in zf.namelist() if n.endswith('.csv')]
sess=sorted({n.split('/')[1] for n in names})[0]
print("session",sess)
for n in sorted([x for x in names if x.split('/')[1]==sess]):
    with zf.open(n) as f:
        df=pd.read_csv(f,nrows=2)
    print("--",n.split('/')[-1], "cols",len(df.columns))
    print("   ",list(df.columns)[:14])
