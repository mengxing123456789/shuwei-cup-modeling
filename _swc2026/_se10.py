import json,time,sys,io,requests,websocket,urllib.parse
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
BASE="http://127.0.0.1:9333"
def pages(): return [t for t in requests.get(f"{BASE}/json/list",timeout=8).json() if t["type"]=="page"]
def ws_for(p): return websocket.create_connection(p["webSocketDebuggerUrl"],timeout=40,max_size=None)
def jse(p,expr,timeout=30):
    ws=ws_for(p)
    ws.send(json.dumps({"id":1,"method":"Runtime.evaluate","params":{"expression":expr,"returnByValue":True,"awaitPromise":True}}))
    t0=time.time();o=None
    while time.time()-t0<timeout:
        try: m=json.loads(ws.recv())
        except Exception: return None
        if m.get("id")==1: o=m;break
    ws.close()
    try: return o["result"]["result"]["value"]
    except Exception: return None
q="2026数维杯秋季赛B题 深度解析"
p0=[p for p in pages() if "baidu.com/s" in p["url"]]
if not p0:
    p0=pages()
p=p0[0]
jse(p,"document.querySelectorAll('h3 a')[0].click();1")
time.sleep(7)
for t in pages(): print(t["url"][:130],"|",t["title"][:50])
