import json,time,sys,io,requests,websocket
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
BASE="http://127.0.0.1:9333"
def pages(): return [t for t in requests.get(f"{BASE}/json/list",timeout=8).json() if t["type"]=="page"]
def jse(expr,timeout=35):
    p=pages()[0]
    ws=websocket.create_connection(p["webSocketDebuggerUrl"],timeout=timeout+5,max_size=None)
    ws.send(json.dumps({"id":1,"method":"Runtime.evaluate","params":{"expression":expr,"returnByValue":True,"awaitPromise":True}}))
    t0=time.time();o=None
    while time.time()-t0<timeout:
        try: m=json.loads(ws.recv())
        except Exception: return None
        if m.get("id")==1: o=m;break
    ws.close()
    try: return o["result"]["result"]["value"]
    except Exception: return None
def nav(url,w=6):
    p=pages()[0]
    ws=websocket.create_connection(p["webSocketDebuggerUrl"],timeout=40,max_size=None)
    ws.send(json.dumps({"id":1,"method":"Page.navigate","params":{"url":url}}))
    try: ws.recv()
    except Exception: pass
    ws.close(); time.sleep(w)
nav("https://www.nmmcm.org.cn/News/220.html",7)
print("TITLE:",jse("document.title"))
t=jse("(document.body&&document.body.innerText||'').slice(0,8000)")
print(t)
