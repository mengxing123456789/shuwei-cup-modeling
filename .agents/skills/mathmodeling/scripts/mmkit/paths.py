"""探出当前 paper 工程的根目录：换工程不用改任何脚本。

用法
    from mmkit.paths import find_paper
    P = find_paper()          # -> Paper(root, tex, pdf, code, data, figures, tables, refs)
    P = find_paper("D:/other")  # 显式指定

查找顺序（命中即停）：
    1. 显式参数
    2. 环境变量 MM_PAPER
    3. 当前工作目录向上逐级找 main.tex
    4. <workspace>/ 下按修改时间最新的、含 main.tex 的直接子目录

设计理由：`compare_to_awards.py` 原来用 `Path(__file__).parents[1]`，把
「脚本放在 code/ 里」这个布局焊死了。做成 skill 后脚本被搬进 scripts/mmkit/，
同一条语句会指到 skill 目录而不是论文目录，于是必须先解耦。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Paper:
    root: Path

    @property
    def tex(self) -> Path:
        return self.root / "main.tex"

    @property
    def pdf(self) -> Path:
        return self.root / "main.pdf"

    @property
    def code(self) -> Path:
        return self.root / "code"

    @property
    def data(self) -> Path:
        return self.root / "data"

    @property
    def figures(self) -> Path:
        return self.root / "figures"

    @property
    def tables(self) -> Path:
        return self.root / "tables"

    @property
    def refs(self) -> Path:
        return self.root / "refs"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    def __str__(self) -> str:
        return str(self.root)


def _latest_paper_under(base: Path) -> Path | None:
    cands = []
    try:
        # os.scandir 不 stat（不跟链接）；pathlib 的 iterdir/glob 会在
        # E:\WpSystem 这种挂载点上抛 WinError 1337（安全 ID 结构无效）。
        entries = [e for e in os.scandir(base) if e.is_dir(follow_symlinks=False)]
    except OSError:
        return None
    for e in entries:
        d = base / e.name
        try:
            if (d / "main.tex").exists():
                cands.append(d)
        except OSError:
            continue
    if not cands:
        return None
    return max(cands, key=lambda d: (d / "main.tex").stat().st_mtime)


def find_paper(explicit: str | Path | None = None) -> Paper:
    if explicit is not None:
        return Paper(Path(explicit).resolve())

    env = os.environ.get("MM_PAPER")
    if env:
        return Paper(Path(env).resolve())

    here = Path.cwd().resolve()
    for p in [here, *here.parents]:
        try:
            if (p / "main.tex").exists():
                return Paper(p)
        except OSError:
            continue

    try:
        hit = _latest_paper_under(here)
    except OSError:
        hit = None
    if hit is not None:
        return Paper(hit)

    # 5. 工作区（skill 所在的那个 E:\数学建模）：当 cwd 在 skill 内部时，第 4 步会失败，
    #    而人几乎总是从 skill 目录跑脚本，所以要补这一级。
    for probe in Path(__file__).resolve().parents:
        if (probe / ".agents" / "skills").is_dir():
            # 第 5 步只在工作区直接子目录里找，不递归：工作区根不是论文目录。
            hit = None
            try:
                names = [e.name for e in os.scandir(probe) if e.is_dir(follow_symlinks=False)]
            except OSError:
                names = []
            texes = []
            for name in names:
                f = probe / name / "main.tex"
                try:
                    if f.exists():
                        texes.append((f.stat().st_mtime, probe / name))
                except OSError:
                    continue
            if texes:
                hit = max(texes)[1]
            if hit is not None:
                return Paper(hit)
            break

    raise FileNotFoundError(
        "no main.tex found: pass a path, set MM_PAPER, or run from the paper folder"
    )