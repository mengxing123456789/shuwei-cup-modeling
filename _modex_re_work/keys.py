import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

txt = open(r"E:\数学建模\_modex_re_work\simulated_forms_raw.txt", encoding="utf-8", errors="replace").read()

# find form keys and show context
for k in ["cn_thesis", "cn_journal", "cn_journal_hum", "en_journal", "ml_conf", "en_conf", "nature", "cn_course", "cn_proposal", "cn_review"]:
    idxs = [m.start() for m in re.finditer(re.escape(k), txt)]
    print("\n#####", k, "hits", idxs[:10])
    if idxs:
        i = idxs[0]
        print(txt[max(0, i - 300):i + 700].replace("\n", "\\n"))
