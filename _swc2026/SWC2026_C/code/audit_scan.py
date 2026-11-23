
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""只读扫描：data/*.json 的结构与关键标量；code/*.py 的接口与产物引用。

输出 stdout（UTF-8），不写任何文件。
"""
import json, os, re, io, sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
CODE = os.path.join(ROOT, 'code')


def walk(obj, prefix='', depth=0, maxdepth=3, out=None):
    if out is None:
        out = []
    if depth > maxdepth:
        return out
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f'{prefix}.{k}' if prefix else str(k)
            if isinstance(v, (dict, list)):
                out.append((p, type(v).__name__, len(v)))
                walk(v, p, depth + 1, maxdepth, out)
            else:
                out.append((p, type(v).__name__, v))
    elif isinstance(obj, list):
        if obj and isinstance(obj[0], dict):
            out.append((prefix + '[]', 'list[dict]', len(obj)))
            out.append((prefix + '[0] keys', 'keys', list(obj[0].keys())))
            # first row scalar values only
            for k, v in obj[0].items():
                if not isinstance(v, (dict, list)):
                    out.append((f'{prefix}[0].{k}', type(v).__name__, v))
        else:
            out.append((prefix + '[]', 'list', len(obj)))
    return out


def scan_json(path):
    name = os.path.basename(path)
    mt = datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d %H:%M:%S')
    size = os.path.getsize(path)
    print(f'\n===== {name} | {size} bytes | mtime {mt} =====')
    try:
        with open(path, encoding='utf-8') as f:
            obj = json.load(f)
    except Exception as e:
        print('  PARSE-FAIL', repr(e))
        return
    if isinstance(obj, dict):
        print('  TOP KEYS:', list(obj.keys()))
    rows = walk(obj, maxdepth=2)
    for p, t, v in rows[:120]:
        s = repr(v)
        if len(s) > 160:
            s = s[:157] + '...'
        print(f'  {p} <{t}> = {s}')


def scan_code(path):
    name = os.path.basename(path)
    with open(path, encoding='utf-8', errors='replace') as f:
        src = f.read()
    lines = src.splitlines()
    mt = datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d %H:%M:%S')
    print(f'\n===== {name} | {len(lines)} lines | mtime {mt} =====')
    # docstring
    m = re.match(r'\s*(?:#.*\n)*\s*(?:"""(.*?)"""|\'\'\'(.*?)\'\'\')', src, re.S)
    if m:
        doc = (m.group(1) or m.group(2) or '').strip().splitlines()
        print('  DOC:', ' / '.join(doc[:4]))
    # defs with line numbers
    for i, ln in enumerate(lines, 1):
        if re.match(r'^(def |class )', ln):
            print(f'  L{i}: {ln.strip()}')
    # file references
    refs = sorted(set(re.findall(r'[\w\-./\\]*\.(?:json|csv|npz|pt|png|log|parquet|xlsx)', src)))
    refs = [r for r in refs if '/' in r or '\\' in r or r.startswith(('p1', 'p2', 'p3', 'panel', 'state', 'prefix', 'segments', 'feature', 'gpu'))]
    print('  REFS:', '; '.join(refs[:40]))


if __name__ == '__main__':
    print('ROOT', ROOT)
    for fn in sorted(os.listdir(DATA)):
        if fn.endswith('.json'):
            scan_json(os.path.join(DATA, fn))
    print('\n\n########## CODE ##########')
    for fn in sorted(os.listdir(CODE)):
        if fn.endswith('.py') and not fn.startswith('audit_'):
            scan_code(os.path.join(CODE, fn))