import requests, re, io, sys, json, urllib.parse
from bs4 import BeautifulSoup
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
H={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
   "Accept-Language":"zh-CN,zh;q=0.9"}
q="数维杯 2026 秋季赛 A题 思路 site:xiaohongshu.com"
for eng,url in [("baidu","https://www.baidu.com/s?wd="),("so","https://www.so.com/s?q="),("sogou","https://www.sogou.com/web?query=")]:
    try:
        r=requests.get(url+urllib.parse.quote(q),headers=H,timeout=15)
        soup=BeautifulSoup(r.text,"lxml")
        txt=soup.get_text("\n",strip=True)
        print("=====",eng,r.status_code,len(r.text),"textlen",len(txt))
        print(txt[:1200])
    except Exception as e:
        print("=====",eng,"ERR",e)
