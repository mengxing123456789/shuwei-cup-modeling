import json
p=r"E:\数学建模\_swc2026\SWC2026_A\data\ledger.json"
d=json.load(open(p,encoding="utf-8"))
recs=[]
for f in d.get("files",[]):
    recs.append({"name":f["name"],"source":f.get("source",""),"url":f.get("origin",""),
                 "sha256":f["sha256"],"fetched_at":f.get("ingested_at",""),"size":f["size"],
                 "verdict":f.get("verdict","")})
d["records"]=recs
json.dump(d,open(p,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
print("records",len(recs))
