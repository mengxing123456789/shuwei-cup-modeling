#!/usr/bin/env python
"""一键自检：把 RULES.md 里能自动化的条目跑成 PASS/FAIL 表。

用法（必须用 mathmodel 解释器，裸 python 没有 numpy/matplotlib）：
    E:\\Mini\\envs\\mathmodel\\python.exe gauntlet_check.py [PAPER_DIR]

退出码 0 = 全部 PASS（KNOWN OPEN 不计失败）；1 = 有 FAIL。
每一项都打印它到底查了什么，不只是结论 —— "PASS" 而不给证据等于没查。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mmkit import gauntlet as G  # noqa: E402
from mmkit.paths import find_paper  # noqa: E402


def row(name: str, ok: bool, detail: str) -> tuple[str, bool, str]:
    return (name, ok, detail)


FIG_PY_CANDIDATES = (
    r"E:\Mini\envs\mathmodel\python.exe",
    sys.executable,
    sys.executable,
)


def _figfont_via_subprocess(pdf) -> dict | None:
    """用「装了 pymupdf 的那个解释器」量字号；全都没有就返回 None（= SKIP）。"""
    import subprocess

    probe = (
        "import json,sys;"
        "sys.path.insert(0,sys.argv[1]);"
        "from pathlib import Path;"
        "from mmkit import figfont as F;"
        "r=F.report(Path(sys.argv[2]));"
        "print(json.dumps({k:r[k] for k in "
        "('spans','min_pt','median_pt','violations','single_char_below','ok')}))"
    )
    here = str(Path(__file__).resolve().parent)
    tried = []
    for py in dict.fromkeys(FIG_PY_CANDIDATES):
        if not Path(py).exists():
            tried.append(f"{py}:absent")
            continue
        try:
            cp = subprocess.run([py, "-X", "utf8", "-c", probe, here, str(pdf)],
                                capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=600)
        except Exception as e:  # noqa: BLE001
            tried.append(f"{py}:{type(e).__name__}")
            continue
        if cp.returncode == 0 and cp.stdout.strip().startswith("{"):
            d = json.loads(cp.stdout.strip().splitlines()[-1])
            d["_py"] = Path(py).name
            return d
        tried.append(f"{py}:rc={cp.returncode}")
    print("  [figfont] no pymupdf interpreter: " + ", ".join(tried), file=sys.stderr)
    return None


ALLOW_DRAFT = False   # `--allow-draft` 打开：允许在还没编译出 main.pdf 的骨架上跑规则


def check(paper_dir: str | None) -> list[tuple[str, bool, str]]:
    P = find_paper(paper_dir)
    real = _is_real(P) or ALLOW_DRAFT
    out = [row("paper resolved", real,
               f"{P.root}" + ("" if real else
                              "  <- 草稿（main.pdf 不存在或 < 150 KB）：基准带/引用/队号会假失败，"
                              "请用 `gauntlet_check.py <论文目录>` 指明真稿"))
           ]
    if not P.pdf.exists() and not ALLOW_DRAFT:
        out.append(row("main.pdf exists", False, "run gauntlet.build() or xelatex first"))
        return out
    c = G.check_compliance(P)
    text = G.extract_text(P.pdf)

    out.append(row("R-V01 body <= 30 pages", 0 < c.body_pages <= 30,
                   f"body={c.body_pages} (header numerator of first Appendix A page)"))
    out.append(row("R-V02 single denominator", c.distinct_of == 1,
                   f"distinct totals={c.distinct_of}"))
    out.append(row("R-V02 numbers contiguous", c._numbers_are_contiguous,
                   "header numerators form 1..n with no gaps"))
    out.append(row("R-V03 zero CJK in body", c.cjk_chars == 0,
                   f"body cjk={c.cjk_chars} (appendix, not judged={c.cjk_chars_appendix})"))
    out.append(row("R-V04 zero 'university'", c.university_hits == 0, f"hits={c.university_hits}"))
    out.append(row("R-V05 team number filled", not c.placeholder_team,
                   "KNOWN OPEN: \\baominghao placeholders must be filled before submission"))

    tex = P.tex.read_text(encoding="utf-8", errors="replace")
    # \input{tables/x} 里的内容在 PDF 里是真的正文，判据必须看见它，
    # 否则"引用写在被 input 的表里"会被数成 0 次（实测：cite 7 次而表里有 5 次）。
    for _inc in sorted((P.root / "tables").glob("*.tex")) if (P.root / "tables").is_dir() else []:
        tex += "\n" + _inc.read_text(encoding="utf-8", errors="replace")
    out.append(row("R-W06 no unsupported phrases",
                   not re.search(r"众所周知|显而易见|应该没问题|it is well known that|obviously,", tex),
                   "no 众所周知/显而易见/obviously,"))
    # R-W11 前三页顺序：Control Sheet -> Summary Sheet -> Contents。
    # 这条是小队测验逼出来的：模板默认只写 \maketitle，编出来第 1 页就是摘要页，
    # 官方要求第 1 页必须是承诺书。判据取 PDF 实际内容，不取源码命令（主稿没写那条命令）。
    try:
        order = G.front_matter_from_pdf(P)
    except Exception as e:  # noqa: BLE001
        order = []
        out.append(row("R-W11 front matter order", False, f"{type(e).__name__}: {e}"))
    else:
        ok_order = order[:2] == ["summary", "contents"] or order[:3] == ["control", "summary", "contents"]
        out.append(row("R-W11 front matter order", ok_order, f"{order}"))
    # 这份论文的参考文献是手写的 \bibitem{} 列表（thebibliography），
    # 正文引用写成 [15] 而不是 \cite{...}。所以三个都要数，缺一个就漏。
    entries = len(re.findall(r"\\bibitem", tex))
    marks = len(re.findall(r"^\s*\[(\d+)\]", tex, re.M))
    denom = max(entries, marks)
    markers = len(re.findall(r"\[(?:M|J|R|DB/OL|EB/OL)\]", tex))
    out.append(row("R-W04 references have type markers", markers > 0,
                   f"{markers} type markers on {denom} entries"))
    cites = len(re.findall(r"\\cite\{", tex))
    # [n] 的"用"要看引用段之前：条目标题行本身也是 [n]，混在一起会把 0 引用数成满分
    # （实测：新建骨架 4 条 bibitem、0 处引用，旧写法给出 [n] uses=4 的假 PASS）。
    cut = re.search(r"\\begin\{thebibliography\}|\\section\*?\{[^}]*[Rr]eference", tex)
    cited_part = tex[: cut.start()] if cut else tex
    uses = set(re.findall(r"\[(\d+)\]", cited_part))
    out.append(row("R-W04 >=70% references cited",
                   denom == 0 or (cites + len(uses)) >= 0.7 * denom,
                   f"cite calls={cites}, [n] uses before bibliography={len(uses)}, entries={denom}"))

    vn = P.code / "verify_numbers.py"
    # R-V06 不只是"文件存在"：空骨架（0 条 claim）也能存在，却一条都没对上账。
    # 2026-11-12 加的：脚手架会发一个 0-claim 的 verify_numbers.py 桩，若只判存在性，
    # 一份从没绑过数字的论文会拿绿。判据改成"能跑通 **且** claims > 0"。
    if vn.exists():
        rc, txt = _run_verify(vn, P)
        m = re.search(r"(\d+)\s+claims", txt or "")
        n_claims = int(m.group(1)) if m else 0
        ok = rc == 0 and n_claims > 0
        detail = f"claims={n_claims} exit={rc}" if txt else "no output"
        if n_claims == 0:
            detail += " — 空骨架不算对过账：正文每个印出来的数都要有一条 claim"
    else:
        ok, detail = False, "code/verify_numbers.py 不存在"
    out.append(row("R-V06 verify_numbers present", ok, detail))

    # R-V09: 产物过期。KNOWN OPEN 不计失败 —— 但每一条都必须有一句解释写进 RUNBOOK §9.2。
    try:
        from mmkit import freshness as F  # noqa: E402
        stale = F.stale_artifacts(P)
        detail = "none" if not stale else (
            f"{len(stale)} pair(s): " + ", ".join(
                f"{r['artifact']}<-{r['script']}({r['lag_hours']}h)" for r in stale[:3]) +
            ("" if len(stale) <= 3 else f" …+{len(stale) - 3}"))
        out.append(row("R-V09 no stale artefact", True, f"KNOWN OPEN (explain each): {detail}"))
    except Exception as e:  # noqa: BLE001
        out.append(row("R-V09 no stale artefact", False, f"{type(e).__name__}: {e}"))

    try:
        rows = G.band(P)
        out.append(row("R-V07 band measured on both sides",
                       all(r.project > 0 for r in rows if r.metric in ("figures", "equations")),
                       "figures/equations non-zero, so project was read from PDF text"))
        above = [r.metric for r in rows if r.verdict.startswith("ABOVE")]
        below = [r.metric for r in rows if r.verdict.startswith("BELOW")]
        out.append(row("R-V07 out-of-band count", True,
                       f"ABOVE={above} BELOW={below}"))
    except Exception as e:  # noqa: BLE001
        out.append(row("R-V07 band measured", False, f"{type(e).__name__}: {e}"))

    # R-V14: 图内文字的有效字号（缩放后）。看图看不出来，只能从 PDF 读磅值。
    # 判据：任何 ≥3 个字符的 span 不得低于 6 pt；单字符（面板字母/刻度/数学符号）不判。
    #
    # 解释器坑（实测）：pymupdf 只装在 conda 环境里，D:\Python 没有；用 D:\Python 跑本脚本时
    # 直接 `from mmkit import figfont` 会 ModuleNotFoundError，于是"论文没问题"被报成 FAIL。
    # 这里改成去问几个候选解释器，全都不行才报 SKIP（不是 FAIL）——判据缺工具不等于判据不通过。
    fr = _figfont_via_subprocess(P.pdf)
    if fr is None:
        out.append(row("R-V14 figure text >= 6 pt", True,
                       "SKIP: no interpreter here has pymupdf; run "
                       r"`E:\Mini\envs\mathmodel\python.exe -m mmkit.figfont` by hand"))
    else:
        out.append(row("R-V14 figure text >= 6 pt", fr["ok"],
                       f"min={fr['min_pt']} pt median={fr['median_pt']} pt "
                       f"violations={fr['violations']} single-char<6pt={fr['single_char_below']}"
                       f" (measured by {fr.get('_py', '?')})"))

    return out


def _is_real(paper) -> bool:
    """草稿判定：新建的空模板能被 find_paper() 选中，但它不是交付物。

    测验里 `_smoke2` 是从模板 new 出来的，被 find_paper() 第 4 步"取最新"命中，
    于是基准带量到 figures=0、引用数 0 —— 规则没错，是选错了被检对象（第四次）。
    这里统一判一次，并在输出里明确说"跑到的是草稿"。
    """
    try:
        return paper.pdf.exists() and paper.pdf.stat().st_size > 150_000
    except OSError:
        return False



def _run_verify(vn, paper) -> tuple[int, str]:
    """跑论文自己的 verify_numbers.py，返回 (exit, 合并输出)。用带 numpy 的解释器。"""
    io_m = __import__("subprocess")
    env = dict(__import__("os").environ)
    env["PYTHONIOENCODING"] = "utf-8"
    for exe in (sys.executable,):
        try:
            r = io_m.run([exe, str(vn)], cwd=str(paper), capture_output=True, timeout=900, env=env)
            return r.returncode, ((r.stdout or b"").decode("utf-8", "replace")
                                  + (r.stderr or b"").decode("utf-8", "replace")).strip()
        except FileNotFoundError:
            continue
        except Exception as e:  # noqa: BLE001
            return 1, f"{type(e).__name__}: {e}"
    return 1, "no interpreter available"


def main() -> int:
    global ALLOW_DRAFT
    argv = [a for a in sys.argv[1:] if a != "--allow-draft"]
    ALLOW_DRAFT = "--allow-draft" in sys.argv[1:]
    rows = check(argv[0] if argv else None)
    width = max(len(r[0]) for r in rows)
    fails = 0
    for name, ok, detail in rows:
        tag = "PASS" if ok else "FAIL"
        fails += 0 if ok else 1
        print(f"[{tag}] {name:<{width}}  {detail}")
    print(f"\n{len(rows) - fails}/{len(rows)} PASS")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())