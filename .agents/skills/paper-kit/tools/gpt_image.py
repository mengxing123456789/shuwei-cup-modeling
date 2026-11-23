#!/usr/bin/env python3
"""GPT Image 2 命令行工具 — 供 Claude skill 调用生成示意图/技术路线图/流程图。

用法:
  python _utils/gpt_image.py --check
  python _utils/gpt_image.py --prompt "..." --output figures/fig_xxx.png --lang zh
  python _utils/gpt_image.py --prompt "..." --output figures/fig_xxx.png --lang en --aspect-ratio 16:9

环境变量:
  GPT_IMAGE_API_KEY  — API Key（必须）
  PAPERKIT_SIGNED_GATEWAY_CONFIG — 由父进程传入、经本工具验签的网关配置

退出码:
  0 = 成功（--check 模式：API Key 已配置；生成模式：图片已保存）
  1 = 失败（未配置 key / API 错误 / 网络错误）
  3 = 照线框重绘不可用（本机工具票据），没有发请求
  4 = 构图不合规（method 图非 multi_panel 却带字母面板，或本篇已用过同一构图族），没有发请求、不算次数

输出 PNG 后自动转 PDF（LaTeX 需要 PDF 格式）。
"""
from __future__ import annotations

import argparse
import base64
import colorsys
import hashlib
import http.client
import json
import os
import random
import re
import socket
import ssl
from trusted_gateway_config import verified_tls_context
import sys
import time as _time
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

MAX_IMAGE_BYTES = 32 * 1024 * 1024
MAX_RESPONSE_BYTES = 48 * 1024 * 1024


def image_model_id(value: str | None = None) -> str:
    """Only legacy/absent settings use the default; invalid IDs never fall back."""
    value = os.environ.get("GPT_IMAGE_MODEL_ID", "gpt-image-2") if value is None else value
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,199}", value):
        raise ValueError("生图模型 ID 无效，请重新选择模型")
    return value

# ============================================================
# 提示词模板（集中管理，方便修改替换）
# ============================================================

# 中文语言适配前缀（精简版——GPT Image 越简洁效果越好）
ZH_LANG_PREFIX = (
    "生成一张科研级别的学术论文插图。"
    "字体不要出现乱码，确保生成简体中文可适配。"
    "数学变量保持拉丁字母。\n\n"
)

# 英文语言适配前缀
EN_LANG_PREFIX = (
    "Generate a research-grade academic paper illustration. "
    "All text in English, clean sans-serif font.\n\n"
)

# 统一风格后缀（极简——只保留必要约束，让 GPT Image 自由发挥）
UNIFIED_STYLE_SUFFIX = (
    "\n\n图表上方不需要标题。白色背景，无水印无签名无装饰边框。"
    "配色自由搭配，丰富专业。4K分辨率。"
)

# 安全约束后缀（精简）
SAFETY_SUFFIX = (
    "\n不要生成真人面孔或肖像照片，需要人物时用抽象图标代替。"
)


def build_prompt(user_prompt: str, lang: str) -> str:
    """注入语言适配 + 统一风格 + 安全约束。Claude 只需写核心场景描述。"""
    if lang == "zh":
        prefix = ZH_LANG_PREFIX
    else:
        prefix = EN_LANG_PREFIX
    return prefix + user_prompt + UNIFIED_STYLE_SUFFIX + SAFETY_SUFFIX


# ============================================================
# 论文风格合同（--style paper-* / --spec）
# ============================================================
# 上面的 legacy 后缀写着"配色自由搭配，丰富专业"，同样内容会画出 3D 彩虹板、纹理、
# 写实物体，还自加二十来处文字。下面两份合同来自 2026-10-08 美赛 A 题实测：把风格写死成
# 论文矢量图，并只准写规格里列出的文字。legacy 调用方（编辑器等）行为不变。

PAPER_STYLE_ARCHITECTURE = (
    "STYLE: it must look like a figure drawn by a researcher in PowerPoint or Adobe Illustrator "
    "for a top-conference or top-journal paper (\"Figure 1: overview of our method\"), not like AI art.\n"
    "- Pure white background. Flat 2D vector graphics only.\n"
    "- Rounded rectangles with a small corner radius, thin 1-1.5 px dark-gray (#4A4A4A) outlines and very "
    "light flat fills. Related boxes sit inside a larger lightly tinted region with a bold region title.\n"
    "- Palette: muted blue #4C72B0, muted orange #DD8452, muted green #55A868, used only as pale tints for "
    "region fills and as thin accent lines; everything else black or gray.\n"
    "- Text: black, clean sans-serif (Helvetica or Arial style), consistent sizes, bold only for region and "
    "box titles; math set in italic serif like LaTeX. The smallest text must stay readable when the whole "
    "figure is printed 6.5 inches wide.\n"
    "- Arrows: straight and orthogonal (horizontal or vertical with right-angle bends), thin dark-gray lines "
    "with small solid triangular heads.\n"
    "- Everything aligned to a grid with consistent spacing and margins; generous whitespace; balanced and "
    "uncluttered.\n"
    "- Tiny inline glyphs only where the description asks for them: simple one-color line drawings. "
    "No other icons.\n"
)

PAPER_STYLE_SCHEMATIC = (
    "STYLE: a clean scientific schematic in the style of a Nature or Science paper figure, drawn as flat 2D "
    "vector art in Adobe Illustrator. It must not look like AI art or a storybook illustration.\n"
    "- Pure white background. Panels separated by whitespace, no panel borders; bold lowercase panel letters "
    "at each panel's top-left corner when there are several panels.\n"
    "- Objects are simplified geometric drawings: clean straight or smooth lines, flat light-gray fills "
    "(#E6E6E6) with dark-gray outlines (#4A4A4A); one or two muted accent colors (#DD8452, #4C72B0) only "
    "where the description asks for emphasis.\n"
    "- Thin lines (1-1.5 px), consistent stroke widths, small solid arrowheads.\n"
    "- Text: small black sans-serif labels (Helvetica or Arial style) with thin leader lines; math in italic "
    "serif like LaTeX. The smallest text must stay readable when the figure is printed 6.5 inches wide.\n"
    "- Schematic only: no axis ticks, no numbers that are not listed below, no data values, no grids.\n"
)

PAPER_AVOID = (
    "STRICTLY AVOID: hand-drawn, pencil, sketch, watercolor, paper or stone texture, photorealism, 3D, "
    "perspective, drop shadows, glow, gradients, neon colors, colormaps, charts with numeric axes or tick "
    "values, clip-art, emoji, cartoon people, decorative icons, a title at the top of the image, "
    "sentence-long captions, logos, signatures, watermarks, a frame around the whole image.\n"
)

PAPER_TEXT_RULE = (
    "TEXT RULES: the only text allowed in the image is the list below. Render each string exactly as "
    "written (same spelling, symbols and capitalization). Do not add any other words, numbers, units, "
    "axis labels, legends or numbering."
)

WIREFRAME_INSTRUCTION = (
    "The attached image is a rough wireframe made by the authors. Keep exactly the same layout, the same "
    "blocks in the same positions, the same arrows and the same text strings. Redraw it as a polished "
    "publication figure following the STYLE below; you may adjust spacing and alignment slightly, but do "
    "not move, add or remove any block, arrow or text."
)

PAPER_STYLES = {
    "paper-architecture": PAPER_STYLE_ARCHITECTURE,
    "paper-schematic": PAPER_STYLE_SCHEMATIC,
}
# method = 每问流程图、模型/算法原理图：版式由图规格的 grammar（版式库）定，造型由本篇 house style 定。
SPEC_KINDS = {"architecture": "paper-architecture", "schematic": "paper-schematic", "method": "paper-method"}

# 图规格可带 palette，让一篇论文的 AI 图跟随本篇的流程图风格族（美赛：A 暖棕 / B 靛蓝 / C 黑白），
# 不同论文的 AI 图因此不撞色。不带时用上面合同里的默认三色。
_ARCH_BOX_LINE = (
    "- Rounded rectangles with a small corner radius, thin 1-1.5 px dark-gray (#4A4A4A) outlines and very "
    "light flat fills. Related boxes sit inside a larger lightly tinted region with a bold region title.\n"
)
_ARCH_PALETTE_LINE = (
    "- Palette: muted blue #4C72B0, muted orange #DD8452, muted green #55A868, used only as pale tints for "
    "region fills and as thin accent lines; everything else black or gray.\n"
)
_SCHEMATIC_COLOR_LINE = (
    "- Objects are simplified geometric drawings: clean straight or smooth lines, flat light-gray fills "
    "(#E6E6E6) with dark-gray outlines (#4A4A4A); one or two muted accent colors (#DD8452, #4C72B0) only "
    "where the description asks for emphasis.\n"
)
_HEX_COLOR = re.compile(r"#[0-9A-Fa-f]{6}")


def _paper_style(kind: str, palette=None) -> str:
    """kind=architecture/schematic；palette=None（默认三色）/ "mono"（纯黑白）/ [强调色, 浅底…]。"""
    style = PAPER_STYLES[SPEC_KINDS[kind]]
    if palette is None:
        return style
    if palette == "mono":
        if kind == "architecture":
            return style.replace(_ARCH_BOX_LINE, (
                "- Rounded rectangles with a small corner radius, thin 1-1.5 px black outlines and white fills. "
                "Related boxes sit inside a larger region drawn with a thin black solid or dashed outline and a bold "
                "region title.\n")).replace(_ARCH_PALETTE_LINE, (
                "- Palette: black and white only. No color and no gray fills anywhere; separate regions with thin "
                "solid or dashed black outlines and whitespace; mark the single most important box with a slightly "
                "thicker black outline.\n"))
        return style.replace(_SCHEMATIC_COLOR_LINE, (
            "- Objects are simplified geometric drawings: clean straight or smooth lines, white or light-gray "
            "fills (#E6E6E6) with black outlines; emphasis only by line weight, dashed lines or hatching, never "
            "by color.\n"))
    accent, tints = palette[0], palette[1:]
    tint_text = ", ".join(tints) if tints else f"very pale tints of {accent}"
    if kind == "architecture":
        return style.replace(_ARCH_PALETTE_LINE, (
            f"- Palette: a single accent color {accent}, used only for thin accent lines, the arrowheads of the "
            f"main flow and the outline of the one most important box; region fills are white or very pale tints "
            f"({tint_text}); everything else black or gray. No other colors.\n"))
    return style.replace(_SCHEMATIC_COLOR_LINE, (
        "- Objects are simplified geometric drawings: clean straight or smooth lines, flat light-gray fills "
        f"(#E6E6E6) with dark-gray outlines (#4A4A4A); the accent color {accent} (pale fill: {tint_text}) only "
        "where the description asks for emphasis. No other colors.\n"))

_MAX_SPEC_STRINGS = 80
_MAX_SPEC_STRING_LEN = 120
_MAX_SPEC_DESCRIPTION = 6000
_MAX_SPEC_RELATIONS = 12
_MAX_SPEC_RELATION_LEN = 200
_MAX_REFERENCE_BYTES = 16 * 1024 * 1024   # 与本机工具代理的请求体上限一致


class EditsUnavailable(Exception):
    """当前凭据通路不支持参考图重绘：桌面版本机工具票据只放行 images/generations。"""


def parse_aspect(value) -> float | None:
    """'2:1' → 2.0；只接受 GPT Image 支持的 1:3–3:1 范围，其余返回 None。"""
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*:\s*(\d+(?:\.\d+)?)\s*", str(value or ""))
    if not m:
        return None
    w, h = float(m.group(1)), float(m.group(2))
    if w <= 0 or h <= 0 or not (1 / 3 <= w / h <= 3):
        return None
    return w / h


def validate_size(size: str) -> str:
    """GPT Image 自定义尺寸：宽高为 16 的倍数、比例 1:3–3:1、单边 ≤3840、总像素 655360–8294400。"""
    m = re.fullmatch(r"(\d{3,4})x(\d{3,4})", str(size or ""))
    if not m:
        raise ValueError("size 必须写成 宽x高，例如 2048x1024")
    w, h = int(m.group(1)), int(m.group(2))
    if (w % 16 or h % 16 or not (1 / 3 <= w / h <= 3) or max(w, h) > 3840
            or not (655_360 <= w * h <= 8_294_400)):
        raise ValueError("size 不在 GPT Image 支持范围内")
    return f"{w}x{h}"


def validate_spec(spec) -> dict:
    """校验图规格：kind / description / strings 必填；只返回清洗后的副本。"""
    if not isinstance(spec, dict):
        raise ValueError("图规格必须是 JSON 对象")
    if spec.get("kind") not in SPEC_KINDS:
        raise ValueError("图规格 kind 只能是 architecture、schematic 或 method")
    grammar = spec.get("grammar")
    if grammar is not None and grammar not in FIGURE_GRAMMARS:
        raise ValueError("图规格 grammar 必须是版式库里的 id：" + ", ".join(FIGURE_GRAMMARS))
    if spec.get("kind") == "method" and grammar is None:
        raise ValueError("kind=method 的图规格必须写 grammar（按内容从版式库里选）")
    cands = spec.get("candidates")
    if cands is not None and (
            not isinstance(cands, list) or not 3 <= len(cands) <= 12 or len(set(map(str, cands))) != len(cands)
            or not all(c in FIGURE_GRAMMARS for c in cands) or grammar not in cands):
        raise ValueError("图规格 candidates 必须是 3–12 个不重复的版式库 id，并且包含 grammar 本身")
    relations = spec.get("relations")
    if relations is not None and (
            not isinstance(relations, list) or not 1 <= len(relations) <= _MAX_SPEC_RELATIONS
            or not all(isinstance(r, str) and r.strip() and len(r) <= _MAX_SPEC_RELATION_LEN
                       and not any(ord(c) < 32 for c in r) for r in relations)):
        raise ValueError(f"图规格 relations 必须是 1–{_MAX_SPEC_RELATIONS} 条单行文字，每条不超过 "
                         f"{_MAX_SPEC_RELATION_LEN} 字符")
    if spec.get("allow_two_way") is not None and not isinstance(spec["allow_two_way"], bool):
        raise ValueError("图规格 allow_two_way 只能是 true 或 false")
    desc = spec.get("description")
    if not isinstance(desc, str) or not desc.strip() or len(desc) > _MAX_SPEC_DESCRIPTION:
        raise ValueError("图规格 description 必须是 1–6000 字符的文字")
    strings = spec.get("strings")
    if not isinstance(strings, list) or not strings or len(strings) > _MAX_SPEC_STRINGS:
        raise ValueError("图规格 strings 必须是 1–80 条文字")
    clean = []
    for item in strings:
        if (not isinstance(item, str) or not item.strip() or len(item) > _MAX_SPEC_STRING_LEN
                or any(ord(c) < 32 for c in item)):
            raise ValueError("图规格 strings 每条必须是 1–120 字符的单行文字")
        clean.append(item.strip())
    if len(set(clean)) != len(clean):
        raise ValueError("图规格 strings 有重复条目")
    if spec.get("target_aspect") is not None and parse_aspect(spec["target_aspect"]) is None:
        raise ValueError("图规格 target_aspect 必须写成 宽:高，且在 1:3–3:1 之间")
    fig_id = spec.get("id")
    if fig_id is not None and (not isinstance(fig_id, str) or not re.fullmatch(r"[A-Za-z0-9_\-]{1,64}", fig_id)):
        raise ValueError("图规格 id 只能用字母、数字、下划线和连字符")
    palette = spec.get("palette")
    if palette is not None and palette != "mono" and (
            not isinstance(palette, list) or not 1 <= len(palette) <= 4
            or not all(isinstance(c, str) and _HEX_COLOR.fullmatch(c) for c in palette)):
        raise ValueError('图规格 palette 只能是 "mono" 或 1–4 个 #RRGGBB 颜色（第一个是强调色）')
    return {**spec, "description": desc.strip(), "strings": clean}


# ============================================================
# 版式库（grammar）与本篇版式风格（house style）
# ============================================================
# 2026-10-10 实验（修改记录 2026-10-10_1057）：同一份"编号阶段 + 圆角卡片 + 插画 + 小字"
# 的风格合同让 4 张图一个模子。顶会主图（FigureForge 画廊 3452 张）的共性是"版式跟着方法逻辑走"，
# 所以 method 图按内容从下面的版式库选 grammar，造型细节（标号、分隔、圆角、箭头、线宽、填充、字体、
# 配色）由本篇 house style 统一：同一篇一致，不同论文、不同用户各不相同。
# house style 的种子就是 paper-figure-html Step 1 的 SEED（工作区名的 cksum），旋钮位段对齐那边的
# TONE/RADIUS/ARROW/SECT/NUMBER/INK/GENRE_SEED，所以退回 HTML 画的图在同一篇里造型也相近。

FIGURE_GRAMMARS = {
    "decomposition": (
        "Visual-equation layout: the observed object is shown once, followed by \"≈\" or \"=\" and a row of "
        "equal-size component tiles joined by \"+\" (or \"×\"), all on one baseline and vertically centred; each "
        "tile is a miniature of the same object showing one component; labels sit centred under the tiles."),
    "constraint_plane": (
        "Concept-plot layout: one clean coordinate plane (thin black L-shaped axes, axis labels only) in which "
        "each source of information or constraint is a band or region with straight or smooth edges and a pale "
        "flat fill; where they overlap, a small solid shape marks the joint estimate or optimum; a dashed outline "
        "may show the prior or the feasible set; other groups feed into or read off this plane."),
    "model_optimizer_tiers": (
        "Two-tier layout: the upper tier shows the model or simulator; the lower tier is a full-width, very light "
        "gray band holding the optimizer or algorithm, with the decision variables at its left and the objective "
        "at its right; thin vertical arrows connect the tiers, one going up and one coming down, each with a "
        "short label."),
    "nested_scales": (
        "Nested-scale layout: the fast process sits inside a dashed rounded region labelled with its index range "
        "(for example each day), the slow process in another region labelled with its own range (for example "
        "each year) that contains or follows it; one feedback arrow returns from the slow scale to the fast one."),
    "forward_inverse": (
        "Forward-inverse layout: the forward model runs left to right with solid arrows from parameters to "
        "predicted observations; the measured data enter from below; a comparison step joins them; the inverse or "
        "fitting step returns to the parameters with dashed accent-coloured arrows; estimates are read off at the "
        "end."),
    "stage_strip": (
        "Stage-strip layout: three to five stages from left to right separated by whitespace (no cards, no "
        "numbered badges); each stage shows a small, real-looking visual of the data or object at that stage "
        "(mini plot, map, matrix or profile), and each arrow between stages carries the operation as a short math "
        "or word label."),
    "iteration_loop": (
        "Loop layout: the steps of the iteration sit on one closed loop with all arrows going the same way round; "
        "the convergence test is a small diamond or a labelled gate on the loop; the initialisation enters the "
        "loop from outside and one exit arrow leaves it towards the result."),
    "causal_loop": (
        "Causal-loop layout in system-dynamics notation: variables are plain text nodes or small stock boxes; "
        "links are curved arrows, each with a small \"+\" or \"−\" near its head; every feedback loop has a small "
        "circular-arrow marker with its loop name at its centre; policy inputs enter with dashed arrows."),
    "side_by_side": (
        "Side-by-side comparison: two or three settings are drawn next to each other with identical or mirrored "
        "internal layouts; what changes between them is in the accent colour and what stays the same is gray; a "
        "shared element sits between them and connects to each."),
    "rank_slope": (
        "Slope-chart layout: two or three vertical axes, one per condition; the same items are listed at their "
        "rank positions on every axis with small dots and joined across axes by straight lines, so crossings show "
        "rank changes; one or two highlighted lines in the accent colour, all other lines gray."),
    "network_map": (
        "Network layout: sites or agents are nodes placed like a simple schematic map; links are thin lines or "
        "flows whose width or dash style encodes their role; where described, an outline ring shows a node's "
        "capacity and an inner filled disc its load; each node carries a short label next to it."),
    "timeline": (
        "Timeline layout: one horizontal time axis with an arrowhead; events are short ticks with labels; "
        "durations are brackets above or below the axis; states at chosen times may sit above the axis as small "
        "aligned drawings."),
    "layered_stack": (
        "Layered layout: three to five horizontal layers stacked from top to bottom (for example data, models, "
        "solution, answers), each a labelled band holding its items, with arrows only where one item really "
        "feeds another."),
    "tree_branch": (
        "Branching layout: the root (problem or data) on the left splits into branches to the right; each branch "
        "is one model or sub-problem and ends in the output it answers; branches rejoin only where results are "
        "really combined."),
    "matrix_grid": (
        "Grid layout: rows and columns of a scenario or comparison grid with short header labels; each cell holds "
        "a small glyph (mini plot, symbol or shape) rather than text; at most one row or column is highlighted in "
        "the accent colour."),
    "zoom_inset": (
        "Inset layout: one overview drawing of the object with one or two magnified circular or rectangular insets "
        "linked to their locations by thin lines; the mechanism is drawn inside the insets."),
    # 10-10 画廊 216 张构图普查后补的 6 种（普查结论见修改记录 2026-10-10_1226"续"一节）
    "pipeline_row": (
        "Single-row pipeline: one main line runs from left to right through four to seven modules (cards, data "
        "glyphs or small illustrations) joined by arrows; side inputs enter from above or below; the whole figure "
        "is one connected diagram, not separate panels."),
    "snake_flow": (
        "Snake layout: a long process runs left to right along the top row, turns down at the right edge and "
        "continues along a second row, so it reads as one continuous path; a feedback arrow may cut back through "
        "the middle."),
    "hub_spoke": (
        "Hub layout: the core model or system sits large in the centre; its inputs, components or uses sit around "
        "it, left and right or in a ring, each joined to the hub by a short arrow; satellites of one kind share a "
        "colour."),
    "hero_callouts": (
        "Hero layout: one large flat illustration of the real object or scene fills a third to a half of the "
        "canvas; thin callout lines lead from its parts to the cards, glyphs and formulas that explain the method "
        "around it."),
    "fan_out_in": (
        "Fan layout: one source fans out into several parallel branches or components of equal size (spread on a "
        "gentle arc or stacked in a column), which then converge into the result or results, so the split and the "
        "merge are both obvious."),
    "multi_panel": (
        "Multi-panel layout: two to four panels of different kinds (for example a schematic, a mini plot and a "
        "map) arranged in a grid or an L shape, each with its panel letter and a short title; this is the only "
        "layout that uses panel letters."),
}

# 构图族：同一篇里每张 AI 图的族都不一样（出图前按本篇账本拦），字母面板只属于 panels 族
GRAMMAR_FAMILY = {
    "decomposition": "fan", "fan_out_in": "fan",
    "constraint_plane": "plot", "rank_slope": "plot",
    "model_optimizer_tiers": "bands", "layered_stack": "bands",
    "nested_scales": "nest", "zoom_inset": "nest",
    "forward_inverse": "loop", "iteration_loop": "loop", "causal_loop": "loop",
    "stage_strip": "columns", "side_by_side": "contrast", "network_map": "map", "timeline": "timeline",
    "tree_branch": "tree", "matrix_grid": "grid", "pipeline_row": "flow", "snake_flow": "flow",
    "hub_spoke": "hub", "hero_callouts": "hero", "multi_panel": "panels",
}
FAMILY_LABELS = {
    "fan": "汇聚/发散", "plot": "示意坐标图", "bands": "上下分带", "nest": "总图+放大/嵌套", "loop": "闭环",
    "columns": "并列分栏", "contrast": "对照", "map": "示意地图", "timeline": "时间线", "tree": "树/层级",
    "grid": "网格", "flow": "流水线", "hub": "中心辐射", "hero": "主插画", "panels": "多面板拼版",
}
# 面板标号：(a) xxx、(A) xxx，或本篇 panel_label 的 "a  xxx" / "A  xxx"（两个空格）；"E environment" 这类一空格的不算
_LETTERED_TITLE = re.compile(r"^\([a-hA-H]\)\s|^[a-hA-H]\s{2,}\S")


def composition_problem(spec: dict, ledger_rows=(), house: dict | None = None) -> str | None:
    """method 图的构图规则；违反时返回给规格作者看的说明（出图前就拦，不发请求、不算次数）。

    1. 只有 multi_panel 分字母面板，其余构图画成一整张连贯的图（画廊 216 张里带字母分栏的只占 24.5%）；
    2. 同一篇里每张 AI 图的构图族都不一样：账本里别的图（spec_id 不同）出图成功用过的族，这张不能再用；
    3. 有本篇 house style 时（软件里总有），规格要列出内容合适的全部构图 candidates，grammar 必须是其中
       按本篇 grammar_order 排第一、且本篇还没用过的那一族——不同用户种子不同，同一张图就会选出不同构图；
       不这样拦，写规格的模型会总挑自己顺手的那一两种（10-10 用户："架构用户都不能重复最好"）。
    """
    if spec.get("kind") != "method" or spec.get("grammar") not in GRAMMAR_FAMILY:
        return None
    family = GRAMMAR_FAMILY[spec["grammar"]]
    lettered = [s for s in spec.get("strings", []) if _LETTERED_TITLE.match(s)]
    if lettered and family != "panels":
        return (f"构图 {spec['grammar']} 画成一整张连贯的图，不分字母面板；把这些标号去掉或改成不带字母的小标题："
                + " | ".join(lettered[:4]) + "。只有 multi_panel 才用 (a)(b)")
    used = {}
    for row in ledger_rows:
        if (isinstance(row, dict) and row.get("ok") and row.get("spec_id") != spec.get("id")
                and row.get("grammar") in GRAMMAR_FAMILY):
            used.setdefault(GRAMMAR_FAMILY[row["grammar"]], (row.get("spec_id"), row["grammar"]))
    if house is not None:
        cands = spec.get("candidates")
        if not cands:
            return ("规格要写 \"candidates\"：内容合适的全部构图（至少 3 个，尽量跨不同构图族），"
                    "工具按本篇 grammar_order 从中挑；grammar 写挑中的那个")
        expected = next((g for g in validate_house_style(house)["grammar_order"]
                         if g in cands and GRAMMAR_FAMILY[g] not in used), None)
        if expected is None:
            return "candidates 里的构图族本篇都用过了：再补几个内容合适、且本篇没用过的构图族"
        if spec["grammar"] != expected:
            return (f"按本篇偏好顺序，candidates 里应选 {expected}（「{FAMILY_LABELS[GRAMMAR_FAMILY[expected]]}」）："
                    "把 grammar 改成它，并按它的画法重写 description")
        return None
    if family in used:
        spec_id, grammar = used[family]
        return (f"本篇的 {spec_id} 已经用了「{FAMILY_LABELS[family]}」构图（{grammar}），"
                "同一篇不重复：按内容换一个别的构图族的 grammar")
    return None

HOUSE_STYLE_VERSION = 3   # 第 3 版（10-15）：丰满画法加点睛色 + 分区底色，功能色中高饱和；第 2 版文件照旧按原画法出图
# 10-10 用户嫌第一版接入的线稿"没有那么丰满，不像画廊那些"：三档都改成画廊主图常见的丰满画法（种子位不变）
_HS_FILLS = (
    "Tinted-zone look: each group of elements sits on a soft tinted rounded zone with a slightly darker header "
    "strip; the items inside are white cards with thin coloured outlines.",
    "Card look: elements are white rounded cards with thin coloured outlines and a coloured top edge; the "
    "background stays white; exactly one focal element is filled with the accent colour.",
    "Framed-section look: each group is enclosed by a medium-weight coloured outline with its title on a small "
    "coloured tab; inside, pale tinted cards and colourful glyphs.",
)
# 用户可选两种画法（10-10 用户："可以选择两种风格，一个是丰满的一个是之前的那种"）：
#   rich  丰满：浅色分区、领域小插画、彩色数据小图形、胶囊标签（默认）
#   clean 简洁：午前接入时的线稿画法，原话保留；构图规则（不分字母面板、同篇构图族不重复）两种都适用
HOUSE_LOOKS = ("rich", "clean")
_HS_FILLS_CLEAN = (
    "Line-art look: white fills everywhere; colour appears only in thin strokes, small markers and the single "
    "highlighted element.",
    "Outlined look: shapes are white with thin outlines; elements on the main thread have accent-coloured "
    "outlines, all others gray outlines.",
    "Tinted-group look: related elements sit on pale tinted regions without borders; exactly one focal element "
    "is filled with the accent colour.",
)
# 第 3 版丰满画法：分组的底由 _rich_style_text 的分区行负责，这里只管分组里的方框（不用 card 一词：出图模型会画成带投影的界面卡片）
_HS_FILLS_V3 = (
    "Boxes: white boxes with thin outlines and a slightly darker header strip in their category colour.",
    "Boxes: white boxes with thin coloured outlines and a thin coloured top edge; exactly one focal element is "
    "filled with the accent colour.",
    "Boxes: lightly tinted boxes with thin outlines and titles on small coloured tabs; colourful glyphs inside.",
)
# 黑白配色（PALETTE 为 "mono"）时规格里的颜色词照样写（规程不分配色），这里统一换成灰度。
# 10-15：以前只说"只用黑白灰"，规格写 the highlight colour / the third colour 时出图模型只能自己猜
_MONO_ROLE_WORDS = (
    "The description's colour words map to grays: 'the accent colour' is black, 'the secondary colour' is dark "
    "gray (#555555), 'the third colour' is mid gray (#8C8C8C) and 'the highlight colour' is a black fill with "
    "white text or a thick black outline")
# 第 3 版丰满画法的黑白版方框写法（和 _HS_FILLS_V3 按同一个 fill 旋钮取）
_HS_FILLS_V3_MONO = (
    "Boxes: white boxes with thin black outlines and a light gray header strip.",
    "Boxes: white boxes with thin dark-gray outlines; exactly one focal element is filled with black and carries "
    "white text.",
    "Boxes: very light gray boxes with thin outlines and titles on small dark-gray tabs; gray glyphs inside.",
)
_HS_CORNERS = ("square corners on every box", "slightly rounded corners (about 3 px)",
               "rounded corners (about 8 px)", "pill-shaped small node boxes, square-cornered large regions")
_HS_CONNECTORS = (
    "straight thin arrows with small solid triangular heads",
    "straight medium-weight arrows with solid triangular heads",
    "gently curved thin arrows with small open V-shaped heads",
    "orthogonal connectors with right-angle bends and small solid heads",
)
# {unit}：multi_panel 是 panel，其余构图是 group（一整张图里的分组，不带字母）
_HS_SEPARATORS = (
    "{unit}s separated by generous whitespace only",
    "{unit}s separated by thin light-gray dashed lines",
    "each {unit} title preceded by a short thin {bar} vertical bar; whitespace between {unit}s",
)
_HS_TITLES = (
    "{unit} titles in bold sans-serif (Helvetica-like)",
    "{unit} titles in bold serif (Times-like), all other labels sans-serif",
    "{unit} titles in semibold sans-serif with a thin hairline rule under each title",
)
_HS_STROKES = ("hairline strokes (about 0.6 pt)", "thin strokes (about 0.8 pt)", "regular strokes (about 1 pt)")
_HS_INKS = ("#1F1F1F", "#24292E", "#2E2A26", "#1E2B33")
# 面板标题怎么写：规格作者按本篇格式把标号写进 strings（核对时括号与大小写不影响比对）
_HS_LABELS = ("(a) {title}", "a  {title}", "A  {title}")
_HS_KNOBS = {"fill": len(_HS_FILLS), "corners": len(_HS_CORNERS), "connector": len(_HS_CONNECTORS),
             "separator": len(_HS_SEPARATORS), "label": len(_HS_LABELS), "title": len(_HS_TITLES),
             "stroke": len(_HS_STROKES), "ink": len(_HS_INKS)}

METHOD_AVOID = (
    "STRICTLY AVOID: panel letters such as (a), (b), A or 1 unless the layout above asks for them, numbered circle "
    "badges for steps unless the description asks for them, a row of identical rounded cards, app-style cards with "
    "drop shadows or glossy fills, neon colours, saturated background zones, generic clip-art or stock icons that "
    "the description does not name (gears, documents, magnifiers, light bulbs, map pins, robots, computers, brains, rockets), 3-D, "
    "isometric or perspective views, drop shadows, glow, decorative gradients, textures, photorealism, hand-drawn "
    "or sketchy lines, watercolor, blurred or smudged patches, emoji, logos, a title at the top of the image, a "
    "frame around the whole image, long sentences, double-headed arrows that were not asked for, and any text "
    "that is not in the list.\n"
)
METHOD_AVOID_CLEAN = (
    "STRICTLY AVOID: panel letters such as (a), (b), A or 1 unless the layout above asks for them, numbered circle "
    "badges for steps, a row of identical rounded cards, large pastel boxes around every element, icons or "
    "clip-art (gears, documents, magnifiers, light bulbs, map pins, people, robots, computers, shoes), 3-D, "
    "isometric or perspective views, drop shadows, glow, decorative gradients, textures, photorealism, hand-drawn "
    "or sketchy lines, watercolor, blurred or smudged patches, emoji, logos, a title at the top of the image, a "
    "frame around the whole image, long sentences, double-headed arrows that were not asked for, and any text "
    "that is not in the list.\n"
)


def _hsl_hex(h_deg: float, s: float, l: float) -> str:
    """与 plot_utils.paper_accent / paper-figure-html 的 hsl(H,S%,L%) 同一换算。"""
    r, g, b = colorsys.hls_to_rgb((h_deg % 360) / 360.0, l, s)
    return "#%02X%02X%02X" % (round(r * 255), round(g * 255), round(b * 255))


def _hex_hls(color: str) -> tuple[float, float, float]:
    """#RRGGBB → (色相度数, 明度, 饱和度)。"""
    r, g, b = (int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h * 360, l, s


def _hue_gap(a: float, b: float) -> float:
    d = abs(a - b) % 360
    return min(d, 360 - d)


_HS_SECONDARY_SL = ((0.38, 0.44), (0.45, 0.48), (0.52, 0.52))
# 第三色比副色再收一档：10-10 实测 0.52/0.52 落在绿色上是荧光绿（#61C445），顶刊配色要沉稳
_HS_THIRD_SL = ((0.30, 0.40), (0.36, 0.44), (0.42, 0.48))
# 10-15 画廊提取（画廊 40 张高分图逐张看 + 1633 张同类图量化 + PaperBanana 的 NeurIPS 2025 方法图风格指南）：
# 我们的丰满图颜色全压在低饱和中明度（彩色 C* 中位 22，鲜艳色只占画面 0.2%，画廊高分图 4.3%），图与图一个模子。
# 顶会方法图的配色结构是：很淡的多色分区底 + 中高饱和的功能色 + 高饱和只给结果/最终输出。丰满画法改用这个结构：
# 色相规则不变（主色色相 = 本篇 PALETTE，和流程图步骤的 H0 同源；副色、第三色仍取本篇数据图配色），
# 饱和度/明度改成中高饱和、按种子三档（并保证白底对比度），另加点睛色和一套分区底色（或白底 + 彩色虚线框）。
_HS_RICH_ACCENT_SL = ((0.58, 0.40), (0.52, 0.33), (0.64, 0.45))
_HS_RICH_SECONDARY_SL = ((0.60, 0.48), (0.66, 0.45), (0.55, 0.40))
_HS_RICH_THIRD_SL = ((0.50, 0.44), (0.56, 0.48), (0.46, 0.38))
_HS_ZONE_SETS = (
    ("#FBF5E6", "#E9F2FB", "#E7F4EE", "#F2EBF7"),   # 奶油 / 冰蓝 / 薄荷 / 淡紫（PaperBanana 指南的四种分区底）
    ("#FDF0E6", "#E8F0F7", "#EDF5E5", "#F9E9EE"),   # 淡桃 / 雾蓝 / 淡鼠尾草 / 淡玫瑰
    ("#FFF7DA", "#E6F1FA", "#EFE9F8", "#E4F3F2"),   # 柠檬 / 天蓝 / 丁香 / 淡水绿
    ("#F3F3F0", "#E9EFF5", "#F5EEE4", "#ECF2E8"),   # 暖灰 / 石板蓝 / 沙色 / 苔绿（沉稳）
    ("#F5EFFA", "#E9F5EF", "#FFF2E4", "#E9EFFA"),   # 淡紫罗兰 / 薄荷 / 杏色 / 长春花蓝
    ("#F0F6EA", "#FDF1EA", "#EBF0F7", "#F8F1DE"),   # 开心果 / 淡桃 / 雾霾蓝 / 麦色
)
_HS_ZONE_STYLES = ("zones", "zones", "dashed")   # 约三分之二淡彩分区，三分之一白底 + 彩色虚线框（指南：约两成）
_HS_HIGHLIGHTS = ((32.0, 0.88, 0.52), (6.0, 0.80, 0.50), (48.0, 0.90, 0.50), (336.0, 0.78, 0.50),
                  (152.0, 0.62, 0.36), (268.0, 0.55, 0.52))   # 点睛色（色相, 饱和度, 明度）：橙、朱红、金黄、品红、祖母绿、紫罗兰；
# 绿、紫按各自的饱和度明度压住，不出荧光色；
# 与主色、副色、第三色都差 ≥40° 的里按种子挑（只取第一个时，蓝橙配色的论文总落到品红，又撞色；
# 10-15 第四轮 B 题只看前两色时，点睛橙和第三色橙棕撞成一类，图例上分不清"关键输出"和第三类）


def _house_palette(palette, data_colors, seed: int = 0) -> dict:
    """本篇 PALETTE token（[强调色, 浅底] 或 "mono"）+ 数据图配色 → 强调色、副色、浅底、深色。

    副色取数据图配色里第一个与强调色色相相差 ≥40° 的饱和色，饱和度/明度按种子在三档里取，所以示意图和
    本篇数据图同一套颜色、不同论文各不相同；数据图里找不到就取强调色的近补色。
    强调色不在这里改：它与 paper-figure-html 的 --accent 同源（plot_utils.paper_accent），退回 HTML 的图要同色。
    """
    if palette == "mono" or palette is None:
        return {"mode": "mono"}
    if (not isinstance(palette, list) or not palette
            or not all(isinstance(c, str) and _HEX_COLOR.fullmatch(c) for c in palette)):
        raise ValueError('palette 必须是 "mono" 或 [强调色, 浅底]（#RRGGBB）')
    accent = palette[0].upper()
    h_acc, _, _ = _hex_hls(accent)
    tint = palette[1].upper() if len(palette) > 1 else _hsl_hex(h_acc, 0.40, 0.95)
    h_sec = None
    for color in data_colors or []:
        if not (isinstance(color, str) and _HEX_COLOR.fullmatch(color)):
            continue
        h, l, s = _hex_hls(color)
        if s >= 0.2 and 0.15 <= l <= 0.8 and _hue_gap(h, h_acc) >= 40:
            h_sec = h
            break
    if h_sec is None:
        h_sec = (h_acc + 160) % 360
    s_sec, l_sec = _HS_SECONDARY_SL[(seed // 223) % len(_HS_SECONDARY_SL)]
    h_third = _third_hue(h_acc, h_sec, data_colors)
    s_th, l_th = _HS_THIRD_SL[(seed // 229) % len(_HS_THIRD_SL)]
    return {"mode": "color", "accent": accent, "accent_tint": tint,
            "secondary": _hsl_hex(h_sec, s_sec, l_sec), "secondary_tint": _hsl_hex(h_sec, 0.40, 0.94),
            "third": _hsl_hex(h_third, s_th, l_th), "third_tint": _hsl_hex(h_third, 0.40, 0.94),
            "dark": _hsl_hex(h_acc, 0.45, 0.22)}


def _third_hue(h_acc: float, h_sec: float, data_colors=None) -> float:
    """第三色（丰满画法要三类颜色）：数据图配色里第一个与强调色、副色都相差 ≥40° 的饱和色；没有就在色相环上
    取离两者都最远的位置。"""
    for color in data_colors or []:
        if not (isinstance(color, str) and _HEX_COLOR.fullmatch(color)):
            continue
        h, l, s = _hex_hls(color)
        if s >= 0.2 and 0.15 <= l <= 0.8 and min(_hue_gap(h, h_acc), _hue_gap(h, h_sec)) >= 40:
            return h
    return max(((h_acc + d) % 360 for d in range(0, 360, 5)),
               key=lambda h: (min(_hue_gap(h, h_acc), _hue_gap(h, h_sec)), -h))


def _contrast_on_white(color: str) -> float:
    """WCAG 对比度（相对白底）。"""
    def lum(part: str) -> float:
        v = int(part, 16) / 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    y = 0.2126 * lum(color[1:3]) + 0.7152 * lum(color[3:5]) + 0.0722 * lum(color[5:7])
    return 1.05 / (y + 0.05)


def _readable(h: float, s: float, l: float, ratio: float) -> str:
    """hsl → 色号；白底对比度不到 ratio 就把明度往下压（黄、绿这类亮色相常要压），保证线条和字清楚。"""
    color = _hsl_hex(h, s, l)
    while _contrast_on_white(color) < ratio and l > 0.18:
        l -= 0.02
        color = _hsl_hex(h, s, l)
    return color


def _rich_palette(palette, data_colors, seed: int = 0) -> dict:
    """丰满画法第 3 版配色（10-15 画廊提取）：色相同 _house_palette（主色 = PALETTE 的色相，副色/第三色取本篇数据图配色），
    饱和度/明度改成中高饱和三档（主色白底对比度 ≥4.5、副色/第三色 ≥3）；加点睛色 highlight（只给最终输出/关键结果，
    色相与主色、副色、第三色都错开）、
    一套很淡的分区底色 zones（分组依次用）和分区方式 zone_style（淡彩分区 / 白底彩色虚线框）。"""
    base = _house_palette(palette, data_colors, seed)
    if base["mode"] == "mono":
        return base
    h_acc, h_sec, h_th = (_hex_hls(base[k])[0] for k in ("accent", "secondary", "third"))
    s_a, l_a = _HS_RICH_ACCENT_SL[(seed // 233) % len(_HS_RICH_ACCENT_SL)]
    s_s, l_s = _HS_RICH_SECONDARY_SL[(seed // 223) % len(_HS_RICH_SECONDARY_SL)]
    s_t, l_t = _HS_RICH_THIRD_SL[(seed // 229) % len(_HS_RICH_THIRD_SL)]
    ok = ([c for c in _HS_HIGHLIGHTS if min(_hue_gap(c[0], h_acc), _hue_gap(c[0], h_sec), _hue_gap(c[0], h_th)) >= 40]
          or [c for c in _HS_HIGHLIGHTS if min(_hue_gap(c[0], h_acc), _hue_gap(c[0], h_sec)) >= 40]
          or [_HS_HIGHLIGHTS[3]])   # 三色把合格的全占了才退到只看主色、副色
    h_hl, s_hl, l_hl = ok[(seed // 257) % len(ok)]
    return dict(base, accent=_readable(h_acc, s_a, l_a, 4.5), secondary=_readable(h_sec, s_s, l_s, 3.0),
                third=_readable(h_th, s_t, l_t, 3.0), highlight=_hsl_hex(h_hl, s_hl, l_hl),
                accent_tint=_hsl_hex(h_acc, 0.55, 0.94), secondary_tint=_hsl_hex(h_sec, 0.55, 0.94),
                third_tint=_hsl_hex(h_th, 0.50, 0.94), dark=_hsl_hex(h_acc, 0.50, 0.20),
                zones=list(_HS_ZONE_SETS[(seed // 241) % len(_HS_ZONE_SETS)]),
                zone_style=_HS_ZONE_STYLES[(seed // 251) % len(_HS_ZONE_STYLES)])


def house_style(seed: int, palette=None, data_colors=None, look: str = "rich") -> dict:
    """本篇版式风格。seed = paper-figure-html 的 SEED；同 seed、同配色输入必得同一结果（不用时间戳）。
    look = 用户选的画法（rich 丰满 / clean 简洁），只改填充、插画、配色段的写法，旋钮与构图偏好不变。"""
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("seed 必须是非负整数（工作区名的 cksum）")
    if look not in HOUSE_LOOKS:
        raise ValueError("look 只能是 rich（丰满）或 clean（简洁）")
    knobs = {
        "fill": seed % 3,                # = TONE
        "corners": (seed // 7) % 4,      # = RADIUS
        "connector": (seed // 11) % 4,   # = ARROW
        "separator": (seed // 17) % 3,   # = SECT
        "label": (seed // 41) % 3,       # ≈ NUMBER
        "title": (seed // 59) % 3,
        "stroke": (seed // 61) % 3,
        "ink": (seed // 113) % 4,        # ≈ INK
    }
    order = list(FIGURE_GRAMMARS)
    random.Random(seed // 127).shuffle(order)   # ≈ GENRE_SEED：同样合适的版式里，本篇先用哪个
    body = {"version": HOUSE_STYLE_VERSION, "seed": seed, "look": look, **knobs,
            "palette": (_rich_palette(palette, data_colors, seed) if look == "rich"
                        else _house_palette(palette, data_colors, seed)), "grammar_order": order,
            "panel_label": _HS_LABELS[knobs["label"]]}
    body["id"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    return body


def validate_house_style(house) -> dict:
    """读回 house_style.json 时校验：旋钮在范围内、颜色合法、版式顺序只含版式库里的 id。

    第 1 版文件（10-10 午前生成，没有第三色、版式库只有 16 种）就地升级：补第三色，把新版式按本篇种子
    排在原顺序后面；旋钮、强调色、副色都不变，所以同一篇前后出的图仍是一套风格。
    """
    if not isinstance(house, dict) or house.get("version") not in (1, 2, HOUSE_STYLE_VERSION):
        raise ValueError("house style 文件版本不对，请重新生成")
    for name, size in _HS_KNOBS.items():
        value = house.get(name)
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < size:
            raise ValueError(f"house style 的 {name} 不在范围内")
    pal = house.get("palette")
    if not isinstance(pal, dict) or pal.get("mode") not in ("color", "mono"):
        raise ValueError("house style 的 palette 无效")
    base = ("accent", "accent_tint", "secondary", "secondary_tint", "dark")
    if pal["mode"] == "color" and not all(isinstance(pal.get(k), str) and _HEX_COLOR.fullmatch(pal[k]) for k in base):
        raise ValueError("house style 的颜色无效")
    order = house.get("grammar_order")
    if not isinstance(order, list) or not order or not set(order) <= set(FIGURE_GRAMMARS):
        raise ValueError("house style 的 grammar_order 无效")
    if house.get("panel_label") not in _HS_LABELS:
        raise ValueError("house style 的 panel_label 无效")
    # 第 1 版文件是线稿时代生成的 → 简洁；第 2 版早期文件没有 look 字段 → 丰满（当时只有丰满）
    look = house.get("look", "clean" if house["version"] == 1 else "rich")
    if look not in HOUSE_LOOKS:
        raise ValueError("house style 的 look 只能是 rich 或 clean")
    if house.get("look") != look:
        house = dict(house, look=look)
    if house["version"] == 1:
        house = dict(house, version=HOUSE_STYLE_VERSION)
        if pal["mode"] == "color":
            h_third = _third_hue(_hex_hls(pal["accent"])[0], _hex_hls(pal["secondary"])[0])
            s_th, l_th = _HS_THIRD_SL[(int(house.get("seed", 0)) // 229) % len(_HS_THIRD_SL)]
            house["palette"] = dict(pal, third=_hsl_hex(h_third, s_th, l_th), third_tint=_hsl_hex(h_third, 0.40, 0.94))
        extra = [g for g in FIGURE_GRAMMARS if g not in order]
        random.Random(int(house.get("seed", 0)) // 127).shuffle(extra)
        house["grammar_order"] = list(order) + extra
    elif pal["mode"] == "color" and not all(
            isinstance(pal.get(k), str) and _HEX_COLOR.fullmatch(pal[k]) for k in ("third", "third_tint")):
        raise ValueError("house style 的第三色无效")
    if pal["mode"] == "color" and "zones" in pal:
        zones = pal.get("zones")
        if (not isinstance(zones, list) or len(zones) != 4
                or not all(isinstance(z, str) and _HEX_COLOR.fullmatch(z) for z in zones)
                or pal.get("zone_style") not in _HS_ZONE_STYLES
                or not (isinstance(pal.get("highlight"), str) and _HEX_COLOR.fullmatch(pal["highlight"]))):
            raise ValueError("house style 的分区底色或点睛色无效")
    return house


def house_in_use(path, fresh: dict):
    """本篇已经用 path 这份版式风格成功出过图时返回 (原文件内容, 出过几张)，再跑 token 块就保留它；否则返回 None。

    10-15：token 块每次都重新生成版式风格，软件中途升级（如第 2 版 → 第 3 版）时，已采用的旧画法图和新图会混在
    同一篇论文里。只认账本里成功出图的记录（背景示意图不用版式风格，不算）；用户改了画法、黑白/彩色或配色族
    （主色色相差 >12°）时照常换新。账本按规程放在版式风格文件旁边（_mcm_ai/AI_IMAGE_LEDGER.jsonl）。
    """
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        old = validate_house_style(raw)
    except (OSError, ValueError, TypeError):
        return None
    if raw.get("seed") != fresh["seed"] or old["look"] != fresh["look"]:
        return None
    po, pf = old["palette"], fresh["palette"]
    if po["mode"] != pf["mode"]:
        return None
    if pf["mode"] == "color" and _hue_gap(_hex_hls(po["accent"])[0], _hex_hls(pf["accent"])[0]) > 12:
        return None
    used = sum(1 for row in read_ledger_rows(path.parent / "AI_IMAGE_LEDGER.jsonl")
               if row.get("ok") is True and row.get("house_style") == raw.get("id")
               and row.get("style") != "paper-schematic")
    return (raw, used) if used else None


def house_summary(house: dict) -> str:
    pal = house["palette"]
    colors = ("mono" if pal["mode"] == "mono"
              else f"accent={pal['accent']} secondary={pal['secondary']} third={pal['third']} "
                   f"tints={pal['accent_tint']},{pal['secondary_tint']},{pal['third_tint']}"
                   + (f" highlight={pal['highlight']} zones={','.join(pal['zones'])} zone_style={pal['zone_style']}"
                      if pal.get("zones") else ""))
    knobs = " ".join(f"{k}={house[k]}" for k in _HS_KNOBS)
    return (f"HOUSE_STYLE id={house['id']} look={house.get('look', 'rich')} {knobs} {colors} "
            f"panel_label=\"{house['panel_label']}\" grammar_order={','.join(house['grammar_order'])}")


def _house_style_text(house: dict, palette=None, *, overview: bool = False, panels: bool = False) -> str:
    """house style → 提示词的 STYLE 段。palette 是图规格自带的 token，优先于 house 的强调色（"mono" 则全黑白）。

    panels=True 只给 multi_panel：分字母面板；其余构图一律写成"一整张连贯的图、不带面板字母"。
    """
    raw_version = house.get("version") if isinstance(house, dict) else None   # 第 1 版会被就地升级成第 3 版，先记下原版本
    house = validate_house_style(house)
    pal = dict(house["palette"])
    if palette == "mono":
        pal = {"mode": "mono"}
    elif isinstance(palette, list) and palette and pal.get("mode") == "color" and not (
            pal.get("zones") and _hue_gap(_hex_hls(palette[0])[0], _hex_hls(pal["accent"])[0]) <= 12):
        # 第 3 版丰满：图规格照规程抄的 PALETTE 是流程图公式的低饱和强调色；同色相时用本篇加深后的主色
        pal["accent"] = palette[0]
        if len(palette) > 1:
            pal["accent_tint"] = palette[1]
    ink = _HS_INKS[house["ink"]]
    mono = pal["mode"] == "mono"
    unit = "panel" if panels else "group"
    separator = _HS_SEPARATORS[house["separator"]].format(unit=unit, bar="black" if mono else "accent-coloured")
    titles = _HS_TITLES[house["title"]].format(unit=unit)
    what = ("an overview figure (\"Figure 1: overview of our approach\")" if overview
            else "a method figure")
    if panels:
        layout = f"- Panels: {separator}; {titles}; each panel letter sits at the top-left of its panel."
    else:
        layout = (f"- Composition: one connected diagram that follows the layout above, with no panel letters such "
                  f"as (a), (b), A or 1 anywhere; {separator}; {titles}, where the description gives titles.")
    if house["look"] == "clean":
        return _clean_style_text(house, pal, ink, what, layout)
    if pal.get("zones") or (mono and raw_version == HOUSE_STYLE_VERSION):
        return _rich_style_text(house, pal, ink, what, layout)
    lines = [
        f"STYLE: {what} drawn by the authors in Adobe Illustrator for a top-venue paper (Nature-family journals, "
        "NeurIPS, ICML, CVPR) and printed 6.5 inches wide. Rich, colourful and carefully finished, yet orderly; it "
        "must look like a real publication figure, not AI art, a poster, a slide or a marketing infographic.",
        f"- Pure white background; crisp flat vector shapes; {_HS_STROKES[house['stroke']]}; "
        f"{_HS_CORNERS[house['corners']]}.",
        "- " + _HS_FILLS[house["fill"]],
        layout,
        f"- Connectors: {_HS_CONNECTORS[house['connector']]}, colour-coded by meaning. Every arrow has exactly one "
        "arrowhead, at its destination end, unless the description explicitly asks for a two-way arrow; feedback "
        "or secondary links are dashed.",
        f"- Text: small sans-serif labels in ink {ink}; all math in italic serif like LaTeX (Computer Modern); "
        "every label readable at print size (about 7 pt or larger); no sentences.",
        # 10-10 实测：画成带森林雪山的小风景时会被判"照片感 / 3D"，所以写死成图标式小插画
        "- Pictures: the real objects named in the description are small flat pictogram-style illustrations (two or "
        "three flat colours, thin dark outlines, a dozen simple shapes at most; no scenery, no shading, no realistic "
        "detail; one consistent style), each placed next to the element it explains; no generic icons.",
        "- Data appear as colourful glyphs (mini-plots, cell strips, bars, heatmap tiles): thin L-shaped axes with "
        "axis labels only; no ticks, no tick numbers, no grids, no legend boxes, no colour bars.",
        "- Solvers and operations appear as pill-shaped tags; key formulas sit in small pale callout boxes.",
    ]
    if mono:
        lines.append("- Colour: black, white and grays only; tell categories apart by line style (solid, dashed, "
                     "dotted), hatching or line weight, never by colour. " + _MONO_ROLE_WORDS + ".")
        lines.append("- Shading, only where the description asks for it: one ramp from white to black.")
    else:
        lines.append(f"- Colour: accent {pal['accent']} for the main thread and the focal element; secondary "
                     f"{pal['secondary']} and third {pal['third']} for the other categories named in the "
                     f"description; pale fills {pal['accent_tint']}, {pal['secondary_tint']} and "
                     f"{pal['third_tint']}; text and outlines ink {ink}; everything else grays. The same colour "
                     "always means the same thing everywhere in the figure. If the description names 'the highlight "
                     f"colour', use the accent {pal['accent']} on that element.")
        lines.append(f"- Heatmaps or density shading, only where the description asks for them: one sequential "
                     f"ramp from white through {pal['accent']} to {pal['dark']}.")
    lines.append("- Fill the canvas evenly with no large empty areas, keeping clear gutters between groups.")
    return "\n".join(lines) + "\n"


def _clean_style_text(house: dict, pal: dict, ink: str, what: str, layout: str) -> str:
    """简洁画法（clean）：午前接入时的线稿原话，只把面板一行换成构图规则那一行。"""
    lines = [
        f"STYLE: {what} drawn by the authors in Adobe Illustrator for a top-venue paper (Nature-family journals, "
        "NeurIPS, ICML) and printed 6.5 inches wide. It must look like a real publication figure, not AI art, "
        "a poster, a slide or a marketing infographic.",
        f"- Pure white background; crisp flat vector shapes; {_HS_STROKES[house['stroke']]}; "
        f"{_HS_CORNERS[house['corners']]}.",
        "- " + _HS_FILLS_CLEAN[house["fill"]],
        layout,
        f"- Connectors: {_HS_CONNECTORS[house['connector']]}. Every arrow has exactly one arrowhead, at its "
        "destination end, unless the description explicitly asks for a two-way arrow; feedback or secondary "
        "links are dashed.",
        f"- Text: small sans-serif labels in ink {ink}; all math in italic serif like LaTeX (Computer Modern); "
        "every label readable at print size (about 7 pt or larger); no sentences.",
        "- Mini-plots: thin L-shaped axes with axis labels only; no ticks, no tick numbers, no grids, no legend "
        "boxes, no colour bars.",
        "- Pictures: only flat outline drawings of the real objects named in the description; no generic icons.",
    ]
    if pal["mode"] == "mono":
        lines.append("- Colour: black, white and grays only; tell categories apart by line style (solid, dashed, "
                     "dotted), hatching or line weight, never by colour. " + _MONO_ROLE_WORDS + ".")
        lines.append("- Shading, only where the description asks for it: one ramp from white to black.")
    else:
        lines.append(f"- Colour: accent {pal['accent']} for the main thread and the single highlight; secondary "
                     f"{pal['secondary']} only for the one contrasting category named in the description; pale "
                     f"fills {pal['accent_tint']} and {pal['secondary_tint']}; everything else ink {ink} and grays. "
                     "The same colour always means the same thing everywhere in the figure. If the description names "
                     f"'the highlight colour', use the accent {pal['accent']}; if it names 'the third colour', use a "
                     "mid gray (#8C8C8C).")
        lines.append(f"- Heatmaps or density shading, only where the description asks for them: one sequential "
                     f"ramp from white through {pal['accent']} to {pal['dark']}.")
    return "\n".join(lines) + "\n"


def _rich_style_text(house: dict, pal: dict, ink: str, what: str, layout: str) -> str:
    """丰满画法第 3 版（10-15 画廊提取 + PaperBanana NeurIPS 2025 方法图风格指南）：
    很淡的多色分区底 + 中高饱和功能色 + 点睛色只给结果；印刷式平面；靠描述里的内容撑满，不加装饰。
    黑白配色（PALETTE 为 "mono"）同一套画法，颜色换成灰度：分区是浅灰底或灰色虚线框（比例同彩色），颜色词映射成灰度。"""
    mono = pal["mode"] == "mono"
    seed = house.get("seed")
    seed = seed if isinstance(seed, int) and not isinstance(seed, bool) and seed >= 0 else 0
    zone_style = _HS_ZONE_STYLES[(seed // 251) % len(_HS_ZONE_STYLES)] if mono else pal.get("zone_style")
    if mono and zone_style == "dashed":
        ground = ("- Groups: white background; each group is enclosed by a thin dashed gray border; a title, when the "
                  "group has one, is in black.")
    elif mono:
        ground = ("- Groups: each group sits on its own very light gray zone (#F4F4F4 or #ECECEC, alternating between "
                  "neighbouring groups); zone shading is background only and never carries meaning.")
    elif zone_style == "dashed":
        ground = ("- Groups: white background; each group is enclosed by a thin dashed border in the colour of the "
                  "category it belongs to (gray when it has none); a title, when the group has one, is in that colour.")
    else:
        ground = (f"- Groups: each group sits on its own very pale zone; use these zone colours for successive "
                  f"groups: {', '.join(pal['zones'])}. Zone colours are backgrounds only and never carry meaning.")
    # 10-15 第四轮：分区让出图模型自己给每列编标题（多出规格之外的字被核对拦下），分区比内容大一圈留成整列空白
    ground += (" A group has a title only when the description names one; never invent group titles. Each zone or "
               "border wraps closely around what it holds, with no large empty part.")
    arrow_tint = "gray shade or dash style" if mono else "category colour"
    pictures = "black, white and two or three grays" if mono else "two or three flat colours"
    glyphs, cells = ("small gray glyphs", "small shaded cells") if mono else ("small colourful glyphs", "small colour cells")
    if mono:
        colour = [
            "- Colour: black, white and grays only, no hue anywhere. " + _MONO_ROLE_WORDS + ", in one or two small "
            "spots; where categories must be told apart, also use line style (solid, dashed, dotted) or hatching; "
            f"text ink {ink}. The same shade always means the same thing everywhere in the figure.",
            "- Heatmaps or density shading, only where the description asks for them: one ramp from white to black.",
        ]
    else:
        colour = [
            f"- Colour: functional colours carry meaning. Accent {pal['accent']} for the main model and the main "
            f"thread; secondary {pal['secondary']} and third {pal['third']} for the other categories named in the "
            f"description (outlines, header text, glyph fills, small tags); their light fills {pal['accent_tint']}, "
            f"{pal['secondary_tint']} and {pal['third_tint']} only inside small elements; the vivid highlight "
            f"{pal['highlight']} only on the final output or the single key result that the description marks with the "
            f"highlight colour, in one or two small spots; text ink {ink}; everything else grays. The same colour "
            "always means the same thing everywhere in the figure.",
            f"- Heatmaps or density shading, only where the description asks for them: one sequential ramp from white "
            f"through {pal['accent']} to {pal['dark']}.",
        ]
    lines = [
        f"STYLE: {what} drawn by the authors in Adobe Illustrator for a top-venue paper (Nature-family journals, "
        "NeurIPS, ICML, CVPR) and printed 6.5 inches wide. Rich and information-dense yet orderly, like the method "
        "figures of top papers: every group is packed with labelled items, small data or structure glyphs and math "
        "symbols, and the main path reads at a glance. It must look like a real publication figure, not AI art, a "
        "poster, a slide, an app screen or a marketing infographic.",
        f"- Print-flat vector rendering: crisp solid fills and {_HS_STROKES[house['stroke']]}; absolutely no drop "
        f"shadows, glows, gradients, bevels or 3-D lighting on boxes, so every box looks printed on paper, not like "
        f"an app card; {_HS_CORNERS[house['corners']]}.",
        ground,
        "- " + (_HS_FILLS_V3_MONO if mono else _HS_FILLS_V3)[house["fill"]],
        layout,
        f"- Connectors: {_HS_CONNECTORS[house['connector']]}. The main flow is solid dark gray; feedback, optional "
        f"or auxiliary links are dashed; an arrow takes a {arrow_tint} only when the description gives it one. "
        "Where the description names what an arrow carries, write that short label on the arrow. Every arrow has "
        "exactly one arrowhead, at its destination end, unless the description explicitly asks for a two-way "
        "arrow.",
        f"- Text: small sans-serif labels in ink {ink}, module names bold and details regular; all math in italic "
        "serif like LaTeX (Computer Modern); every label at least 6.5 pt at print size; no sentences.",
        f"- Pictures: the real objects named in the description are small flat pictogram-style illustrations ({pictures}, "
        "thin dark outlines, a dozen simple shapes at most; no scenery, no shading, no realistic detail; one "
        "consistent style), each placed next to the element it explains; no generic icons.",
        f"- Data and structure appear as {glyphs}, only where the description asks for them: flat grids for "
        f"matrices, rows of {cells} for state vectors or sequences, a few offset stacked sheets for many samples, "
        "scenarios or time steps, cylinders for data stores, smooth distribution curves, heatmap tiles, small network "
        "graphs, map outlines, and mini-plots with thin L-shaped axes and axis labels only (no ticks, tick numbers, "
        "grids, legend boxes or colour bars).",
        "- Solvers and operations appear as pill-shaped tags; key formulas sit in small light callout boxes; a "
        "legend strip, when the description asks for one, runs along the bottom edge in a single row.",
        *colour,
        "- Density: a compact rectangular layout without dead zones; fill the space with the described content "
        "(labelled items, glyphs, formulas), never with decorative filler; do not add mini-plots, icons, badges or "
        "pictures that the description does not ask for; a box that the description gives only a title is a "
        "compact title box, with no empty body under the title.",
    ]
    return "\n".join(lines) + "\n"

def _avoid_for(house: dict | None) -> str:
    return METHOD_AVOID_CLEAN if house is not None and validate_house_style(house)["look"] == "clean" else METHOD_AVOID


def default_house_style() -> dict:
    """没有本篇 house style 时（单独调用、旧调用方）的中性默认：种子 0、旧合同的蓝橙两色。"""
    return house_style(0, ["#4C72B0", "#E4ECF6"], ["#DD8452"])


def build_spec_prompt(spec: dict, *, reference: bool = False, house: dict | None = None) -> str:
    """图规格 → 提示词：图意描述 + 版式 + 唯一允许的文字清单 + 风格合同 + 禁用清单。

    method 图（每问流程图、原理图）一律用 house style；architecture 总览图给了 house 就用 house，
    否则保持原合同；schematic 背景图保持原合同。
    """
    spec = validate_spec(spec)
    parts = [WIREFRAME_INSTRUCTION] if reference else []
    parts.append("FIGURE: " + spec["description"])
    ratio = parse_aspect(spec["target_aspect"]) if spec.get("target_aspect") and spec["kind"] != "method" else None
    if ratio is not None and ratio >= 1.3 and not reference:   # 照线框重绘时版面由线框定，不再叫它铺满
        # 10-15：总览图提示词里不写画布比例时，5 张里 3–4 张画成 1.5:1，补白到 2:1 后左右各空约 13%
        parts.append(f"CANVAS: one wide landscape figure about {round(ratio, 1):g} times as wide as it is tall; "
                     "spread the content over the full width, with no empty strip at the left or right edge.")
    if spec.get("grammar"):
        parts.append(f"LAYOUT GRAMMAR ({spec['grammar']}): {FIGURE_GRAMMARS[spec['grammar']]}")
    parts.append(PAPER_TEXT_RULE + "\n" + "\n".join(f'- "{s}"' for s in spec["strings"]))
    if spec["kind"] == "method":
        panels = GRAMMAR_FAMILY.get(spec.get("grammar")) == "panels"
        house = house or default_house_style()
        parts.append(_house_style_text(house, spec.get("palette"), panels=panels) + _avoid_for(house))
    elif spec["kind"] == "architecture" and house is not None:
        parts.append(_house_style_text(house, spec.get("palette"), overview=True) + _avoid_for(house))
    else:
        parts.append(_paper_style(spec["kind"], spec.get("palette")) + PAPER_AVOID)
    return "\n\n".join(parts)


def build_paper_prompt(user_prompt: str, style: str, *, reference: bool = False) -> str:
    """没有图规格时套用论文风格合同（不注入 legacy 的"配色自由搭配"后缀）。"""
    parts = [WIREFRAME_INSTRUCTION] if reference else []
    parts.append("FIGURE: " + user_prompt.strip())
    parts.append(PAPER_STYLES[style] + PAPER_AVOID)
    return "\n\n".join(parts)


def _multipart_body(fields: dict, file_field: tuple) -> tuple[bytes, str]:
    """images/edits 的 multipart/form-data 请求体（标准库手写，不依赖 requests）。"""
    import secrets
    boundary = "----PaperkitImage" + secrets.token_hex(12)
    out = BytesIO()
    for key, value in fields.items():
        out.write(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"))
        out.write(str(value).encode("utf-8"))
        out.write(b"\r\n")
    name, filename, data, mime = file_field
    out.write((f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
               f"Content-Type: {mime}\r\n\r\n").encode("utf-8"))
    out.write(data)
    out.write(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    return out.getvalue(), f"multipart/form-data; boundary={boundary}"


# ============================================================
# GPT Image API 调用（基于用户提供的 GPTImage2ChatProvider 代码）
# ============================================================

def _download_image_bytes(url: str) -> bytes:
    """Public HTTPS only, pinned DNS, no credentials/proxy/redirect to local services."""
    import ipaddress
    parsed = urlparse(url)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.fragment or parsed.port not in (None, 443) or len(url) > 8192
            or any(ord(c) <= 32 or ord(c) == 127 for c in url)):
        raise ValueError("图片下载地址无效")
    addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
        raise ValueError("图片下载地址不允许访问")
    # HTTPSConnection keeps the original Host and TLS SNI; connect to the vetted IP.
    conn = http.client.HTTPSConnection(parsed.hostname, 443, timeout=60, context=verified_tls_context())
    conn._create_connection = lambda address, timeout, source_address=None: socket.create_connection(
        (addresses[0][4][0], 443), timeout, source_address)
    try:
        conn.request("GET", parsed.path + ("?" + parsed.query if parsed.query else ""), headers={"User-Agent": "Paperkit-Image/1"})
        response = conn.getresponse()
        if response.status != 200:
            raise ValueError("图片下载失败；未重新发送生图请求")
        data = response.read(MAX_IMAGE_BYTES + 1)
        if not data or len(data) > MAX_IMAGE_BYTES:
            raise ValueError("图片为空或超过大小限制")
        return data
    finally:
        conn.close()


def _aspect_to_size(aspect_ratio: str) -> str:
    """把 skill 传入的宽高比映射成 OpenAI images API 的标准 size。
    gpt-image 系列支持 1024x1024 / 1024x1536(竖) / 1536x1024(横)。"""
    m = {
        "1:1": "1024x1024",
        "16:9": "1536x1024", "3:2": "1536x1024", "4:3": "1536x1024",
        "9:16": "1024x1536", "2:3": "1024x1536", "3:4": "1024x1536",
    }
    return m.get((aspect_ratio or "").strip(), "1024x1024")


def _call_gpt_image_api(
    api_base: str,
    api_key: str,
    prompt: str,
    aspect_ratio: str = "16:9",
    timeout: int = 180,
    *,
    config_snapshot=None,
    model: str | None = None,
    api_url_resolver=None,
    https_connection_factory=None,
    quality: str | None = None,
    size: str | None = None,
    reference_png: bytes | None = None,
    meta: dict | None = None,
) -> bytes:
    """调用已选 images-compatible 模型；一次派发，异常不代表未计费。

    仅关键字参数都是可选的：不传时请求体与旧版完全相同（编辑器沿用）。
    reference_png → /v1/images/edits（multipart）；meta 会被填入 endpoint/status/usage。
    """
    selected_model = image_model_id(model)
    endpoint = "/v1/images/edits" if reference_png is not None else "/v1/images/generations"
    if isinstance(meta, dict):
        meta["endpoint"] = endpoint
    if reference_png is not None and (not reference_png or len(reference_png) > _MAX_REFERENCE_BYTES):
        raise ValueError("参考图为空或超过 16 MiB")
    if api_key.startswith(("mxtp_", "mxcp_")):
        if reference_png is not None:
            # 本机代理只放行 images/generations；不发请求、不计费，交给调用方退回底稿。
            raise EditsUnavailable("当前是本机工具票据，参考图重绘（images/edits）不可用")
        from trusted_gateway_config import local_model_proxy_url
        parsed = urlparse(local_model_proxy_url("/v1/images/generations", api_key))
    else:
        # Account mode can supply a per-user provider credential plus a loopback
        # base instead of a short mxtp_ ticket; it has no signed gateway document,
        # so the signed-config path would fail with "签名配置缺失".  An injected
        # resolver (tests/callers) keeps priority over this fallback.
        try:
            from trusted_gateway_config import backend_loopback_url
        except ImportError:      # older embedded copy without this helper
            backend_loopback_url = lambda *_a, **_k: None
        direct = backend_loopback_url(api_base, endpoint) if api_url_resolver is None else None
        if direct:
            parsed = urlparse(direct)
        else:
            if api_url_resolver is None:
                from trusted_gateway_config import api_url as api_url_resolver
            parsed = urlparse(api_url_resolver(endpoint, snapshot=config_snapshot))
    host = parsed.hostname
    if not host:
        raise ValueError(f"API Base URL 格式错误: {api_base}")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    path = parsed.path

    # ⛔ OpenAI images API 的标准参数是 size（不是 aspect_ratio）；gpt-image 系列不支持
    #    response_format（传了会报 unknown parameter）。把宽高比映射成标准 size。
    size_value = validate_size(size) if size else _aspect_to_size(aspect_ratio)
    if quality is not None and quality not in ("low", "medium", "high", "xhigh", "max", "auto"):
        raise ValueError("quality 只能是 low/medium/high/xhigh/max/auto")
    if reference_png is not None:
        fields = {"model": selected_model, "prompt": prompt, "n": "1", "size": size_value}
        if quality:
            fields["quality"] = quality
        payload_bytes, content_type = _multipart_body(
            fields, ("image", "reference.png", reference_png, "image/png"))
    else:
        payload_dict = {
            "model": selected_model,
            "prompt": prompt,
            "n": 1,
            "size": size_value,
        }
        if quality:
            payload_dict["quality"] = quality
        payload_bytes = json.dumps(payload_dict).encode("utf-8")
        content_type = "application/json"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": content_type,
        "Content-Length": str(len(payload_bytes)),
    }

    conn = None
    try:
        if parsed.scheme == "https":
            # 默认 CERT_REQUIRED + check_hostname，防 MITM（端点已锁定且持有效证书）
            ctx = verified_tls_context()
            ctx.check_hostname = True
            ctx.verify_mode = ssl.CERT_REQUIRED
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2
            if https_connection_factory is None:
                from trusted_gateway_config import https_connection as https_connection_factory
            conn = https_connection_factory(host, port, timeout=timeout, context=ctx)
        else:
            conn = http.client.HTTPConnection(host, port, timeout=timeout)

        conn.request("POST", path, payload_bytes, headers)
        res = conn.getresponse()
        data = res.read(MAX_RESPONSE_BYTES + 1)
        if len(data) > MAX_RESPONSE_BYTES:
            raise ValueError("生图响应超过大小限制；未重新发送请求")

        if isinstance(meta, dict):
            meta["status"] = res.status
        if res.status != 200:
            raise Exception(f"生图服务返回 HTTP {res.status}；未自动重试，请先核对调用记录")

        response_json = json.loads(data.decode("utf-8"))
        if isinstance(meta, dict) and isinstance(response_json, dict) and isinstance(response_json.get("usage"), dict):
            meta["usage"] = response_json["usage"]
        data_list = response_json.get("data", []) if isinstance(response_json, dict) else []
        if not isinstance(data_list, list) or len(data_list) != 1 or not isinstance(data_list[0], dict):
            raise ValueError("生图响应格式无效")

        item = data_list[0]

        # 优先 base64
        if item.get("b64_json"):
            decoded = base64.b64decode(item["b64_json"], validate=True)
            if not decoded or len(decoded) > MAX_IMAGE_BYTES:
                raise ValueError("图片为空或超过大小限制")
            return decoded

        # URL 下载（兼容 data URL：某些 API 返回 data:image/png;base64,... 而非 HTTP 链接）
        if item.get("url"):
            url_val = item["url"]
            if not isinstance(url_val, str):
                raise ValueError("图片下载地址无效")
            if url_val.startswith("data:"):
                # data URL：直接解码 base64 部分
                if not re.match(r"^data:image/(?:png|jpeg|webp);base64,", url_val):
                    raise ValueError("图片 data URL 无效")
                decoded = base64.b64decode(url_val.split(",", 1)[1], validate=True)
                if not decoded or len(decoded) > MAX_IMAGE_BYTES:
                    raise ValueError("图片为空或超过大小限制")
                return decoded
            return _download_image_bytes(url_val)

        raise ValueError("响应中既无 b64_json 也无 url")

    except socket.timeout:
        raise Exception(f"请求超时（{timeout}秒），图片生成可能需要更长时间")
    except socket.gaierror:
        raise Exception("无法解析域名，请检查 GPT_IMAGE_BASE_URL")
    except ConnectionRefusedError:
        raise Exception("连接被拒绝，请检查 API 地址和端口")
    finally:
        if conn:
            conn.close()


# ============================================================
# PNG → PDF 转换
# ============================================================

def _png_to_pdf(png_path: str) -> str:
    """将 PNG 转为 PDF（LaTeX 需要），返回 PDF 路径。"""
    pdf_path = png_path.rsplit(".", 1)[0] + ".pdf"
    try:
        from PIL import Image
        img = Image.open(png_path)
        if img.mode == "RGBA":
            # PDF 不支持透明通道，合成白色背景
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[3])
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")
        img.save(pdf_path, "PDF", resolution=300)
        return pdf_path
    except ImportError:
        # PIL 不可用，直接用 PNG（LaTeX 也能用，只是不如 PDF）
        print("WARNING: PIL not available, skipping PNG→PDF conversion")
        return png_path


# ============================================================
# 补白到目标比例 / 用量账本 / AI 使用记录
# ============================================================

def trim_white_margins(png_path: str, keep: float = 0.02) -> tuple[int, int]:
    """裁掉四周大片纯白边（10-10 实测出图常在上下各留 15% 以上空白，放进论文白占版面），四周留 keep 的余量。

    只认接近纯白的像素为空白（任一通道与 255 相差 >6 即算内容），浅色底纹、浅色分区不会被裁；整张近乎全白时不动。
    """
    from PIL import Image, ImageChops
    img = Image.open(png_path).convert("RGB")
    r, g, b = ImageChops.difference(img, Image.new("RGB", img.size, (255, 255, 255))).split()
    bbox = ImageChops.lighter(ImageChops.lighter(r, g), b).point(lambda v: 255 if v > 6 else 0).getbbox()
    if not bbox:
        return img.size
    pad = round(max(img.size) * keep)
    box = (max(0, bbox[0] - pad), max(0, bbox[1] - pad), min(img.width, bbox[2] + pad), min(img.height, bbox[3] + pad))
    if box == (0, 0, img.width, img.height):
        return img.size
    img.crop(box).save(png_path, "PNG")
    return box[2] - box[0], box[3] - box[1]


def pad_to_aspect(png_path: str, ratio: float) -> tuple[int, int]:
    """GPT Image 不照办 size（实测 Flare 固定返回约 2.4:1）；只补白边、不裁剪，内容不变。"""
    from PIL import Image
    img = Image.open(png_path).convert("RGB")
    w, h = img.size
    if abs(w / h - ratio) / ratio < 0.01:
        return img.size
    new_w, new_h = (w, round(w / ratio)) if w / h > ratio else (round(h * ratio), h)
    canvas = Image.new("RGB", (new_w, new_h), (255, 255, 255))
    canvas.paste(img, ((new_w - w) // 2, (new_h - h) // 2))
    canvas.save(png_path, "PNG")
    return canvas.size


def read_ledger_rows(ledger_path) -> list:
    """读本篇用量账本（JSONL）；文件不存在或某行坏了就跳过，不影响出图。"""
    rows = []
    try:
        lines = Path(ledger_path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return rows
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def append_ledger(ledger_path: str, record: dict) -> None:
    """每次调用一行 JSON，导出成内部生图记录 _mcm_ai/AI_USE_IMAGES.md（论文里不写 AI 使用报告，队伍需要时照它自己写）。绝不写入凭据。"""
    path = Path(ledger_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def _ledger_figure(row: dict) -> str:
    """账本行 → 图名（与 STATUS.json 的键一致）：优先图规格 id，否则用输出文件名去掉 cand_ 前缀。"""
    if row.get("spec_id"):
        return str(row["spec_id"])
    stem = Path(str(row.get("output", ""))).stem
    return stem[len("cand_"):] if stem.startswith("cand_") else stem


def ledger_report(ledger_path: str, out_path: str) -> int:
    """账本 → 英文 AI 使用记录（Markdown）。只如实列出生图调用，不替团队声明其他 AI 用途。

    是否用进论文看 STATUS.json（键是图名）。同一张图生成过多次时，每次都覆盖同一个候选文件，
    所以只有最后一次成功的才是被采用的那张，之前的记为被后一次替换。
    """
    rows = []
    for line in Path(ledger_path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and row.get("ok"):
                rows.append(row)
    status = {}
    status_path = Path(ledger_path).with_name("STATUS.json")
    if status_path.is_file():
        try:
            status = json.loads(status_path.read_text(encoding="utf-8")) or {}
        except (OSError, json.JSONDecodeError):
            status = {}
    if not isinstance(status, dict):
        status = {}
    used = {name for name, item in status.items()
            if isinstance(item, dict) and item.get("source") == "ai"}
    last = {_ledger_figure(row): index for index, row in enumerate(rows)}
    lines = [
        "## AI image generation records",
        "",
        "These records are generated automatically from the image-tool ledger. They cover image "
        "generation only; any other AI tools used by the team must be reported separately.",
        "",
    ]
    n = 0
    for index, row in enumerate(rows):
        n += 1
        figure = _ledger_figure(row)
        if figure not in used:
            in_paper = "no (a deterministic version was used instead)"
        elif last[figure] == index:
            in_paper = "yes"
        else:
            in_paper = "no (superseded by a later attempt)"
        lines += [
            f"### Record {n}: {figure}",
            f"- Output file: `{row.get('output', '')}`",
            f"- Tool: OpenAI GPT Image, model `{row.get('model', '')}`, via API "
            f"(`{row.get('endpoint', '')}`)",
            f"- Date: {str(row.get('time', ''))[:10]}",
            "- Purpose: visual rendering of a figure whose structure, labels and formulas were specified "
            "by the team",
            f"- Used in the paper: {in_paper}",
            "- Prompt (verbatim):",
            "",
            "```text",
            str(row.get("prompt", "")),
            "```",
            "",
        ]
    if n == 0:
        lines.append("No AI-generated images were produced.")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return n


# ============================================================
# 主函数
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="GPT Image 2 生成工具")
    parser.add_argument("--check", action="store_true", help="仅检查 API Key 是否配置")
    parser.add_argument("--prompt", type=str, help="生成提示词（核心内容，语言/风格自动注入）")
    parser.add_argument("--output", type=str, help="输出路径（.png），自动生成同名 .pdf")
    parser.add_argument("--lang", type=str, default="zh", choices=["zh", "en"], help="语言：zh 中文（默认）/ en 英文")
    parser.add_argument("--aspect-ratio", type=str, default="16:9", help="宽高比（默认 16:9）")
    parser.add_argument("--model", type=str, default=None, help="生图模型；默认使用任务启动时的设置")
    parser.add_argument("--max-retries", type=int, default=1, help="兼容旧参数；生图不自动重发，避免重复计费")
    parser.add_argument("--spec", type=str, default=None,
                        help="图规格 JSON（kind/description/strings/target_aspect）；按论文风格合同组提示词")
    parser.add_argument("--style", type=str, default="legacy",
                        choices=["legacy", "paper-architecture", "paper-schematic"],
                        help="没有 --spec 时的风格：legacy=旧前后缀；paper-*=论文风格合同")
    parser.add_argument("--reference", type=str, default=None,
                        help="参考图（程序画的线框 PNG）→ images/edits；本机工具票据下不可用（退出码 3）")
    parser.add_argument("--quality", type=str, default=None,
                        choices=["low", "medium", "high", "xhigh", "max", "auto"])
    parser.add_argument("--size", type=str, default=None, help="自定义尺寸 宽x高（16 的倍数）")
    parser.add_argument("--target-aspect", type=str, default=None,
                        help="出图后补白到 宽:高（不裁剪）；--spec 里的 target_aspect 也生效")
    parser.add_argument("--ledger", type=str, default=None, help="用量账本 JSONL（不含凭据）")
    parser.add_argument("--ledger-report", type=str, default=None,
                        help="把这个账本整理成英文 AI 使用记录写到 --output（不调用接口）")
    parser.add_argument("--house-style-init", type=str, default=None, metavar="OUT.json",
                        help="生成本篇版式风格写到这个文件（不调用接口）；配合 --seed/--palette/--accent")
    parser.add_argument("--seed", type=int, default=None, help="本篇种子：工作区名的 cksum（同 paper-figure-html）")
    parser.add_argument("--palette", type=str, default=None,
                        help='本篇 PALETTE token：JSON 列表 ["#强调色", "#浅底"] 或 "mono"')
    parser.add_argument("--accent", type=str, default=None,
                        help="plot_utils.py --paper-accent 的 JSON 输出（取本篇数据图配色做副色）")
    parser.add_argument("--house-style", type=str, default=None, metavar="HOUSE.json",
                        help="按本篇版式风格出图（--spec 的 method/architecture 图用）")
    parser.add_argument("--look", type=str, default="rich", choices=HOUSE_LOOKS,
                        help="--house-style-init 用：用户选的画法 rich（丰满，默认）/ clean（简洁线稿）")
    args = parser.parse_args()

    if args.house_style_init:
        try:
            palette = json.loads(args.palette) if args.palette else None
            accent_info = json.loads(args.accent) if args.accent else {}
            data_colors = accent_info.get("palette") if isinstance(accent_info, dict) else None
            if args.seed is None:
                raise ValueError("--house-style-init 需要 --seed")
            house = house_style(args.seed, palette, data_colors if isinstance(data_colors, list) else None,
                                look=args.look)
            out = Path(args.house_style_init)
            kept = house_in_use(out, house)
            if kept is not None:
                print(house_summary(validate_house_style(kept[0])))
                print(f"HOUSE_STYLE_KEPT: 本篇已有 {kept[1]} 张图用这份版式风格出过，保留它（同一篇前后一套画法）")
                sys.exit(0)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(house, ensure_ascii=False, indent=1), encoding="utf-8")
        except (ValueError, TypeError, json.JSONDecodeError, OSError) as exc:
            print(f"ERROR: {exc}")
            sys.exit(1)
        print(house_summary(house))
        sys.exit(0)

    if args.ledger_report:
        if not args.output:
            print("ERROR: --output is required")
            sys.exit(1)
        try:
            n = ledger_report(args.ledger_report, args.output)
        except OSError as exc:
            print(f"ERROR: {exc}")
            sys.exit(1)
        print(f"OK {args.output} ({n} records)")
        sys.exit(0)

    api_key = os.environ.get("GPT_IMAGE_API_KEY", "").strip()
    api_base = ""  # Kept for the legacy call signature, never used as authority.

    try:
        selected_model = image_model_id(args.model)
    except ValueError as exc:
        print(str(exc))
        sys.exit(1)
    # --check 模式
    if args.check:
        if api_key:
            print("GPT_IMAGE_AVAILABLE=YES")
            sys.exit(0)
        else:
            print("GPT_IMAGE_AVAILABLE=NO (GPT_IMAGE_API_KEY not set)")
            sys.exit(1)

    # 生成模式：参数校验
    if not args.prompt and not args.spec:
        print("ERROR: --prompt is required")
        sys.exit(1)
    if not args.output:
        print("ERROR: --output is required")
        sys.exit(1)
    if not api_key:
        print("GPT_IMAGE_NOT_CONFIGURED: Set GPT_IMAGE_API_KEY in settings")
        sys.exit(1)

    reference_png = None
    spec = None
    house = None
    try:
        if args.reference:
            reference_png = Path(args.reference).read_bytes()
        if args.spec:
            spec = validate_spec(json.loads(Path(args.spec).read_text(encoding="utf-8")))
        if args.house_style:
            house = validate_house_style(json.loads(Path(args.house_style).read_text(encoding="utf-8")))
        if args.size:
            validate_size(args.size)
        target = args.target_aspect or (spec or {}).get("target_aspect")
        if not args.target_aspect and target and spec["kind"] == "method":
            # 流程/原理图保持出图原比例（规程 2.2 节）；照抄总览图的 2:1 会把刚裁掉的白边补回来
            print(f"[GPT Image] method figure: spec target_aspect {target} ignored, keeping the native ratio")
            target = None
        target_ratio = parse_aspect(target) if target else None
        if target and target_ratio is None:
            raise ValueError("target-aspect 必须写成 宽:高，且在 1:3–3:1 之间")
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    # 构图规则（method 图）：非 multi_panel 不分字母面板；同一篇每张图的构图族不重复。
    # 不发请求、不记账本、不算尝试次数，退出码 4：规格作者按提示改了再跑
    if spec is not None:
        problem = composition_problem(spec, read_ledger_rows(args.ledger) if args.ledger else (), house)
        if problem:
            print(f"COMPOSITION: {problem}")
            sys.exit(4)

    # 构建完整 prompt：图规格 > 论文风格 > legacy（注入语言/风格/安全约束）
    if spec is not None:
        full_prompt = build_spec_prompt(spec, reference=reference_png is not None, house=house)
        style_name = SPEC_KINDS[spec["kind"]]
    elif args.style != "legacy":
        full_prompt = build_paper_prompt(args.prompt, args.style, reference=reference_png is not None)
        style_name = args.style
    else:
        full_prompt = build_prompt(args.prompt, args.lang)
        style_name = "legacy"

    # 确保输出目录存在
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    meta: dict = {}
    record = {
        "time": _time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "tool": "gpt_image.py", "model": selected_model, "style": style_name,
        "spec_id": (spec or {}).get("id"), "output": str(out_path).replace("\\", "/"),
        "reference_sha256": hashlib.sha256(reference_png).hexdigest() if reference_png is not None else None,
        "grammar": (spec or {}).get("grammar"),
        "family": GRAMMAR_FAMILY.get((spec or {}).get("grammar")),
        "candidates": (spec or {}).get("candidates"),
        "house_style": house["id"] if house and spec is not None else None,
        "prompt": full_prompt,
    }

    def _ledger(ok: bool, **extra) -> None:
        if not args.ledger:
            return
        try:
            append_ledger(args.ledger, {**record, "ok": ok, "endpoint": meta.get("endpoint"),
                                        "http_status": meta.get("status"), "usage": meta.get("usage"), **extra})
        except OSError as exc:  # 账本写失败不影响出图结果
            print(f"[GPT Image] WARNING: ledger write failed: {exc}")

    # Dispatch only once, including legacy callers passing --max-retries=3.
    args.max_retries = 1
    last_error = None
    for attempt in range(1, args.max_retries + 1):
        try:
            print(f"[GPT Image] Attempt {attempt}/{args.max_retries} ...")
            # 新参数全为空时请求体与旧版一致（legacy 调用方行为不变）。
            img_bytes = _call_gpt_image_api(
                api_base, api_key, full_prompt,
                aspect_ratio=args.aspect_ratio,
                timeout=240,
                model=selected_model,
                quality=args.quality, size=args.size,
                reference_png=reference_png, meta=meta,
            )

            # 保存 PNG（确保格式统一）
            try:
                from PIL import Image as _PILImage
                _img = _PILImage.open(BytesIO(img_bytes))
                if _img.mode == "RGBA":
                    _bg = _PILImage.new("RGB", _img.size, (255, 255, 255))
                    _bg.paste(_img, mask=_img.split()[3])
                    _img = _bg
                elif _img.mode != "RGB":
                    _img = _img.convert("RGB")
                _img.save(str(out_path), "PNG")
            except ImportError:
                # PIL 不可用，直接写原始 bytes
                out_path.write_bytes(img_bytes)
            print(f"[GPT Image] PNG saved: {out_path} ({out_path.stat().st_size} bytes)")
            pixels = None
            if spec is not None and reference_png is None:
                try:
                    pixels = trim_white_margins(str(out_path))
                    print(f"[GPT Image] white margins trimmed: {pixels[0]}x{pixels[1]}")
                except ImportError:
                    pass
            if target_ratio is not None:
                try:
                    pixels = pad_to_aspect(str(out_path), target_ratio)
                    print(f"[GPT Image] padded to {target}: {pixels[0]}x{pixels[1]}")
                except ImportError:
                    print("[GPT Image] WARNING: PIL not available, target aspect not applied")

            # 转 PDF
            pdf_path = _png_to_pdf(str(out_path))
            print(f"[GPT Image] PDF saved: {pdf_path}")
            _ledger(True, pixels=list(pixels) if pixels else None)
            print(f"OK {pdf_path}")
            sys.exit(0)

        except EditsUnavailable as e:
            # 没有发出请求、不计费：调用方应直接采用程序画的底稿。
            _ledger(False, error=str(e))
            print(f"EDITS_UNAVAILABLE: {e}")
            sys.exit(3)
        except Exception as e:
            last_error = str(e)
            _ledger(False, error=last_error[:300])
            print(f"[GPT Image] Attempt {attempt} failed: {last_error}")
            if attempt < args.max_retries:
                import time
                wait = 3 * attempt  # 3s, 6s, 9s
                print(f"[GPT Image] Retrying in {wait}s ...")
                time.sleep(wait)

    # 所有重试都失败
    print(f"FAILED after {args.max_retries} attempts: {last_error}")
    sys.exit(1)


if __name__ == "__main__":
    main()
