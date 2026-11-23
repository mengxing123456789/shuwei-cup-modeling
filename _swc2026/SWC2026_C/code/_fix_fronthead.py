# -*- coding: utf-8 -*-
"""Remove the running head from the summary page (p1) and the contents page (p2).

Why the two rules crossed the red text: `\\fancypagestyle{summarysheet}` cleared the
header *fields* with \\fancyhf{} but inherited \\headrulewidth from the class (1pt), so
the summary sheet still drew a head rule; \\@maketitle pulls the problem/team band up
28mm into that zone, so the rule ran through the red glyphs.  The class also draws its
own 1.5pt rule under the band, hence two lines.

The statement (第三条) only requires the team number and the page number at the top of
every page of the *body*, so the front matter may go without a head; we keep a foot
page number so the "Page n of 25" count stays readable.
"""
import io
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MAIN = ROOT / "main.tex"

OLD_STYLE = (
    r"\fancypagestyle{summarysheet}{\fancyhf{}\fancyfoot[R]{\small Page \thepage\ of \pageref{BodyLastPage}}}"
)
NEW_STYLE = "\n".join([
    r"\fancypagestyle{summarysheet}{%",
    r"  \fancyhf{}%",
    r"  \renewcommand{\headrulewidth}{0pt}%",
    r"  \renewcommand{\footrulewidth}{0pt}%",
    r"  \fancyfoot[R]{\small Page \thepage\ of \pageref{BodyLastPage}}}",
])

OLD_TOC = r"\tableofcontents" + "\n" + r"\thispagestyle{fancy}"
NEW_TOC = r"\tableofcontents" + "\n" + r"\thispagestyle{summarysheet}"

def main():
    apply = "--apply" in sys.argv
    text = io.open(MAIN, encoding="utf-8").read()
    before = len(text)

    n1 = text.count(OLD_STYLE)
    n2 = text.count(OLD_TOC)
    print("summarysheet style occurrences:", n1)
    print("toc pagestyle occurrences:", n2)
    if n1 != 1 or n2 != 1:
        print("ABORT: expected exactly one of each")
        return 1

    new = text.replace(OLD_STYLE, NEW_STYLE).replace(OLD_TOC, NEW_TOC)
    print("bytes %d -> %d" % (before, len(new)))
    if not apply:
        print("dry run; pass --apply to write")
        return 0
    io.open(MAIN, "w", encoding="utf-8", newline="\n").write(new)
    print("written", MAIN)
    return 0

if __name__ == "__main__":
    sys.exit(main())
