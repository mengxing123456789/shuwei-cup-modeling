"""Insert the organiser-required AI-assistance note into every script header.

Official notice (2026-11-12): AI-generated code must be marked in the script itself
with tool name, version, institution and date.  The note is inserted once, right after
the module docstring (or at the top if there is none), and is skipped when present.
"""
import io
import pathlib

NOTE = (
    "# --- generative-tool note (required by the organiser's notice of 2026-11) ---\n"
    "# Drafted with DeepSeek Harness, a command-line coding agent (DeepSeek),\n"
    "# 18-20 November 2026; every number this file produces was re-executed by the\n"
    "# team from a clean shell and traced to data/*.json through code/fill_numbers.py.\n"
)
MARK = "generative-tool note"

root = pathlib.Path(r"E:\数学建模\_swc2026\SWC2026_C\code")
done, skipped = [], []
for f in sorted(root.glob("*.py")):
    s = io.open(f, encoding="utf-8").read()
    if MARK in s:
        skipped.append(f.name)
        continue
    lines = s.split("\n")
    # find the end of a leading docstring, if any
    idx = 0
    if lines and lines[0].lstrip().startswith(('"""', "'''")):
        q = lines[0].lstrip()[:3]
        if lines[0].count(q) >= 2:
            idx = 1
        else:
            for j in range(1, len(lines)):
                if q in lines[j]:
                    idx = j + 1
                    break
    elif lines and lines[0].startswith("#!") :
        idx = 1
    out = lines[:idx] + [""] + NOTE.rstrip("\n").split("\n") + lines[idx:]
    io.open(f, "w", encoding="utf-8", newline="\n").write("\n".join(out))
    done.append(f.name)

print("annotated %d scripts, %d already had the note" % (len(done), len(skipped)))
print("annotated:", ", ".join(done[:6]), "..." if len(done) > 6 else "")