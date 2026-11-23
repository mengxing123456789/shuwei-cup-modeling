import os
for sub in [r"C:\modex-mh-agent\resources\app\backend", r"C:\modex-mh-agent\resources\app\backend\routers", r"C:\modex-mh-agent\resources\app\backend\services"]:
    print("==",sub)
    try:
        print([n for n in sorted(os.listdir(sub)) if any(k in n.lower() for k in ["precomp","vision","compile","paper","figure"])])
    except Exception as e: print(e)
