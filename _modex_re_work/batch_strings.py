# -*- coding: utf-8 -*-
"""Batch strings extraction for Modex backend pyd/pyc files."""
import sys, os, subprocess
sys.path.insert(0, os.path.dirname(__file__))
from extract_strings import strings_utf8, strings_utf16

FILES = [
    'skill_capsule', 'skill_source', 'skill_delivery_gate', 'skill_runtime_policy',
    'skill_provenance', 'skill_crypto', 'skill_mcp',
    'workflow_engine', 'workflow_acceptance', 'workflow_intake',
    'paper_modeling_quality', 'writing_guide', 'writing_profile', 'paper_readiness',
    'submission_review', 'quality_receipts', 'step_review_report', 'paper_finalization',
    'venue_ai_statement', 'venue_spec', 'paper_submission_contract', 'custom_steps',
]

BASE = r'C:\modex-mh-agent\resources\app\backend\services'
OUT = r'E:\数学建模\_modex_re_work\strings'
os.makedirs(OUT, exist_ok=True)

def dump(path, out):
    d = open(path, 'rb').read()
    rows = []
    seen = set()
    for off, s in strings_utf8(d):
        if ('u8', s) in seen: continue
        seen.add(('u8', s))
        rows.append((off, 'utf8', s))
    for off, s in strings_utf16(d):
        if ('u16', s) in seen: continue
        seen.add(('u16', s))
        rows.append((off, 'utf16', s))
    rows.sort()
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        for off, enc, s in rows:
            f.write(f'{off:08x}\t{enc}\t{s}\n')
    return len(rows)

for name in FILES:
    cands = [os.path.join(BASE, name + '.cp311-win_amd64.pyd'), os.path.join(BASE, name + '.pyc')]
    path = next((p for p in cands if os.path.exists(p)), None)
    if not path:
        print('MISSING', name); continue
    n = dump(path, os.path.join(OUT, name + '.txt'))
    print(f'{name}\t{os.path.getsize(path)}\t{n}')
