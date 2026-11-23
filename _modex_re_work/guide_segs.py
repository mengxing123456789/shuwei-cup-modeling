import io, sys, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def segs(raw, minlen=12):
    out = []
    cur = bytearray()
    start = 0
    i = 0
    n = len(raw)
    while i < n:
        b = raw[i]
        ok = (32 <= b < 127) or b >= 0xC0 or b in (0x0A, 0x09)
        if ok:
            if not cur:
                start = i
            cur.append(b)
            i += 1
        else:
            if len(cur) >= minlen:
                out.append((start, bytes(cur)))
            cur = bytearray()
            i += 1
    if len(cur) >= minlen:
        out.append((start, bytes(cur)))
    return out

p = r'E:\数学建模\_modex_re_work\zlib3\writing_guide_25770.txt'
raw = open(p, 'rb').read()
ss = segs(raw)
print('segments', len(ss))
for off, b in ss:
    t = b.decode('utf-8', 'replace')
    print(f'--- @{off} len={len(t)}')
    print(t)
