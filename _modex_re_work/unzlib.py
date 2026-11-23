import zlib

p = r"C:\modex-mh-agent\resources\app\backend\services\simulated_review.cp311-win_amd64.pyd"
d = open(p, "rb").read()
off = 0xf4e50
o = zlib.decompressobj()
out = o.decompress(d[off:])
with open(r"E:\数学建模\_modex_re_work\simulated_forms_raw.txt", "wb") as f:
    f.write(out)
print(len(out))

# split into printable runs to make readable
txt = out.decode("utf-8", errors="replace")
import re
# insert newlines at likely boundaries: after 。！？； and around known keys
txt2 = re.sub(r"([。！？；])", r"\1\n", txt)
with open(r"E:\数学建模\_modex_re_work\simulated_forms_lines.txt", "w", encoding="utf-8") as f:
    f.write(txt2)
print("lines", txt2.count("\n"))
