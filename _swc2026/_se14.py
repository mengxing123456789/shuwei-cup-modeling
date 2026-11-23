import json,time,sys,io,requests,websocket,urllib.parse
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
for q in ["数维杯 2026 秋季赛 论文 格式规范 AIGC 检测 规则","2026数维杯秋季赛 D题 思路 双共振 轨道环"]:
    nav("https://www.baidu.com/s?wd="+urllib.parse.quote(q),4)
    v=jse("""JSON.stringify([...document.querySelectorAll('div.result,div.c-container')].slice(0,7).map(d=>[d.getAttribute('mu')||'',(d.innerText||'').replace(/\\s+/g,' ').slice(0,60)]))""")
    print("="*12,q[:34])
    try:
        for u,t in json.loads(v):
            if u.startswith("http") and "baidu.com" not in u: print("  ",u[:100],"|",t[:56])
    except Exception: print("none")
