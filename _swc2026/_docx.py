
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

﻿import io,sys
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
from docx import Document
p=_corpus_root() + r"\2025年第十一届数维杯大学生数学建模挑战赛（秋季赛）承诺书.docx"
d=Document(p)
for i,para in enumerate(d.paragraphs):
    if para.text.strip(): print(i,repr(para.text))
for t in d.tables:
    print("TABLE")
    for row in t.rows:
        print([c.text for c in row.cells])
