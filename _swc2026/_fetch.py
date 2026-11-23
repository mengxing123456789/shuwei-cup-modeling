import json,time,sys,io,requests,websocket,os
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
BASE="http://127.0.0.1:9333"
OUT=r"E:\数学建模\_swc2026\_posts"
os.makedirs(OUT,exist_ok=True)
def pages(): return requests.get(f"{BASE}/json/list",timeout=8).json()
def ev(ws,expr,timeout=30):
    ws.send(json.dumps({"id":1,"method":"Runtime.evaluate","params":{"expression":expr,"returnByValue":True,"awaitPromise":True}}))
    t0=time.time();o=None
    while time.time()-t0<timeout:
        try: m=json.loads(ws.recv())
        except Exception as e: return {"err":str(e)}
        if m.get("id")==1: o=m;break
    return o
def fetch(url,name,wait=6):
    p=[t for t in pages() if t["type"]=="page"][0]
    ws=websocket.create_connection(p["webSocketDebuggerUrl"],timeout=35,max_size=None)
    ws.send(json.dumps({"id":1,"method":"Page.navigate","params":{"url":url}}))
    try: ws.recv()
    except Exception: pass
    ws.close()
    time.sleep(wait)
    p=[t for t in pages() if t["type"]=="page"][0]
    ws=websocket.create_connection(p["webSocketDebuggerUrl"],timeout=60,max_size=None)
    r=ev(ws,"document.title+'\\n@@@\\n'+(document.body?document.body.innerText:'')")
    ws.close()
    txt=""; 
    if r and "result" in r and "result" in r["result"]:
        txt=r["result"]["result"].get("value","")
    open(os.path.join(OUT,name+".txt"),"w",encoding="utf-8").write(txt)
    print(f"[{name}] len={len(txt)}"); print(txt[:1500].replace("\n"," | ")[:1500]); print("-"*60)
    return txt

fetch("https://zhuanlan.zhihu.com/p/2107052257086908137","zhihuA",7)
fetch("https://blog.csdn.net/qq_40379132/article/details/171096962","csdnC",7)
