
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

﻿import json,io,sys,pandas as pd
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
b=_corpus_root() + r"\C_Problem_Data\C_Problem_Data\Restocking_Problem_and_Data_EN\Restocking_Problem_and_Data_EN\Restocking_Tasks_and_Constraints"
print(open(b+r"\common_conditions.json",encoding="utf-8").read())
t=pd.read_csv(b+r"\tasks.csv"); print("\ntasks",t.shape); print(t.head(4).to_string())
s=pd.read_csv(b+r"\source_segment_index.csv"); print("\nsegments",s.shape); print(s.columns.tolist()); print(s.head(3).to_string())
r=pd.read_csv(b+r"\record_split.csv"); print("\nsplit",r.shape, r.columns.tolist()); print(r["split"].value_counts().to_dict() if "split" in r else "")
print("\nzones"); print(open(b+r"\service_zones.csv",encoding="utf-8").read())
print("families"); print(open(b+r"\job_families.csv",encoding="utf-8").read())
