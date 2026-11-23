
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

﻿import fitz,sys
d=fitz.open(_corpus_root() + r'\C_Problem_Data\C_Problem_Data\Restocking_Problem_and_Data_EN\Restocking_Problem_and_Data_EN\Restocking_Tasks_and_Constraints\Problem_3_Requirements.pdf')
txt='\n'.join([f'--- PAGE {i+1} ---\n'+pg.get_text() for i,pg in enumerate(d)])
open(r'E:\数学建模\_swc2026\problem_text\C_Problem3_Requirements.txt','w',encoding='utf-8').write(txt)
print('C_Problem3_Requirements.txt', d.page_count, len(txt))
