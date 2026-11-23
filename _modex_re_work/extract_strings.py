# -*- coding: utf-8 -*-
"""Extract printable ASCII + UTF-8 CJK + UTF-16LE strings with file offsets."""
import re, sys, json

CJK = '\u0370-\u03ff\u2010-\u2027\u3000-\u303f\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff00-\uffef'
PAT = re.compile(('(?:[ -~]|[' + CJK + ']){4,}').encode('utf-8'))

def strings_utf8(d):
    out = []
    for m in PAT.finditer(d):
        try:
            s = m.group().decode('utf-8')
        except UnicodeDecodeError:
            continue
        out.append((m.start(), s))
    return out

def strings_utf16(d):
    out = []
    text = d.decode('utf-16le', errors='ignore')
    pat = re.compile('[ -~' + CJK + ']{4,}')
    for m in pat.finditer(text):
        s = m.group()
        if all(ord(c) < 128 for c in s):
            continue
        out.append((m.start() * 2, s))
    return out

def main():
    path = sys.argv[1]
    d = open(path, 'rb').read()
    rows = []
    seen = set()
    for off, s in strings_utf8(d):
        key = ('u8', s)
        if key in seen: continue
        seen.add(key)
        rows.append({'off': off, 'enc': 'utf8', 's': s})
    for off, s in strings_utf16(d):
        # skip pure-ascii utf16 duplicates of utf8
        if all(ord(c) < 128 for c in s) and any(r['s'] == s for r in rows if r['enc']=='utf8'):
            continue
        key = ('u16', s)
        if key in seen: continue
        seen.add(key)
        rows.append({'off': off, 'enc': 'utf16', 's': s})
    rows.sort(key=lambda r: r['off'])
    out = open(sys.argv[2], 'w', encoding='utf-8', newline='\n') if len(sys.argv) > 2 else sys.stdout
    for r in rows:
        out.write(f"{r['off']:08x}\t{r['enc']}\t{r['s']}\n")
    if out is not sys.stdout:
        out.close()

if __name__ == '__main__':
    main()
