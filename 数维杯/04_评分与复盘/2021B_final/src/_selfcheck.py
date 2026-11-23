import json, re, sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]          # 2021_B_ExtremeRainfall
PDF = ROOT / "04_paper" / "main.pdf"
RESULTS = ROOT / "03_results"
OUT = ROOT / "05_audit" / "selfcheck_report.json"

doc = fitz.open(PDF)
text_pages = [p.get_text() for p in doc]
full = "\n".join(text_pages)

# page landmarks
def find_page(pattern):
    rx = re.compile(pattern)
    for i, t in enumerate(text_pages):
        if rx.search(t):
            return i + 1
    return None

landmarks = {
    "summary": find_page(r"\bSummary\b"),
    "contents": find_page(r"^\s*Contents\s*$|^Contents$"),
    "intro": find_page(r"^1\s*\n?\s*Introduction"),
    "assume": find_page(r"^2\s*\n?\s*Assumptions"),
    "data": find_page(r"^3\s*\n?\s*Data"),
    "q1": find_page(r"^4\s*\n?\s*Task\s*1"),
    "q2": find_page(r"^5\s*\n?\s*Task\s*2"),
    "q3": find_page(r"^6\s*\n?\s*Task\s*3"),
    "q4": find_page(r"^7\s*\n?\s*Task\s*4"),
    "q5": find_page(r"^8\s*\n?\s*Task\s*5"),
    "eval": find_page(r"^9\s*\n?\s*Sensitivity"),
    "refs": find_page(r"^References\s*$"),
    "appendix": find_page(r"^A\s*\n?\s*Notation"),
}

body_pages = None
if landmarks["intro"] and landmarks["refs"]:
    body_pages = landmarks["refs"] - landmarks["intro"]
front = None
if landmarks["intro"]:
    front = landmarks["intro"] - 1  # summary + contents

# structural counts
n_fig = len(re.findall(r"^Figure\s+\d+:", full, re.M))
n_tab = len(re.findall(r"^Table\s+\d+:", full, re.M))
n_eq = len(re.findall(r"\(\d+\)", full))
words = len(re.findall(r"[A-Za-z][A-Za-z\-']+", full))

# fonts
fonts = set()
for p in doc:
    for f in p.get_fonts():
        fonts.add((f[3], f[4]))

# placeholder / anonymity / TODO scan
bad = []
for pat in [r"TODO", r"XXX", r"待补", r"lorem", r"\?\?"]:
    hits = re.findall(pat, full)
    if hits:
        bad.append({"pattern": pat, "count": len(hits)})
anon_hits = re.findall(r"(?i)university|college|@|\b(student|author)\b", full)

# key numbers to cross-check against results json
def load(name):
    p = RESULTS / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

def flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, f"{prefix}{k}."))
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        out[prefix[:-1]] = float(obj)
    return out

flat = {}
for name in ["q1_results.json", "q2_results.json", "q3_results.json", "q4_results.json", "q5_results.json"]:
    d = load(name)
    if d:
        for k, v in flatten(d).items():
            flat[f"{name[:-5]}:{k}"] = v

# numbers appearing in text with 3+ significant digits, check each has a plausible source
text_nums = re.findall(r"(?<![\w.])-?\d+\.\d{2,}", full)
uniq_text = sorted(set(text_nums), key=lambda s: -len(s))
values = list(flat.values())
tol = lambda a, b: abs(a - b) <= max(0.02 * max(abs(a), abs(b)), 0.05)
unmatched = []
for s in uniq_text:
    x = float(s)
    if not any(tol(x, v) for v in values):
        unmatched.append(s)

report = {
    "file": str(PDF),
    "pages_total": len(doc),
    "page_landmarks": landmarks,
    "body_pages": body_pages,
    "front_matter_pages": front,
    "summary_plus_toc_plus_body": (front + body_pages) if (front and body_pages) else None,
    "figures_captioned": n_fig,
    "tables_captioned": n_tab,
    "display_equations": n_eq,
    "words_total": words,
    "fonts": sorted({f"{a}@{b}" for a, b in fonts})[:12],
    "placeholders": bad,
    "anonymity_hits": anon_hits[:10],
    "numbers_in_text_3sig": len(uniq_text),
    "numbers_not_matching_any_json_value": unmatched[:40],
    "results_json_keys": len(flat),
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({k: v for k, v in report.items() if k not in ("fonts",)}, ensure_ascii=False, indent=2))
# dump full text with page markers for reviewers
txt = "\n\n".join(f"=== PAGE {i+1} ===\n{t}" for i, t in enumerate(text_pages))
(ROOT / "05_audit" / "paper_text.txt").write_text(txt, encoding="utf-8")
print("wrote paper_text.txt")