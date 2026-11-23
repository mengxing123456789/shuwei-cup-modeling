import json, time, sys, io, requests, websocket
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
BASE="http://127.0.0.1:9333"

def newtab(url):
    r=requests.put(f"{BASE}/json/new?{requests.utils.quote(url,safe=':/?=&%')}",timeout=10)
    if r.status_code!=200:
        r=requests.get(f"{BASE}/json/new?{requests.utils.quote(url,safe=':/?=&%')}",timeout=10)
    return r.json()

def ev(ws_url, expr, timeout=20):
    ws=websocket.create_connection(ws_url,timeout=timeout,max_size=None)
    mid=1
    ws.send(json.dumps({"id":mid,"method":"Runtime.evaluate","params":{"expression":expr,"returnByValue":True,"awaitPromise":True}}))
    out=None
    t0=time.time()
    while time.time()-t0<timeout:
        try: m=json.loads(ws.recv())
        except Exception: break
        if m.get("id")==mid: out=m; break
    ws.close()
    return out

t=newtab("https://www.xiaohongshu.com/search_result?keyword=%E6%95%B0%E7%BB%B4%E6%9D%AF")
print("TAB",t.get("id"),t.get("url"))
time.sleep(9)
res=ev(t["webSocketDebuggerUrl"],"document.title + '\\n@@@\\n' + document.body.innerText.slice(0,3000)")
if res and "result" in res:
    print(res["result"]["result"].get("value","")[:2500])
else:
    print("ERR",json.dumps(res)[:800])
