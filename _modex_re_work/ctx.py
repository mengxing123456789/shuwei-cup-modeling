import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

txt = open(r"E:\数学建模\_modex_re_work\simulated_forms_raw.txt", encoding="utf-8", errors="replace").read()
print("LEN", len(txt))

kws = sys.argv[1:] or ["学位论文评阅", "中文期刊", "英文期刊", "机器学习", "其他学术会议", "Nature", "课程论文", "开题", "文献综述"]
for k in kws:
    for m in re.finditer(re.escape(k), txt):
        s = max(0, m.start() - 80)
        e = min(len(txt), m.start() + 1200)
        print("\n\n##########", k, "@", m.start(), "##########")
        print(txt[s:e])
        break
