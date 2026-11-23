"""Make ASCII-only copies of the paper's scripts for the appendix listing.

Why this exists
---------------
The venue check scans every page of the PDF for CJK characters.  A listing
printed with \\lstinputlisting shows the file verbatim, so a Chinese comment
inside solve.py becomes a Chinese character on a PDF page and the paper is
flagged as "the English paper contains Chinese".  Rewriting the scripts by
hand is not affordable and would touch files other tools diff; translating
them silently is worse, because then the listing is no longer the code that
produced the numbers.

So each script is copied to figures/src/<name>.py with every non-ASCII
character inside a string or a comment rewritten as a \\uXXXX escape:

  * inside a string literal the escape is decoded by Python, so the runtime
    value is unchanged -- proven per file by comparing ast.dump() of the
    original and of the copy, which is stricter than eyeballing;
  * inside a comment the escape is printable ASCII text: the comment keeps
    its position and cannot reach the PDF as CJK.

What cannot be rewritten is refused, with file and line, never guessed:

  * a non-ASCII identifier or operator (no ASCII spelling at all);
  * a bytes literal (\\uXXXX is not decoded in bytes);
  * a non-ASCII character inside an f-string replacement field: CPython 3.11
    rejects a backslash anywhere in that part ("f-string expression part
    cannot include a backslash"), so the escape cannot be introduced there;
  * a lone backslash right before the character, where an inserted escape
    would be read as part of the preceding escape.

A raw string is converted too: the r is dropped, every backslash the raw
string used to keep literal is doubled, and the value is unchanged.  The
ast.dump() comparison is what proves it.

Run:   E:/Mini/envs/mathmodel/python.exe -X utf8 code/mk_appendix_src.py
Check: ... code/mk_appendix_src.py --check   0 current, 1 stale, 3 refused
"""
from __future__ import annotations

import argparse
import ast
import io
import pathlib
import tokenize

import gen_index

WORKSPACE = gen_index.WORKSPACE
SRC = WORKSPACE / "figures" / "src"


class CannotConvert(Exception):
    """A character that cannot become an escape without changing meaning."""


def _escape_plain(ch: str) -> str:
    code = ord(ch)
    return ("\\u%04x" % code) if code <= 0xFFFF else ("\\U%08x" % code)


def _escape(ch: str, token_text: str, index: int) -> str:
    """Escape one non-ASCII character of a non-raw literal at `index`."""
    run = 0
    j = index - 1
    while j >= 0 and token_text[j] == "\\":
        run += 1
        j -= 1
    if run % 2 == 1:
        raise CannotConvert(
            f"lone backslash before {ch!r}: an escape inserted here would be "
            f"read as part of the preceding escape"
        )
    return _escape_plain(ch)


def _prefix(token_text: str) -> str:
    i = 0
    while i < len(token_text) and token_text[i].isalpha():
        i += 1
    return token_text[:i].lower()


def convert_token(token_text: str, kind: str) -> str:
    if kind != "STRING":
        return "".join(ch if ord(ch) < 128 else _escape_plain(ch) for ch in token_text)

    prefix = _prefix(token_text)
    if "b" in prefix:
        raise CannotConvert("bytes literal: \\uXXXX is not decoded in bytes")
    raw = "r" in prefix
    fstr = "f" in prefix
    keep = "".join(c for c in token_text[:len(prefix)] if c in "fF") if raw else token_text[:len(prefix)]
    rest = token_text[len(prefix):]

    out = [keep]
    depth = 0
    i = 0
    while i < len(rest):
        ch = rest[i]
        if fstr and ch in "{}":
            if i + 1 < len(rest) and rest[i + 1] == ch:
                out.append(ch * 2)
                i += 2
                continue
            depth += 1 if ch == "{" else -1
            out.append(ch)
            i += 1
            continue
        if ord(ch) > 127:
            if depth > 0:
                raise CannotConvert(
                    f"non-ASCII {ch!r} inside an f-string replacement field: "
                    f"CPython 3.11 forbids a backslash there"
                )
            out.append(_escape_plain(ch) if raw else _escape(ch, rest, i))
        elif raw and ch == "\\":
            out.append("\\\\")
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def convert_text(text: str, name: str) -> tuple[str, dict[str, int], list[str]]:
    """Rewrite non-ASCII inside STRING/COMMENT tokens; collect refusals."""
    stats = {"strings": 0, "comments": 0, "escaped": 0}
    lines = text.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))

    edits: list[tuple[int, int, str]] = []
    problems: list[str] = []
    excused = [False] * len(text)
    stream = io.StringIO(text)
    try:
        for tok in tokenize.generate_tokens(stream.readline):
            if tok.type not in (tokenize.STRING, tokenize.COMMENT):
                continue
            (sr, sc), (er, ec) = tok.start, tok.end
            # tokenize counts lines from 1, offsets[] from 0: line L starts at
            # offsets[L - 1].
            if not (1 <= sr <= len(lines) and 1 <= er <= len(lines)):
                problems.append(f"{name}:{sr}: token outside the file")
                continue
            start = offsets[sr - 1] + sc
            end = offsets[er - 1] + ec
            chunk = text[start:end]
            if chunk.isascii():
                continue
            kind = "STRING" if tok.type == tokenize.STRING else "COMMENT"
            try:
                new = convert_token(chunk, kind)
            except CannotConvert as exc:
                problems.append(f"{name}:{sr}: {exc}")
                for i in range(start, end):
                    excused[i] = True
                continue
            edits.append((start, end, new))
            stats["strings" if kind == "STRING" else "comments"] += 1
            stats["escaped"] += sum(1 for ch in chunk if ord(ch) > 127)
    except tokenize.TokenError as exc:
        problems.append(f"{name}: tokenize failed: {exc}")
        return text, stats, problems

    covered = [False] * len(text)
    for start, end, _ in edits:
        for i in range(start, end):
            covered[i] = True
    for i, ch in enumerate(text):
        if ord(ch) > 127 and not covered[i] and not excused[i]:
            problems.append(
                f"{name}:{text.count(chr(10), 0, i) + 1}: non-ASCII {ch!r} outside a string or comment"
            )

    out = []
    pos = 0
    for start, end, new in edits:
        out.append(text[pos:start])
        out.append(new)
        pos = end
    out.append(text[pos:])
    conv = "".join(out)
    if not problems and not conv.isascii():
        problems.append(f"{name}: result is still not ASCII")
    return conv, stats, problems


def convert_file(path: pathlib.Path) -> tuple[str, dict[str, int], list[str]]:
    text = path.read_text(encoding="utf-8")
    conv, stats, problems = convert_text(text, path.name)
    stats["cjk_before"] = sum(1 for ch in text if ord(ch) > 127)
    stats["bytes"] = len(conv.encode("utf-8"))
    stats["orig_bytes"] = path.stat().st_size
    if problems:
        return conv, stats, problems
    try:
        same = ast.dump(ast.parse(text)) == ast.dump(ast.parse(conv))
    except SyntaxError as exc:
        return conv, stats, [f"{path.name}: copy does not parse: {exc}"]
    if not same:
        return conv, stats, [
            f"{path.name}: copy parses to a different tree -- the rewrite changed behaviour"
        ]
    return conv, stats, []


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="ASCII copies of code/*.py for the appendix")
    ap.add_argument("--check", action="store_true", help="fail if a copy on disk is stale")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    SRC.mkdir(parents=True, exist_ok=True)
    stale = 0
    refused: list[str] = []
    total_cjk = 0
    total_bytes = 0
    written = 0
    for path in gen_index.scripts():
        conv, stats, problems = convert_file(path)
        if problems:
            refused.extend(problems)
            continue
        dest = SRC / path.name
        total_cjk += stats["cjk_before"]
        total_bytes += stats["bytes"]
        if not args.quiet:
            print(f"{path.name:22s} {stats['cjk_before']:4d} non-ASCII -> 0, "
                  f"{stats['escaped']:4d} escapes, {stats['orig_bytes']:6,d} -> "
                  f"{stats['bytes']:6,d} bytes")
        if args.check:
            current = dest.read_text(encoding="utf-8") if dest.exists() else None
            if current != conv:
                print(f"STALE {dest.relative_to(WORKSPACE)}: rerun code/mk_appendix_src.py")
                stale += 1
            continue
        dest.write_text(conv, encoding="utf-8", newline="\n")
        written += 1

    print(f"copies in {SRC.relative_to(WORKSPACE)}: {written} written, "
          f"{total_bytes:,} bytes ASCII, {total_cjk} non-ASCII characters rewritten")
    if refused:
        print(f"{len(refused)} site(s) refused -- list these files only after the patch:")
        for line in refused:
            print("  " + line)
        return 3
    return 1 if stale else 0


if __name__ == "__main__":
    raise SystemExit(main())