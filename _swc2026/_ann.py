import zipfile,json,io,sys
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
p=r"C:\Users\29900\Downloads\AsterLink\C_Problem_Data\C_Problem_Data\Restocking_Problem_and_Data_EN\Restocking_Problem_and_Data_EN\Raw_Data\EgoDemo.zip"
zf=zipfile.ZipFile(p)
a=json.loads(zf.read("EgoDemo/E001/annotation.json")); print("annotation.json keys",list(a.keys())); print(json.dumps(a,ensure_ascii=False)[:800])
i=json.loads(zf.read("EgoDemo/E001/meta/info.json")); print("\ninfo.json keys",list(i.keys()))
print(json.dumps(i,ensure_ascii=False)[:1500])
