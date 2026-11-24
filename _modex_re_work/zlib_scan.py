import zlib, re

p = r"C:\modex-mh-agent\resources\app\backend\services\simulated_review.cp311-win_amd64.pyd"
d = open(p, "rb").read()
print("size", len(d))

hits = []
found = 0
for i in range(len(d) - 2):
    if d[i] == 0x78 and d[i+1] in (0x01, 0x5e, 0x9c, 0xda):
        try:
            o = zlib.decompressobj()
            out = o.decompress(d[i:i+400000])
        except Exception:
            continue
        if len(out) > 200:
            found += 1
            hits.append((i, len(out), out))
print("zlib blobs:", found)

keys = [b"cn_thesis", b"cn_journal", b"ml_conf", b"nature", "创新".encode(), "评分".encode()]
for off, ln, out in hits:
    for k in keys:
        if k in out:
            print("HIT", hex(off), ln, k)
            break

if hits:
    hits.sort(key=lambda t: -t[1])
    with open(r"E:\数学建模\_modex_re_work\simulated_zlib.txt", "wb") as f:
        for off, ln, out in hits[:20]:
            f.write(b"\n\n===== off %d len %d =====\n" % (off, ln))
            f.write(out)
    print("biggest:", hits[0][0], hits[0][1])
