import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
txt = open(r"E:\数学建模\_modex_re_work\simulated_forms_raw.txt", encoding="utf-8", errors="replace").read()
labels = sys.argv[1:]
for k in labels:
    idxs = [m.start() for m in re.finditer(re.escape(k), txt)]
    print("\n########", k, idxs[:6])
    for i in idxs[:2]:
        print("---- window @", i)
        print(txt[max(0, i - 200):i + 600])
