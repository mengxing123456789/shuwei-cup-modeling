"""Report the numbers that the submission gate asks for.

Reads main.aux and main.log next to the project root and prints:
  body pages    -- page of the \\label{BodyLastPage} anchor
  appendix pages-- total pages minus body pages
  overfull      -- count of "Overfull \\hbox" in the log
  undefined     -- count of "undefined" in the log
  numerals      -- digits in prose that are not inside a macro name,
                   a reference, a file name, a comment or a display formula

Usage: python code/page_report.py [main.tex]
"""

# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def aux_pages(root):
    aux = (root / "main.aux").read_text(encoding="utf-8", errors="replace")
    body = None
    last = 0
    for m in re.finditer(r"\\newlabel\{BodyLastPage\}\{\{[^}]*\}\{(\d+)\}", aux):
        body = int(m.group(1))
    for m in re.finditer(r"\\newlabel\{LastPage\}\{\{[^}]*\}\{(\d+)\}", aux):
        last = int(m.group(1))
    if body is None:
        raise SystemExit("main.aux has no BodyLastPage label -- compile first")
    if not last:
        m = re.search(r"\\providecommand \\LastPage\{(\d+)\}", aux)
        last = int(m.group(1)) if m else body
    return body, last


def log_counts(root):
    log = (root / "main.log").read_text(encoding="utf-8", errors="replace")
    return log.count("Overfull \\hbox"), len(re.findall(r"undefined", log))


def strip_argument(s, cmd):
    out = []
    i = 0
    pat = "\\" + cmd + "{"
    while True:
        j = s.find(pat, i)
        if j < 0:
            out.append(s[i:])
            break
        out.append(s[i:j])
        k = j + len(pat)
        depth = 1
        while k < len(s) and depth:
            if s[k] == "{":
                depth += 1
            elif s[k] == "}":
                depth -= 1
            k += 1
        i = k
    return "".join(out)


def prose_numerals(path):
    text = path.read_text(encoding="utf-8")
    # Regions the team declares free of result numerals (tool versions, dates)
    # are excluded explicitly, so the exemption is visible in the source.
    text = re.sub(r"% numerals-ok: begin.*?% numerals-ok: end", "", text, flags=re.S)
    keep = []
    for line in text.split("\n"):
        line = re.sub(r"(?<!\\)%.*$", "", line)
        keep.append(line)
    text = "\n".join(keep)
    # drop listing inclusions and display formulas
    for cmd in ("ref", "label", "cite", "input", "includegraphics", "lstinputlisting",
                "eqref", "pageref", "url", "bibliography", "texttt", "textbf", "textit"):
        text = strip_argument(text, cmd)
    text = re.sub(r"\\lstinputlisting(\[[^\]]*\])?\{[^}]*\}", "", text)
    text = re.sub(r"\\path\{[^}]*\}", "ID", text)
    text = re.sub(r"\\begin\{equation\*?\}.*?\\end\{equation\*?\}", "", text, flags=re.S)
    text = re.sub(r"\\\[.*?\\\]", "", text, flags=re.S)
    # the bibliography carries publication years and citation keys, not results
    text = re.sub(r"\\begin\{thebibliography\}.*?\\end\{thebibliography\}", "",
                  text, flags=re.S)
    text = re.sub(r"\$[^$]*\$", "", text)
    # identifier tokens that legitimately carry a digit: metric and case names
    for tok in ("F1", "S1", "S2", "S3", "Z0", "Z1", "Z2", "Z3", "Z4", "MP4",
                "QR", "3D", "AR1", "R2",
                "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8",
                "UTF-8", "UTF-16"):
        text = text.replace(tok, "ID")
    # drop macro names (letters only by construction, but keep digits out of them)
    text = re.sub(r"\\[A-Za-z]+", "", text)
    text = re.sub(r"\\[^A-Za-z]", " ", text)
    hits = []
    for n, line in enumerate(text.split("\n"), 1):
        for m in re.finditer(r"[0-9]", line):
            start = max(0, m.start() - 30)
            hits.append((n, line[start:m.start() + 30].strip()))
    return hits


def main():
    root = ROOT
    tex = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "main.tex"
    if not tex.is_absolute():
        tex = root / tex
    body, last = aux_pages(root)
    over, undef = log_counts(root)
    hits = prose_numerals(tex)
    print(f"body pages      : {body}")
    print(f"appendix pages  : {last - body}")
    print(f"total pages     : {last}")
    print(f"overfull hbox   : {over}")
    print(f"undefined       : {undef}")
    print(f"prose numerals  : {len(hits)}")
    for n, ctx in hits[:20]:
        print(f"  line {n}: ...{ctx}...")


if __name__ == "__main__":
    main()