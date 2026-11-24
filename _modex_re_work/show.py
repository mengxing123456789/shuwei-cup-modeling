import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
L = open(r"E:\数学建模\_modex_re_work\simulated_forms_lines.txt", encoding="utf-8").read().split("\n")
a = int(sys.argv[1]); b = int(sys.argv[2])
print("TOTAL", len(L))
for i in range(a - 1, min(b, len(L))):
    print("=== line", i + 1, "===")
    print(L[i])
