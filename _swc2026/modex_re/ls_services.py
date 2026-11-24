import os
root=r"C:\modex-mh-agent\resources\app\backend\services"
names=sorted(os.listdir(root))
for kw in ["precompile","vision","submission","writing","receipt","review","figure","checkpoint","artifact"]:
    print("==",kw)
    print([n for n in names if kw in n.lower()])
