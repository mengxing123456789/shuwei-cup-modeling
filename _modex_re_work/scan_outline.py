import io, os, sys, re, zlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = r'C:\modex-mh-agent\resources\app\backend'
KWS = ['OUTLINE_SKELETON', '论证主线', 'WRITING_GUIDE.md', 'section_keys', 'academic_outlines']

def blobs(data):
    i = 0
    n = len(data)
    while i < n - 2:
        if data[i] == 0x78 and data[i+1] in (0x01, 0x9c, 0xda, 0x5e):
            try:
                d = zlib.decompressobj()
                out = d.decompress(data[i:i+8_000_000])
                if len(out) > 500:
                    yield i, out
                i += max(1, len(out) // 4)
                continue
            except Exception:
                pass
        i += 1

hits = {}
for dirpath, _, files in os.walk(ROOT):
    for f in files:
        if not f.endswith('.pyd'):
            continue
        p = os.path.join(dirpath, f)
        try:
            data = open(p, 'rb').read()
        except Exception:
            continue
        for off, out in blobs(data):
            try:
                t = out.decode('utf-8', 'replace')
            except Exception:
                continue
            for kw in KWS:
                if kw in t:
                    hits.setdefault(kw, []).append((f, off, len(t)))

for kw in KWS:
    print('####', kw)
    for h in hits.get(kw, []):
        print('   ', h)
