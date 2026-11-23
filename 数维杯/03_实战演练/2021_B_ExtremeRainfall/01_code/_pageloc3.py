import re, json
from pathlib import Path
import fitz

ROOT = Path(__file__).resolve().parents[1]
doc = fitz.open(ROOT / "04_paper" / "main.pdf")
pages = [re.sub(r"\s+", " ", p.get_text()) for p in doc]

targets = {
    "contents": r"\bContents\b",
    "intro": r"\b1 Introduction\b",
    "assume": r"\b2 Assumptions\b",
    "data": r"\b3 Data\b",
    "q1": r"\b4 Task 1\b",
    "q2": r"\b5 Task 2\b",
    "q3": r"\b6 Task 3\b",
    "q4": r"\b7 Task 4\b",
    "q5": r"\b8 Task 5\b",
    "eval": r"\b9 Sensitivity\b",
    "refs": r"\bReferences\b",
    "appendix": r"\bA Notation\b",
}

found = {}
for name, pat in targets.items():
    rx = re.compile(pat)
    hit = None
    for i, t in enumerate(pages):
        if rx.search(t):
            # skip the table of contents page for section headings
            if name != "contents" and i == found.get("contents", -10) - 1:
                continue
            hit = i + 1
            break
    found[name] = hit

body = None
front = None
if found["intro"] and found["refs"]:
    body = found["refs"] - found["intro"]
    front = found["intro"] - 1

out = {
    "pages_total": len(doc),
    "landmarks": found,
    "body_pages": body,
    "front_matter_pages": front,
    "summary_plus_toc_plus_body": (front + body) if (front and body) else None,
}
(ROOT / "05_audit" / "page_map.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=2))