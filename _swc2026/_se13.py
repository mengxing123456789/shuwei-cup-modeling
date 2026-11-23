import json,time,sys,io,os,requests,websocket
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
BASE="http://127.0.0.1:9333"; OUT=r"E:\数学建模\_swc2026\_posts"
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
tgt={"zhihuB":"https://zhuanlan.zhihu.com/p/2107061938349946514",
     "zhihuABCD":"https://zhuanlan.zhihu.com/p/2106780738486064128",
     "csdnC":"https://blog.csdn.net/qq_40379132/article/details/171096962",
     "csdnAB":"https://blog.csdn.net/qq_40379132/article/details/160869338"}
for k,u in tgt.items():
    nav(u,6)
    t=jse("document.title")
    body=jse("(document.body&&document.body.innerText||'').slice(0,60000)")
    n=len(body or "")
    p=os.path.join(OUT,k+".txt")
    open(p,"w",encoding="utf-8",newline="\n").write(f"URL: {u}\nTITLE: {t}\nLEN: {n}\n\n"+(body or ""))
    print(k,"|",(t or "")[:60],"|",n)
