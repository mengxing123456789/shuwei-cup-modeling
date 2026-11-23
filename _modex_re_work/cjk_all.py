import re, sys

p = r"C:\modex-mh-agent\resources\app\backend\services\simulated_review.cp311-win_amd64.pyd"
d = open(p, "rb").read()

# decode utf-8 ignoring errors, then find runs containing CJK
txt = d.decode("utf-8", errors="ignore")
pat = re.compile(r"[\u4e00-\u9fff][\u4e00-\u9fff0-9A-Za-z，。、：；（）()\-—/ %．\.]{1,60}")
seen = {}
for m in pat.finditer(txt):
    s = m.group(0)
    seen.setdefault(s, 0)
    seen[s] += 1

items = sorted(seen.items(), key=lambda kv: -len(kv[0]))
with open(r"E:\数学建模\_modex_re_work\cjk_simulated_all.txt", "w", encoding="utf-8") as f:
    for s, c in items:
        f.write(f"{c:3d}  {s}\n")
print("unique:", len(items))
short = [s for s, c in items if len(s) <= 12]
print("short<=12:", len(short))
with open(r"E:\数学建模\_modex_re_work\cjk_simulated_short.txt", "w", encoding="utf-8") as f:
    for s in short:
        f.write(s + "\n")
