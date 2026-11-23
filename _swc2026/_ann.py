
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

﻿import zipfile,json,io,sys
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
p=_corpus_root() + r"\C_Problem_Data\C_Problem_Data\Restocking_Problem_and_Data_EN\Restocking_Problem_and_Data_EN\Raw_Data\EgoDemo.zip"
zf=zipfile.ZipFile(p)
a=json.loads(zf.read("EgoDemo/E001/annotation.json")); print("annotation.json keys",list(a.keys())); print(json.dumps(a,ensure_ascii=False)[:800])
i=json.loads(zf.read("EgoDemo/E001/meta/info.json")); print("\ninfo.json keys",list(i.keys()))
print(json.dumps(i,ensure_ascii=False)[:1500])
