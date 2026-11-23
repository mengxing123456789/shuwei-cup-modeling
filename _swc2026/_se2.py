import requests,urllib.parse,re,sys,io,time
from bs4 import BeautifulSoup
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
H={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
   "Accept-Language":"zh-CN,zh;q=0.9","Accept":"text/html,application/xhtml+xml"}
qs=["数维杯2026秋季赛A题","数维杯 2026 秋季赛 思路","2026数维杯秋季赛C题 无人超市 补货","2026数维杯秋季赛B题 无人机 定位"]
for q in qs:
    print("="*30,q)
    for eng,url in [("baidu","https://www.baidu.com/s?wd="),("so","https://www.so.com/s?q=")]:
        try:
            r=requests.get(url+urllib.parse.quote(q),headers=H,timeout=15)
            soup=BeautifulSoup(r.text,"lxml")
            hits=[]
            for a in soup.select("h3 a, .res-list h3 a, .result h3 a"):
                t=a.get_text(strip=True)
                if t: hits.append((t,a.get("href","")[:90]))
            print(f"  [{eng}] {len(hits)} hits")
            for t,h in hits[:8]: print("   -",t,"|",h)
        except Exception as e: print(f"  [{eng}] ERR {e}")
        time.sleep(1)
