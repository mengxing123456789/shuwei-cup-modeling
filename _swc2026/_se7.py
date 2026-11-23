import requests,sys,io
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
H={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
   "Accept-Language":"zh-CN,zh;q=0.9","Referer":"https://www.baidu.com/"}
links={"B":"http://www.baidu.com/link?url=dIR7EV0NLHzUV6v3I8HKxwUALkGegvYbq4RRlq-lp_DXxJ9Ryu",
       "ALL":"http://www.baidu.com/link?url=WAbRJSiy8a8_HWxKt9xMsp-ygOJI7QbOwzeThtWwtEj42FXcxN",
       "AI":"http://www.baidu.com/link?url=qQcJlXhIcujIeWfgrjiD7JFJXsk6m_RJKHleqGCZrKzjOhlr6k"}
for k,L in links.items():
    try:
        r=requests.get(L,headers=H,timeout=15,allow_redirects=True)
        print(k,r.status_code,r.url)
    except Exception as e:
        print(k,"ERR",e)
