import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
txt = open(r"E:\数学建模\_modex_re_work\simulated_forms_raw.txt", encoding="utf-8", errors="replace").read()

# find all Chinese-labeled criteria of form  xxx（English）
pat = re.compile(r"[\u4e00-\u9fff（）()、，,/A-Za-z0-9 \-]{2,60}（[A-Za-z][A-Za-z /&\-]{2,40}）")
for m in pat.finditer(txt):
    print(m.start(), "|", m.group(0))
