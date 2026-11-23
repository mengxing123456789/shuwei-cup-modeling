import json,time,sys,io,os,requests,websocket,urllib.parse
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
BASE="http://127.0.0.1:9333"; OUT=r"E:\数学建模\_swc2026\_posts"
os.makedirs(OUT,exist_ok=True)
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
found={}
for tag,q in [("D","2026数维杯秋季赛D题 深度解析"),("C","2026数维杯秋季赛C题 深度解析"),("AB","2026数维杯秋季赛 B题 无人机 思路 CSDN")]:
    nav("https://www.baidu.com/s?wd="+urllib.parse.quote(q),4)
    v=jse("""JSON.stringify([...document.querySelectorAll('div.result,div.c-container')].slice(0,7).map(d=>[d.getAttribute('mu')||'',(d.innerText||'').slice(0,30)]))""")
    print("="*12,tag)
    try: rows=json.loads(v)
    except Exception: rows=[]
    for u,t in rows:
        if u.startswith("http") and ("zhihu" in u or "csdn" in u or "bilibili" in u):
            print("  ",u,"|",t[:40]); found.setdefault(tag,[]).append(u)
json.dump(found,open(os.path.join(OUT,"_index.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=1)
