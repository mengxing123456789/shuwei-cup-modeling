#!/usr/bin/env python3
"""Markdown → DOCX 转换引擎（中文学术文档格式）

用法：
    python docx_export.py --source paper.md --output paper.docx
    python docx_export.py --source paper.md --output paper.docx --profile literature_review.json
    python docx_export.py --source paper.md --output paper.docx --workspace /path/to/workspace

依赖：python-docx（已在 requirements.txt 中）
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Optional

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml
from docx.oxml.ns import qn, nsdecls
from docx.shared import Cm, Pt, RGBColor

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 样式配置加载
# ---------------------------------------------------------------------------

_PROFILES_DIR = Path(__file__).resolve().parent / "docx_style_profiles"
_DEFAULT_PROFILE = "default_cn_thesis.json"


def load_style_profile(profile_path: Optional[Path] = None) -> dict[str, Any]:
    """加载样式配置 JSON。缺失字段用默认值填充。"""
    default_path = _PROFILES_DIR / _DEFAULT_PROFILE
    if not default_path.exists():
        log.warning("Default profile not found: %s", default_path)
        return _builtin_defaults()

    default_data = json.loads(default_path.read_text(encoding="utf-8"))

    if profile_path is None or not profile_path.exists():
        return default_data

    try:
        custom_data = json.loads(profile_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Failed to load profile %s: %s, using defaults", profile_path, e)
        return default_data

    # 深度合并：custom 覆盖 default
    return _deep_merge(default_data, custom_data)


def _builtin_defaults() -> dict[str, Any]:
    """内置兜底默认值（当 JSON 文件不存在时使用）。"""
    return {
        "page": {"size": "A4", "margin_top_cm": 2.5, "margin_bottom_cm": 2.5,
                 "margin_left_cm": 2.5, "margin_right_cm": 2.5},
        "fonts": {"chinese_heading": "SimHei", "chinese_body": "SimSun",
                  "latin": "Times New Roman", "monospace": "Consolas"},
        "headings": {"level1_pt": 18, "level2_pt": 15, "level3_pt": 12, "bold": True,
                     "level1_alignment": "center", "level2_alignment": "left",
                     "level3_alignment": "left", "level1_page_break_before": True,
                     "level2_page_break_before": False, "level3_page_break_before": False},
        "body": {"font_size_pt": 12, "line_spacing": 1.5,
                 "first_line_indent_chars": 2, "space_before_pt": 0, "space_after_pt": 0},
        "title": {"font_size_pt": 18, "bold": True, "alignment": "center", "font_family": "SimHei"},
        "table": {"top_border_pt": 1.5, "header_border_pt": 0.75, "bottom_border_pt": 1.5,
                  "font_size_pt": 10.5, "header_bold": True, "cell_alignment": "center"},
        "references": {"hanging_indent_cm": 0.74, "font_size_pt": 10.5, "numbering_style": "bracket"},
        "image": {"max_width_cm": 14, "max_height_cm": 20, "alignment": "center"},
        "code_block": {"font_size_pt": 9, "line_spacing": 1.0, "background_color": "F5F5F5"},
    }


def _deep_merge(base: dict, override: dict) -> dict:
    """递归合并字典，override 覆盖 base。"""
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


# ---------------------------------------------------------------------------
# Markdown 文件读取（多编码 fallback）
# ---------------------------------------------------------------------------

def _read_markdown(path: Path) -> str:
    from docx_text import read_markdown
    return read_markdown(path)


def _ensure_png_for_docx(md_content: str, workspace: Path) -> None:
    """扫描 markdown 中的图片引用，若 .png 不存在但同名 .pdf 存在，自动转换。
    优先使用 PyMuPDF (fitz)，回退到 pdf2image。失败则保留原始情况，由后续渲染流程提示。

    ⛔ 主动兜底: 不仅扫 markdown 引用, 还把 figures/ 下所有 fig_*.pdf 强制转成同名
    png (没有同名 png 时才转), 覆盖以下情况:
    - AI 在 markdown 里写错路径 (例如写 figures/q1.pdf 而非 figures/fig_q1.pdf)
    - AI 把图引用写成 \\includegraphics 形式 (没 ![]()) 导致引用扫描漏掉
    - 写作步漏转 PDF 但产物本身在 figures/ 下完整存在
    """
    refs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", md_content)
    # 收集 markdown 引用的 png/jpg 中缺失项
    for ref in refs:
        ref_clean = ref.strip().split(" ")[0]
        if not ref_clean:
            continue
        # 只处理 PNG/JPG 引用
        suffix = Path(ref_clean).suffix.lower()
        if suffix not in (".png", ".jpg", ".jpeg"):
            continue
        # 解析路径
        cand_paths = [workspace / ref_clean,
                      workspace / "figures" / Path(ref_clean).name]
        png_path = next((p for p in cand_paths if p.exists()), None)
        if png_path is not None:
            continue  # PNG/JPG 已存在
        # 找同名 PDF
        pdf_candidates = [workspace / Path(ref_clean).with_suffix(".pdf"),
                          workspace / "figures" / Path(ref_clean).with_suffix(".pdf").name]
        pdf_path = next((p for p in pdf_candidates if p.exists()), None)
        if pdf_path is None:
            continue  # PDF 也没有，跳过（后续会插占位符）
        # 目标 PNG 路径（与 PDF 同目录）
        target_png = pdf_path.with_suffix(".png")
        if target_png.exists():
            continue  # 已经有 PNG（可能在另一个目录），跳过
        if _convert_pdf_to_png(pdf_path, target_png, dpi=350):
            log.info("Auto-converted %s -> %s for Word embedding (md ref)",
                     pdf_path.name, target_png.name)
            _trim_png_whitespace(target_png)
        else:
            log.warning("Could not convert %s to PNG for md ref", pdf_path.name)

    # ⛔ 主动兜底: 把 figures/ 下所有 fig_*.pdf 都尝试转成同名 png
    # (不依赖 markdown 引用, 防 AI 写错路径或漏 ![]() 标记)
    figures_dir = workspace / "figures"
    if not figures_dir.is_dir():
        return
    for pdf in figures_dir.glob("fig_*.pdf"):
        target_png = pdf.with_suffix(".png")
        if target_png.exists():
            continue
        if _convert_pdf_to_png(pdf, target_png, dpi=350):
            log.info("Proactive PDF→PNG for %s -> %s", pdf.name, target_png.name)
            _trim_png_whitespace(target_png)
        else:
            log.warning("Proactive PDF→PNG failed for %s (no PyMuPDF / pdf2image)", pdf.name)


def _convert_pdf_to_png(pdf_path: Path, png_path: Path, dpi: int = 350) -> bool:
    """把单页 PDF 转成 PNG。优先 PyMuPDF(fitz)，回退 pdf2image。成功返回 True。"""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(pdf_path))
        if doc.page_count > 0:
            pix = doc[0].get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), alpha=False)
            pix.save(str(png_path))
            doc.close()
            return True
        doc.close()
    except Exception as e:
        log.debug("fitz convert failed for %s: %s", pdf_path.name, e)
    try:
        from pdf2image import convert_from_path
        images = convert_from_path(str(pdf_path), dpi=dpi, first_page=1, last_page=1)
        if images:
            images[0].save(str(png_path), "PNG")
            return True
    except Exception as e:
        log.debug("pdf2image convert failed for %s: %s", pdf_path.name, e)
    return False


def _ensure_tikz_png_for_docx(workspace: Path) -> None:
    """TikZ 兜底：把 figures/tikz_*.pdf 转成 PNG 供 Word 嵌入。

    TikZ 由 paper-figure-drawio 编译成 figures/tikz_diagrams.pdf（多图则多页）。
    Word 不能嵌 PDF，必须转 PNG。处理两种情况：
    - 单页 PDF → 同名 PNG（tikz_diagrams.pdf → tikz_diagrams.png）
    - 多页 PDF → 逐页 PNG（tikz_diagrams.pdf → tikz_diagrams_1.png / _2.png ...）

    幂等：目标 PNG 已存在则跳过。不删除原 PDF（保留供 PDF 模式/排查），
    Word 嵌入时 _add_image 会优先用 PNG。
    """
    figures_dir = workspace / "figures"
    if not figures_dir.is_dir():
        return
    tikz_pdfs = sorted(figures_dir.glob("tikz_*.pdf"))
    if not tikz_pdfs:
        return
    # 检测页数需要 fitz；没有则按单页处理
    try:
        import fitz  # PyMuPDF
        _has_fitz = True
    except Exception:
        _has_fitz = False

    for tpdf in tikz_pdfs:
        bn = tpdf.stem  # tikz_diagrams
        page_count = 1
        if _has_fitz:
            try:
                import fitz
                _d = fitz.open(str(tpdf))
                page_count = _d.page_count
                _d.close()
            except Exception:
                page_count = 1

        if page_count <= 1:
            target = figures_dir / f"{bn}.png"
            if not target.exists():
                if _convert_pdf_to_png(tpdf, target):
                    log.info("TikZ: converted %s -> %s for Word", tpdf.name, target.name)
                    _trim_png_whitespace(target)
        else:
            # 多页：逐页拆成 tikz_xxx_1.png / _2.png ...
            try:
                import fitz
                _d = fitz.open(str(tpdf))
                for i in range(_d.page_count):
                    target = figures_dir / f"{bn}_{i + 1}.png"
                    if target.exists():
                        continue
                    pix = _d[i].get_pixmap(matrix=fitz.Matrix(350 / 72, 350 / 72), alpha=False)
                    pix.save(str(target))
                    log.info("TikZ: converted %s page %d -> %s", tpdf.name, i + 1, target.name)
                    _trim_png_whitespace(target)
                _d.close()
                # 同时保留一份首页同名 PNG，兼容 main.md 直接引用 tikz_diagrams.png 的情况
                first_png = figures_dir / f"{bn}.png"
                if not first_png.exists():
                    _convert_pdf_to_png(tpdf, first_png)
                    if first_png.exists():
                        _trim_png_whitespace(first_png)
            except Exception as e:
                log.warning("TikZ multi-page conversion failed for %s: %s", tpdf.name, e)


def _trim_png_whitespace(png_path: Path, bg_threshold: int = 240, padding: int = 12) -> bool:
    """裁掉 PNG 四周的白边。

    Args:
        png_path: 目标 PNG 路径
        bg_threshold: 背景判定阈值（亮度 ≥ bg_threshold 视为白边，容忍轻微抗锯齿灰）
        padding: 裁完后保留的像素边距（避免贴边）

    Returns:
        True 表示成功裁边并保存；False 表示跳过（PIL 不可用或图无白边）
    """
    try:
        from PIL import Image, ImageChops
    except ImportError:
        return False
    try:
        im = Image.open(str(png_path))
        if im.mode in ("RGBA", "LA"):
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[-1])
            im = bg
        elif im.mode != "RGB":
            im = im.convert("RGB")
        bg_ref = Image.new("RGB", im.size, (255, 255, 255))
        diff = ImageChops.difference(im, bg_ref)
        bbox_data = diff.point(lambda x: 0 if x < (255 - bg_threshold) else 255)
        bbox = bbox_data.getbbox()
        if bbox is None:
            return False  # 全白图
        x0, y0, x1, y1 = bbox
        orig_w, orig_h = im.size
        # 加 padding
        x0 = max(0, x0 - padding)
        y0 = max(0, y0 - padding)
        x1 = min(orig_w, x1 + padding)
        y1 = min(orig_h, y1 + padding)
        new_w, new_h = x1 - x0, y1 - y0
        # ★ 阈值降到 2%：原 5% 太宽松，2-panel 顶部小图 + 下方 80% 白边的图无法触发裁剪
        # ★ 同时增加"严重失衡"判定：内容占比 < 50% 强制裁
        cut_w_pct = (orig_w - new_w) / orig_w
        cut_h_pct = (orig_h - new_h) / orig_h
        content_area_pct = (new_w * new_h) / (orig_w * orig_h)
        should_trim = (cut_w_pct > 0.02 or cut_h_pct > 0.02 or content_area_pct < 0.5)
        if should_trim:
            cropped = im.crop((x0, y0, x1, y1))
            cropped.save(str(png_path), "PNG", optimize=True)
            log.info("Trimmed %s whitespace: %dx%d -> %dx%d (content %.0f%% -> 100%%)",
                     png_path.name, orig_w, orig_h, new_w, new_h, content_area_pct * 100)
            return True
        return False
    except Exception as e:
        log.debug("Trim whitespace failed for %s: %s", png_path.name, e)
        return False


# ---------------------------------------------------------------------------
# 字体设置辅助
# ---------------------------------------------------------------------------

def _set_run_fonts(run, profile: dict[str, Any], style_type: str = "body"):
    """为 run 设置中英文字体。style_type: body / heading / code / reference"""
    fonts = profile.get("fonts", {})

    if style_type == "heading":
        cn_font = fonts.get("chinese_heading", "SimHei")
        en_font = fonts.get("latin", "Times New Roman")
    elif style_type == "code":
        cn_font = fonts.get("monospace", "Consolas")
        en_font = fonts.get("monospace", "Consolas")
    elif style_type == "reference":
        cn_font = fonts.get("chinese_body", "SimSun")
        en_font = fonts.get("latin", "Times New Roman")
    else:
        cn_font = fonts.get("chinese_body", "SimSun")
        en_font = fonts.get("latin", "Times New Roman")

    run.font.name = en_font
    r_pr = run._element.get_or_add_rPr()
    r_fonts = r_pr.find(qn("w:rFonts"))
    if r_fonts is None:
        from docx.oxml import OxmlElement
        r_fonts = OxmlElement("w:rFonts")
        r_pr.insert(0, r_fonts)
    r_fonts.set(qn("w:eastAsia"), cn_font)
    r_fonts.set(qn("w:ascii"), en_font)
    r_fonts.set(qn("w:hAnsi"), en_font)


# ---------------------------------------------------------------------------
# 段落/标题/表格/图片 应用函数
# ---------------------------------------------------------------------------

_ALIGNMENT_MAP = {
    "center": WD_ALIGN_PARAGRAPH.CENTER,
    "left": WD_ALIGN_PARAGRAPH.LEFT,
    "right": WD_ALIGN_PARAGRAPH.RIGHT,
    "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
}


def _clean_markdown_inline(text: str) -> str:
    """清理 Markdown 行内标记（加粗/斜体/代码/链接），保留纯文本。"""
    # **bold** 或 __bold__
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    # *italic* 或 _italic_
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"\1", text)
    # `code`
    text = re.sub(r"`(.+?)`", r"\1", text)
    # [text](url)
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    return text.strip()


def _add_heading(doc: Document, text: str, level: int, profile: dict, first_heading: bool = False):
    """添加标题段落。

    first_heading=True（第一个 H1）走 profile['title'] 样式（论文标题，居中、加粗、22pt）；
    其他标题走 profile['headings'] 的 levelN 配置。
    """
    headings_cfg = profile.get("headings", {})
    title_cfg = profile.get("title", {})

    # 第一个 H1 使用 title 样式（替代封面，把论文标题渲染成醒目的居中大字）
    if first_heading and level == 1 and title_cfg:
        font_size = title_cfg.get("font_size_pt", 22)
        bold = title_cfg.get("bold", True)
        alignment = title_cfg.get("alignment", "center")
        page_break = False
    else:
        size_key = f"level{level}_pt"
        # H4/H5/H6 在 profile 里通常没定义, fallback 到上一级大小再 -1pt 便于视觉区分
        if size_key in headings_cfg:
            font_size = headings_cfg[size_key]
        else:
            # 找最近的已定义级别（向上回退）
            font_size = 12
            for _try_lvl in range(level - 1, 0, -1):
                _try_key = f"level{_try_lvl}_pt"
                if _try_key in headings_cfg:
                    font_size = max(headings_cfg[_try_key] - (level - _try_lvl), 10.5)
                    break
        bold = headings_cfg.get("bold", True)
        align_key = f"level{level}_alignment"
        alignment = headings_cfg.get(align_key, "left")
        page_break_key = f"level{level}_page_break_before"
        page_break = headings_cfg.get(page_break_key, False)

    para = doc.add_paragraph()
    # 首个一级标题不分页（避免文档开头空白页）
    if page_break and not first_heading:
        from docx.oxml import OxmlElement
        pPr = para._p.get_or_add_pPr()
        pb = OxmlElement("w:pageBreakBefore")
        pPr.append(pb)

    para.alignment = _ALIGNMENT_MAP.get(alignment, WD_ALIGN_PARAGRAPH.LEFT)
    # 第一个 H1（论文标题）多一些上下间距
    if first_heading and level == 1 and title_cfg:
        para.paragraph_format.space_before = Pt(24)
        para.paragraph_format.space_after = Pt(18)
    run = para.add_run(_clean_markdown_inline(text))
    run.bold = bold
    run.font.size = Pt(font_size)
    _set_run_fonts(run, profile, "heading")
    return para


def _add_body_paragraph(doc: Document, text: str, profile: dict):
    """添加正文段落（首行缩进 + 中文字体）。"""
    body_cfg = profile.get("body", {})
    font_size = body_cfg.get("font_size_pt", 12)
    line_spacing = body_cfg.get("line_spacing", 1.5)
    indent_chars = body_cfg.get("first_line_indent_chars", 2)

    para = doc.add_paragraph()
    para.paragraph_format.line_spacing = line_spacing
    para.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    # 首行缩进：1 个中文字符 ≈ 12pt，2 字符 = 24pt（在 12pt 字号下）
    indent_pt = indent_chars * font_size
    para.paragraph_format.first_line_indent = Pt(indent_pt)
    para.paragraph_format.space_before = Pt(body_cfg.get("space_before_pt", 0))
    para.paragraph_format.space_after = Pt(body_cfg.get("space_after_pt", 0))

    run = para.add_run(_clean_markdown_inline(text))
    run.font.size = Pt(font_size)
    _set_run_fonts(run, profile, "body")
    return para


def _add_runs_with_inline_bold(para, text: str, profile: dict, role: str, font_size: float):
    """把 text 按 **加粗** 拆成多个 run：加粗段 bold=True，其余段正常；
    每段都先 _clean_markdown_inline 清掉其它行内标记（斜体/代码/链接），再逐 run 套字体+字号。
    仅用于摘要正文（竞赛摘要加粗关键方法/结果）。普通正文不走此路径，行为不变。

    边缘：
    - 无 **加粗** → parts 仅一段非加粗，等价于旧的单 run（清洗后加一个 run）。
    - 连续/多处加粗、加粗跨标点 → re.split 天然正确切分。
    - 未闭合 **（如 "**未闭合"）→ 不成对，不匹配加粗，整段当普通文本清洗（与旧行为一致）。
    - 加粗段清洗后为空 → 跳过该 run，不产生空粗体。
    - 全部清空（理论不会）→ 兜底加一个空 run 保住段落存在。
    """
    parts = re.split(r"(\*\*.+?\*\*)", text)
    any_run = False
    for seg in parts:
        if not seg:
            continue
        m = re.match(r"^\*\*(.+?)\*\*$", seg)
        if m:
            content = _clean_markdown_inline(m.group(1))
            is_bold = True
        else:
            content = _clean_markdown_inline(seg)
            is_bold = False
        if not content:
            continue
        run = para.add_run(content)
        run.bold = is_bold
        run.font.size = Pt(font_size)
        _set_run_fonts(run, profile, role)
        any_run = True
    if not any_run:
        run = para.add_run("")
        run.font.size = Pt(font_size)
        _set_run_fonts(run, profile, role)
    return para


def _add_abstract_body_paragraph(doc: Document, text: str, profile: dict):
    """摘要正文段落：段落格式与正文完全一致（首行缩进/行距/字体），
    但 run 层支持 **加粗** 行内解析，用于竞赛摘要加粗关键方法名/关键结果数值。"""
    body_cfg = profile.get("body", {})
    font_size = body_cfg.get("font_size_pt", 12)
    line_spacing = body_cfg.get("line_spacing", 1.5)
    indent_chars = body_cfg.get("first_line_indent_chars", 2)

    para = doc.add_paragraph()
    para.paragraph_format.line_spacing = line_spacing
    para.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    indent_pt = indent_chars * font_size
    para.paragraph_format.first_line_indent = Pt(indent_pt)
    para.paragraph_format.space_before = Pt(body_cfg.get("space_before_pt", 0))
    para.paragraph_format.space_after = Pt(body_cfg.get("space_after_pt", 0))

    _add_runs_with_inline_bold(para, text, profile, "body", font_size)
    return para


def _add_reference_paragraph(doc: Document, text: str, profile: dict):
    """添加参考文献段落（悬挂缩进）。"""
    ref_cfg = profile.get("references", {})
    font_size = ref_cfg.get("font_size_pt", 10.5)
    hanging_cm = ref_cfg.get("hanging_indent_cm", 0.74)

    para = doc.add_paragraph()
    para.paragraph_format.first_line_indent = Cm(-hanging_cm)
    para.paragraph_format.left_indent = Cm(hanging_cm)
    para.paragraph_format.line_spacing = 1.25
    para.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    para.paragraph_format.space_before = Pt(0)
    para.paragraph_format.space_after = Pt(2)

    run = para.add_run(_clean_markdown_inline(text))
    run.font.size = Pt(font_size)
    _set_run_fonts(run, profile, "reference")
    return para


def _add_abstract_heading(doc: Document, text: str, profile: dict):
    """添加摘要标题（居中、加粗，对标 cumcmthesis.cls 的 \\zihao{4}\\bfseries 摘要）。"""
    abstract_cfg = profile.get("abstract", {})
    label_size = abstract_cfg.get("label_size_pt", 14)
    label_bold = abstract_cfg.get("label_bold", True)

    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para.paragraph_format.first_line_indent = Pt(0)
    para.paragraph_format.space_before = Pt(12)
    para.paragraph_format.space_after = Pt(6)

    run = para.add_run(_clean_markdown_inline(text))
    run.bold = label_bold
    run.font.size = Pt(label_size)
    _set_run_fonts(run, profile, "heading")
    return para


def _add_keywords_paragraph(doc: Document, label: str, value: str, profile: dict):
    """添加关键词段落（黑体加粗标签 + 正文内容）。"""
    kw_cfg = profile.get("keywords", {})
    body_cfg = profile.get("body", {})
    label_size = kw_cfg.get("label_size_pt", body_cfg.get("font_size_pt", 12))
    label_bold = kw_cfg.get("label_bold", True)

    para = doc.add_paragraph()
    para.paragraph_format.first_line_indent = Pt(label_size * 2)  # 2 字符首行缩进
    para.paragraph_format.line_spacing = body_cfg.get("line_spacing", 1.5)
    para.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE

    run_label = para.add_run(label)
    run_label.bold = label_bold
    run_label.font.size = Pt(label_size)
    _set_run_fonts(run_label, profile, "heading")  # 标签用黑体

    run_value = para.add_run(_clean_markdown_inline(value))
    run_value.font.size = Pt(label_size)
    _set_run_fonts(run_value, profile, "body")  # 正文用宋体
    return para


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """解析并丢弃 YAML frontmatter（封面元数据已不再渲染，但要确保它不会被当正文）。

    返回 (meta_dict, body_without_frontmatter)。
    """
    m = re.match(r'^---\s*\r?\n([\s\S]*?)\r?\n---\s*\r?\n', content)
    if not m:
        return {}, content
    meta = {}
    for line in m.group(1).split("\n"):
        kv = re.match(r'^([\w\-]+)\s*:\s*(.*)$', line)
        if kv:
            v = kv.group(2).strip()
            if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                v = v[1:-1]
            meta[kv.group(1)] = v
    return meta, content[m.end():]


def _add_code_block(doc: Document, lines: list[str], profile: dict):
    """添加代码块（等宽字体 + 浅灰底色 + 每行独立段落保留缩进与换行）。"""
    code_cfg = profile.get("code_block", {})
    font_size = code_cfg.get("font_size_pt", 9)
    bg_color = code_cfg.get("background_color", "F5F5F5")

    # ⛔ Python-docx 没有直接 shading API，需要手动注入 w:shd 元素
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    for line in lines:
        # 制表符展开为 4 空格，保留原始缩进
        expanded = line.replace("\t", "    ").rstrip()
        para = doc.add_paragraph()
        para.paragraph_format.first_line_indent = Pt(0)
        para.paragraph_format.left_indent = Cm(0.5)
        para.paragraph_format.line_spacing = code_cfg.get("line_spacing", 1.0)
        para.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        para.paragraph_format.space_before = Pt(0)
        para.paragraph_format.space_after = Pt(0)

        # 浅灰底色：在 pPr 中加 w:shd
        try:
            pPr = para._p.get_or_add_pPr()
            shd = OxmlElement("w:shd")
            shd.set(qn("w:val"), "clear")
            shd.set(qn("w:color"), "auto")
            shd.set(qn("w:fill"), bg_color)
            pPr.append(shd)
        except Exception:
            pass

        # 空行也要占一行（避免 docx 折叠）
        run = para.add_run(expanded if expanded else " ")
        run.font.size = Pt(font_size)
        _set_run_fonts(run, profile, "code")


def _add_image(doc: Document, image_ref: str, workspace: Optional[Path], profile: dict):
    """嵌入图片或插入占位符。image_ref 是 Markdown 中的路径。

    宽度策略：正常图统一按 max_width_cm（≈文本宽 85%）嵌入，不大不小；
    真·低像素图（放到目标宽会糊，有效 DPI<150）才回退原生尺寸；
    瘦长图按 max_height_cm 封顶反向缩宽，防止溢出页面。
    """
    img_cfg = profile.get("image", {})
    target_width_cm = float(img_cfg.get("max_width_cm", 14))
    max_height_cm = float(img_cfg.get("max_height_cm", 20))
    # 双栏时图片不能超过单栏宽，否则冲破栏界；留 0.2cm 余量防边界溢出
    col_w = _text_column_width_cm(profile)
    if col_w < target_width_cm:
        target_width_cm = max(col_w - 0.2, 2.0)
    max_width = Cm(target_width_cm)
    alignment = img_cfg.get("alignment", "center")

    # 解析图片路径
    image_path = None
    if workspace:
        candidate = workspace / image_ref
        if candidate.exists():
            image_path = candidate
        else:
            # 尝试 figures/ 子目录
            candidate2 = workspace / "figures" / Path(image_ref).name
            if candidate2.exists():
                image_path = candidate2

    # 如果原始路径是 PDF/SVG（python-docx 不支持），尝试找同名 PNG
    if image_path and image_path.suffix.lower() in (".pdf", ".svg"):
        png_alt = image_path.with_suffix(".png")
        if png_alt.exists():
            image_path = png_alt
    # 如果原始路径是 PNG/JPG 但找不到，尝试同名 PDF→PNG（最后机会）
    if image_path is None and workspace:
        ref_path = Path(image_ref)
        if ref_path.suffix.lower() in (".png", ".jpg", ".jpeg"):
            for base in [workspace / ref_path.with_suffix(".pdf"),
                         workspace / "figures" / ref_path.with_suffix(".pdf").name]:
                if base.exists():
                    # 同名 PDF 存在但找不到 PNG，提示
                    log.warning("Image %s not found, but %s exists. Word 需要 PNG。", image_ref, base)
                    break

    if image_path and image_path.exists():
        ext = image_path.suffix.lower()
        # 跳过不支持的格式
        if ext in (".svg", ".pdf"):
            log.warning("%s not supported by python-docx, skipping: %s", ext, image_ref)
            para = doc.add_paragraph()
            para.alignment = _ALIGNMENT_MAP.get(alignment, WD_ALIGN_PARAGRAPH.CENTER)
            run = para.add_run(f"[{ext.upper().lstrip('.')}图片无法嵌入 Word，需要 PNG: {image_ref}]")
            run.font.size = Pt(10)
            run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
            return

        para = doc.add_paragraph()
        para.alignment = _ALIGNMENT_MAP.get(alignment, WD_ALIGN_PARAGRAPH.CENTER)
        para.paragraph_format.first_line_indent = Pt(0)
        run = para.add_run()
        try:
            # 图片尺寸规范化：正常图统一目标宽；低像素图防糊；瘦长图防溢出
            actual_width_cm = target_width_cm  # 默认按目标宽（正常大小）
            try:
                from PIL import Image as _PILImage
                with _PILImage.open(image_path) as _im:
                    img_w_px, img_h_px = _im.size
                # 1) 低像素防糊：放到目标宽后有效 DPI < 150 才回退原生尺寸
                #    (fig_*.pdf 按 350 DPI 转出的 PNG 像素充足，恒走目标宽，不会被误缩)
                eff_dpi = img_w_px / (target_width_cm / 2.54)
                if eff_dpi < 150:
                    native_cm = img_w_px / 96 * 2.54
                    actual_width_cm = min(native_cm, target_width_cm)
                # 2) 高度封顶：按当前宽算高，超 max_height_cm 则反向缩宽（瘦长图防溢出）
                if img_w_px > 0:
                    aspect = img_h_px / img_w_px
                    height_cm = actual_width_cm * aspect
                    if height_cm > max_height_cm:
                        actual_width_cm = max_height_cm / aspect
            except Exception:
                # PIL 不可用或读图失败，退回按目标宽嵌入（python-docx 会按比例算 height）
                pass
            run.add_picture(str(image_path), width=Cm(actual_width_cm))
        except Exception as e:
            log.warning("Failed to embed image %s: %s", image_path, e)
            para.clear()
            run2 = para.add_run(f"[图片加载失败: {image_ref}]")
            run2.font.size = Pt(10)
            run2.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
    else:
        # 占位符
        para = doc.add_paragraph()
        para.alignment = _ALIGNMENT_MAP.get(alignment, WD_ALIGN_PARAGRAPH.CENTER)
        para.paragraph_format.first_line_indent = Pt(0)
        run = para.add_run(f"[图片缺失: {image_ref}]")
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)


def _add_three_line_table(doc: Document, headers: list[str], rows: list[list[str]], profile: dict):
    """添加三线表。"""
    table_cfg = profile.get("table", {})
    font_size = table_cfg.get("font_size_pt", 10.5)
    header_bold = table_cfg.get("header_bold", True)

    col_count = len(headers)
    table = doc.add_table(rows=1 + len(rows), cols=col_count)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    # 填充表头
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = ""
        para = cell.paragraphs[0]
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para.paragraph_format.first_line_indent = Pt(0)
        run = para.add_run(_clean_markdown_inline(h))
        run.bold = header_bold
        run.font.size = Pt(font_size)
        _set_run_fonts(run, profile, "body")

    # 填充数据行
    for row_idx, row_data in enumerate(rows):
        for col_idx, cell_text in enumerate(row_data):
            if col_idx >= col_count:
                break
            cell = table.rows[row_idx + 1].cells[col_idx]
            cell.text = ""
            para = cell.paragraphs[0]
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            para.paragraph_format.first_line_indent = Pt(0)
            run = para.add_run(_clean_markdown_inline(cell_text))
            run.font.size = Pt(font_size)
            _set_run_fonts(run, profile, "body")

    # 锁定表宽=可用文本宽（双栏时为单栏宽），关 autofit 让 Word 按比例压列，防冲破栏界
    _fix_table_width(table, profile, col_count)
    # 应用三线表边框
    _apply_three_line_borders(table, profile)
    return table


def _fix_table_width(table, profile: dict, col_count: int):
    """把表宽锁到可用文本宽、列宽平分、固定布局。双栏时 = 单栏栏宽，防溢出。"""
    if col_count <= 0:
        return
    avail_twips = int(_text_column_width_cm(profile) * 567)
    per_col = max(avail_twips // col_count, 1)
    total_twips = per_col * col_count  # 与 gridCol/tcW 总和严格一致，避免 Word 重算列宽
    table.autofit = False
    tblPr = table._tbl.tblPr
    for tag in ("w:tblW", "w:tblLayout"):
        for existing in tblPr.findall(qn(tag)):
            tblPr.remove(existing)
    tblPr.append(parse_xml(f'<w:tblW {nsdecls("w")} w:w="{total_twips}" w:type="dxa"/>'))
    tblPr.append(parse_xml(f'<w:tblLayout {nsdecls("w")} w:type="fixed"/>'))
    # 重写 tblGrid 列宽（平分栏宽）
    grid = table._tbl.find(qn("w:tblGrid"))
    if grid is not None:
        for gc in grid.findall(qn("w:gridCol")):
            grid.remove(gc)
        for _ in range(col_count):
            grid.append(parse_xml(f'<w:gridCol {nsdecls("w")} w:w="{per_col}"/>'))
    # 单元格也写宽，个别 Word 版本只认 tcW
    for row in table.rows:
        for cell in row.cells:
            tcPr = cell._tc.get_or_add_tcPr()
            for existing in tcPr.findall(qn("w:tcW")):
                tcPr.remove(existing)
            tcPr.append(parse_xml(f'<w:tcW {nsdecls("w")} w:w="{per_col}" w:type="dxa"/>'))


def _apply_three_line_borders(table, profile: dict):
    """为表格应用三线表边框样式。"""
    table_cfg = profile.get("table", {})
    top_sz = int(table_cfg.get("top_border_pt", 1.5) * 8)  # pt → eighth-points
    header_sz = int(table_cfg.get("header_border_pt", 0.75) * 8)
    bottom_sz = int(table_cfg.get("bottom_border_pt", 1.5) * 8)

    row_count = len(table.rows)
    for row_idx, row in enumerate(table.rows):
        for cell in row.cells:
            tc = cell._tc
            tcPr = tc.get_or_add_tcPr()
            # 移除已有边框
            existing = tcPr.find(qn("w:tcBorders"))
            if existing is not None:
                tcPr.remove(existing)

            # 确定当前单元格的边框
            if row_idx == 0:
                # 表头行：顶线粗 + 底线细
                borders_xml = (
                    f'<w:tcBorders {nsdecls("w")}>'
                    f'  <w:top w:val="single" w:sz="{top_sz}" w:space="0" w:color="000000"/>'
                    f'  <w:bottom w:val="single" w:sz="{header_sz}" w:space="0" w:color="000000"/>'
                    f'  <w:left w:val="nil"/>'
                    f'  <w:right w:val="nil"/>'
                    f'</w:tcBorders>'
                )
            elif row_idx == row_count - 1:
                # 最后一行：底线粗
                borders_xml = (
                    f'<w:tcBorders {nsdecls("w")}>'
                    f'  <w:top w:val="nil"/>'
                    f'  <w:bottom w:val="single" w:sz="{bottom_sz}" w:space="0" w:color="000000"/>'
                    f'  <w:left w:val="nil"/>'
                    f'  <w:right w:val="nil"/>'
                    f'</w:tcBorders>'
                )
            else:
                # 中间行：无边框
                borders_xml = (
                    f'<w:tcBorders {nsdecls("w")}>'
                    f'  <w:top w:val="nil"/>'
                    f'  <w:bottom w:val="nil"/>'
                    f'  <w:left w:val="nil"/>'
                    f'  <w:right w:val="nil"/>'
                    f'</w:tcBorders>'
                )
            tcPr.append(parse_xml(borders_xml))


# ---------------------------------------------------------------------------
# Markdown 伪标记修复（章节标题/图注/公式编号被写成 list 项的还原）
# ---------------------------------------------------------------------------

# 章节序号关键 regex（结构特征，不依赖语义）
_CN_SECTION_NUM_RE = re.compile(
    r"^(?:第[一二三四五六七八九十百千零〇\d]+[章节部篇]|"  # 第X章/节/部/篇
    r"[一二三四五六七八九十]+、|"  # 一、二、三、
    r"[（(][一二三四五六七八九十]+[)）])"  # （一）（二）
)
_NUMERIC_SECTION_RE = re.compile(r"^\d+(?:\.\d+){0,4}\.?\s")  # 1.  1.1  1.1.1
_KNOWN_HEADING_LABELS = (
    "摘要", "Abstract", "关键词", "Keywords", "Key words",
    "参考文献", "References", "致谢", "Acknowledgement", "Acknowledgements",
    "附录", "Appendix",
)

# 图/表注释结构特征（精确匹配，避免误吃 "图书"/"表面"/"表达式" 等普通词）
# 允许的形式：
#   "图 X：..."  "图 X-Y：..."  "图 X.Y..."  (X 必须是数字或字母)
#   "Figure X..." "Fig. X..." "Table X..." "Tab. X..."
#   "图：..."  "表：..."        (单字 + 中文冒号开头, 严格要求紧跟冒号)
_FIG_TABLE_CAPTION_RE = re.compile(
    r"^(?:"
    r"(?:图|表)\s*[\dA-Za-z][\dA-Za-z\-\.]*\s*[：:、\.\-]|"  # 中文 + 编号
    r"(?:图|表)\s*[：:]|"                                     # 中文 + 紧跟冒号
    r"(?:Figure|Fig\.?|Table|Tab\.?)\s*[\dA-Za-z][\dA-Za-z\-\.]*"  # 英文 + 编号
    r")"
)

# 公式编号独占行：仅 [1] / (1) / 【1】 形式
_BARE_EQ_NUMBER_RE = re.compile(r"^\s*[\[\(【]\s*\d+(?:\.\d+)?\s*[\]\)】]\s*$")


def _classify_pseudo_heading(text: str) -> int:
    """如果 text 看起来像被误写成 list 的章节标题，返回应有的级别（1/2/3/4）；否则 0。"""
    s = text.strip()
    if not s or len(s) > 80:  # 标题不会太长
        return 0
    # 已知关键标签：摘要/关键词/参考文献等 → H2
    for lbl in _KNOWN_HEADING_LABELS:
        if s == lbl or s.startswith(lbl + "（") or s.startswith(lbl + "(") \
                or s.startswith(lbl + ":") or s.startswith(lbl + "："):
            return 2
    # 中文序号开头 → H1
    if _CN_SECTION_NUM_RE.match(s):
        return 1
    # 数字小节号 → 按层级
    m = _NUMERIC_SECTION_RE.match(s)
    if m:
        prefix = m.group(0).rstrip(". ").rstrip()
        depth = prefix.count(".") + 1
        return min(depth, 4)
    return 0


def _normalize_pseudo_markup(content: str) -> str:
    """把 LLM 误写为 list 的章节标题、图注、独行公式编号还原成合法 markdown。

    不依赖语义判断，只看结构特征：
      - "- 一、问题重述"          → "# 一、问题重述"
      - "- 1.1 问题背景"          → "## 1.1 问题背景"
      - "- 1.1.1 子小节"          → "### 1.1.1 子小节"
      - "- 摘要"                  → "## 摘要"
      - "- 图 4-1：方法对比结果"  → "图 4-1：方法对比结果"  (去 bullet, 保留正文)
      - "- (1)" / "- [1]"         → 与上一行公式合并成 "$$...$$ (1)"
    在 ``` 代码块内不处理，避免破坏代码示例。
    """
    if not content:
        return content
    out: list[str] = []
    in_code = False
    fence_re = re.compile(r"^\s*```")
    list_re = re.compile(r"^(\s*)([-*+])\s+(.+?)\s*$")

    lines = content.splitlines()
    for raw in lines:
        if fence_re.match(raw):
            in_code = not in_code
            out.append(raw)
            continue
        if in_code:
            out.append(raw)
            continue

        m = list_re.match(raw)
        if m:
            indent, bullet, body = m.group(1), m.group(2), m.group(3)
            # 1) 章节标题伪 list
            if indent == "":  # 只动顶格的，缩进 list 多半是真实条目
                lvl = _classify_pseudo_heading(body)
                if lvl > 0:
                    out.append(("#" * lvl) + " " + body)
                    continue
                # 2) 图/表注释伪 list
                if _FIG_TABLE_CAPTION_RE.match(body):
                    out.append(body)
                    continue
                # 3) 独行公式编号伪 list（"- (1)" / "- [1]"）
                if _BARE_EQ_NUMBER_RE.match(body):
                    # 找到上一条非空 out, 若是公式块结尾或公式行, 把编号合并
                    j = len(out) - 1
                    while j >= 0 and not out[j].strip():
                        j -= 1
                    if j >= 0:
                        prev = out[j].rstrip()
                        # 公式块（$$...$$ 单行）或行内带 $ 的公式行 → 直接拼到末尾
                        if (prev.endswith("$$") or prev.count("$") >= 2):
                            number = body.strip()
                            # 统一成 "(N)"
                            num_match = re.search(r"\d+(?:\.\d+)?", number)
                            if num_match:
                                num = num_match.group(0)
                                out[j] = prev + f" ({num})"
                                continue
                    # 若不能合并就保留为正文（去掉 bullet）
                    out.append(body)
                    continue

        out.append(raw)
    return "\n".join(out) + ("\n" if content.endswith("\n") else "")


# 参考文献章节标题：与 docx_precheck 一致，允许"七、""第七章""（七）""7 "等序号和"主要参考文献"
_REF_SECTION_HEADING_RE = re.compile(
    r"^(#{1,4})[ \t]*"
    r"(?:第[一二三四五六七八九十百零〇\d]+[章节部分篇][ \t]*"
    r"|[（(][一二三四五六七八九十百零〇\d]+[)）][、.．]?[ \t]*"
    r"|[一二三四五六七八九十百零〇\d]+[、.．][ \t]*"
    r"|\d+(?:\.\d+)*[ \t]+)?"
    r"(?:(?:主要)?参[ \t]*考[ \t]*文[ \t]*献|References|Bibliography)[ \t]*$",
    re.IGNORECASE,
)
_ANY_HEADING_RE = re.compile(r"^(#{1,6})\s*\S")          # 与 Node 引擎认标题的写法一致
_REF_NUMBERED_ENTRY_RE = re.compile(r"^[ \t]*(?:[-*+][ \t]+)?[\[［]\d{1,3}[\]］]")
_REF_TYPE_MARK_RE = re.compile(r"\[(?:M|C|N|J|D|R|S|P|G|A|Z|EB|DB|CP|PP|DS)(?:/OL)?\]")
_REF_APA_YEAR_RE = re.compile(r"\((?:19|20)\d{2}[a-z]?\)\.")                      # Smith, J. (2020).
_REF_GB_AUTHOR_YEAR_RE = re.compile(r"^[^\[\]]{1,120}?[,，][ \t]*(?:19|20)\d{2}[a-z]?[.．。]")  # 王建国, 2020.
_REF_LINE_END_RE = re.compile(r"(?:[.。．]|https?://\S+|doi:[ \t]*\S+)[ \t]*$", re.IGNORECASE)


def _split_reference_entries(content: str) -> str:
    """参考文献区里一行一条、条目之间没空行时，Markdown 会把它们并成一段，Word 里就粘成一大段。

    这里在条目之间补一个空行：
      - 编号制：以 [n] 开头的行一定是新条目；不以 [n] 开头的行是上一条被拆开的后半截，照旧并回去；
      - 著者-出版年制（本章节没有 [n] 编号）：上一行以句号或网址结尾、当前这一条里已经出现过
        [J] [M] [EB/OL] 等类型标识（APA 式则是 "(2020)."），而本行又像一条新文献的开头
        （带类型标识，或以"作者, 2020."起头；APA 式带 "(2020)."）时另起一条；
        前后两行都带类型标识时也拆开。折成两行的长条目，后半截不像新条目开头，照旧并回去；
      - 条目前误加的列表符号（"- [1] …"）去掉，否则会被排成项目符号列表。
    只动参考文献章节（到下一个同级或更高级标题为止），代码块内不动。
    """
    if not content:
        return content
    lines = content.split("\n")
    out: list[str] = []
    in_refs = False
    ref_level = 0
    fence = None
    numbered_section = False
    prev_mark = prev_ends = False   # 上一行：带类型标识 / 以句号或网址结尾
    cur_mark = cur_apa = False      # 当前这一条（可能跨几行）里出现过类型标识 / APA 年份
    for raw in lines:
        stripped = raw.strip()
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", raw)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            out.append(raw)
            prev_mark = prev_ends = cur_mark = cur_apa = False
            continue
        if fence is not None:
            out.append(raw)
            continue
        heading = _ANY_HEADING_RE.match(stripped)
        if heading:
            level = len(heading.group(1))
            if _REF_SECTION_HEADING_RE.match(stripped):
                in_refs, ref_level, numbered_section = True, level, False
            elif in_refs and level <= ref_level:
                in_refs = False
            out.append(raw)
            prev_mark = prev_ends = cur_mark = cur_apa = False
            continue
        if not in_refs or not stripped:
            out.append(raw)
            prev_mark = prev_ends = cur_mark = cur_apa = False
            continue
        numbered = bool(_REF_NUMBERED_ENTRY_RE.match(raw))
        numbered_section = numbered_section or numbered
        line = re.sub(r"^([ \t]*)[-*+][ \t]+(?=[\[［])", r"\1", raw) if numbered else raw
        mark = bool(_REF_TYPE_MARK_RE.search(stripped))
        apa = bool(_REF_APA_YEAR_RE.search(stripped[:200]))
        if numbered_section:
            starts_new = numbered
        else:
            gb_start = bool(_REF_GB_AUTHOR_YEAR_RE.match(stripped))
            starts_new = (prev_ends and ((cur_mark and (mark or gb_start)) or (cur_apa and apa))) \
                or (mark and prev_mark)
        if starts_new and out and out[-1].strip():
            out.append("")
            cur_mark = cur_apa = False
        out.append(line)
        cur_mark, cur_apa = cur_mark or mark, cur_apa or apa
        prev_mark, prev_ends = mark, bool(_REF_LINE_END_RE.search(stripped))
    return "\n".join(out)


def _normalize_for_export(content: str) -> str:
    """导出前对私有副本做的结构整理：伪标记还原 + 参考文献逐条成段。"""
    return _split_reference_entries(_normalize_pseudo_markup(content))


# ---------------------------------------------------------------------------
# 核心转换函数
# ---------------------------------------------------------------------------

class DocxEngineUnavailable(RuntimeError):
    repairable = False


def _prose_for_features(content: str) -> str:
    """Ignore literal examples when deciding whether native math is required."""
    content = re.sub(r"(?ms)^\s*(`{3,}|~{3,})[^\n]*\n.*?^\s*\1\s*$", "", content)
    return re.sub(r"(`+).*?\1", "", content)


def _has_math(content: str) -> bool:
    return bool(re.search(r"(?<![\\$])\$(?!\$)[^$\n]+(?<!\\)\$|^\s*\$\$|\\\([\s\S]*?\\\)|\\\[[\s\S]*?\\\]", _prose_for_features(content), re.M))


def _prepare_local_images(content: str, source_md: Path, workspace: Path, temporary: Path) -> tuple[str, int]:
    """Resolve against the original manuscript before relocating its UTF-8 copy.

    Both engines consume standalone Markdown images. Prepare only these actual
    references, never every figure in a project. Conversion intermediates are
    private; missing/unsupported images cannot become successful placeholders.
    """
    from urllib.parse import unquote
    from PIL import Image
    lines = []
    count = 0
    fence = None
    for line in content.splitlines(keepends=True):
        marker = re.match(r'^\s{0,3}(`{3,}|~{3,})', line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            lines.append(line)
            continue
        image = None if fence else re.fullmatch(r'\s*!\[([^\]]*)\]\((.+)\)\s*', line)
        if image is None:
            lines.append(line)
            continue
        ref = image.group(2).strip()
        titled = re.fullmatch(r'(<[^>]+>|.+?)\s+[\"\'][^\"\']*[\"\']', ref)
        ref = (titled.group(1) if titled else ref).strip('<>')
        ref = unquote(ref).replace('\\', '/')
        # No arbitrary host paths/URLs are read by a paper export.
        if not ref or re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', ref) or ref.startswith('/'):
            raise ValueError(f'Word 图片必须引用工作区内文件：{ref}')
        candidates = [source_md.parent / ref, workspace / ref, workspace / 'figures' / Path(ref).name]
        resolved = []
        for path in candidates:
            candidate = path.resolve()
            if candidate.is_relative_to(workspace) and candidate.is_file():
                resolved.append(candidate)
        # Retain the documented PNG-reference / PDF-only compatibility.
        if not resolved and Path(ref).suffix.lower() in {'.png', '.jpg', '.jpeg'}:
            resolved = [p.with_suffix('.pdf').resolve() for p in candidates
                        if p.with_suffix('.pdf').resolve().is_relative_to(workspace)
                        and p.with_suffix('.pdf').is_file()]
        if not resolved:
            raise ValueError(f'Word 图片不存在或不在工作区：{ref}')
        path = resolved[0]
        count += 1
        prepared = temporary / f'image-{count}.png'
        if path.suffix.lower() == '.pdf':
            if not _convert_pdf_to_png(path, prepared, dpi=350):
                raise ValueError(f'PDF 图表转换失败，未导出缺图的 Word：{ref}')
        else:
            try:
                with Image.open(path) as picture:
                    picture.load()
                    picture.convert('RGBA' if 'A' in picture.getbands() else 'RGB').save(prepared)
            except Exception as exc:
                raise ValueError(f'Word 图片无法读取，请提供可用图片：{ref}') from exc
        lines.append(f'![{image.group(1)}]({prepared.as_posix()})\n')
    return ''.join(lines), count


def markdown_to_docx(source_md: Path, output_path: Path, style_profile: Optional[Path] = None,
                     workspace: Optional[Path] = None, engine: str = "auto") -> Path:
    """Normalize a private UTF-8 copy; replace the output only after validation.

    Applies to CLI, workflow and editor exports, including template content builds.
    A failed converter cannot truncate the previous good Word document.
    """
    import os
    import tempfile
    import zipfile
    import xml.etree.ElementTree as ET
    source_md, output_path = Path(source_md).resolve(), Path(output_path).resolve()
    content = _normalize_for_export(_read_markdown(source_md))
    workspace = Path(workspace).resolve() if workspace else source_md.parent
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".docx-source-", dir=source_md.parent) as src_temp, \
            tempfile.TemporaryDirectory(prefix=".docx-output-", dir=output_path.parent) as out_temp:
        content, expected_images = _prepare_local_images(content, source_md, workspace, Path(src_temp))
        normalized = Path(src_temp) / source_md.name
        normalized.write_text(content, encoding="utf-8", newline="\n")
        built = Path(out_temp) / output_path.name
        _markdown_to_docx_unchecked(normalized, built, style_profile, workspace, engine)
        with zipfile.ZipFile(built) as archive:
            if archive.testzip():
                raise ValueError("Word 文件校验失败，保留旧版")
            document = ET.fromstring(archive.read("word/document.xml"))
            ET.fromstring(archive.read("[Content_Types].xml"))
            drawings = document.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}drawing')
            if len(drawings) < expected_images:
                raise ValueError(f'Word 正文图片未完整嵌入（应有 {expected_images} 张，实际 {len(drawings)} 张），保留旧版')
        os.replace(built, output_path)
    return output_path


def _markdown_to_docx_unchecked(
    source_md: Path,
    output_path: Path,
    style_profile: Optional[Path] = None,
    workspace: Optional[Path] = None,
    engine: str = "auto",
) -> Path:
    """
    将 Markdown 文件转换为格式化的 .docx 文档。

    Args:
        source_md: 源 .md 文件路径
        output_path: 输出 .docx 文件路径
        style_profile: 可选的样式配置 JSON 路径
        workspace: 工作区根目录（用于解析图片相对路径）
        engine: 引擎选择 - "auto" / "python" / "node"
                auto 模式下：含 $...$ 公式时优先用 node，否则用 python

    Returns:
        生成的 .docx 文件路径

    Raises:
        FileNotFoundError: source_md 不存在
        ValueError: 文件无法解码
    """
    if not source_md.exists():
        raise FileNotFoundError(f"源文件不存在: {source_md}")

    # 读取内容用于引擎选择和后续处理
    content = _read_markdown(source_md)

    # ⛔ Markdown 伪标记修复（章节标题/图注/独行公式编号被 LLM 写成 list 项时还原），
    # 参考文献逐条成段。不依赖语义判断，只看结构特征；在代码块内不会动。
    _normalized_content = _normalize_for_export(content)
    if _normalized_content != content:
        content = _normalized_content
        # 同步落盘到一个清洗后的副本，让 Node 引擎也用这份
        _normalized_md = source_md.with_name(source_md.stem + "._normalized.md")
        _normalized_md.write_text(content, encoding="utf-8", newline="\n")
        _source_for_engine = _normalized_md
        log.info("Pseudo-markup normalized for %s", source_md.name)
    else:
        _source_for_engine = source_md

    # The public wrapper has prepared exactly the referenced images in its
    # private directory. Do not convert/trim unrelated figures in the workspace.
    if workspace is None:
        workspace = source_md.parent

    # 引擎选择
    chosen_engine = engine
    if chosen_engine == "auto":
        # 检测复杂内容，优先选 Node 引擎（更专业）
        # 1. 行内/块公式
        has_inline_math = _has_math(content)
        has_block_math = False  # _has_math covers both delimiter families.
        # 2. 三线表（Markdown 表格）
        has_table = bool(re.search(r"^\s*\|.+\|\s*$", content, re.MULTILINE)) and \
                    bool(re.search(r"^\s*\|[\s\-:|]+\|\s*$", content, re.MULTILINE))
        # 3. 上标引用 [1] [2,3] [4-6]
        has_citation = bool(re.search(r"\[\d+(?:[,\-]\d+)*\]", content))
        # 4. 参考文献区域
        has_references = any(_REF_SECTION_HEADING_RE.match(line.strip()) for line in content.splitlines())
        # 5. 学术格式特征：摘要 + 关键词
        has_academic = bool(re.search(
            r"^#{1,3}\s*(?:摘要|Abstract)\s*$", content, re.MULTILINE | re.IGNORECASE
        )) or "关键词：" in content or "Keywords:" in content

        # 任意一项触发就用 Node（如果可用）
        node_indicators = {
            "公式": has_inline_math or has_block_math,
            "三线表": has_table,
            "上标引用": has_citation,
            "参考文献": has_references,
            "学术格式": has_academic,
        }
        active_indicators = [k for k, v in node_indicators.items() if v]

        if active_indicators and _is_node_engine_available():
            chosen_engine = "node"
            log.info("Auto-detected complex content [%s], using Node engine",
                     ", ".join(active_indicators))
        elif active_indicators:
            raise DocxEngineUnavailable("Word 专业转换引擎不可用，无法保真导出" + "、".join(active_indicators)
                                        + "；请检查 Node.js 和 docx-cn-engine 安装，不会降级生成残缺文档。")
        else:
            chosen_engine = "python"
            log.info("Simple content, using Python engine")

    # Node 引擎路径
    if chosen_engine == "node":
        if not _is_node_engine_available():
            raise DocxEngineUnavailable("Word 专业转换引擎不可用，请检查 Node.js 和 docx-cn-engine 安装。")
        try:
            _result = _convert_with_node(_source_for_engine, output_path, workspace, style_profile)
        except Exception as e:
            # Syntax failures can be repaired in source. Infrastructure failures
            # cannot be fixed by spending model tokens rewriting a paper.
            if "DOCX_FORMULA_ERROR" in str(e):
                raise ValueError("Word 公式转换失败，请修正源稿中的公式：" + str(e)) from e
            raise DocxEngineUnavailable("Word 转换引擎执行失败，保留旧版且未降级；请检查导出环境。" + str(e)) from e
        else:
            # 清理临时副本
            if _source_for_engine != source_md:
                try:
                    _source_for_engine.unlink()
                except Exception:
                    pass
            return _result

    # Python 引擎路径（默认）
    if chosen_engine != "python":
        raise ValueError("未知 Word 导出引擎：" + str(engine))
    if _has_math(content):
        raise DocxEngineUnavailable("当前 Python 转换器不支持原生 Word 公式，请使用 auto 或 node 引擎；未降级公式。")
    try:
        return _convert_with_python(content, source_md, output_path, style_profile, workspace)
    finally:
        if _source_for_engine != source_md:
            try:
                _source_for_engine.unlink()
            except Exception:
                pass


def _is_node_engine_available() -> bool:
    """检测 Node.js 引擎是否可用。"""
    engine_dir = _resolve_engine_dir()
    if not engine_dir or not engine_dir.is_dir():
        return False
    if not (engine_dir / "md_to_docx.js").exists():
        return False
    if not (engine_dir / "node_modules").is_dir():
        return False
    # 检测系统是否有 node 可执行文件
    import shutil as _shutil
    if _shutil.which("node"):
        return True
    # Windows 默认安装位置
    for candidate in ["D:\\nodejs\\node.exe", "C:\\Program Files\\nodejs\\node.exe"]:
        if Path(candidate).exists():
            return True
    return False


def _resolve_engine_dir() -> Optional[Path]:
    """查找 docx-cn-engine 目录。优先级：
        1. 环境变量 DOCX_CN_ENGINE_DIR
        2. 与 docx_export.py 同目录下的 docx-cn-engine
        3. 上层 tools/docx-cn-engine（_utils/ 复制时实际目录）
    """
    import os as _os
    env_path = _os.environ.get("DOCX_CN_ENGINE_DIR")
    if env_path:
        p = Path(env_path)
        if p.is_dir():
            return p
    same_dir = Path(__file__).resolve().parent / "docx-cn-engine"
    if same_dir.is_dir():
        return same_dir
    # 尝试沿路径向上找：_utils → workspace → 项目根 / tools
    cur = Path(__file__).resolve().parent
    for _ in range(5):
        cand = cur / "tools" / "docx-cn-engine"
        if cand.is_dir():
            return cand
        cur = cur.parent
    return None


def _find_node_executable() -> Optional[str]:
    """查找 node 可执行文件路径。"""
    import shutil as _shutil
    found = _shutil.which("node")
    if found:
        return found
    for candidate in ["D:\\nodejs\\node.exe", "C:\\Program Files\\nodejs\\node.exe"]:
        if Path(candidate).exists():
            return candidate
    return None


def _convert_with_node(source_md: Path, output_path: Path, workspace: Optional[Path],
                       style_profile: Optional[Path] = None) -> Path:
    """使用 Node.js docx-cn-engine 转换。"""
    import subprocess as _subprocess
    node_exe = _find_node_executable()
    if not node_exe:
        raise RuntimeError("Node.js 不可用")

    engine_dir = _resolve_engine_dir()
    if engine_dir is None:
        raise RuntimeError("docx-cn-engine 目录找不到")
    script = engine_dir / "md_to_docx.js"
    if not script.exists():
        raise RuntimeError(f"md_to_docx.js 不存在: {script}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        node_exe, str(script),
        "--source", str(source_md),
        "--output", str(output_path),
    ]
    if workspace:
        cmd.extend(["--workspace", str(workspace)])
    if style_profile and style_profile.exists():
        cmd.extend(["--profile", str(style_profile)])

    # Windows 下 Node stderr 默认 GBK，errors='replace' 防解码失败
    result = _subprocess.run(
        cmd, capture_output=True, text=True, timeout=120,
        encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(f"Node 引擎失败 (exit {result.returncode}): {result.stderr or result.stdout}")
    log.info("DOCX exported via Node engine: %s (profile=%s)",
             output_path, style_profile.name if style_profile else 'default')
    return output_path


def _convert_with_python(
    content: str,
    source_md: Path,
    output_path: Path,
    style_profile: Optional[Path],
    workspace: Optional[Path],
) -> Path:
    """使用 python-docx 转换。"""
    profile = load_style_profile(style_profile)
    if workspace is None:
        workspace = source_md.parent

    # 解析并丢弃 frontmatter（封面已不再渲染，但仍要把它从正文剥离避免被误当文本）
    fm_meta, body = _parse_frontmatter(content)
    lines = body.splitlines()

    doc = Document()
    _setup_page(doc, profile)
    _render_markdown(doc, lines, profile, workspace)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    log.info("DOCX exported via Python engine: %s (%d bytes)",
             output_path, output_path.stat().st_size)
    return output_path


def _setup_page(doc: Document, profile: dict):
    """设置页面大小和页边距。"""
    page_cfg = profile.get("page", {})
    section = doc.sections[0]
    section.top_margin = Cm(page_cfg.get("margin_top_cm", 2.5))
    section.bottom_margin = Cm(page_cfg.get("margin_bottom_cm", 2.5))
    section.left_margin = Cm(page_cfg.get("margin_left_cm", 2.5))
    section.right_margin = Cm(page_cfg.get("margin_right_cm", 2.5))
    # A4: 21cm x 29.7cm
    if page_cfg.get("size", "A4") == "A4":
        section.page_width = Cm(21)
        section.page_height = Cm(29.7)
    # 双栏（最小实验）：profile.page.columns>=2 时给整篇正文分栏
    cols = int(page_cfg.get("columns", 1) or 1)
    if cols >= 2:
        sectPr = section._sectPr
        for existing in sectPr.findall(qn("w:cols")):
            sectPr.remove(existing)
        space_twips = int(float(page_cfg.get("column_spacing_cm", 0.6)) * 567)
        sectPr.append(parse_xml(
            f'<w:cols {nsdecls("w")} w:num="{cols}" w:space="{space_twips}" w:equalWidth="1"/>'
        ))


def _text_column_width_cm(profile: dict) -> float:
    """按边距+栏数算单栏可用文本宽（cm），供双栏时图/表缩放用。"""
    page_cfg = profile.get("page", {})
    left = float(page_cfg.get("margin_left_cm", 2.5))
    right = float(page_cfg.get("margin_right_cm", 2.5))
    cols = int(page_cfg.get("columns", 1) or 1)
    spacing = float(page_cfg.get("column_spacing_cm", 0.6))
    text_w = 21.0 - left - right
    if cols >= 2:
        return (text_w - spacing * (cols - 1)) / cols
    return text_w


def _render_markdown(doc: Document, lines: list[str], profile: dict, workspace: Path):
    """逐行解析 Markdown 并渲染到 Document。"""
    i = 0
    total = len(lines)
    in_code_block = False
    code_lines: list[str] = []
    in_table = False
    table_lines: list[str] = []
    in_references = False
    in_abstract = False  # 是否在摘要区（仅摘要正文段落支持 **加粗** 行内解析）
    first_h1_seen = False
    body_buffer: list[str] = []  # 连续正文行缓冲

    def flush_body():
        """将缓冲的正文行合并为一个段落（识别关键词、参考文献、普通正文）。"""
        nonlocal body_buffer
        if not body_buffer:
            return
        text = " ".join(body_buffer)
        # ⛔ 关键词识别：**关键词**：内容 / 关键词：内容 / **Keywords**: content
        kw_match = re.match(
            r'^\*{0,2}(关键词|关键字|Key\s*words|Keywords)\*{0,2}\s*[：:]\s*(.+)$',
            text, re.IGNORECASE,
        )
        if kw_match:
            label_raw = kw_match.group(1)
            value = kw_match.group(2)
            is_cn = any('\u4e00' <= c <= '\u9fff' for c in label_raw)
            label_out = "关键词：" if is_cn else "Keywords: "
            _add_keywords_paragraph(doc, label_out, value, profile)
            body_buffer = []
            return
        if in_references and re.match(r"^\[\d+\]", text):
            _add_reference_paragraph(doc, text, profile)
        elif in_abstract:
            # 仅摘要正文支持 **加粗**（关键方法/结果）；关键词已在上面单独处理
            _add_abstract_body_paragraph(doc, text, profile)
        else:
            _add_body_paragraph(doc, text, profile)
        body_buffer = []

    def flush_table():
        """将缓冲的表格行渲染为三线表。"""
        nonlocal table_lines, in_table
        if not table_lines:
            in_table = False
            return
        # 解析表格
        parsed_rows = []
        for tl in table_lines:
            cells = [c.strip() for c in tl.strip().strip("|").split("|")]
            # 跳过分隔行 |---|---|
            if all(re.fullmatch(r"[-:]+", c) for c in cells if c):
                continue
            parsed_rows.append(cells)
        if len(parsed_rows) >= 2:
            headers = parsed_rows[0]
            data_rows = parsed_rows[1:]
            # 补齐列数
            max_cols = max(len(headers), max((len(r) for r in data_rows), default=0))
            headers = headers + [""] * (max_cols - len(headers))
            data_rows = [r + [""] * (max_cols - len(r)) for r in data_rows]
            _add_three_line_table(doc, headers, data_rows, profile)
        elif len(parsed_rows) == 1:
            # 只有表头没有数据，作为普通段落
            _add_body_paragraph(doc, " | ".join(parsed_rows[0]), profile)
        table_lines = []
        in_table = False

    while i < total:
        line = lines[i]
        stripped = line.strip()

        # --- 代码块处理 ---
        if stripped.startswith("```"):
            if in_code_block:
                # 结束代码块
                flush_body()
                _add_code_block(doc, code_lines, profile)
                code_lines = []
                in_code_block = False
            else:
                # 开始代码块
                flush_body()
                if in_table:
                    flush_table()
                in_code_block = True
                code_lines = []
            i += 1
            continue

        if in_code_block:
            code_lines.append(line.rstrip())
            i += 1
            continue

        # --- 表格处理 ---
        if stripped.startswith("|"):
            flush_body()
            if not in_table:
                in_table = True
                table_lines = []
            table_lines.append(stripped)
            i += 1
            continue
        elif in_table:
            flush_table()

        # --- 空行 ---
        if not stripped:
            flush_body()
            i += 1
            continue

        # --- 分隔线 ---
        if re.fullmatch(r"[-*_]{3,}", stripped):
            flush_body()
            i += 1
            continue

        # --- 标题 ---
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading_match:
            flush_body()
            level = len(heading_match.group(1))
            text = heading_match.group(2).strip()

            # 检测是否进入参考文献区域
            if level == 1 or level == 2:
                normalized = text.replace(" ", "").lower()
                if "参考文献" in normalized or "references" in normalized:
                    in_references = True
                elif level <= 2:
                    in_references = False

            # ⛔ 摘要识别（仅 level 2）：## 摘要 / ## Abstract / ## Summary
            normalized_h = text.replace(" ", "").lower()
            is_abstract = level == 2 and (
                normalized_h == "摘要" or normalized_h == "abstract"
                or normalized_h == "summary"  # MCM/ICM 惯例
                or normalized_h == "summarysheet"  # 美赛 "## Summary Sheet"（去空格小写后）
                or normalized_h.startswith("摘要(") or normalized_h.startswith("摘要（")
            )
            if is_abstract:
                in_abstract = True  # 进入摘要区：后续正文段落走加粗解析
                _add_abstract_heading(doc, text, profile)
                i += 1
                continue
            # 任何其它标题（level 1/2/3…）都结束摘要区，正文回到普通渲染
            # （统计建模中英双摘要之间无其它标题，## Abstract 会重新置 True，不受影响）
            in_abstract = False

            is_first = (level == 1 and not first_h1_seen)
            if level == 1:
                first_h1_seen = True
            _add_heading(doc, text, level, profile, first_heading=is_first)
            i += 1
            continue

        # --- 图片 ---
        img_match = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", stripped)
        if img_match:
            flush_body()
            alt_text = img_match.group(1)
            img_path = img_match.group(2)
            _add_image(doc, img_path, workspace, profile)
            # 如果 alt_text 非空，作为图题
            if alt_text and alt_text.strip():
                cap_para = doc.add_paragraph()
                cap_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                cap_para.paragraph_format.first_line_indent = Pt(0)
                cap_run = cap_para.add_run(alt_text.strip())
                cap_run.font.size = Pt(10.5)
                _set_run_fonts(cap_run, profile, "body")
            i += 1
            continue

        # --- 列表项 ---
        list_match = re.match(r"^(\s*)([-*+]|\d+[.)]) (.+)$", stripped)
        if list_match:
            flush_body()
            text = list_match.group(3)
            para = doc.add_paragraph()
            para.paragraph_format.first_line_indent = Pt(0)
            para.paragraph_format.left_indent = Cm(0.74)
            bullet = list_match.group(2)
            if re.match(r"\d+", bullet):
                prefix = bullet + " "
            else:
                prefix = "• "
            run = para.add_run(prefix + _clean_markdown_inline(text))
            run.font.size = Pt(profile.get("body", {}).get("font_size_pt", 12))
            _set_run_fonts(run, profile, "body")
            i += 1
            continue

        # --- 普通正文（缓冲连续行） ---
        body_buffer.append(stripped)
        i += 1

    # 处理末尾残留
    flush_body()
    if in_code_block and code_lines:
        _add_code_block(doc, code_lines, profile)
    if in_table:
        flush_table()


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Markdown → DOCX 转换（中文学术格式）")
    parser.add_argument("--source", "-s", type=Path, required=True, help="源 Markdown 文件路径")
    parser.add_argument("--output", "-o", type=Path, required=True, help="输出 DOCX 文件路径")
    parser.add_argument("--profile", "-p", type=Path, default=None,
                        help="样式配置 JSON 路径（默认使用 default_cn_thesis.json）")
    parser.add_argument("--workspace", "-w", type=Path, default=None,
                        help="工作区根目录（用于解析图片相对路径）")
    parser.add_argument("--engine", "-e", type=str, default="auto",
                        choices=["auto", "python", "node"],
                        help="引擎选择：auto（自动）/ python（python-docx）/ node（docx.js）")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    try:
        result = markdown_to_docx(
            source_md=args.source,
            output_path=args.output,
            style_profile=args.profile,
            workspace=args.workspace,
            engine=args.engine,
        )
        print(f"✓ 导出成功: {result}")
    except FileNotFoundError as e:
        print(f"✗ 错误: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"✗ 编码错误: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"✗ 转换失败: {e}", file=sys.stderr)
        sys.exit(3)


if __name__ == "__main__":
    main()
