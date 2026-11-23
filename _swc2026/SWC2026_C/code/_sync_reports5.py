# -*- coding: utf-8 -*-
from pathlib import Path

ROOT = Path(r".\_swc2026")
files = ["43-官方格式核对与图表重做.md", "45-逐问复查与参数核对.md", "47-备用稿与获奖论文对比评估.md"]
repl = [
    ("2,059,928", "2,475,316"),
    ("66 页 (body 25 / appendix 41)", "67 页 (body 25 / appendix 42)"),
    ("12,189,330", "12,695,666"),
    ("549 条目", "558 条目"),
    ("13.78 MB", "14.66 MB"),
    ("626 defined / 620 used", "626 defined / 618 used"),
    ("619 条", "618 条"),
    ("全量 1,548", "全量 1,655"),
    ("1,568 条", "1,655 条"),
    ("66 页，正文 25 页（p3–p25），附录 A–N 41 页", "67 页，正文 25 页（p3–p25），附录 A–O 42 页"),
    ("66 页：正文 25 / 附录 41", "67 页：正文 25 / 附录 42"),
    ("附录 41 页、总 66 页", "附录 42 页、总 67 页"),
    ("附录 41 / 总 66 页", "附录 42 / 总 67 页"),
    ("549 条目可解压重编译", "558 条目可解压重编译"),
]
for name in files:
    p = ROOT / name
    s = p.read_text(encoding="utf-8")
    n = 0
    for a, b in repl:
        if a in s:
            n += s.count(a)
            s = s.replace(a, b)
    p.write_text(s, encoding="utf-8")
    print(name, "replacements", n)
