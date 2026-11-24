# -*- coding: utf-8 -*-
"""Extract UTF-8/ASCII strings from a compiled PE module (Nuitka-style), with section info."""
import sys, re, struct, json, os

def sections(data):
    if data[:2] != b'MZ': return []
    pe = struct.unpack_from('<I', data, 0x3C)[0]
    nsec = struct.unpack_from('<H', data, pe+6)[0]
    opt = struct.unpack_from('<H', data, pe+20)[0]
    sec = pe + 24 + opt
    out = []
    for i in range(nsec):
        off = sec + i*40
        name = data[off:off+8].rstrip(b'\0').decode('latin1')
        vsize, vaddr, rawsize, rawptr = struct.unpack_from('<IIII', data, off+8)
        out.append((name, rawptr, rawsize))
    return out

# UTF-8 sequence regex: runs of printable ASCII or valid multibyte utf-8
pat = re.compile(rb'(?:[\x20-\x7E]|[\xC2-\xDF][\x80-\xBF]|\xE0[\xA0-\xBF][\x80-\xBF]|[\xE1-\xEC\xEE\xEF][\x80-\xBF]{2}|\xED[\x80-\x9F][\x80-\xBF]|\xF0[\x90-\xBF][\x80-\xBF]{2}|[\xF1-\xF3][\x80-\xBF]{3}|\xF4[\x80-\x8F][\x80-\xBF]{2})+')

def main():
    p = sys.argv[1]
    outpath = sys.argv[2]
    minlen = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    data = open(p,'rb').read()
    secs = sections(data)
    rows = []
    for name, ptr, size in secs:
        if name not in ('.rdata', '.data', '.text'): continue
        chunk = data[ptr:ptr+size]
        for m in pat.finditer(chunk):
            b = m.group(0)
            if len(b) < minlen: continue
            try:
                s = b.decode('utf-8')
            except Exception:
                continue
            # keep strings that contain non-ascii or look meaningful
            rows.append({"sec": name, "off": ptr + m.start(), "s": s})
    with open(outpath, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    print("strings:", len(rows), "->", outpath)
    cjk = [r for r in rows if any('\u4e00' <= ch <= '\u9fff' for ch in r['s'])]
    print("cjk strings:", len(cjk))
    for r in cjk[:10]: print(" ", r['sec'], hex(r['off']), r['s'][:100])

if __name__ == '__main__': main()
