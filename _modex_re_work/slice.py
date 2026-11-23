import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
txt = open(r"E:\数学建模\_modex_re_work\simulated_forms_raw.txt", encoding="utf-8", errors="replace").read()
a = int(sys.argv[1]); b = int(sys.argv[2])
print("LEN", len(txt))
print(txt[a:b])
