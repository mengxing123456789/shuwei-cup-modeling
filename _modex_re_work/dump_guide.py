import io, os, sys, zlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = r'C:\modex-mh-agent\resources\app\backend'
TARGETS = {
    'writing_guide': 'writing_guide.cp311-win_amd64.pyd',
    'writing_profile': 'writing_profile.cp311-win_amd64.pyd',
    'writing_review': 'writing_review.cp311-win_amd64.pyd',
}
OUT = r'E:\数学建模\_modex_re_work\zlib3'
os.makedirs(OUT, exist_ok=True)

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
                i += max(1, len(out)//4)
                continue
            except Exception:
                pass
        i += 1

for name, fn in TARGETS.items():
    p = os.path.join(ROOT, 'services', fn)
    data = open(p, 'rb').read()
    for off, out in blobs(data):
        t = out.decode('utf-8', 'replace')
        fp = os.path.join(OUT, f'{name}_{off:x}.txt')
        open(fp, 'w', encoding='utf-8', newline='\n').write(t)
        print(name, hex(off), len(t), 'bad=', t.count('\ufffd'), '->', fp)
