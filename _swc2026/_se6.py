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
links=["http://www.baidu.com/link?url=dIR7EV0NLHzUV6v3I8HKxwUALkGegvYbq4RRlq-lp_DXxJ9Ryu",
       "http://www.baidu.com/link?url=WAbRJSiy8a8_HWxKt9xMsp-ygOJI7QbOwzeThtWwtEj42FXcxN",
       "http://www.baidu.com/link?url=qQcJlXhIcujIeWfgrjiD7JFJXsk6m_RJKHleqGCZrKzjOhlr6k"]
for L in links:
    jse(f"location.href='{L}';1",5)
    time.sleep(3)
    print(jse("location.href"))
