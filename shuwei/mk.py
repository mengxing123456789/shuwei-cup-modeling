
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

﻿# -*- coding: utf-8 -*-
import os, shutil, io, sys
sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
base=_corpus_root()
d25=os.path.join(base,'2025年数维杯秋季赛题目'); d23=os.path.join(base,'2023第九届数维杯国际赛题目（整理版）')
os.makedirs(d25,exist_ok=True); os.makedirs(d23,exist_ok=True)
src=r'E:\数学建模\shuwei\_src\2025autumn\ProblemA\英文原题.pdf'
dst=os.path.join(d25,'2025_ShuWei Cup A_Problem（官方原件）.pdf')
shutil.copyfile(src,dst); print('copied',dst,os.path.getsize(dst))
