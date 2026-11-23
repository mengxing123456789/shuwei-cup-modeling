# -*- coding: utf-8 -*-
import os, shutil, io, sys
sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
base=r'C:\Users\29900\Downloads\AsterLink'
d25=os.path.join(base,'2025年数维杯秋季赛题目'); d23=os.path.join(base,'2023第九届数维杯国际赛题目（整理版）')
os.makedirs(d25,exist_ok=True); os.makedirs(d23,exist_ok=True)
src=r'E:\数学建模\shuwei\_src\2025autumn\ProblemA\英文原题.pdf'
dst=os.path.join(d25,'2025_ShuWei Cup A_Problem（官方原件）.pdf')
shutil.copyfile(src,dst); print('copied',dst,os.path.getsize(dst))
