import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def segs(raw, minlen=10):
    out = []
    cur = bytearray(); start = 0; i = 0; n = len(raw)
    while i < n:
        b = raw[i]
        ok = (32 <= b < 127) or b >= 0x80 or b in (0x0A, 0x09)
        if ok:
            if not cur: start = i
            cur.append(b); i += 1
        else:
            if len(cur) >= minlen: out.append((start, bytes(cur)))
            cur = bytearray(); i += 1
    if len(cur) >= minlen: out.append((start, bytes(cur)))
    return out

for p in [r'E:\数学建模\_modex_re_work\zlib3\writing_profile_303e0.txt',
          r'E:\数学建模\_modex_re_work\zlib3\writing_review_22810.txt']:
    raw = open(p, 'rb').read()
    print('#' * 25, p, len(raw))
    for off, b in segs(raw):
        t = b.decode('utf-8', 'replace')
        if any('\u4e00' <= c <= '\u9fff' for c in t):
            print(f'--- @{off} len={len(t)}')
            print(t)
    print()
