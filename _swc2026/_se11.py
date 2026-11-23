import json,time,sys,io,requests,websocket,urllib.parse,re
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
BASE="http://127.0.0.1:9333"
def pages(): return [t for t in requests.get(f"{BASE}/json/list",timeout=8).json() if t["type"]=="page"]
def jse(expr,timeout=30):
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
def nav(url,w=4):
    p=pages()[0]
    ws=websocket.create_connection(p["webSocketDebuggerUrl"],timeout=40,max_size=None)
    ws.send(json.dumps({"id":1,"method":"Page.navigate","params":{"url":url}}))
    try: ws.recv()
    except Exception: pass
    ws.close(); time.sleep(w)
for q in ["2026数维杯秋季赛B题 深度解析","2026数维杯秋季赛A题 深度解析"]:
    nav("https://www.baidu.com/s?wd="+urllib.parse.quote(q),4)
    v=jse("""JSON.stringify([...document.querySelectorAll('div.result,div.c-container')].slice(0,6).map(d=>[d.getAttribute('mu')||'', (d.innerText||'').slice(0,40)]))""")
    print("="*15,q)
    print(v[:900] if v else "none")
