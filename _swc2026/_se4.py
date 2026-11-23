import requests,urllib.parse,sys,io,re
from bs4 import BeautifulSoup
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
H={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36","Accept-Language":"zh-CN,zh;q=0.9"}
qs=["知乎 2026数维杯秋季赛B题 深度解析 无人机",
    "知乎 2026数维杯秋季赛D题 深度解析 行星",
    "2026数维杯秋季赛D题 双重共振 轨道 思路",
    "2026数维杯秋季赛B题 双车交汇 定位 代码"]
seen={}
for q in qs:
    try:
        r=requests.get("https://www.baidu.com/s?wd="+urllib.parse.quote(q),headers=H,timeout=15)
        for a in BeautifulSoup(r.text,"lxml").select("h3 a"):
            t=a.get_text(strip=True);h=a.get("href","")
            if h.startswith("http://www.baidu.com/link"): seen[t]=h
    except Exception as e: print("ERR",q,e)
print("found",len(seen))
for t,h in list(seen.items())[:20]:
    try:
        u=requests.get(h,headers=H,timeout=12,allow_redirects=True).url
    except Exception: u=h
    print(f"- {t[:80]}\n    {u}")
