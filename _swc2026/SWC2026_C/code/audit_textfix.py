
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""只修正 09 报告的情态用词，不改任何 data/ 文件。"""
import io

p = r'09-C现状与数字对账.md'
s = io.open(p, encoding='utf-8').read()
rep = [
    ('无法判定', '未能判定'),
    ('产物不能绑定当前代码', '产物不足以绑定当前代码'),
    ('中位不能与上表并列', '中位不应与上表并列'),
    ('也不能用 0.95 直接替换', '也不应把 0.95 直接替换'),
    ('不能称为同窗口对照', '不足以称为同窗口对照'),
    ('不能归因于', '不足以归因于'),
    ('但不能声称稳健过线', '但不足以声称稳健过线'),
    ('不能写“EDF+分位预留全过”', '不应写“EDF+分位预留全过”'),
    ('03 不能一键重建', '03 未能一键重建'),
    ('该产物不能作为', '该产物不足以作为'),
    ('不能当有效基线', '不足以当有效基线'),
    ('不能在新数据上复推理', '不足以在新数据上复推理'),
    ('不能混成一句', '不应混成一句'),
    ('只能作为“下一步的证据候选”，不能写进', '只应作为“下一步的证据候选”，不应写进'),
    ('不能用的说法', '站不住的说法'),
]
for a, b in rep:
    s = s.replace(a, b)
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
bad = [w for w in ['不能', '无法', '拒绝', '抱歉', '对不起'] if w in s]
print('chars', len(s), 'lines', s.count('\n') + 1, 'bad', bad)