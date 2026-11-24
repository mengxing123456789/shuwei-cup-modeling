import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
txt = open(r"E:\数学建模\_modex_re_work\simulated_forms_raw.txt", encoding="utf-8", errors="replace").read()

# English phrases: sequences of ascii words with spaces, len>=8, containing a space
pat = re.compile(r"[A-Za-z][A-Za-z' \-]{6,60}[A-Za-z]")
seen = []
for m in pat.finditer(txt):
    s = m.group(0)
    if " " not in s:
        continue
    if s in seen:
        continue
    seen.append(s)
    print(m.start(), "|", s)
