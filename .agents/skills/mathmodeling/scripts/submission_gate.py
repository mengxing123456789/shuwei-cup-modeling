#!/usr/bin/env python
"""把 `paper-kit` 的检查脚本包成「可被流水线调用的闸门」，同时保留独立 CLI。

## 这个文件有两个身份

1. **独立 CLI**：人手动跑一次，出统一结论表（原来就有的用法）。
2. **闸门库**：`pipeline.py` 的 G10–G13 直接 `import` 这里的 `run_*` 函数，
   拿到 `(True | False | None, 详情)` 三元态，与其它九道门同构。

两种身份共用的前提是**目录视图**：`paper-kit` 的脚本按旧布局写死了 `paper/` 子目录，
而本工作区是扁平布局（`main.tex` 就在论文目录根上），所以每个闸门跑之前先搭一个临时
视图，跑完即删，不动原目录。

## 四个视图（互相不能混用，混了就静默跳过）

| 视图 | 谁要 | 布局 |
|---|---|---|
| 根视图 | `gauntlet_check.py` | `<ws>/main.tex` + `<ws>/main.pdf` |
| `paper/` 视图 | `venue_submission_check.py`、`academic_writing_check.py` | `<ws>/paper/main.*`，`.mh` 在 `<ws>/.mh` |
| 数据视图 | `paper_data_check.py` | 在 `paper/` 视图之上，再要 `<ws>/results_*.json` 与 `<ws>/figures/` |
| 原目录 | `paper_source_scope.py` | 直接读论文目录，不搭视图 |

数据视图是最容易踩的：`paper_data_check.py` 的源码里 `figures_dir = workspace / "figures"`、
`workspace.glob("results_*.json")` —— 它找的是**视图根**，不是 `paper/` 子目录。
第一版没搬 `results_*.json`，它就报「无 figures/*.json 或 TABLE_* — 无数据需要核对」并 exit 0，
一个数字都没核，却看起来像通过了。

## 三元态与「软闸门」

`True` 过、`False` 不过、`None` 判不出。`None` 默认**不算通过**（沿用 `pipeline.py` 的规矩），
但视觉审查（G13）例外：它要调外部视觉模型，模型不可用时判不出是常态，
把它算成 FAIL 会让整条链因为第三方额度而永久堵死。所以 G13 在 `pipeline.py` 里被列为软闸门：
`None` 记 SKIP 不拦，`False` 照样拦。

用法（本机 mathmodel 解释器，自带 numpy/pymupdf/python-docx）：
    python submission_gate.py <论文目录>
    python submission_gate.py <论文目录> --only venue
    python submission_gate.py <论文目录> --only data
    python submission_gate.py <论文目录> --main main_en
    python submission_gate.py <论文目录> --with-writing --stage draft

写作规则默认**不跑**：它按「学术论文」文体判（要有 Limitations 一节、Discussion 要与已有研究比较…），
数学建模竞赛论文没这些硬要求，强跑会出假 FIX。要查就先在论文目录写 `.mh\\writing_spec.json`
（**必须用 python 写，别用 PowerShell `Set-Content -Encoding UTF8`——5.1 带 BOM 会让 json 解析失败**），
再带 `--with-writing`。

退出码：0 = 全过（SKIP 不算失败）；1 = 有 FAIL 或有「要你处理」；2 = 环境不全/参数不对。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILLS = HERE.parent.parent  # <workspace>\.agents\skills
TOOLS = SKILLS / "paper-kit" / "tools"
RUNNER = TOOLS / "run_tool.py"

# 要跟着走的文件：`main.*` 系列按 stem 改名，其余原名照搬
STAGE_COPY = ("main.tex", "main.pdf", "main.log", "main.bbl", "main.bcf", "main.aux",
              "main.out", "main.toc", "refs.bib")
# gauntlet 会读这些子目录（figures/tables 里的 \input 与图、code/data 用于溯源）
GAUNTLET_DIRS = ("figures", "figure", "tables", "code", "data", "refs", "logs")
# venue / writing 只关心版式与写作档案
VENUE_DIRS = ("figures", "tables", ".mh")

VERBOSE = False


def _say(*a, **kw) -> None:
    if VERBOSE:
        print(*a, **kw)


def _pick_main(paper: Path) -> tuple[str, str]:
    """定主文件 stem。两套工具都只认 `main`，所以扁平布局要先改名。

    优先 `main`；没有就用目录里唯一那个 `main_*.tex`（本工作区是 `main_en.tex` / `main_zh.tex`）。
    返回 (stem, 说明)；stem 为空串表示无法确定，调用方应报错退出。
    """
    if (paper / "main.tex").is_file():
        return "main", "main"
    cands = sorted(p.stem for p in paper.glob("main_*.tex"))
    if len(cands) == 1:
        return cands[0], f"{cands[0]}（唯一主文件，当作 main）"
    if len(cands) > 1:
        return "", f"目录里有多个主文件 {cands}，必须用 --main 指定其一"
    return "", "找不到 main.tex 或 main_*.tex"


def _run(cmd: list[str], timeout: int = 900) -> tuple[int, str]:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    try:
        cp = subprocess.run(cmd, capture_output=True, timeout=timeout, env=env)
    except FileNotFoundError as e:
        return 2, f"找不到解释器或脚本：{e}"
    except subprocess.TimeoutExpired:
        return 3, f"超时（{timeout}s）：{' '.join(cmd[:2])}"
    out = (cp.stdout or b"").decode("utf-8", "replace") + (cp.stderr or b"").decode("utf-8", "replace")
    return cp.returncode, out.strip()


def _hdr(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def _copy_main_set(paper: Path, stem: str, dest: Path) -> list[str]:
    """把 `stem.*` 改名叫 `main.*` 复制进 dest，其余 STAGE_COPY 原名照搬。"""
    copied = []
    for name in STAGE_COPY:
        if name.startswith("main."):
            src = paper / (stem + name[len("main"):])
            dst_name = name
        else:
            src = paper / name
            dst_name = name
        if src.is_file():
            shutil.copy2(src, dest / dst_name)
            copied.append(dst_name)
    return copied


def _copy_toolchain(paper: Path, dest: Path) -> None:
    """类文件与配置要跟着走，否则 `\\documentclass{swmcmthesis}` 在视图里找不到。"""
    for cls in paper.glob("*.cls"):
        shutil.copy2(cls, dest / cls.name)
    for cfg in paper.glob("*.cfg"):
        shutil.copy2(cfg, dest / cfg.name)


def stage_gauntlet(paper: Path, stem: str) -> tuple[Path, tempfile.TemporaryDirectory | None]:
    """gauntlet 视图：`main.tex` / `main.pdf` 直接在 ws 根上，外加它要读的子目录。

    已是 `main.tex` + `main.pdf` 的真稿布局就原样用，省掉复制。
    """
    if (paper / "main.tex").is_file() and (paper / "main.pdf").is_file():
        return paper, None
    tmp = tempfile.TemporaryDirectory(prefix="gate_g_")
    ws = Path(tmp.name)
    copied = _copy_main_set(paper, stem, ws)
    for name in GAUNTLET_DIRS:
        src = paper / name
        if src.is_dir():
            shutil.copytree(src, ws / name, dirs_exist_ok=True)
    _copy_toolchain(paper, ws)
    _say(f"（扁平布局 → 临时根视图：{', '.join(copied) or '空'}）")
    return ws, tmp


def stage_venue(paper: Path, stem: str) -> tuple[Path, tempfile.TemporaryDirectory | None]:
    """venue / writing 视图：文件要落在 `<ws>/paper/main.*`，`.mh` 在 `<ws>/.mh`。"""
    if (paper / "paper" / "main.tex").is_file():
        return paper, None
    tmp = tempfile.TemporaryDirectory(prefix="gate_v_")
    ws = Path(tmp.name)
    dest = ws / "paper"
    dest.mkdir(parents=True, exist_ok=True)
    copied = _copy_main_set(paper, stem, dest)
    for name in VENUE_DIRS:
        src = paper / name
        if src.is_dir():
            shutil.copytree(src, dest / name, dirs_exist_ok=True)
    _copy_toolchain(paper, dest)
    # `.mh` 必须在 ws 根（工具读 <ws>/.mh），不是 paper/.mh
    if (dest / ".mh").is_dir():
        shutil.move(str(dest / ".mh"), str(ws / ".mh"))
    _say(f"（扁平布局 → 临时 paper/ 视图：{', '.join(copied) or '空'}）")
    return ws, tmp


def stage_data(paper: Path, stem: str) -> tuple[Path, tempfile.TemporaryDirectory | None]:
    """数据视图：`paper_data_check.py` 在 `paper/` 视图之上还要两样东西在**视图根**。

    - `results_*.json`：论文里的结果类数字要靠它回溯。缺了它工具会报
      「无 figures/*.json 或 TABLE_* — 无数据需要核对」并 exit 0 —— 零核对却像通过。
    - `figures/`：工具按 `workspace / "figures"` 找 `*_results.json` 与 `TABLE_*`。

    本项目的 `data/results_*.json`（8 个）与 `figures/`（manifest 等）分别搬到这两处。
    """
    ws, tmp = stage_venue(paper, stem)
    if tmp is None:                      # 已经是 paper/ 布局，仍要补数据文件
        tmp = tempfile.TemporaryDirectory(prefix="gate_d_")
        dst = Path(tmp.name)
        shutil.copytree(ws, dst, dirs_exist_ok=True)
        ws = dst
    moved = 0
    cand = sorted((paper / "data").glob("results_*.json")) + \
        [q for q in (paper / "data").glob("results.json") if q.is_file()]
    for f in cand:
        shutil.copy2(f, ws / f.name)
        moved += 1
    if (paper / "figures").is_dir() and not (ws / "figures").is_dir():
        shutil.copytree(paper / "figures", ws / "figures", dirs_exist_ok=True)
    _say(f"（数据视图：另搬 {moved} 个 results_*.json 到视图根）")
    return ws, tmp


# ---------------------------------------------------------------- 四个闸门

def run_gauntlet(paper: Path) -> tuple[bool | None, str]:
    script = HERE / "gauntlet_check.py"
    if not script.exists():
        return None, f"缺 {script}"
    code, out = _run([sys.executable, str(script), str(paper)])
    _say(out)
    if code in (2, 3):
        return None, out.splitlines()[0] if out else "跑不起来"
    tail = [ln for ln in out.splitlines() if "PASS" in ln and "/" in ln]
    return code == 0, tail[-1] if tail else ""


def run_venue(ws: Path) -> tuple[bool | None, str]:
    if not (RUNNER.exists() and TOOLS.is_dir()):
        return None, f"缺 {RUNNER}"
    code, out = _run([sys.executable, str(RUNNER), "venue_submission_check.py", str(ws)])
    _say(out)
    if code in (2, 3):
        return None, out.splitlines()[0] if out else "跑不起来"
    verdict = ""
    for ln in out.splitlines():
        if "结论" in ln:
            verdict = ln.strip().lstrip("- ").strip()
            break
    bad = "要你处理" in verdict and "0 项要你处理" not in verdict
    return (not bad), verdict


def run_data(ws: Path, mode: str = "pdf") -> tuple[bool | None, str]:
    """数据真实性核对。判据是「致命项为 0」，不是「未溯源项为 0」。

    未溯源项（本项目 134 个）是**线索**不是错误：派生系数、题给常量、种子、
    文件字节数都会落在里面。`verify_numbers.py` 管的是另一件事——正文每个数字
    必须回到 JSON 键；两者互补，不能互相替代。
    """
    if not (RUNNER.exists() and TOOLS.is_dir()):
        return None, f"缺 {RUNNER}"
    # 不加 --quiet：quiet 只回一行报告路径，正文不打印，摘要判不出来
    code, out = _run([sys.executable, str(RUNNER), "paper_data_check.py",
                      "--mode", mode, "--workspace", str(ws)])
    _say(out)
    if code in (2, 3):
        return None, out.splitlines()[0] if out else "跑不起来"
    name = "TABLE_DATA_CHECK_REPORT.md" if mode == "table" else "PAPER_DATA_CHECK_REPORT.md"
    report = ws / name
    txt = report.read_text(encoding="utf-8", errors="replace") if report.is_file() else out

    def _num(pattern: str) -> int | None:
        m = re.search(pattern, txt)
        return int(m.group(1)) if m else None

    if mode == "table" and "无 TABLE 文件" in txt:
        # 表格直接写在 main.tex 里（本项目就是这样），没有 TABLE_* 可核
        return None, "没有 figures/TABLE_*（表格写在正文里），表格模式无从核对"
    fatal = _num(r"(\d+)\s*致命")
    checked = _num(r"结果类数字（已比对）:\s*(\d+)")
    untraced = _num(r"按显示精度在数据里找不到的数字:\s*(\d+)")
    entries = _num(r"数据条目数:\s*(\d+)")
    if checked is None and entries is None:
        # 一个数据文件都没找到 —— 判不出，不许当通过
        return None, "视图里没有数据文件，工具零核对（看 stage_data 是否搬了 results_*.json）"
    if fatal:
        return False, f"{fatal} 个致命项（格式残留），看 {report.name}"
    detail = f"致命=0 条目={entries} 已比对={checked} 未溯源={untraced}"
    if code != 0:
        return False, f"exit={code} " + detail
    return True, detail


def run_template(ws: Path) -> tuple[bool | None, str]:
    """上传模板有没有被改坏。没用上传模板时判不出（返回 None），不是通过。"""
    if not (RUNNER.exists() and TOOLS.is_dir()):
        return None, f"缺 {RUNNER}"
    code, out = _run([sys.executable, str(RUNNER), "template_ingest.py", "verify", str(ws)])
    _say(out)
    if code == 0 and "没有用上传的 LaTeX 模板" in out:
        return None, "没有用上传的 LaTeX 模板，跳过模板核对"
    if code == 0:
        return True, out.splitlines()[-1].strip()[:120] if out.strip() else "模板未被改坏"
    return False, (out.splitlines()[-1].strip()[:160] if out.strip() else f"exit={code}")


def run_sources(paper: Path) -> tuple[bool | None, str]:
    """源文件闭包：`figures/` 里的 .tex 要么被 `main.tex` 引到，要么是死文件。

    为什么值得一道门：`.seal.tex` 由 `make_figures.py` 自动生成，改图名/删图之后
    旧的印章文件会留在磁盘上，`main.tex` 不再引用它，但也没人删它——
    交稿时附录里多出几个没人引用的文件，评委看不出，作者也看不出。
    这里用 `paper-kit` 的 `paper_source_scope.py` 解析真实引用闭包（它会剥注释、
    认 `\\input` 递归、跳过被注释掉的指令），再与磁盘上的文件比对。
    """
    if not (RUNNER.exists() and TOOLS.is_dir()):
        return None, f"缺 {RUNNER}"
    if not (paper / "main.tex").is_file():
        return None, "缺 main.tex"
    code, out = _run([sys.executable, str(RUNNER), "paper_source_scope.py", str(paper)])
    if code != 0:
        return None, f"paper_source_scope 跑不起来 exit={code}"
    active = {Path(ln.strip()).resolve() for ln in out.splitlines()
              if ln.strip() and not ln.startswith((" ", "\t"))}
    if not active:
        return None, "解析不出引用闭包"
    on_disk = {p.resolve() for p in (paper / "figures").glob("*.tex")} if (paper / "figures").is_dir() else set()
    orphans = sorted(p.name for p in on_disk - active)
    if orphans:
        return False, f"{len(orphans)} 个 figures/*.tex 没被引用（死文件）: {orphans[:5]}"
    return True, f"闭包 {len(active)} 个源文件，figures/ 无死文件"


VISION_CFG = Path(r"E:\数学建模\.agents\skills\paper-kit\vision.json")


def _vision_env() -> dict[str, str]:
    """视觉模型的连接参数：`paper-kit/vision.json` 优先，其次进程环境。

    为什么要有配置文件而不是只认环境变量：环境变量在「换个终端就丢」，
    而这条通道**不该靠记住 export**——2026-11-18 那次就是因为额度打到 429，
    G11 静默变成 `??` 没人管，图里被裁的断头句拖到 venue 才暴露。
    写进文件、并在 `--status` 里显示成 NA，才看得见「这门今天没真判」。
    """
    cfg: dict[str, str] = {}
    if VISION_CFG.exists():
        try:
            raw = json.loads(VISION_CFG.read_text(encoding="utf-8"))
            cfg = {k: str(v) for k, v in raw.items() if isinstance(v, (str, int))}
        except (OSError, json.JSONDecodeError):
            pass
    env: dict[str, str] = {}
    for src, dst in (("base_url", "OPENAI_BASE_URL"), ("api_key", "OPENAI_API_KEY"),
                     ("model", "REVIEWER_MODEL_ID")):
        v = cfg.get(src) or os.environ.get(dst)
        if v:
            env[dst] = v
    if not env.get("OPENAI_API_KEY") and os.environ.get("EDITOR_AI_API_KEY"):
        env["OPENAI_API_KEY"] = os.environ["EDITOR_AI_API_KEY"]
    return env


def run_vision(paper: Path, limit: int | None = None) -> tuple[bool | None, str]:
    """图表视觉审查：把每张 png 交给视觉模型，看图上文字有没有糊/截断/重叠。

    连接参数见 `_vision_env()`（`paper-kit/vision.json` 或环境变量）。
    模型不可用时返回 None —— 那是「没审」，不是「审过且合格」。
    """
    if not (RUNNER.exists() and TOOLS.is_dir()):
        return None, f"缺 {RUNNER}"
    env = _vision_env()
    if not env.get("OPENAI_API_KEY"):
        return None, ("没配视觉模型：写 .agents/skills/paper-kit\\vision.json"
                      "（base_url/api_key/model），或跑 scripts\\set_vision.py 填。本图未审")
    if not env.get("REVIEWER_MODEL_ID"):
        return None, "没配视觉模型名（vision.json 的 model），本图未审"
    saved = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    figs = sorted((paper / "figures").glob("*.png"))
    if not figs:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        return None, "figures/ 里没有 png"
    if limit:
        figs = figs[:limit]
    bad, unreviewed = [], []
    try:
        for png in figs:
            pdf = png.with_suffix(".pdf")
            cmd = [sys.executable, str(RUNNER), "data_fig_vision_check.py", str(png)]
            if pdf.is_file():
                cmd += ["--source", str(pdf)]
            code, out = _run(cmd, timeout=300)
            if code == 0:
                continue
            if code == 2:
                unreviewed.append(png.stem)
            else:
                bad.append(f"{png.stem}({out.splitlines()[-1][:60] if out.strip() else code})")
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    if bad:
        return False, f"{len(bad)} 张图有问题: {bad[:3]}"
    if unreviewed:
        return None, f"{len(unreviewed)}/{len(figs)} 张没审成（视觉模型不可用），不算通过"
    return True, f"{len(figs)} 张图全部视觉审查通过  [{env.get('REVIEWER_MODEL_ID')}]"


def run_writing(ws: Path, stage: str, skill: str) -> tuple[bool | None, str]:
    if not (RUNNER.exists() and TOOLS.is_dir()):
        return None, f"缺 {RUNNER}"
    if not (ws / ".mh" / "writing_spec.json").is_file():
        return None, "没有 .mh/writing_spec.json（竞赛论文不必有；要查就自己写一份）"
    code, out = _run([sys.executable, str(RUNNER), "academic_writing_check.py",
                      "--stage", stage, "--skill", skill, str(ws)])
    _say(out)
    if code == 0:
        return True, "无需修"
    if code == 1:
        return False, "有需修项（见上面 FIX/HINT）"
    if code == 2:
        return None, "不适用（这一阶段没对应规则，或找不到成稿）"
    return None, "检查没跑成"


# ---------------------------------------------------------------- CLI

SUITES = ("gauntlet", "venue", "data", "table", "template", "sources", "vision", "writing")


def main(argv: list[str]) -> int:
    global VERBOSE
    VERBOSE = True
    ap = argparse.ArgumentParser(description="交稿前总闸：规则自检 + 投稿体检 + 数据核对 + 视觉审查")
    ap.add_argument("paper", nargs="?", help="论文目录（含 main.tex / main.pdf，或扁平 main_*.tex）")
    ap.add_argument("--stage", default="draft", choices=["plan", "draft", "final"])
    ap.add_argument("--skill", default="paper-write", help="写作规则套的技能名，如 paper-write / paper-compile")
    ap.add_argument("--with-writing", action="store_true", help="也跑 40 条写作规则（需 .mh/writing_spec.json）")
    ap.add_argument("--only", choices=SUITES, help="只跑其中一套")
    ap.add_argument("--main", default=None, help="主文件 stem（默认自动：main，或目录里唯一的 main_*.tex）")
    args = ap.parse_args(argv)

    paper = Path(args.paper).resolve() if args.paper else Path.cwd()
    if not paper.is_dir():
        print(f"不是目录：{paper}", file=sys.stderr)
        return 2

    stem, note = (args.main, f"{args.main}（手动指定）") if args.main else _pick_main(paper)
    if not stem:
        print(f"主文件：{note}", file=sys.stderr)
        return 2
    print(f"论文目录：{paper}")
    print(f"主文件  ：{note}")
    print(f"解释器  ：{sys.executable}")

    rows: list[tuple[str, bool | None, str]] = []
    tmps: list[tempfile.TemporaryDirectory] = []

    def _stage(kind: str):
        if kind == "gauntlet":
            ws, t = stage_gauntlet(paper, stem)
        elif kind == "data" or kind == "table":
            ws, t = stage_data(paper, stem)
        else:
            ws, t = stage_venue(paper, stem)
        if t is not None:
            tmps.append(t)
        return ws

    try:
        want = {args.only} if args.only else ({"gauntlet", "venue", "data", "sources", "vision"}
                                              | ({"writing"} if args.with_writing else set()))
        if "gauntlet" in want:
            _hdr("① 规则自检（mathmodeling / gauntlet_check.py）")
            rows.append(("gauntlet", *run_gauntlet(_stage("gauntlet"))))
        if "venue" in want:
            _hdr("② 投稿前体检（paper-kit / venue_submission_check.py）")
            rows.append(("venue", *run_venue(_stage("venue"))))
        if "data" in want:
            _hdr("③ 论文数据真实性核对（paper-kit / paper_data_check.py --mode pdf）")
            rows.append(("data", *run_data(_stage("data"), "pdf")))
        if "table" in want:
            _hdr("④ 表格数据真实性核对（paper-kit / paper_data_check.py --mode table）")
            rows.append(("table", *run_data(_stage("table"), "table")))
        if "template" in want:
            _hdr("⑤ 上传模板核对（paper-kit / template_ingest.py verify）")
            rows.append(("template", *run_template(_stage("template"))))
        if "sources" in want:
            _hdr("⑥ 源文件闭包（paper-kit / paper_source_scope.py）")
            rows.append(("sources", *run_sources(paper)))
        if "vision" in want:
            _hdr("⑦ 图表视觉审查（paper-kit / data_fig_vision_check.py）")
            rows.append(("vision", *run_vision(paper)))
        if "writing" in want:
            _hdr(f"⑧ 写作规则（paper-kit / academic_writing_check.py --stage {args.stage}）")
            rows.append(("writing", *run_writing(_stage("writing"), args.stage, args.skill)))
    finally:
        for t in tmps:
            t.cleanup()

    _hdr("结论")
    width = max(len(n) for n, _, _ in rows) if rows else 8
    fails = skips = 0
    for name, ok, detail in rows:
        tag = "PASS" if ok else ("SKIP" if ok is None else "FAIL")
        fails += 1 if ok is False else 0
        skips += 1 if ok is None else 0
        print(f"[{tag}] {name:<{width}}  {detail}")
    print()
    if fails:
        print(f"{fails} 套没过，{skips} 套跳过。先修 FAIL 再交。")
        return 1
    print(f"全部通过（{skips} 套跳过）。SKIP 不等于通过：看上面每一套自己说了什么。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
