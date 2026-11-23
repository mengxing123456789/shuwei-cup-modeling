import requests,urllib.parse,sys,io,json
from bs4 import BeautifulSoup
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
H={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36","Accept-Language":"zh-CN,zh;q=0.9"}
seen={}
for q in ["数维杯2026秋季赛A题","数维杯 2026 秋季赛 思路","数维杯2026秋季赛D题","数维杯2026秋季赛A题 代码 结果"]:
    r=requests.get("https://www.baidu.com/s?wd="+urllib.parse.quote(q),headers=H,timeout=15)
    soup=BeautifulSoup(r.text,"lxml")
    for a in soup.select("h3 a"):
        t=a.get_text(strip=True); h=a.get("href","")
        if h.startswith("http://www.baidu.com/link"):
            try:
                rr=requests.get(h,headers=H,timeout=12,allow_redirects=True)
                seen[t]=rr.url
            except Exception: pass
for t,u in seen.items():
    print(f"{t}\n    -> {u}\n")
