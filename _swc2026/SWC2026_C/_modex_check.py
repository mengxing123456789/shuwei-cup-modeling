import pathlib
import sys

APP = r"C:\modex-mh-agent\resources\app\backend"
sys.path.insert(0, APP)
sys.path.insert(0, APP + r"\services")
import paper_modeling_quality as Q

P = pathlib.Path(r"E:\数学建模\_swc2026\SWC2026_C")
text = (P / "main.tex").read_text(encoding="utf-8")
print("anchors        :", sorted(Q._extract_paper_problem_anchors(text)))
print("display math   :", len(Q._extract_display_math(text)))
print("opt evidence   :", Q._optimization_evidence(text))
print("notation rows  :", Q._notation_row_count(text))
for n, t in Q._split_problem_sections(text):
    print(f"section {n}: {len(t)} chars, gaps={Q._solver_depth_gaps(t, '')}")