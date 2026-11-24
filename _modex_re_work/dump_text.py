# -*- coding: utf-8 -*-
"""Dump long text strings (docstrings, rule text) from an extracted strings file."""
import sys, re, io

def dump(path, out, minlen=20, chinese_only=False):
    rows = []
    for line in open(path, encoding='utf-8', errors='replace'):
        m = re.match(r'^([0-9a-f]{8})\t(utf8|utf16)\t(.*)$', line.rstrip('\n'))
        if not m:
            continue
        off, enc, s = m.groups()
        if enc != 'utf8':
            continue
        if len(s) < minlen:
            continue
        if chinese_only and not re.search(r'[\u4e00-\u9fff]', s):
            continue
        rows.append((off, s))
    with io.open(out, 'w', encoding='utf-8') as f:
        for off, s in rows:
            f.write(f'{off}\t{s}\n')
    print(path, '->', out, len(rows))

if __name__ == '__main__':
    dump(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 20,
         len(sys.argv) > 4 and sys.argv[4] == 'zh')
