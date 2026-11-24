import marshal, sys, io, json

p = r"C:\modex-mh-agent\resources\app\backend\services\skill_mcp.pyc"
d = open(p, "rb").read()
code = marshal.loads(d[16:])

out = []

def walk(c, path=""):
    name = path + c.co_name
    out.append((name, len(c.co_code), c.co_consts))
    for k in c.co_consts:
        if hasattr(k, "co_code"):
            walk(k, name + ".")

walk(code)
print("total code objects:", len(out))
with open(r"E:\数学建模\_modex_re_work\skill_mcp_objects.txt", "w", encoding="utf-8") as f:
    for name, size, consts in out:
        f.write(f"{size:6d}  {name}\n")
        for k in consts:
            if isinstance(k, str) and len(k) > 40:
                f.write("        STR: " + k.replace("\n", "\\n")[:600] + "\n")
print("done")
