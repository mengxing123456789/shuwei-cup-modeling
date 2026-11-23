# -*- coding: utf-8 -*-
import subprocess, sys, os
PY = r'python'
EX = r'E:\数学建模\_modex_re_work\extract_strings.py'
BASE = r'C:\modex-mh-agent\resources\app\backend\services'
OUT = r'E:\数学建模\_modex_re_work\strings'
mods = ['chat_template','user_template','writing_review','conversation_writing_check','artifact_catalogue','newapi_catalog','skill_trim']
for m in mods:
    p = os.path.join(BASE, m + '.cp311-win_amd64.pyd')
    o = os.path.join(OUT, m + '.txt')
    print(m, os.path.getsize(p))
    subprocess.run([PY, EX, p, o], check=True)
print('ok')
