import json,time,sys,io,requests,websocket
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
BASE="http://127.0.0.1:9333"
def pages():
    return requests.get(f"{BASE}/json/list",timeout=8).json()
def ws_of(t): return t["webSocketDebuggerUrl"]
def ev(ws_url,expr,timeout=25):
    ws=websocket.create_connection(ws_url,timeout=timeout,max_size=None)
    ws.send(json.dumps({"id":1,"method":"Runtime.evaluate","params":{"expression":expr,"returnByValue":True,"awaitPromise":True}}))
    out=None;t0=time.time()
    while time.time()-t0<timeout:
        try: m=json.loads(ws.recv())
        except Exception: break
        if m.get("id")==1: out=m;break
    ws.close(); return out
p=[t for t in pages() if t["type"]=="page"][0]
print("PAGE",p["url"])
kw="数维杯"
expr=f"""(function(){{location.href='https://www.xiaohongshu.com/search_result?keyword='+encodeURIComponent('{kw}');return 'nav';}})()"""
print(ev(ws_of(p),expr))
time.sleep(10)
r=ev(ws_of(p),"document.title+'\\n###\\n'+document.body.innerText.slice(0,4000)")
print(r["result"]["result"]["value"][:4000] if r and "result" in r else json.dumps(r)[:500])
