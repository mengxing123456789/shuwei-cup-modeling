"""统一入口：把 tools 目录塞进 sys.path，再按脚本名跑任意一个工具。

为什么需要这个壳：
    这批脚本之间有互相 import（`count_chapter_words` → `markdown_utils`，
    `docx_export` → `docx_text`，几个 vision 检查 → `trusted_gateway_config`）。
    直接 `python tools\\xxx.py` 时脚本目录不一定在 sys.path 首位，
    在 isolated 解释器（带 `._pth`）下更是完全进不去。

用法（用本机 mathmodel 解释器跑）：
    python run_tool.py count_chapter_words.py paper.md
    python run_tool.py academic_writing_check.py --stage final --skill paper-write <工作区>
    python run_tool.py --list

依赖：`trusted_gateway_config` 与 `docx_text` 都是本目录下的自建实现（不再指向任何安装目录）。
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv[0] == "--list":
        for p in sorted(TOOLS.glob("*.py")):
            if p.name != Path(__file__).name:
                print(f"{p.name:34} {p.stat().st_size:>8} B")
        return 0

    target = TOOLS / argv[0]
    if not target.exists():
        print(f"找不到脚本：{target}", file=sys.stderr)
        return 2

    if str(TOOLS) not in sys.path:
        sys.path.insert(0, str(TOOLS))

    sys.argv = [str(target)] + argv[1:]
    try:
        runpy.run_path(str(target), run_name="__main__")
    except SystemExit as exc:  # 脚本自己的退出码
        return int(exc.code or 0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
