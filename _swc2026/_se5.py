import json,time,sys,io,requests,websocket,urllib.parse,re
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
BASE="http://127.0.0.1:9333"
def pages(): return [t for t in requests.get(f"{BASE}/json/list",timeout=8).json() if t["type"]=="page"]
def nav(url,wait=5):
    p=pages()[0]
    ws=websocket.create_connection(p["webSocketDebuggerUrl"],timeout=40,max_size=None)
    ws.send(json.dumps({"id":1,"method":"Page.navigate","params":{"url":url}})); 
    try: ws.recv()
    except Exception: pass
    ws.close(); time.sleep(wait)
def jse(expr,timeout=25):
    p=pages()[0]
    ws=websocket.create_connection(p["webSocketDebuggerUrl"],timeout=timeout+5,max_size=None)
    ws.send(json.dumps({"id":1,"method":"Runtime.evaluate","params":{"expression":expr,"returnByValue":True,"awaitPromise":True}}))
    t0=time.time();o=None
    while time.time()-t0<timeout:
        try: m=json.loads(ws.recv())
        except Exception as e: return None
        if m.get("id")==1: o=m;break
    ws.close()
    try: return o["result"]["result"]["value"]
    except Exception: return None
for q in ["2026数维杯秋季赛B题 深度解析","2026数维杯秋季赛D题 深度解析","数维杯 秋季赛 D题 双重共振"]:
    nav("https://www.baidu.com/s?wd="+urllib.parse.quote(q),4)
    js="""JSON.stringify([...document.querySelectorAll('h3 a')].map(a=>[a.innerText.trim(),a.href]))"""
    v=jse(js)
    print("="*20,q)
    if v:
        try:
            for t,h in json.loads(v)[:8]: print("  -",t[:70],"|",h[:80])
        except Exception as e: print("parse err",v[:200])
    else: print("  none / blocked:", jse("document.title"))
