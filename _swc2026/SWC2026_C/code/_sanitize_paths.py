import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
TARGETS = []
for sub in ("data", "code", "tables", "snippets"):
    d = ROOT / sub
    if d.exists():
        TARGETS += [p for p in d.rglob("*") if p.is_file() and p.suffix in {".json", ".py", ".tex", ".md", ".ps1", ".txt", ".csv"}]
TARGETS.append(ROOT / "README_FJ.md")

REPLACEMENTS = [
    ("C:\\\\Users\\\\29900\\\\Downloads\\\\AsterLink\\\\C_Problem_Data\\\\C_Problem_Data\\\\Restocking_Problem_and_Data_EN\\\\Restocking_Problem_and_Data_EN", "Restocking_Problem_and_Data_EN"),
    ("Restocking_Problem_and_Data_EN", "Restocking_Problem_and_Data_EN"),
    ("C:\\\\Users\\\\29900\\\\Desktop\\\\Restocking_Problem_and_Data_EN", "Restocking_Problem_and_Data_EN"),
    ("Restocking_Problem_and_Data_EN", "Restocking_Problem_and_Data_EN"),
    ("Restocking_Problem_and_Data_EN", "Restocking_Problem_and_Data_EN"),
    ("E:\\\\数学建模\\\\_swc2026\\\\SWC2026_C\\\\", ""),
    ("", ""),
    ("E:\\\\数学建模\\\\_swc2026\\\\", ""),
    ("", ""),
    ("", ""),
    ("E:\\\\数学建模", "."),
    (".", "."),
]

changed = []
for p in TARGETS:
    if not p.exists():
        continue
    try:
        s = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    old = s
    for a, b in REPLACEMENTS:
        s = s.replace(a, b)
    if s != old:
        if p.suffix == ".json":
            try:
                json.loads(s)
            except Exception as e:
                print("JSON-INVALID after", p, e)
                continue
        p.write_text(s, encoding="utf-8", newline="\n")
        changed.append(str(p.relative_to(ROOT)))

print("changed", len(changed))
for c in changed:
    print(c)
