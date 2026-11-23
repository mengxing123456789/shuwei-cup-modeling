"""Rebuild tables/app_n.tex: restored original body + the four tables that the
broken mover script had appended at the tail of the corrupted copy.

The corrupted copy (app_n.tex.broken_20261122_1240) had a full copy of the
article body spliced in; the moved tables survive at its tail, each preceded by
a '\\subsection*{Tables moved out of the body}' line. We take only those blocks.
"""

import io

BASE = "tables/app_n.tex"          # restored clean original (133 lines)
BROKEN = "tables/app_n.tex.broken_20261122_1240"
OUT = "tables/app_n.tex"

WANT = ["tab:ablation", "tab:negative", "tab:env", "tab:intervals", "tab:paired"]


def blocks(lines):
    """Yield (label, block_lines) for every table block in lines."""
    out = []
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith("\\begin{table}"):
            depth = 0
            j = i
            while j < len(lines):
                s = lines[j].strip()
                if s.startswith("\\begin{table}"):
                    depth += 1
                elif s.startswith("\\end{table}"):
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            block = lines[i : j + 1]
            label = ""
            for l in block:
                if "\\label{tab:" in l:
                    label = l.split("\\label{")[1].split("}")[0]
                    break
            out.append((label, block))
            i = j + 1
        else:
            i += 1
    return out


def main():
    base = io.open(BASE, encoding="utf-8").read().rstrip("\n")
    broken = io.open(BROKEN, encoding="utf-8").read().splitlines()

    found = {}
    for label, block in blocks(broken):
        if label in WANT:
            found[label] = block  # last occurrence wins = the moved copy

    missing = [w for w in WANT if w not in found]
    if missing:
        raise SystemExit("missing in broken copy: %s" % missing)

    parts = [base, "\n\\subsection{Tables moved out of the body}\n"]
    for w in WANT:
        parts.append("\n".join(found[w]).rstrip("\n") + "\n")
    text = "\n".join(parts)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(text)
    print("wrote %d bytes, %d labels: %s" % (len(text.encode("utf-8")), len(found), WANT))


if __name__ == "__main__":
    main()
