#!/usr/bin/env python3
"""paper_data_check — 论文数据真实性自检辅助（PDF 与 DOCX 通用）

设计原则：
    引擎层不做语义判断（哪个数字"应该"来自 JSON、哪个是论文叙述里自然出现的，
    机器算法判断不准，会大量假阳性）。
    引擎只做两件事：
    1. 准备「数据原料清单」（PAPER_DATA_CHECKLIST.md）— 把 JSON 全数据 +
       TABLE_*.tex|md 全文贴在一起给 Claude 看
    2. 确定性硬规则检查（LaTeX 表格残留、Markdown 残留）— 这两类是格式问题，
       不依赖语义

    数据真实性的判断与修复完全交给 Claude：
    - Claude 读 PAPER_DATA_CHECKLIST.md（数据原料）
    - Claude 读论文（main.md / sections/*.tex）
    - Claude 自己判断：论文里出现的数字哪些应该核对、哪些是叙述里的自然数字
    - Claude 自己修：以 JSON 为准，禁止反向操作
    - 后置自检写调用方指定的独立回执；不为登记检查状态修改已编译的正文
    - 旧源码注释仅兼容识别，不能单凭它跳过新内容的核对

CLI：
    python paper_data_check.py --mode docx --workspace ./workspace
"""
from __future__ import annotations

import argparse
import ast
import json
import logging
import math
import hashlib
import os
import tempfile
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paper_source_scope import active_sources


def _configure_utf8_stdio() -> None:
    """Keep the CLI usable on Windows consoles whose default encoding is GBK.

    Reports intentionally contain Chinese text and status glyphs.  Without an
    explicit UTF-8 stream, a successful check can crash while printing its
    summary, which incorrectly turns a completed audit into a failed run.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="backslashreplace")
        except (OSError, ValueError):
            # Some embedded/redirected streams are not reconfigurable.  Their
            # host already owns the encoding contract, so leave them intact.
            pass

log = logging.getLogger(__name__)


def figure_data_bindings(workspace: Path) -> list[dict]:
    """Observe literal JSON sources and local helper calls; never execute code.

    Unknown dynamic paths remain unknown. A different question's data may be a
    legitimate comparison, so these are review evidence, not automatic failures.
    """
    root = workspace.resolve()
    figures = root / 'figures'
    parsed = {}

    def parse(path):
        path = path.resolve()
        if path not in parsed:
            try:
                if not path.is_relative_to(root) or not path.is_file() or path.stat().st_size > 2_000_000:
                    return None
                parsed[path] = ast.parse(path.read_text(encoding='utf-8-sig'))
            except (SyntaxError, UnicodeError, OSError):
                parsed[path] = None
        return parsed[path]

    def sources(path, node, depth=0, seen=None):
        seen = set() if seen is None else seen
        result = set()
        full = parse(path)
        if full is None or depth > 3:
            return result
        imports = {}
        for n in ast.walk(full):
            if isinstance(n, ast.ImportFrom) and n.module and '.' not in n.module:
                for alias in n.names:
                    imports[alias.asname or alias.name] = (path.parent / (n.module + '.py'), alias.name)
        for n in ast.walk(node):
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value.endswith('.json') and '\n' not in n.value:
                for base in (path.parent, root):
                    candidate = (base / n.value).resolve()
                    if candidate.is_relative_to(root) and candidate.is_file():
                        result.add(candidate.relative_to(root).as_posix())
                        break
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                name = n.func.id
                target, fn = imports.get(name, (path, name))
                key = (target.resolve(), fn)
                if key in seen:
                    continue
                seen.add(key)
                module = parse(target)
                if module:
                    for definition in module.body:
                        if isinstance(definition, (ast.FunctionDef, ast.AsyncFunctionDef)) and definition.name == fn:
                            result.update(sources(target, definition, depth + 1, seen))
        return result

    bindings = []
    for script in sorted(figures.glob('gen_*.py'))[:160]:
        tree = parse(script)
        if tree is None:
            continue
        bindings.append({'figure': script.stem.removeprefix('gen_'),
                         'script': script.relative_to(root).as_posix(),
                         'sources': sorted(sources(script, tree))})
    return bindings


# ===========================================================================
# 检查报告
# ===========================================================================

class DataCheckReport:
    def __init__(self, mode: str, sources: list[Path]):
        self.mode = mode  # "docx" | "pdf"
        self.sources = sources
        self.fatal: list[str] = []          # 确定性硬规则违反
        self.warn: list[str] = []           # 软警告
        self.info: list[str] = []           # 信息
        self.checklist_md: str = ""         # 给 Claude 的数据清单
        self.need_self_check: bool = False  # 是否要 Claude 进自检
        self.passed_marker_found: bool = False  # 论文里有没有 PASSED 标记
        self.stats: dict[str, Any] = {}
        # 按显示精度在数据/题设里找不到的结果类数字（待核对线索，不是致命项）
        self.untraced: list[dict] = []

    def add_fatal(self, msg: str): self.fatal.append(msg)
    def add_warn(self, msg: str): self.warn.append(msg)
    def add_info(self, msg: str): self.info.append(msg)

    def has_fatal(self) -> bool:
        return bool(self.fatal)

    def render_summary(self) -> str:
        parts = []
        if self.fatal:
            parts.append(f"{len(self.fatal)} 致命")
        if self.warn:
            parts.append(f"{len(self.warn)} 警告")
        if self.passed_marker_found:
            parts.append("Claude 已自检")
        elif self.need_self_check:
            parts.append("待 Claude 自检")
        return " / ".join(parts) if parts else "无问题"


# ===========================================================================
# 确定性硬规则（不依赖语义）
# ===========================================================================

def _strip_for_residue_scan(content: str, mode: str) -> str:
    text = re.sub(r'```[\s\S]*?```', "", content)
    text = re.sub(r'`[^`\n]+`', "", text)
    if mode == "docx":
        text = re.sub(r'\$\$[\s\S]*?\$\$', "", text)
        text = re.sub(r'\$[^\n$]+?\$', "", text)
        text = re.sub(r'<!--[\s\S]*?-->', "", text)
    else:
        text = re.sub(r'\$\$[\s\S]*?\$\$', "", text)
        text = re.sub(r'\$[^\n$]+?\$', "", text)
        text = re.sub(r'\\\([\s\S]*?\\\)', "", text)
        text = re.sub(r'\\\[[\s\S]*?\\\]', "", text)
        text = re.sub(r'\\begin\{equation\*?\}[\s\S]*?\\end\{equation\*?\}', "", text)
        text = re.sub(r'\\begin\{align\*?\}[\s\S]*?\\end\{align\*?\}', "", text)
        text = re.sub(r'(?m)(?<!\\)%.*$', "", text)
    return text


def check_latex_table_residue_in_md(content: str, report: DataCheckReport):
    """DOCX 模式：markdown 不应有 LaTeX 表格代码（确定性硬规则 → fatal）。"""
    text = _strip_for_residue_scan(content, "docx")
    patterns = [
        (r'\\begin\{tabular\}', r'\begin{tabular}'),
        (r'\\end\{tabular\}', r'\end{tabular}'),
        (r'\\begin\{table\*?\}', r'\begin{table}'),
        (r'\\begin\{longtable\}', r'\begin{longtable}'),
        (r'\\toprule', r'\toprule'),
        (r'\\midrule', r'\midrule'),
        (r'\\bottomrule', r'\bottomrule'),
        (r'\\input\{[^}]*figures/TABLE_[^}]+\}', r'\input{figures/TABLE_*.tex}'),
        (r'\\input\{figures/[^}]*\.tex\}', r'\input{figures/*.tex}'),
    ]
    found: list[tuple[str, int]] = []
    for pat, name in patterns:
        cnt = len(re.findall(pat, text))
        if cnt > 0:
            found.append((name, cnt))
    if found:
        residue_lines = [f"`{name}` × {cnt}" for name, cnt in found]
        report.add_fatal(
            "Markdown 中残留 LaTeX 表格代码（Word 不会渲染）：\n"
            + "\n".join(f"    - {ln}" for ln in residue_lines)
            + "\n  → 修复：替换为 Markdown 三线表 `| 表头 |\\n|---|---|\\n| 数据 |`，"
            "或 `cat figures/TABLE_*.md`（paper-figure 已自动生成 Markdown 版本）。"
        )


def check_markdown_residue_in_tex(content: str, report: DataCheckReport):
    """PDF 模式：.tex 不应有 markdown 表格语法（warn，不阻塞）。"""
    text = _strip_for_residue_scan(content, "pdf")
    found: list[str] = []
    if re.search(r'(?m)^\s*\|[\s\-:|]+\|\s*$', text):
        found.append("Markdown 表格分隔行 `|---|---|`（应改为 booktabs `\\toprule`+`\\midrule`+`\\bottomrule`）")
    if re.search(r'(?m)^#{1,6}\s+\S', text):
        found.append("Markdown 标题（`#`/`##`）应改为 `\\section{}`/`\\subsection{}`")
    if found:
        report.add_warn(
            "LaTeX 中残留 Markdown 语法：" + "; ".join(found)
            + "  → 这些语法 LaTeX 不解析，会丢失格式。"
        )


# ===========================================================================
# JSON 数据扁平化（给 Claude 的核对清单）
# ===========================================================================

def _flatten_json(obj: Any, prefix: str = "",
                  out: list[tuple[str, Any]] | None = None) -> list[tuple[str, Any]]:
    if out is None:
        out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            _flatten_json(v, f"{prefix}.{k}" if prefix else str(k), out)
    elif isinstance(obj, list):
        # list 短的逐项展开，长的取前 3 + 末 1（节省清单长度）。
        # ⛔ 省略处必须写明范围和"去原 JSON 查"，否则模型会把清单没列出的真实值当成编造删掉。
        if len(obj) <= 8:
            for i, v in enumerate(obj):
                _flatten_json(v, f"{prefix}[{i}]", out)
        else:
            for i in [0, 1, 2, len(obj) - 1]:
                _flatten_json(obj[i], f"{prefix}[{i}]", out)
            nums = [v for v in obj if isinstance(v, (int, float)) and not isinstance(v, bool)
                    and not (isinstance(v, float) and (math.isnan(v) or math.isinf(v)))]
            span = (f"；数值范围 [{_format_value(min(nums))}, {_format_value(max(nums))}]"
                    if nums else "")
            out.append((f"{prefix}[3..{len(obj) - 2}]",
                        f"<省略中间 {len(obj) - 4} 项{span}；论文引用的值不在上面时，直接读原 JSON 的这个路径核对>"))
    else:
        if obj is None:
            return out
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return out
        out.append((prefix, obj))
    return out


def _format_value(v: Any) -> str:
    if isinstance(v, float):
        # ⛔ 清单给出的是 JSON 原值，不能降精度：旧版 |v|≥1000 用 4 位有效数字，
        #    2376.83 显示成 2377，而清单又被当作"论文以此为准"——正确的数会被改错。
        #    12 位有效数字足以还原结果，又能去掉 0.30000000000000004 这类浮点尾巴。
        return f"{v:.12g}"
    if isinstance(v, str):
        return f"`{v[:60]}`" if len(v) <= 60 else f"`{v[:55]}...`"
    return str(v)


def build_data_checklist(workspace: Path, mode: str) -> tuple[str, int]:
    """构建给 Claude 的数据原料清单（含 JSON 全数据 + TABLE 文件全文）。

    返回 (markdown 内容, 数据条目数)。
    """
    figures_dir = workspace / "figures"
    # 收集 JSON (即使 figures 目录不存在, 也要去工作根目录找用户的 results.json)

    # 收集 JSON
    json_sources: list[tuple[Path, Any]] = []
    seen = set()
    if figures_dir.exists():
        for c in ["all_results.json"]:
            if c not in seen:
                seen.add(c)
                p = figures_dir / c
                if p.exists():
                    try:
                        json_sources.append((p, json.loads(p.read_text(encoding="utf-8"))))
                    except Exception as e:
                        log.warning("无法解析 %s: %s", p, e)
        for f in sorted(figures_dir.glob("*_results.json")):
            if f.name in seen:
                continue
            seen.add(f.name)
            try:
                json_sources.append((f, json.loads(f.read_text(encoding="utf-8"))))
            except Exception as e:
                log.warning("无法解析 %s: %s", f, e)

    # paper_from_assets 工作流: 用户提供的 results.json/results_*.json 在工作根目录
    # 也要纳入数据源(否则用户已知数值会被自检误判为编造)
    for c in ["results.json"]:
        wp = workspace / c
        if wp.exists() and c not in seen:
            seen.add(c)
            try:
                json_sources.append((wp, json.loads(wp.read_text(encoding="utf-8"))))
            except Exception as e:
                log.warning("无法解析 %s: %s", wp, e)
    for f in sorted(workspace.glob("results_*.json")):
        if f.name in seen:
            continue
        seen.add(f.name)
        try:
            json_sources.append((f, json.loads(f.read_text(encoding="utf-8"))))
        except Exception as e:
            log.warning("无法解析 %s: %s", f, e)

    # 扁平化所有条目
    all_entries: list[tuple[str, str, Any]] = []
    for jp, data in json_sources:
        for kp, v in _flatten_json(data):
            all_entries.append((jp.name, kp, v))

    # 收集 TABLE 文件
    table_files: list[Path] = []
    if figures_dir.exists():
        table_files = sorted(figures_dir.glob("TABLE_*.tex")) + \
                      sorted(figures_dir.glob("TABLE_*.md"))

    if not all_entries and not table_files:
        return "", 0

    # 渲染清单
    lines = [
        "# 论文数据真实性核对清单（数据原料）",
        "",
        f"**模式**: {mode.upper()}",
    ]
    if json_sources:
        lines.append(f"**JSON 源**: {', '.join(p.name for p, _ in json_sources)}")
        lines.append(f"**JSON 数据条目**: {len(all_entries)}")
    if table_files:
        lines.append(f"**已生成的 TABLE 文件**: {len(table_files)} 个")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 使用说明 — 由 Claude 自己判断和修复
    if mode == "docx":
        embed_hint = "`cat figures/TABLE_*.md >> paper/main.md` 直接嵌入"
    else:
        embed_hint = "`\\input{figures/TABLE_*.tex}` 引入"

    lines += [
        "## 自检步骤（请你按以下顺序执行）",
        "",
        "**重要原则**：本工作区的实验/分析阶段已经把所有真实数据存到 `figures/*.json`，",
        "并由 paper-figure 步骤渲染成 `figures/TABLE_*.tex|md`。",
        "**论文数据应能追溯到这些文件或题设，并允许有明确计算依据的派生量、单位换算及舍入。未直接匹配不等于编造。**",
        "",
        "### 第 1 步：识别论文中的「数据性数字」",
        "",
        "打开你的论文文件，逐章扫描：",
        "",
        "- ✅ **需要核对的**：表格里的所有单元格数字、正文里引用实验结果的数字"
        "（如 \"RMSE 达到 0.023\"、\"准确率 94%\"、\"最优解 295.83\"、\"R² 为 0.94\"）",
        "- ⏭️ **不需要核对的**（叙述里自然出现的数字）：",
        "    - 章节编号、列号、引用 [1][2,3]、图编号「图 3-1」",
        "    - 年份「2024 年」、日期「3 月 5 日」",
        "    - 公式本身的数学常数与下标（如 `$\\frac{1}{2}$`、`$x_1$`）；"
        "但写在公式里的结果值（如 `$R^2=0.94$`、`$Z^*=295.83$`）仍要核对",
        "    - 算法描述里的步骤数「分 5 步」",
        "    - 文献综述里别人论文的数字",
        "",
        "### 第 2 步：对每个「数据性数字」核对",
        "",
        "对照下方的 JSON 数据清单和 TABLE 文件全文：",
        "",
        "1. **能在数据清单/TABLE 文件里找到一致的数字（含正常舍入）** → ✅ 真实，跳过",
        "2. **清单里同一数据字段的值与论文不一致**（如 RMSE 真实是 0.023，论文写的 0.999）"
        f" → 以 JSON 原值为准改正文，**禁止反向操作**（禁止改 JSON）",
        "3. **清单里没找到这个数字** → 按顺序排除，不要直接删：",
        "   - 清单标了「省略中间 N 项」的列表 → 直接读原 JSON 该路径核对",
        "   - 有明确公式的派生量（百分比 = 子集/总数 ×100、差值、比值、单位换算）或题设参数 → 检查派生是否正确",
        "   - 以上都不是 → 才是无依据的数字：改成有依据的值，或删掉该说法",
        "   - ⛔ 不要为了「对上清单」把正确的数改成清单里的近似值或别的字段的值",
        "",
        "### 第 3 步：表格优先用预生成的 TABLE 文件",
        "",
        f"如果论文里手抄了表格内容，**优先改成** {embed_hint}（已经从 JSON 渲染好，不会出错）。",
        "",
        "### 第 4 步：自检完成后登记独立回执",
        "",
        "后置自检使用本轮任务指定的 `.mh/quality/data-review-ack-*.txt` 和确认值；不要将确认值写入论文。",
        "如果本轮写作上下文仍明确要求兼容旧注释，必须在最终编译之前完成；编译之后不得为登记状态再次改源码。",
        "没有本轮确认值时不要复制旧回执或自行编造；系统只接受与当前内容绑定的有效核对。",
        "",
        "**判断原则**：",
        "- 以 JSON 为准修论文，禁止反向修 JSON",
        "- 不必把 JSON 中的每个数字都搬到论文里——只关心论文里出现的数字是否真实",
        "- 不确定某个数字是不是数据 → 当成数据核对一遍，确认能找到来源就行",
        "",
        "---",
        "",
    ]

    bindings = figure_data_bindings(workspace)
    if bindings:
        lines += ["## 图表来源与论断对应（并入本次核对，不启动额外模型轮次）", "",
                  "数字出现过不等于支持当前论断。逐图核对数据所属问题、场景、参数、样本量和统计量；",
                  "跨问题引用允许，但必须解释可迁移的结论。一个概率水平的收敛曲线不能直接证明另一个临界点可靠。",
                  "下面仅列静态识别的真实文件引用，不代表已经验证数学结论；动态路径请按生成脚本补查。", "",
                  "| 图 | 生成脚本 | 可观察的数据来源 |", "|---|---|---|"]
        lines.extend(f"| {b['figure']} | {b['script']} | {', '.join(b['sources']) or '动态来源，需按脚本定位'} |" for b in bindings)
        lines.append("")

    # JSON 数据清单
    if all_entries:
        lines.append("## JSON 真实数据清单")
        lines.append("")

        by_file: dict[str, list[tuple[str, Any]]] = {}
        for fn, kp, v in all_entries:
            by_file.setdefault(fn, []).append((kp, v))

        for fn, entries in by_file.items():
            lines.append(f"### `{fn}`（{len(entries)} 条）")
            lines.append("")
            lines.append("| 数据路径 | 数值 |")
            lines.append("|---|---|")
            for kp, v in entries:
                kp_safe = kp.replace("|", r"\|")
                lines.append(f"| `{kp_safe}` | {_format_value(v)} |")
            lines.append("")

    # TABLE 文件原文 — 论文应直接嵌入这些表，给 Claude 看完整内容方便对照
    if table_files:
        lines.append("---")
        lines.append("")
        lines.append("## 已生成的 TABLE 文件（论文应直接嵌入这些表，不要自己手抄）")
        lines.append("")
        for tf in table_files:
            try:
                text = tf.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                lines.append(f"### `figures/{tf.name}` — 读取失败：{e}")
                continue
            lang = "latex" if tf.suffix == ".tex" else "markdown"
            lines.append(f"### `figures/{tf.name}` ({tf.stat().st_size} 字节)")
            lines.append("")
            lines.append(f"```{lang}")
            # 截断过大的表（>200 行）
            tf_lines = text.split("\n")
            if len(tf_lines) > 200:
                lines.extend(tf_lines[:100])
                lines.append(f"... [中间 {len(tf_lines) - 200} 行省略] ...")
                lines.extend(tf_lines[-100:])
            else:
                lines.append(text.rstrip())
            lines.append("```")
            lines.append("")

    return "\n".join(lines), len(all_entries)


# ===========================================================================
# 主入口
# ===========================================================================

_PASSED_MARKER_DOCX = "<!-- DATA_CHECK_PASSED -->"
_PASSED_MARKER_PDF = "% DATA_CHECK_PASSED"


# ===========================================================================
# 确定性数字溯源（只给线索，不判致命）
#
# 把论文里的结果类数字按"显示精度四舍五入"到数据/题设里找。找不到的逐条列给模型核对，
# 比让它通读几万条数据清单精确得多。⛔ 只作为待核对清单：派生量、方法常数、正文里
# 合法的推算都可能对不上，所以绝不据此判失败，也不要求"对上清单"而改数。
# ===========================================================================

_TRACE_LONG_LIST = 50            # 超过这么多数值的列表只取 min/max/首/尾：长序列会让编造的数"碰巧命中"
_TRACE_MAX_REPORT = 40
_TRACE_CONSTANTS = {0.05, 0.01, 0.1, 0.001, 0.95, 0.99, 0.9, 1.96, 2.58, 2.576, 1.645, 1.282, 0.6745,
                    1.345, 1.4826, 3.841, 3.14, 3.1416, 3.14159, 2.718, 2.71828, 9.8, 9.81,
                    60, 24, 3600, 365, 100, 1000}
_TRACE_NUM = re.compile(
    r"(?<![A-Za-z0-9_.])(?P<sign>[-+−]?)(?P<num>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
    r"(?![.\d])(?P<suffix>\s*(?:\\?%|％|万|亿)|\s*(?:\\times|×)\s*10\s*\^\s*\{?\s*(?P<exp>[-−+]?\d+)\s*\}?)?")
_TRACE_PREFIX = re.compile(
    r"(?:图|表|式|公式|第|问题|附录|章|节|步骤|算法|定理|引理|命题|假设|方案|情景|场景|编号|序号|"
    r"Fig\.?|Figure|Table|Tab\.|Eq\.?|Equation|Section|Sec\.|Chapter|Appendix|Problem|Step|Algorithm|"
    r"Theorem|Lemma|No\.|Python|MATLAB|Gurobi|CPLEX|numpy|scipy|pandas|版本|version|v)\s*[（(\[]?\s*$", re.I)
_TRACE_CHANGE = re.compile(r"(?:提高|降低|减少|增加|提升|下降|缩短|节省|节约|增长|减小|增大|改善|优于|"
                           r"较|相比|比|高出|低于|多出|少了|差距|相差|偏差|误差|差|占|"
                           r"reduc|increas|improv|decreas|lower|higher|gap|differ)", re.I)
_TRACE_DIM = re.compile(r"\s*(?:pt|cm|mm|em|ex|in|bp|\\textwidth|\\linewidth|\\columnwidth|\\textheight|"
                        r"\\paperwidth|\\baselineskip)\b")


def _trace_add_text_numbers(text: str, out: set) -> None:
    for m in _TRACE_NUM.finditer(text):
        value, _decimals, scale = _trace_parse(m)
        if value is None:
            continue
        out.add(value)
        if scale != 1.0:
            out.add(value * scale)


def _trace_value_pool(workspace: Path) -> list[float]:
    """数据/题设里出现过的数值（排序后供二分查找）。"""
    values: set = set()

    def walk(o):
        if isinstance(o, bool) or o is None:
            return
        if isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            nums = [x for x in o if isinstance(x, (int, float)) and not isinstance(x, bool)
                    and math.isfinite(float(x))]
            if len(nums) > _TRACE_LONG_LIST:
                values.update(float(x) for x in (min(nums), max(nums), nums[0], nums[-1]))
                for x in o:
                    if isinstance(x, (dict, list)):
                        walk(x)
            else:
                for x in o:
                    walk(x)
        elif isinstance(o, (int, float)):
            if math.isfinite(float(o)):
                values.add(float(o))
        elif isinstance(o, str) and len(o) <= 40:
            m = _TRACE_NUM.fullmatch(o.strip())
            if m:
                _trace_add_text_numbers(o, values)

    json_files: list[Path] = []
    figures = workspace / "figures"
    if figures.is_dir():
        json_files += sorted(figures.glob("*.json"))
    json_files += [workspace / "results.json", *sorted(workspace.glob("results_*.json")),
                   workspace / "PROBLEM_FACTS.json", workspace / "DATA_FACTS.json",
                   workspace / "DATA_PROFILE.json"]
    for path in json_files:
        try:
            if path.is_file() and path.stat().st_size <= 64 * 1024 * 1024:
                walk(json.loads(path.read_text(encoding="utf-8", errors="replace")))
        except (OSError, ValueError):
            continue
    texts: list[Path] = []
    if figures.is_dir():
        texts += sorted(figures.glob("TABLE_*.tex")) + sorted(figures.glob("TABLE_*.md")) \
            + sorted(figures.glob("TABLE_*.csv"))
    user_data = workspace / "user_data"
    if user_data.is_dir():
        texts += sorted(p for p in user_data.rglob("*_extracted.*") if p.suffix.lower() in {".txt", ".md"})
    for path in texts:
        try:
            if path.stat().st_size <= 16 * 1024 * 1024:
                _trace_add_text_numbers(_safe_read(path), values)
        except OSError:
            continue
    return sorted(values)


def _trace_parse(m):
    """(数值, 显示小数位, 后缀倍率)；解析失败返回 (None, 0, 1)。"""
    raw = m.group("num").replace(",", "")
    try:
        value = float(raw)
    except ValueError:
        return None, 0, 1.0
    if m.group("sign") in ("-", "−"):
        value = -value
    decimals = len(raw.split(".", 1)[1]) if "." in raw else 0
    suffix = (m.group("suffix") or "").strip()
    scale = 1.0
    if m.group("exp"):
        scale = 10.0 ** int(m.group("exp").replace("−", "-"))
    elif suffix in ("%", "\\%", "％"):
        scale = 0.01
    elif suffix == "万":
        scale = 1e4
    elif suffix == "亿":
        scale = 1e8
    return value, decimals, scale


def _trace_found(pool: list[float], value: float, decimals: int, scale: float) -> bool:
    import bisect
    half = 0.5 * 10.0 ** (-decimals)
    candidates = [(value, half)]
    if scale != 1.0:
        candidates.append((value * scale, half * abs(scale)))
    for target, tol in candidates:
        tol = tol * (1 + 1e-9) + 1e-12 * max(1.0, abs(target))
        for t in (target, -target):                 # "降低 12.3%" 常对应负的数据值
            i = bisect.bisect_left(pool, t - tol)
            if i < len(pool) and pool[i] <= t + tol:
                return True
    return False


def _trace_derived_on_line(target: float, decimals: int, scale: float,
                           others: list[float]) -> bool:
    """target 能否由同一行里另外 1–3 个数字做一次加减乘除得到（论文里写出的推算链）。

    只在同一行内组合：放宽到全体数据两两组合会让任何数都"算得出来"。
    """
    tol = 0.5 * 10.0 ** (-decimals) * abs(scale) * (1 + 1e-9) + 1e-12 * max(1.0, abs(target))
    vals = [v for v in others if abs(v - target) > tol][:24]
    if not vals:
        return False

    def close(x):
        return abs(abs(x) - abs(target)) <= tol

    n = len(vals)
    for i in range(n):
        a = vals[i]
        for j in range(n):
            if i == j:
                continue
            b = vals[j]
            if close(a + b) or close(a - b) or close(a * b) or (b != 0 and close(a / b)) \
                    or (b != 0 and close((a - b) / b)) or (b != 0 and close(100 * (a - b) / b)) \
                    or (b != 0 and close(100 * a / b)):
                return True
            for k in range(j + 1, n):
                if k != i and close(a + b + vals[k]):
                    return True
    return False


def _trace_clean(text: str, mode: str) -> str:
    """去掉注释与不含结果数据的结构，保持字符数不变（便于回算行号）。"""
    def blank(match):
        return re.sub(r"[^\n]", " ", match.group(0))
    # 参考文献（年份、卷期、页码）不是本文数据
    text = re.sub(r"\\begin\{thebibliography\}[\s\S]*?(?:\\end\{thebibliography\}|\Z)", blank, text)
    text = re.sub(r"(?m)^#{1,6}\s*(?:参考文献|References|Bibliography)\s*$[\s\S]*?(?=^#{1,2}\s|\Z)", blank, text)
    if mode != "docx" and "\\begin{document}" in text:
        head = text.index("\\begin{document}")
        text = re.sub(r"[^\n]", " ", text[:head]) + text[head:]      # 导言区的版式参数不是数据
    # 区间写法 a--b、a—b、a~b：端点照查，但连接符不能被当成负号
    text = re.sub(r"(?<=\d)\s*(?:--|—|–|~|～)\s*(?=[-+−]?\d)", lambda m: " " * len(m.group(0)), text)
    if mode == "docx":
        text = re.sub(r"<!--[\s\S]*?-->", blank, text)
        text = re.sub(r"```[\s\S]*?```", blank, text)
        text = re.sub(r"!\[[^\]]*\]\([^)]*\)|\]\([^)]*\)|https?://\S+", blank, text)
        # 表格分隔行 | --- | :---: |。空白只在行内匹配：\s 会跨行，上一句把整段附录代码换成空白以后，
        # 两个 \s* 在几十万个空白上来回回溯，一篇带完整程序附录的 Word 稿能把后端卡住半小时以上（10-18 实跑）
        text = re.sub(r"(?m)^[ \t]*\|?[ \t]*:?-{3,}.*$", blank, text)
        text = re.sub(r"\{#[^}]*\}|\[@[^\]]*\]", blank, text)
    else:
        text = re.sub(r"(?<!\\)%[^\n]*", blank, text)
        text = re.sub(r"\\(?:label|ref|eqref|autoref|cref|Cref|pageref|cite[a-z]*|url|href|input|include|"
                      r"includegraphics|bibliography|bibliographystyle|usepackage|documentclass|"
                      r"vspace|hspace|vskip|hskip|setlength|addtolength|setcounter|addtocounter|"
                      r"rule|fontsize|linespread|renewcommand|newcommand|definecolor|captionsetup|geometry|"
                      r"cline|cmidrule|arraystretch|tabcolsep)\*?(?:\[[^\]]*\])*(?:\([^)]*\))?(?:\{[^{}]*\})*",
                      blank, text)
        text = re.sub(r"\\multi(?:column|row)\{[^{}]*\}\{[^{}]*\}", blank, text)
        text = re.sub(r"\\begin\{(?:tabular|tabularx|longtable|array|tabu)\*?\}(?:\[[^\]]*\])?(?:\{(?:[^{}]|\{[^{}]*\})*\})+",
                      blank, text)
        text = re.sub(r"\\(?:resizebox|scalebox)\{[^{}]*\}(?:\{[^{}]*\})?", blank, text)
    # 引用编号 [1] [2,3] [4-6] 与时间 10:30 不是数据
    text = re.sub(r"\[\s*\d+(?:\s*[,，\-–]\s*\d+)*\s*\]", blank, text)
    text = re.sub(r"\b\d{1,2}:\d{2}\b", blank, text)
    # 数学上下标里的数字是符号编号，不是结果（科学计数 10^{-3} 由数字正则整体识别，先保护）
    protected = re.sub(r"(?:\\times|×)\s*10\s*\^\s*\{?\s*[-−+]?\d+\s*\}?",
                       lambda m: "\0" * len(m.group(0)), text)
    protected = re.sub(r"[_^](?:\{[^{}]*\}|[0-9A-Za-z])", blank, protected)
    return "".join(orig if prot == "\0" else prot for orig, prot in zip(text, protected))


def paper_number_trace(workspace: Path, mode: str, sources: list[Path]) -> dict:
    """论文里对不上任何数据/题设值的结果类数字（按显示精度四舍五入比对）。"""
    pool = _trace_value_pool(workspace)
    result = {"checked": 0, "untraced": [], "pool_size": len(pool)}
    if not pool:
        return result
    root = workspace.resolve()
    for src in sources:
        try:
            raw = _safe_read(src)
        except OSError:
            continue
        text = _trace_clean(raw, mode)
        try:
            rel = src.resolve().relative_to(root).as_posix()
        except ValueError:
            rel = src.name
        matches = list(_TRACE_NUM.finditer(text))
        line_values: dict[int, list[float]] = {}
        for m in matches:
            value, _d, scale = _trace_parse(m)
            if value is not None:
                line_values.setdefault(text.count("\n", 0, m.start()), []).append(value * scale)
        for m in matches:
            value, decimals, scale = _trace_parse(m)
            if value is None:
                continue
            start, end = m.start(), m.end()
            if decimals == 0 and scale == 1.0 and abs(value) < 10:
                continue                                    # 小整数多是叙述计数
            if decimals == 0 and scale == 1.0 and 1900 <= value <= 2100 and re.match(r"\s*年", text[end:end + 2]):
                continue                                    # 年份
            if re.match(r"\s*(?:月|日|号|时|章|节|页|条|款)", text[end:end + 3]):
                continue
            if _TRACE_DIM.match(text, end):
                continue                                    # 版面尺寸
            if _TRACE_PREFIX.search(text[max(0, start - 14):start]):
                continue                                    # 图/表/式/章节/版本号等编号
            if abs(value) in _TRACE_CONSTANTS and scale == 1.0:
                continue                                    # 显著性水平、常用物理/换算常数
            if scale == 0.01 and _TRACE_CHANGE.search(text[max(0, start - 16):start]):
                continue                                    # "降低 12.3%" 这类派生比较量另行说明
            result["checked"] += 1
            if _trace_found(pool, value, decimals, scale):
                continue
            if scale == 1.0:
                # 区间/并列写法把倍率写在后面：[2.706,\,3.212]\times10^8
                later = re.search(r"(?:\\times|×)\s*10\s*\^\s*\{?\s*([-−+]?\d+)", text[end:end + 40])
                if later and "\n" not in text[end:end + later.start()] and \
                        _trace_found(pool, value, decimals, 10.0 ** int(later.group(1).replace("−", "-"))):
                    continue
            line_index = text.count("\n", 0, start)
            if _trace_derived_on_line(value * scale, decimals, scale, line_values.get(line_index, [])):
                continue                                    # 同一行里能由其他数字算出（如 60.8+6066.7=6127.5）
            line = line_index + 1
            context = re.sub(r"\s+", " ", raw[max(0, start - 18):min(len(raw), end + 12)]).strip()
            result["untraced"].append({"file": rel, "line": line, "text": m.group(0).strip(),
                                       "context": context})
    return result


def find_sources(workspace: Path, mode: str) -> list[Path]:
    if mode == "docx":
        candidates = [
            "paper/main.md", "PROPOSAL.md", "LITERATURE_REVIEW.md",
            "COURSE_PAPER.md", "COURSE_REPORT.md", "REPORT.md",
        ]
        for c in candidates:
            p = workspace / c
            if p.exists() and p.stat().st_size > 100:
                return [p]
        return []
    return active_sources(workspace / "paper")


def _safe_read(p: Path) -> str:
    raw = p.read_bytes()
    for enc in ("utf-8", "utf-8-sig", "gbk", "gb2312", "gb18030", "latin-1"):
        try:
            return raw.decode(enc).replace("\r\n", "\n").replace("\r", "\n")
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


def has_passed_marker(content: str, mode: str) -> bool:
    """检测论文末尾是否有 Claude 写的自证标记。"""
    marker = _PASSED_MARKER_DOCX if mode == "docx" else _PASSED_MARKER_PDF
    return marker in content


def review_fingerprint(workspace: Path, mode: str) -> str:
    """Bind semantic review to actual sources/data and checker implementation.

    Exclude legacy acknowledgement lines and generated diagnostic reports so
    recording a review does not invalidate itself. File addition/deletion and
    content changes do invalidate it, including changes preserving mtimes.
    """
    workspace = workspace.resolve()
    paths = set((workspace / "figures").glob("*.json"))
    paths.update((workspace / "output").glob("*.json"))
    # Changing a plot's data selection invalidates the old paper review even
    # when the paper wording and JSON values themselves have not changed.
    if mode != "table":
        paths.update((workspace / "figures").glob("*.py"))
    paths.update(workspace.glob("results*.json"))
    paths.update((workspace / "figures").glob("TABLE_*.tex"))
    paths.update((workspace / "figures").glob("TABLE_*.md"))
    if mode != "table":
        paths.update(find_sources(workspace, mode))
    digest = hashlib.sha256(("review-v2:" + mode).encode())
    digest.update(Path(__file__).read_bytes())
    for path in sorted(paths):
        resolved = path.resolve()
        if not resolved.is_relative_to(workspace):
            raise ValueError("review input escapes workspace")
        digest.update(path.relative_to(workspace).as_posix().encode("utf-8"))
        payload = path.read_bytes()
        if path.suffix in {".md", ".tex"}:
            payload = re.sub(rb"(?m)^\s*(?:%\s*DATA_CHECK_PASSED|<!--\s*DATA_CHECK_PASSED\s*-->)\s*$", b"", payload)
            payload = payload.replace(b"\r\n", b"\n").rstrip()
        digest.update(hashlib.sha256(payload).digest())
    return digest.hexdigest()


def _review_path(workspace: Path, mode: str) -> Path:
    if mode not in {"pdf", "docx", "table"}:
        raise ValueError("invalid review mode")
    path = workspace / ".mh" / "quality" / f"data-review-{mode}.json"
    if not path.resolve().is_relative_to(workspace.resolve()):
        raise ValueError("review receipt escapes workspace")
    return path


def has_current_review(workspace: Path, mode: str) -> bool:
    try:
        receipt = json.loads(_review_path(workspace, mode).read_text(encoding="utf-8"))
        return receipt.get("schema") == 2 and receipt.get("reviewed") is True and receipt.get("fingerprint") == review_fingerprint(workspace, mode)
    except (OSError, ValueError, TypeError, AttributeError):
        return False


def record_review(workspace: Path, mode: str, *, expected_fingerprint: str,
                  acknowledgement_token: str | None = None) -> bool:
    """Record an explicitly completed semantic review, never fabricate one.

    Caller must have successfully completed the review. Require its explicit
    acknowledgement plus a stable final snapshot; deterministic failures cannot
    be cleared by a receipt. Existing legacy markers alone never auto-upgrade.
    """
    report = (run_table_check(workspace, write_reports=False) if mode == "table"
              else run_check(workspace, mode, write_reports=False))
    if acknowledgement_token is not None:
        # A fresh per-attempt acknowledgement lives outside the manuscript.
        # Reusing a previous marker or receipt is not a completed new review.
        ack = workspace / ".mh" / "quality" / f"data-review-ack-{mode}.txt"
        try:
            raw_ack = (not ack.is_symlink()
                       and ack.resolve().is_relative_to(workspace.resolve())
                       and ack.stat().st_size <= 256
                       and bool(acknowledgement_token)
                       and ack.read_text(encoding="utf-8").strip() == acknowledgement_token)
        except (OSError, UnicodeError):
            raw_ack = False
    else:
        raw_ack = ((workspace / "figures" / _TABLE_PASSED_MARKER_FILE).is_file() if mode == "table"
                   else any(has_passed_marker(_safe_read(p), mode) for p in find_sources(workspace, mode)))
    if report.has_fatal() or not raw_ack or review_fingerprint(workspace, mode) != expected_fingerprint:
        return False
    target = _review_path(workspace, mode)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent, prefix="review-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump({"schema": 2, "reviewed": True, "kind": "semantic_attestation", "fingerprint": expected_fingerprint}, stream)
        if review_fingerprint(workspace, mode) != expected_fingerprint:
            return False
        os.replace(temporary, target)
        return True
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def run_check(
    workspace: Path,
    mode: str = "docx",
    *,
    write_reports: bool = True,
) -> DataCheckReport:
    """运行确定性硬规则检查 + 准备数据清单 + 检测自证标记。

    ``write_reports=False`` 专供协同工作台的“只读检查”使用。检查逻辑
    与自动流程保持一致，但不会在正式工作区生成清单或报告文件。
    """
    sources = find_sources(workspace, mode)
    report = DataCheckReport(mode, sources)

    if not sources:
        report.add_info("未找到待核对的源文件，跳过")
        return report

    # 读论文内容
    contents: list[str] = []
    for src in sources:
        try:
            contents.append(_safe_read(src))
        except Exception as e:
            report.add_warn(f"读取 {src} 失败：{e}")
    if not contents:
        report.add_warn("所有源文件读取失败")
        return report
    full_content = "\n\n".join(contents)
    report.stats["源文件数"] = len(sources)
    report.stats["总字符数"] = len(full_content)

    # 1. 确定性硬规则（格式残留）
    if mode == "docx":
        check_latex_table_residue_in_md(full_content, report)
    else:
        check_markdown_residue_in_tex(full_content, report)

    # 2. 检测自证标记
    report.passed_marker_found = has_current_review(workspace, mode)
    if has_passed_marker(full_content, mode) and not report.passed_marker_found:
        report.add_info("原自检标记未绑定当前文件快照；需一次范围核对，不能据此判数据错误")

    # 3. 构建数据原料清单
    has_data_files = (
        any((workspace / "figures").glob("*.json"))
        or any((workspace / "figures").glob("TABLE_*"))
        # paper_from_assets: 用户在根目录提供的 results.json
        or (workspace / "results.json").exists()
        or any(workspace.glob("results_*.json"))
    )
    if has_data_files:
        checklist_md, n_entries = build_data_checklist(workspace, mode)
        if checklist_md:
            report.checklist_md = checklist_md
            report.stats["数据条目数"] = n_entries
            if write_reports:
                try:
                    (workspace / "PAPER_DATA_CHECKLIST.md").write_text(
                        checklist_md, encoding="utf-8")
                except Exception as e:
                    log.warning("无法写 PAPER_DATA_CHECKLIST.md: %s", e)

            # 没有自证标记 → 需要 Claude 自检
            if not report.passed_marker_found:
                report.need_self_check = True
        try:
            trace = paper_number_trace(workspace, mode, sources)
        except Exception as exc:   # 线索生成失败不影响原有核对流程
            log.warning("数字溯源未完成：%s: %s", type(exc).__name__, exc)
            trace = None
        if trace and trace["checked"]:
            key = re.compile(r"abstract|摘要|summary|conclusion|结论", re.I)
            report.untraced = sorted(trace["untraced"],
                                     key=lambda item: (not key.search(item["file"]), item["file"], item["line"]))
            report.stats["结果类数字（已比对）"] = trace["checked"]
            report.stats["按显示精度在数据里找不到的数字"] = len(trace["untraced"])
        else:
            report.add_info("figures/ 中无 JSON 也无 TABLE — 跳过自检")
    else:
        report.add_info("无 figures/*.json 或 TABLE_* — 无数据需要核对")

    # 写诊断报告
    if write_reports:
        try:
            (workspace / "PAPER_DATA_CHECK_REPORT.md").write_text(
                _render_report(report), encoding="utf-8",
            )
        except Exception as e:
            log.warning("无法写报告文件：%s", e)

    return report


def _render_report(report: DataCheckReport) -> str:
    lines = [
        f"# 论文数据真实性核对报告（{report.mode.upper()} 模式）",
        "",
        f"**核对源**: {', '.join(s.name for s in report.sources) or '(无)'}",
        f"**摘要**: {report.render_summary()}",
        "",
    ]
    if report.stats:
        lines.append("## 统计")
        for k, v in report.stats.items():
            lines.append(f"- {k}: {v}")
        lines.append("")
    if report.fatal:
        lines.append("## ❌ 致命（确定性硬规则违反）")
        for m in report.fatal:
            lines.append(f"- {m}")
        lines.append("")
    if report.warn:
        lines.append("## ⚠ 警告")
        for m in report.warn:
            lines.append(f"- {m}")
        lines.append("")
    if report.info:
        lines.append("## ℹ 信息")
        for m in report.info:
            lines.append(f"- {m}")
        lines.append("")
    if report.untraced:
        lines.append("## 🔎 按显示精度在数据/题设里找不到的数字（待核对，不等于错误）")
        lines.append("")
        lines.append("已把论文数字按其小数位四舍五入，到 figures/*.json、TABLE_*、PROBLEM_FACTS/DATA_FACTS、"
                     "题面原文里查找，并排除了编号、年份、版式参数、参考文献和同一行可算出的推算量。"
                     "下面这些没找到：逐条确认是派生量、单位换算、数据描述还是写错了；"
                     "确认无误的不要改，写错的以 JSON 原值为准改论文。")
        lines.append("")
        lines.append("| 位置 | 数字 | 上下文 |")
        lines.append("|---|---|---|")
        for item in report.untraced[:_TRACE_MAX_REPORT]:
            ctx = item["context"].replace("|", r"\|")
            lines.append(f"| `{item['file']}:{item['line']}` | `{item['text']}` | …{ctx}… |")
        if len(report.untraced) > _TRACE_MAX_REPORT:
            lines.append(f"| … | 另有 {len(report.untraced) - _TRACE_MAX_REPORT} 个 | 同样按上面的规则核对 |")
        lines.append("")
    if report.passed_marker_found:
        lines.append("## ✅ 已通过 Claude 自检")
        lines.append("")
        lines.append(f"论文中含 `{_PASSED_MARKER_DOCX if report.mode == 'docx' else _PASSED_MARKER_PDF}` 标记。")
    elif report.need_self_check:
        lines.append("## 🔄 待 Claude 自检")
        lines.append("")
        lines.append("数据原料已写入 `PAPER_DATA_CHECKLIST.md`，等待 Claude 读清单 + 论文进行自检修复。")
    return "\n".join(lines)


# ===========================================================================
# paper-figure 步骤后的检查（TABLE 文件 vs JSON）
# ===========================================================================

class TableCheckReport:
    """paper-figure 步骤后的检查报告。

    与 DataCheckReport 类似但范围不同：只检查 figures/TABLE_*.tex|md。
    """
    def __init__(self):
        self.fatal: list[str] = []
        self.warn: list[str] = []
        self.info: list[str] = []
        self.checklist_md: str = ""
        self.need_self_check: bool = False
        self.passed_marker_found: bool = False
        self.stats: dict[str, Any] = {}
        self.table_files: list[Path] = []

    def has_fatal(self) -> bool:
        return bool(self.fatal)

    def render_summary(self) -> str:
        parts = []
        if self.fatal:
            parts.append(f"{len(self.fatal)} 致命")
        if self.warn:
            parts.append(f"{len(self.warn)} 警告")
        if self.passed_marker_found:
            parts.append("Claude 已自检")
        elif self.need_self_check:
            parts.append("待 Claude 自检 TABLE")
        return " / ".join(parts) if parts else "无 TABLE 文件，跳过"


_TABLE_PASSED_MARKER_FILE = "TABLE_DATA_CHECK_PASSED.txt"


def has_table_passed_marker(workspace: Path) -> bool:
    """检测 paper-figure 步骤是否写过自证标记文件。"""
    marker = workspace / "figures" / _TABLE_PASSED_MARKER_FILE
    return marker.is_file() and has_current_review(workspace, "table")


def build_table_checklist(workspace: Path,
                           json_sources: list[tuple[Path, Any]],
                           table_files: list[Path]) -> str:
    """构建 TABLE-vs-JSON 核对清单（paper-figure 步骤用）。

    与论文清单的区别：聚焦在「TABLE 数字应该 100% 来自 JSON」这条铁律。
    """
    if not json_sources or not table_files:
        return ""

    all_entries: list[tuple[str, str, Any]] = []
    for jp, data in json_sources:
        for kp, v in _flatten_json(data):
            all_entries.append((jp.name, kp, v))

    lines = [
        "# TABLE 数据真实性核对清单（paper-figure 步骤）",
        "",
        f"**JSON 源**: {', '.join(p.name for p, _ in json_sources)}",
        f"**JSON 数据条目**: {len(all_entries)}",
        f"**TABLE 文件**: {len(table_files)} 个",
        "",
        "---",
        "",
        "## 核心规则",
        "",
        "**表格数字须能由结果数据复算；允许单位换算、舍入、差值、比值与统计区间，保留推导依据。**",
        "",
        "paper-figure 步骤的设计是从 JSON 数据**渲染**出 TABLE 文件",
        "（用 `_utils/stats_utils.py` 的 `regression_table()` / `descriptive_table()` 等函数，",
        "或者读 JSON 后用 Python 脚本生成）。",
        "",
        "**TABLE 中出现 JSON 没有的数字 = 编造**，必须用真实 JSON 数据重新生成对应表格。",
        "",
        "---",
        "",
        "## 自检步骤",
        "",
        "1. **逐个打开 figures/TABLE_*.tex|md**，识别每个表格里的数字单元格",
        "2. **对每个数字**，对照下方 JSON 数据清单：",
        "   - ✅ 能精确匹配（含合理的精度截断如 `0.94` ↔ `0.93724`）→ 真实",
        "   - 未直接匹配 JSON：先查推导、单位和舍入；仍无依据则标记待确认，不能直接认定编造或删除整张表，",
        "     用真实 JSON 数据重新生成（推荐：`python3 -c \"from _utils.stats_utils import descriptive_table; ...\"`）",
        "3. **跳过非数据型数字**：列号 `(1)(2)(3)`、列宽 `width=10cm`、"
        "LaTeX 字号 `\\zihao{5}` 等格式标记中的数字",
        "4. **修完所有 TABLE 后**，写自证标记：",
        "",
        "   ```bash",
        f"   touch figures/{_TABLE_PASSED_MARKER_FILE}",
        "   ```",
        "",
        "   下一轮检查看到此标记会跳过自检循环。",
        "",
        "**禁止**：禁止改 JSON 让数字\"对得上\"、禁止编造解释、禁止保留疑似编造的 TABLE。",
        "",
        "**特别提示**：如果 JSON 中确实没有支撑某张表所需的数据（比如表格规划里有「数据集统计特征」"
        "但 JSON 只存了模型对比结果），说明上游步骤遗漏了该数据。"
        "应该：(a) 删除这张表，并把缺口写进 UPSTREAM_ISSUES.md；"
        "或 (b) 写一个新的补充脚本（如 figures/supp_*.py）只读原始数据/现有结果做派生统计，"
        "输出到新文件（如 figures/supp_*.json）再生成 TABLE，并在表注说明数据来源。"
        "⛔ 不要改写已有的结果 JSON、code/ 或规划文档（本步对这些只读，改动会被还原）。"
        "**不能**直接保留编造的数字。",
        "",
        "---",
        "",
        "## TABLE 文件全文",
        "",
    ]

    for tf in table_files:
        try:
            text = tf.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        lang = "latex" if tf.suffix == ".tex" else "markdown"
        lines.append(f"### `figures/{tf.name}` ({tf.stat().st_size} 字节)")
        lines.append("")
        lines.append(f"```{lang}")
        tf_lines = text.split("\n")
        if len(tf_lines) > 200:
            lines.extend(tf_lines[:100])
            lines.append(f"... [中间 {len(tf_lines) - 200} 行省略] ...")
            lines.extend(tf_lines[-100:])
        else:
            lines.append(text.rstrip())
        lines.append("```")
        lines.append("")

    lines += [
        "---",
        "",
        "## JSON 真实数据完整清单",
        "",
    ]

    by_file: dict[str, list[tuple[str, Any]]] = {}
    for fn, kp, v in all_entries:
        by_file.setdefault(fn, []).append((kp, v))

    for fn, entries in by_file.items():
        lines.append(f"### `{fn}`（{len(entries)} 条）")
        lines.append("")
        lines.append("| 数据路径 | 数值 |")
        lines.append("|---|---|")
        for kp, v in entries:
            kp_safe = kp.replace("|", r"\|")
            lines.append(f"| `{kp_safe}` | {_format_value(v)} |")
        lines.append("")

    return "\n".join(lines)


def run_table_check(
    workspace: Path,
    *,
    write_reports: bool = True,
) -> TableCheckReport:
    """paper-figure 步骤完成后调用：核对 TABLE 文件是否都来自 JSON。

    与 run_check (论文级) 互为补充：
    - run_table_check：paper-figure 后跑，检查表格本身
    - run_check：写作步骤后跑，检查论文 + 嵌入的表格

    这样可以从源头拦截「TABLE 编造 → 写作 cat 进去 → 数字错的论文」的链路。
    """
    report = TableCheckReport()

    figs = workspace / "figures"
    if not figs.is_dir():
        report.info.append("无 figures/ 目录，跳过 TABLE 核对")
        return report

    table_files = sorted(figs.glob("TABLE_*.tex")) + sorted(figs.glob("TABLE_*.md"))
    if not table_files:
        report.info.append("无 figures/TABLE_*.tex|md 文件，跳过 TABLE 核对")
        return report
    report.table_files = table_files
    report.stats["TABLE 文件数"] = len(table_files)

    # 收集 JSON
    json_sources: list[tuple[Path, Any]] = []
    seen = set()
    for c in ["all_results.json"]:
        if c not in seen:
            seen.add(c)
            p = figs / c
            if p.exists():
                try:
                    json_sources.append((p, json.loads(p.read_text(encoding="utf-8"))))
                except Exception as e:
                    log.warning("无法解析 %s: %s", p, e)
    for f in sorted(figs.glob("*_results.json")):
        if f.name in seen:
            continue
        seen.add(f.name)
        try:
            json_sources.append((f, json.loads(f.read_text(encoding="utf-8"))))
        except Exception as e:
            log.warning("无法解析 %s: %s", f, e)
    # paper_from_assets: 用户在根目录的 results.json 也算数据源
    for c in ["results.json"]:
        wp = workspace / c
        if wp.exists() and c not in seen:
            seen.add(c)
            try:
                json_sources.append((wp, json.loads(wp.read_text(encoding="utf-8"))))
            except Exception as e:
                log.warning("无法解析 %s: %s", wp, e)
    for f in sorted(workspace.glob("results_*.json")):
        if f.name in seen:
            continue
        seen.add(f.name)
        try:
            json_sources.append((f, json.loads(f.read_text(encoding="utf-8"))))
        except Exception as e:
            log.warning("无法解析 %s: %s", f, e)

    if not json_sources:
        report.warn.append(
            f"有 {len(table_files)} 个 TABLE 文件但**没有 figures/*.json**，"
            f"无法核对真实性 — 请先确认 paper-analysis 步骤是否产出了 JSON 结果文件"
        )
        return report

    report.stats["JSON 文件数"] = len(json_sources)

    # 检测自证标记
    report.passed_marker_found = has_table_passed_marker(workspace)

    # 构建清单
    checklist = build_table_checklist(workspace, json_sources, table_files)
    if checklist:
        report.checklist_md = checklist
        if write_reports:
            try:
                (workspace / "TABLE_DATA_CHECKLIST.md").write_text(
                    checklist, encoding="utf-8")
            except Exception as e:
                log.warning("无法写 TABLE_DATA_CHECKLIST.md: %s", e)
        if not report.passed_marker_found:
            report.need_self_check = True

    # 写诊断报告
    if write_reports:
        try:
            (workspace / "TABLE_DATA_CHECK_REPORT.md").write_text(
                _render_table_report(report), encoding="utf-8",
            )
        except Exception as e:
            log.warning("无法写 TABLE_DATA_CHECK_REPORT.md: %s", e)

    return report


def _render_table_report(report: TableCheckReport) -> str:
    lines = [
        "# TABLE 数据真实性核对报告",
        "",
        f"**TABLE 文件数**: {len(report.table_files)}",
        f"**摘要**: {report.render_summary()}",
        "",
    ]
    if report.stats:
        lines.append("## 统计")
        for k, v in report.stats.items():
            lines.append(f"- {k}: {v}")
        lines.append("")
    if report.fatal:
        lines.append("## ❌ 致命")
        for m in report.fatal:
            lines.append(f"- {m}")
        lines.append("")
    if report.warn:
        lines.append("## ⚠ 警告")
        for m in report.warn:
            lines.append(f"- {m}")
        lines.append("")
    if report.info:
        lines.append("## ℹ 信息")
        for m in report.info:
            lines.append(f"- {m}")
        lines.append("")
    if report.passed_marker_found:
        lines.append("## ✅ 已通过 Claude 自检")
        lines.append("")
        lines.append(f"`figures/{_TABLE_PASSED_MARKER_FILE}` 已存在。")
    elif report.need_self_check:
        lines.append("## 🔄 待 Claude 自检")
        lines.append("")
        lines.append("数据原料已写入 `TABLE_DATA_CHECKLIST.md`。")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    _configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="论文数据真实性核对（PDF/DOCX/TABLE 通用）")
    parser.add_argument("--mode", choices=["docx", "pdf", "table"], required=True,
                        help="docx/pdf：写作后扫论文；table：paper-figure 后扫 TABLE 文件")
    parser.add_argument("--workspace", "-w", type=Path, required=True)
    parser.add_argument("--quiet", "-q", action="store_true")
    parser.add_argument("--record-review", action="store_true", help="仅在已完成逐项核对后记录当前内容版本的自检凭证")
    args = parser.parse_args()
    if args.record_review:
        fingerprint = review_fingerprint(args.workspace, args.mode)
        ok = record_review(args.workspace, args.mode, expected_fingerprint=fingerprint)
        print("OK: 已记录本次语义核对快照" if ok else "FAIL: 缺少明确确认、存在错误或核对期间文件变化；未记录通过")
        return 0 if ok else 1

    logging.basicConfig(level=logging.WARNING if args.quiet else logging.INFO,
                        format="%(levelname)s: %(message)s")

    if args.mode == "table":
        t_report = run_table_check(args.workspace)
        if not args.quiet:
            print(_render_table_report(t_report))
        print(f"\n报告: {args.workspace}/TABLE_DATA_CHECK_REPORT.md")
        if t_report.need_self_check:
            print(f"清单: {args.workspace}/TABLE_DATA_CHECKLIST.md")
        sys.exit(1 if t_report.has_fatal() else 0)

    report = run_check(args.workspace, mode=args.mode)
    if not args.quiet:
        print(_render_report(report))
    print(f"\n报告: {args.workspace}/PAPER_DATA_CHECK_REPORT.md")
    if report.need_self_check:
        print(f"清单: {args.workspace}/PAPER_DATA_CHECKLIST.md")
    sys.exit(1 if report.has_fatal() else 0)


if __name__ == "__main__":
    sys.exit(main())
