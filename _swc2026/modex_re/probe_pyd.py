# -*- coding: utf-8 -*-
"""Probe compiled .pyd: PE sections, pyc magic occurrences, embedded strings."""
import sys, struct, re

def pe_sections(data):
    if data[:2] != b'MZ':
        return None
    pe = struct.unpack_from('<I', data, 0x3C)[0]
    if data[pe:pe+4] != b'PE\0\0':
        return None
    nsec = struct.unpack_from('<H', data, pe+6)[0]
    opt = struct.unpack_from('<H', data, pe+20)[0]
    sec = pe + 24 + opt
    out = []
    for i in range(nsec):
        off = sec + i*40
        name = data[off:off+8].rstrip(b'\0').decode('latin1')
        vaddr, vsize, rawsize, rawptr = struct.unpack_from('<IIII', data, off+8+4)
        out.append((name, vaddr, vsize, rawptr, rawsize))
    return out

def main():
    p = sys.argv[1]
    data = open(p,'rb').read()
    print("size", len(data))
    secs = pe_sections(data)
    print("sections:", secs)
    # search python magic candidates
    magics = [b'\xa7\r\r\n', b'\x6f\r\r\n', b'\x5f\r\r\n', b'\xcb\r\r\n']
    for m in magics:
        idxs = [i for i in range(len(data)) if data.startswith(m, i)][:10]
        if idxs: print("magic", m.hex(), "at", idxs)
    # look for common marshal type patterns near likely code blobs? print strings stats
    asc = re.findall(rb'[\x20-\x7e]{6,}', data)
    print("ascii strings:", len(asc))
    utf16 = re.findall(rb'(?:[\x20-\x7e]\x00){6,}', data)
    print("utf16 strings:", len(utf16))
    for s in asc[:20]: print("A:", s[:120])
    for s in utf16[:5]: print("U:", s.decode('utf-16le','ignore')[:120])

if __name__ == '__main__': main()
