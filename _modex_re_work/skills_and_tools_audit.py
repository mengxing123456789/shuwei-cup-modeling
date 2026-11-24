# -*- coding: utf-8 -*-
"""Build the unique skill id list from pipelines_dump.txt and compare paper-kit
copies against the original tool layer under C:\\modex-mh-agent\\resources\\app\\tools."""
import hashlib
import json
import re
from collections import Counter, OrderedDict
from pathlib import Path

DUMP = Path(r"E:\数学建模\_modex_re_work\pipelines_dump.txt")
PK = Path(r"E:\数学建模\.agents\skills\paper-kit")
TOOLS = Path(r"C:\modex-mh-agent\resources\app\tools")
OUT = Path(r"E:\数学建模\_modex_re_work\skills_tools_audit.txt")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def parse_dump() -> "OrderedDict[str, dict]":
    tpl = OrderedDict()
    cur = None
    for line in DUMP.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            head, name, skill = line[3:].split("\t")[:3]
            cur = head.strip()
            tpl[cur] = {"name": name.strip(), "pipeline_skill": skill.split("=", 1)[1], "steps": []}
        elif line.startswith("  ") and cur:
            body = line.strip()
            m = re.match(r"(\S+)\t(.+?)\tcheckpoint=(True|False)/(\S+)", body)
            if m:
                tpl[cur]["steps"].append(
                    {"skill_name": m.group(1), "display_name": m.group(2),
                     "has_checkpoint": m.group(3) == "True", "checkpoint_type": m.group(4)}
                )
    return tpl


def main():
    tpl = parse_dump()
    skills = Counter()
    display = {}
    for t in tpl.values():
        for s in t["steps"]:
            skills[s["skill_name"]] += 1
            display.setdefault(s["skill_name"], s["display_name"])
    lines = [f"templates={len(tpl)}  unique_skill_ids={len(skills)}", ""]
    lines.append("== skill_id  (出现模板数)  display_name  出现在哪些模板 ==")
    where = {}
    for tname, t in tpl.items():
        for s in t["steps"]:
            where.setdefault(s["skill_name"], []).append(tname)
    for sid, n in sorted(skills.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"{sid}\t{n}\t{display.get(sid,'')}\t{','.join(where[sid])}")

    lines.append("")
    lines.append("== paper-kit vs 原厂 tools 逐文件比对 ==")
    pk_files = sorted([p for p in PK.rglob("*") if p.is_file()])
    same = diff = only = 0
    for p in pk_files:
        rel = p.relative_to(PK)
        name = p.name
        cand = TOOLS / name
        if cand.is_file():
            a, b = sha(p), sha(cand)
            if a == b:
                same += 1
                lines.append(f"SAME\t{rel}\t{len(p.read_bytes())}\tsha={a[:16]}")
            else:
                diff += 1
                lines.append(f"DIFF\t{rel}\t{len(p.read_bytes())}\tvs {len(cand.read_bytes())}\tpk={a[:16]} orig={b[:16]}")
        else:
            only += 1
            lines.append(f"LOCALONLY\t{rel}\t{len(p.read_bytes())}")
    lines.append(f"\nsummary same={same} diff={diff} local_only={only} total={len(pk_files)}")

    # which tools/*.py are absent from paper-kit/tools
    missing = []
    for p in sorted(TOOLS.glob("*.py")):
        if not (PK / "tools" / p.name).is_file():
            missing.append(f"{p.name}\t{p.stat().st_size}")
    lines.append(f"\n== 原厂 tools/*.py 未被搬进 paper-kit 的（{len(missing)}） ==")
    lines.extend(missing)

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:6]))
    print(f"... written {OUT} ({OUT.stat().st_size} B)")


if __name__ == "__main__":
    main()
