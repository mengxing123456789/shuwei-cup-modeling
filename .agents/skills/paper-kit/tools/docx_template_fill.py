#!/usr/bin/env python3
"""docx_template_fill.py — 把 Markdown 内容填充到用户上传的 .docx 模板。

实现策略：
1. 调用 Node 引擎（md_to_docx.js）把 markdown 渲染成「内容 docx」
   - 复用所有现有渲染能力：OMML 公式 / 三线表 / 上标 / 代码块 / 浅灰底色 / 图片嵌入
2. 打开内容 docx，按章节切元素列表（标题 / 摘要 / 关键词 / 正文 / 参考文献 / 附录）
3. 打开用户模板，启发式找占位段，跨文档深拷贝元素插入到对应位置
4. 跨文档转移图片：复制 word/media/ 下的图片文件 + 注册新 relationship + 重写 rId
5. 保留模板原有的封面表格、页眉页脚、页边距、字体设置

用法：
    python docx_template_fill.py \\
        --template path/to/template.docx \\
        --source paper/main.md \\
        --output paper/main.docx \\
        --workspace .
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import logging
import re
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import List, Optional

from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

log = logging.getLogger("docx_template_fill")

# WordprocessingML 命名空间常量
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
PIC_NS = "http://schemas.openxmlformats.org/drawingml/2006/picture"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"


# ---------------------------------------------------------------------------
# .dotx → .docx 兼容
# ---------------------------------------------------------------------------

def _convert_dotx_to_docx(dotx_path: Path) -> Path:
    """把 .dotx (Word 模板，content-type=template.main+xml) 重写为 .docx
    (content-type=document.main+xml)，其他结构原样保留。

    返回：转换后的 .docx 路径（在系统临时目录，进程退出时自动清理）。
    """
    import hashlib
    import io
    import os
    import zipfile as _zip

    if not dotx_path.exists():
        raise FileNotFoundError(dotx_path)

    # ⛔ 写到系统临时目录而非模板同目录，避免污染 user_data/ 等用户目录
    # 同时用确定性名（含原文件 stem）方便日志关联
    tmp_root = Path(tempfile.gettempdir()) / "docx_template_fill_dotx_cache"
    tmp_root.mkdir(parents=True, exist_ok=True)
    source_bytes = dotx_path.read_bytes()
    # Same-named templates from different workspaces must never share content.
    key = hashlib.sha256(source_bytes).hexdigest()
    out_path = tmp_root / f"{key}.converted.docx"

    # 重写 [Content_Types].xml，把 template.main+xml → document.main+xml
    TEMPLATE_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.template.main+xml"
    DOC_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"

    # 直接读 dotx → 写 out_path（避免先 copyfile 再原子替换的中间文件污染）
    with tempfile.TemporaryDirectory(prefix="dotx-", dir=tmp_root) as build:
        staged = Path(build) / "converted.docx"
        with _zip.ZipFile(io.BytesIO(source_bytes), "r") as zin:
            with _zip.ZipFile(staged, "w", _zip.ZIP_DEFLATED) as zout:
                for item in zin.infolist():
                    data = zin.read(item.filename)
                    if item.filename == "[Content_Types].xml":
                        text = data.decode("utf-8").replace(TEMPLATE_CT, DOC_CT)
                        data = text.encode("utf-8")
                    zout.writestr(item, data)
        os.replace(staged, out_path)
    return out_path




def _transfer_images(rendered_doc, target_doc, elements_to_transfer: list) -> dict:
    """把 rendered_doc 中被引用的图片复制到 target_doc，并返回 rId 映射 {old_rId: new_rId}。

    流程：
      1. 扫描 elements_to_transfer 中所有 <a:blip r:embed="rIdN">，收集旧 rId 集合
      2. 在 rendered_doc 的关系（part.rels）找到对应 image part
      3. 把这些 image part 的二进制注册到 target_doc 的 part 集合中
      4. target_doc.part.relate_to(image_part, IMAGE_TYPE) 得到新 rId
      5. 返回 old_rId → new_rId 映射
    """
    from docx.opc.constants import RELATIONSHIP_TYPE as RT

    rendered_part = rendered_doc.part
    target_part = target_doc.part

    rid_map: dict[str, str] = {}

    # 收集被引用的 rId（含 a:blip / r:link / w:hyperlink 等）
    embed_attr = f"{{{R_NS}}}embed"
    link_attr = f"{{{R_NS}}}link"

    referenced_rids: set[str] = set()
    for el in elements_to_transfer:
        for blip in el.iter(f"{{{A_NS}}}blip"):
            r = blip.get(embed_attr)
            if r:
                referenced_rids.add(r)
            r2 = blip.get(link_attr)
            if r2:
                referenced_rids.add(r2)

    if not referenced_rids:
        return rid_map

    log.info("Transferring %d image relationship(s) cross-document",
             len(referenced_rids))

    for old_rid in referenced_rids:
        # 在源 doc 中根据 rId 找到 image part
        src_rels = rendered_part.rels
        if old_rid not in src_rels:
            raise ValueError("模板内容图片关系缺失，未发布缺图 Word：" + old_rid)
        src_rel = src_rels[old_rid]
        if src_rel.is_external:
            # 外部链接：直接在目标 doc 注册同样的外部链接
            new_rid = target_part.relate_to(
                src_rel.target_ref, src_rel.reltype, is_external=True,
            )
            rid_map[old_rid] = new_rid
            continue
        src_image_part = src_rel.target_part

        # 在目标 doc 中注册同样的 image part
        # docx.opc.part.Part 实例可以直接被 relate_to 接受
        try:
            import io
            # Register image bytes in the destination package: reusing a Part
            # named image1.png can overwrite the template's own logo/image1.png.
            new_rid, _ = target_part.get_or_add_image(io.BytesIO(src_image_part.blob))
            rid_map[old_rid] = new_rid
        except Exception as e:
            raise ValueError("模板图片转移失败，未发布缺图 Word：" + str(e)) from e

    return rid_map


def _rewrite_image_rids(
    elements: list,
    rid_map: dict,
    drawing_id_counter: Optional[list[int]] = None,
):
    """重写跨文档关系，并为插入的绘图分配目标文档唯一 ID。

    Word 的图片关系 ID（``rId``）和绘图对象 ID（``wp:docPr/@id``、
    ``pic:cNvPr/@id``）是两套不同的命名空间。之前只重写了 rId，模板中已有
    图片与渲染文档中的图片会经常从 1 重新编号，产生不合法的重复对象身份。
    这与图片段落继承固定行高是独立问题，不把 ID 冲突当作叠图的唯一根因。
    调用方传入单调递增 counter 后，所有跨文档插入的绘图对象都
    会获得目标文档范围内的新 ID；不传 counter 时保留旧的纯关系重写行为，
    兼容外部调用者。
    """
    embed_attr = f"{{{R_NS}}}embed"
    link_attr = f"{{{R_NS}}}link"
    for el in elements:
        for blip in el.iter(f"{{{A_NS}}}blip"):
            for attr in (embed_attr, link_attr):
                old = blip.get(attr)
                if old and old in rid_map:
                    blip.set(attr, rid_map[old])
        if drawing_id_counter is not None:
            for drawing in el.iter(f"{{{WP_NS}}}docPr"):
                drawing.set("id", str(drawing_id_counter[0]))
                drawing_id_counter[0] += 1
            for drawing in el.iter(f"{{{PIC_NS}}}cNvPr"):
                drawing.set("id", str(drawing_id_counter[0]))
                drawing_id_counter[0] += 1



# ---------------------------------------------------------------------------
# 占位识别正则
# ---------------------------------------------------------------------------

_TITLE_PLACEHOLDER_RE = re.compile(
    r"(标题|论文.*?标题|题目).*?[(（](此处|这里|本处)?.*?(填|换成?|为|输入)?.*?[)）]"
)

_INSTRUCTION_RE = re.compile(
    r"^\s*[(（]?\s*(注[:：]|说明[:：]|示例[:：]|例如|例[:：])"
)

_ABSTRACT_RE = re.compile(r"^\s*(摘\s*要|Abstract)\s*$", re.IGNORECASE)
_KEYWORDS_RE = re.compile(r"^\s*\*{0,2}(关键词|关键字|Key\s*words?)\*{0,2}\s*[：:]", re.IGNORECASE)
_BODY_PLACEHOLDER_RE = re.compile(
    r"^\s*正文\s*("
    r"内容\s*[(（].*?[)）]?"
    r"|大纲"
    r"|.*?(另起|开始).*?"
    r"|（.*?）"
    r"|\(.*?\)"
    r")?\s*$"
)
_REFERENCES_RE = re.compile(r"^\s*(参考文献|References)(\s|（|\(|$)", re.IGNORECASE)
_APPENDIX_RE = re.compile(r"^\s*(附\s*录|Appendix)(\s|（|\(|$)", re.IGNORECASE)
# 附录标题：“附录”“附录A 调查问卷”“附录一：访谈提纲”“附录1”“Appendix B”“AppendixA”都算；正文里以“附录 A 给出了……”
# 开头的句子不算（10-14 复审：以前“附录一 调查问卷”这类带名字的认不出，附录被并进正文、排到了参考文献前面）
_APPENDIX_HEAD_RE = re.compile(
    r"^\s*(?:附\s*录|appendix)\s*(?:[A-Za-z]|\d{1,2}|[一二三四五六七八九十]{1,3})?\s*(?:$|[:：.．、\-—–\s（(])", re.I)


def _is_appendix_heading(text: str) -> bool:
    norm = (text or "").strip()
    return bool(_APPENDIX_HEAD_RE.match(norm)) and len(norm) <= 40 and not re.search(r"[。！？!?；;]$", norm)
_ACK_RE = re.compile(r"^\s*(致\s*谢|Acknowledg)", re.IGNORECASE)


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------

def _is_title_placeholder(text: str) -> bool:
    norm = (text or "").strip()
    if not norm:
        return False
    if "标题" in norm and ("此处" in norm or "这里" in norm or "换成" in norm or "填" in norm):
        return True
    return False


def _is_instruction_paragraph(text: str) -> bool:
    norm = (text or "").strip()
    if not norm:
        return False
    if _INSTRUCTION_RE.search(norm):
        return True
    if "(说明" in norm or "（说明" in norm:
        return True
    if "请删除" in norm or "看完后删除" in norm or "删除该" in norm:
        return True
    if "示例段落" in norm or "本段为示例" in norm:
        return True
    if "[编号]" in norm and ("作者" in norm or "文献" in norm):
        return True
    if "参考文献的编号" in norm or "参考文献按" in norm:
        return True
    if "参考文献中" in norm and ("表述方式" in norm or "格式" in norm):
        return True
    if norm.startswith("书籍") and "表述方式" in norm:
        return True
    return False


# 模板里讲排版要求的条目（“1. 正文用小四号宋体，1.5 倍行距”）：是给作者看的说明，不是样例论文的正文
_FORMAT_NOTE_RE = re.compile(
    r"字体|字号|行距|页边距|宋体|黑体|楷体|仿宋|Times New Roman|小[一二三四五六]号|[一二三四五六]号字|对齐|缩进|"
    r"格式要求|撰写要求|撰写格式|撰写规范|书写要求|排版|装订|打印|A4|页眉|页脚|页码|字数要求")
SAMPLE_PARAGRAPH_CHARS = 40     # 这么长的一段才算“成段的文字”
SAMPLE_PARAGRAPHS = 3           # 模板里有这么多段成段的文字，就是带样例的模板


def _is_sample_text(text: str) -> bool:
    """有字、又不是填写说明或排版要求：样例论文的正文。"""
    return bool(text) and not _is_instruction_paragraph(text) and not _FORMAT_NOTE_RE.search(text)


# 原创性声明、使用授权书这类固定条款：成段、带句号，但不是样例论文
_DECLARATION_RE = re.compile(r"声明|承诺|授权|版权|原创|郑重|保证|签名|签字|保密|知识产权|使用规定|学位论文作者|"
                             r"copyright|declar|hereby|certif|authori[sz]|plagiari|originality|signature", re.I)
_SENTENCE_END_RE = re.compile(r"[。！？；!?;]|\.(?:\s|$)")
SAMPLE_PARAGRAPH_WORDS = 25     # 英文的一段要这么多个词才算成段


def _is_sample_paragraph(text: str) -> bool:
    """一段成段的样例文字（数“模板带不带样例”“填完还剩多少样例”用）：一段完整的话——中文 40 字以上、英文 25 个词
    以上、带句末标点——不是填写说明、排版要求，也不是封面上的一行、原创性声明和授权书这类固定条款
    （10-14 复审：带声明页、英文封面的模板以前被当成“带样例”，没识别过就拦着不让导出）。"""
    norm = (text or "").strip()
    if not _is_sample_text(norm) or _DECLARATION_RE.search(norm) or not _SENTENCE_END_RE.search(norm):
        return False
    words = len(re.findall(r"[A-Za-z]+", norm))
    if len(re.findall(r"[一-鿿]", norm)) >= words:
        return len(re.sub(r"\s+", "", norm)) >= SAMPLE_PARAGRAPH_CHARS
    return words >= SAMPLE_PARAGRAPH_WORDS


def _index(value, what: str = ""):
    """占位映射里的一个序号：只认整数（3.0、"3" 这种意思明确的也算）。小数、布尔、别的字符串一律不用——
    以前这些会让整个导出抛 TypeError，true / false 还被当成第 1 / 第 0 段。"""
    if isinstance(value, bool):
        pass
    elif isinstance(value, int):
        return value
    elif isinstance(value, float) and value.is_integer():
        return int(value)
    elif isinstance(value, str) and re.fullmatch(r"\s*-?\d+\s*", value):
        return int(value)
    if value is not None:
        log.warning("template_map 的 %s 里有一个不是整数的序号 %r，没有用它", what or "序号", value)
    return None


def _indices(value, what: str = "") -> list:
    return [i for i in (_index(v, what) for v in (value if isinstance(value, list) else [])) if i is not None]


def _delete_paragraph(p):
    """删除 paragraph 对象。"""
    el = p._element
    parent = el.getparent()
    if parent is not None:
        parent.remove(el)


def _para_text(para_elem) -> str:
    """提取 <w:p> 元素的纯文本（含所有 <w:t>）。"""
    if para_elem is None:
        return ""
    parts = []
    for t in para_elem.iter(f"{{{W_NS}}}t"):
        if t.text:
            parts.append(t.text)
    return "".join(parts).strip()


def _para_heading_level(para_elem) -> int:
    """从 pStyle 推断 Heading level。1-6 对应 Heading1-Heading6，否则 0。"""
    if para_elem is None:
        return 0
    pStyle = para_elem.find(f".//{{{W_NS}}}pPr/{{{W_NS}}}pStyle")
    if pStyle is None:
        return 0
    val = pStyle.get(f"{{{W_NS}}}val", "")
    m = re.match(r"Heading(\d+)", val)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return 0
    if val == "Title":
        return 1
    return 0


_M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
_P_TAG = f"{{{W_NS}}}p"
_TBL_TAG = f"{{{W_NS}}}tbl"
_SDT_TAG = f"{{{W_NS}}}sdt"
_OBJECT_TAGS = (f"{{{W_NS}}}drawing", f"{{{W_NS}}}pict", f"{{{W_NS}}}object",
                f"{{{_M_NS}}}oMath", f"{{{_M_NS}}}oMathPara")


def _holds_object(p_el) -> bool:
    """段落里有图、公式或嵌入对象。"""
    return any(True for _ in p_el.iter(*_OBJECT_TAGS))


def _holds_section_break(p_el) -> bool:
    """段落带着分节符（这一节的页面设置、页眉页脚挂在它上面）。"""
    ppr = p_el.find(f"{{{W_NS}}}pPr")
    return ppr is not None and ppr.find(f"{{{W_NS}}}sectPr") is not None


def sample_leftovers(start_el, stop_els, deleting, keep=frozenset(), preserved_tables=frozenset()) -> list:
    """样例论文式模板里，夹在要删的样例段落中间的表格、图片、公式和空行（返回要一并删掉的元素）。

    模板段落清单里这些东西是 [表 N] 和 <空>，template_map 的 delete_paragraph_indices 只列得到有字的段落；
    光删有字的段落，成品的正文和参考文献之间会留下几页样例表格、样例图片和空行。

    从正文位置 start_el 往后看，到下一个固定位置为止：stop_els 里的参考文献 / 附录位置，或者一个没被删的
    “参考文献 / 附录 / 致谢”标题，或者文末（实验报告、课程报告的模板后面常常什么标题都没有）。没被列进删除的
    有字段落、留给作者填的段（keep）、点名保留的表格（preserved_tables）、像待填表的表格（成绩评定、评语、签字这类
    字眼，又有空着等人填的格子）、内容控件、分节符把这一段切成几块，只有块里确实有要删的样例文字（deleting 里有字，
    又不是“（说明：……）”这类填写说明、也不是“正文用小四号宋体”这类排版要求的段落）才清这一块：
    - 排在这一块最后一段样例文字之前的表格、只有图 / 公式 / 对象的段落、空行、只带分页符的段落：删；
    - 最后一段样例文字之后的空行和分页是给下一部分留的版式（空一行、参考文献另起一页），保留；之后的表格：删
      （样例论文最后的表格；模板固定的表格要在 preserve_table_indices 里点名）；之后的图片：后面还有固定内容
      （参考文献、附录、没被删的段落）就删，到文末、到分节符才结束的那一块不删——落款、印章、校徽这类图没有办法
      点名保留（10-14 复审：走到文末时以前连模板末尾的固定表格和落款图片一起删了）；
    - 分节符：不动，也不跨过它清（分节以后是另一部分：横向页的附表、封底）。要删的样例段落带着分节符的，
      由调用方只清掉文字、留下段落（删了会改后面的页面设置）。
    占位式模板的正文位置后面只删得到填写说明，它旁边的表格（评分表一类）和空行原样不动。
    """
    if start_el is None:
        return []
    found: list = []
    block: list = []     # (元素, 是不是只起版式作用：空行 / 分页段)；要删的段落占一个位置、元素记 None
    last_sample = -1     # 这一块里最后一段要删的样例文字排第几（-1：这一块没有样例文字）

    def settle(keep_pictures: bool = False) -> None:
        nonlocal block, last_sample
        if last_sample >= 0:
            for pos, (el, layout_only) in enumerate(block):
                if el is None:
                    continue
                if pos > last_sample and (layout_only or (keep_pictures and el.tag != _TBL_TAG)):
                    continue
                found.append(el)
        block, last_sample = [], -1

    el = start_el.getnext()
    while el is not None:
        tag = el.tag
        if tag == _P_TAG:
            if el in stop_els:
                settle()
                return found
            text = _para_text(el)
            if el in deleting:
                if _is_sample_text(text):
                    last_sample = len(block)
                block.append((None, False))
                if _holds_section_break(el):
                    settle(keep_pictures=True)
            elif el in keep:
                settle()
            elif text:
                settle()
                if _REFERENCES_RE.match(text) or _is_appendix_heading(text) or _ACK_RE.match(text):
                    return found
            elif _holds_section_break(el):
                settle(keep_pictures=True)
            else:
                block.append((el, not _holds_object(el)))
        elif tag == _TBL_TAG:
            # 点名保留的、像待填表的是模板的固定内容。⛔ 只看字眼不行：样例论文里的数据表也会有“平均成绩”“专家评分”
            # “负责人”（10-14 复审：这样的样例表以前被永久留在成品里，映射里又没办法说“这张要删”）
            if el in preserved_tables or _looks_like_form(el):
                settle()
            else:
                block.append((el, False))
        elif tag == _SDT_TAG:
            settle()
        el = el.getnext()
    settle(keep_pictures=True)
    return found


MAP_NAME = "_template_map.json"
STAMP_NAME = "_template_map.stamp.json"     # 记着“这份映射是对着哪份模板填成过的”，见 usable_template_map


FINGERPRINT_PREFIX = "s2:"
_STAMP_PREFIXES = (FINGERPRINT_PREFIX, "f1:")


def _stable_text(el) -> str:
    """一个段落 / 表格里的文字，不算域的结果（封面上的日期、页码这类 Word 打开时会自己更新的）。"""
    out: list = []
    fields: list = []          # 复杂域走到哪了："code"（域代码）/ "result"（显示出来的结果）

    def walk(node, in_simple: bool) -> None:
        kind = node.tag.rsplit("}", 1)[-1] if isinstance(node.tag, str) else ""
        if kind == "fldSimple":
            in_simple = True
        elif kind == "fldChar":
            mark = node.get(f"{{{W_NS}}}fldCharType")
            if mark == "begin":
                fields.append("code")
            elif mark == "separate" and fields:
                fields[-1] = "result"
            elif mark == "end" and fields:
                fields.pop()
        elif kind == "t" and not in_simple and not (fields and fields[-1] == "result"):
            out.append(node.text or "")
        for child in node:
            walk(child, in_simple)

    walk(el, False)
    return "".join(out)


def template_fingerprint(template_path: Path) -> str:
    """模板的指纹：按正文里一个个段落、表格（和内容控件）的文字算。占位映射里是段落序号，只和这个序列有关——
    用 Word 打开模板再保存一遍（文档属性、修订号变了，内容没动）指纹不变；增删、改动了段落才变。书签、校对标记
    这些不占段落序号的东西不算，域的结果（日期、页码）也不算——Word 打开、保存时会自己加书签、更新日期（10-14 复审：
    以前算进去，对的映射被当成过期，白补跑一次识别）。读不出结构的按整个文件算。"""
    try:
        from xml.etree import ElementTree
        with zipfile.ZipFile(template_path) as archive:
            root = ElementTree.fromstring(archive.read("word/document.xml"))
        digest = hashlib.sha256()
        body = root.find(f"{{{W_NS}}}body")
        for el in (body if body is not None else ()):
            kind = el.tag.rsplit("}", 1)[-1]
            if kind not in ("p", "tbl", "sdt"):
                continue
            digest.update(f"{kind}\x1f{_stable_text(el)}\x1e".encode("utf-8"))
        return FINGERPRINT_PREFIX + digest.hexdigest()
    except (KeyError, ValueError, zipfile.BadZipFile, SyntaxError):
        digest = hashlib.sha256()
        with open(template_path, "rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return "f1:" + digest.hexdigest()


def _map_digest(tmap: dict) -> str:
    """映射内容的指纹（不管空白、换行、键的顺序）。"""
    return hashlib.sha256(json.dumps(tmap, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _read_stamp(folder: Path) -> dict:
    try:
        value = json.loads((Path(folder) / STAMP_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def usable_template_map(folder: Path, template_path: Path):
    """folder 里的 _template_map.json 能不能用在这份模板上：返回 (映射或 None, 状态)。

    映射里是段落序号，只对识别它时的那份模板有效。在项目文件夹里照映射填成一份成品（识别步骤的试填、完整导出），
    fill_template 就在旁边的 _template_map.stamp.json 里记下“这份映射、这份模板”（见 _stamp_template_map）。状态：
    ok；missing（没有映射）；broken（读不出来）；stale（记着的是另一份模板：模板换过，映射还是原来那份）。
    没记过的、或者记过以后映射又写过的（重新识别过：内容变了，或者内容一样但文件是后来重新写的）照用，
    填成以后重新记。
    ⛔ 不往映射里写任何东西：那是 AI 写的文件，写进去的指纹会被它原样抄回来，模板真换了也认不出；
       映射被工具重排以后，AI 接着改它也对不上。
    """
    map_path = Path(folder) / MAP_NAME
    if not map_path.is_file():
        return None, "missing"
    try:
        tmap = json.loads(map_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, "broken"
    if not isinstance(tmap, dict):
        return None, "broken"
    stamp = _read_stamp(folder)
    # 记录是老算法记的（s1：书签、域的结果也算进去了），当没记过：照用，填成以后按现在的算法重新记
    if (not stamp or stamp.get("map") != _map_digest(tmap) or _written_after(map_path, Path(folder) / STAMP_NAME)
            or not str(stamp.get("template") or "").startswith(_STAMP_PREFIXES)):
        return tmap, "ok"
    try:
        same = stamp.get("template") == template_fingerprint(template_path)
    except OSError:
        same = False
    return (tmap, "ok") if same else (None, "stale")


def _written_after(later: Path, earlier: Path) -> bool:
    try:
        return later.stat().st_mtime > earlier.stat().st_mtime + 1
    except OSError:
        return False


def map_matches_template(folder: Path, template_path: Path) -> bool:
    """folder 里的映射是不是确实对着这份模板填成过：有记录，记录之后映射没再写过，模板的段落也没变。
    usable_template_map 对“没记过”的也放行；这里只有确认过的才算（换模板时用它决定映射要不要跟着旧模板走）。"""
    stamp = _read_stamp(folder)
    map_path = Path(folder) / MAP_NAME
    try:
        tmap = json.loads(map_path.read_text(encoding="utf-8"))
        return (bool(stamp) and isinstance(tmap, dict) and stamp.get("map") == _map_digest(tmap)
                and not _written_after(map_path, Path(folder) / STAMP_NAME)
                and stamp.get("template") == template_fingerprint(Path(template_path)))
    except (OSError, ValueError):
        return False


def _stamp_template_map(folder: Path, template_path: Path) -> None:
    """照 folder 里的映射填成了一份：在旁边记下是哪份映射、哪份模板，之后模板换了就认得出来（usable_template_map）。
    记不上不算错（映射照样能用），只记日志。"""
    stamp_path = Path(folder) / STAMP_NAME
    tmp = stamp_path.with_name(stamp_path.name + ".tmp")
    try:
        tmap = json.loads((Path(folder) / MAP_NAME).read_text(encoding="utf-8"))
        if not isinstance(tmap, dict):
            return
        value = {"map": _map_digest(tmap), "template": template_fingerprint(template_path)}
        if _read_stamp(folder) == value and not _written_after(Path(folder) / MAP_NAME, stamp_path):
            return
        tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(stamp_path)
    except (OSError, ValueError) as exc:
        log.debug("没记上占位映射对应的模板：%s", exc)
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass


def filled_out_of_place(report: Optional[dict]) -> bool:
    """这次填充是不是填乱了，不该发布：模板本身带着成段的样例文字（一篇样例论文），而正文在模板里找不到位置、只能接在
    文末——成品要么是“整篇样例论文 + 真实内容接在后面”，要么样例被摘要那一步的清理一起删了、真实正文排到了参考文献
    后面。不看占位映射在不在、题目换没换上（10-14 复审：映射在、但一个位置都没给；或者模板第一段“论文标题（此处填写
    题目）”被认出来换上了——以前这两种都照样发布）。只有封面、声明页、只有样式的模板没有样例文字
    （见 _is_sample_paragraph），接在后面本来就对，不算。report = fill_template 写的那份。"""
    report = report or {}
    return (report.get("mode") == "paragraph" and report.get("body_placed") == "safety_net"
            and bool(report.get("template_has_sample")))


def _drop_unused_images(doc) -> int:
    """正文里已经没有哪处用到的图片，从文档里拿掉（返回拿掉几张）。样例图片所在的段落删掉以后，图片本身还留在
    文件包里：不显示，但成品白白大一截，别人解开文件还看得到模板里的样例图。页眉页脚的图不在这里，不受影响。
    ⛔ 不能用 python-docx 的 drop_rel：它只数 r:id 一种写法，图片用的是 r:embed，会把正在用的图也拿掉。"""
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    part = doc.part
    used = set()
    for el in part.element.iter():
        used.update(el.attrib.values())
    dropped = 0
    for rid, rel in list(part.rels.items()):
        if rel.reltype == RT.IMAGE and not rel.is_external and rid not in used:
            del part.rels[rid]
            dropped += 1
    return dropped


_PPR_AFTER_OUTLINE = frozenset(qn("w:" + tag) for tag in ("divId", "cnfStyle", "rPr", "sectPr", "pPrChange"))


def _fix_dangling_headings(doc) -> int:
    """稿子的标题用的是 Heading1–6 这几个样式编号；中文 Word 存的模板里标题样式的编号是“1”“2”“a3”这类，没有
    Heading2——引用悬空，Word 按正文显示：标题没有大纲级别、不进目录，导航窗格里也没有（10-14 复审）。
    模板里没有的这个编号去掉，在段落上直接写大纲级别（字体字号本来就直接写在段落和文字上，显示不变）。
    模板里有这个编号的（英文 Word 存的模板）不动。返回改了几段。"""
    styles = getattr(doc.styles, "element", None)
    ids = {style.get(qn("w:styleId")) for style in styles.iter(qn("w:style"))} if styles is not None else set()
    fixed = 0
    for paragraph in doc.element.body.iter(qn("w:p")):
        ppr = paragraph.find(qn("w:pPr"))
        pstyle = ppr.find(qn("w:pStyle")) if ppr is not None else None
        value = pstyle.get(qn("w:val")) if pstyle is not None else None
        if not value or value in ids:
            continue
        match = re.fullmatch(r"Heading([1-6])", value)
        if not match and value != "Title":
            continue
        ppr.remove(pstyle)
        if match and ppr.find(qn("w:outlineLvl")) is None:
            level = OxmlElement("w:outlineLvl")
            level.set(qn("w:val"), str(int(match.group(1)) - 1))
            anchor = next((child for child in ppr if child.tag in _PPR_AFTER_OUTLINE), None)
            if anchor is not None:
                anchor.addprevious(level)
            else:
                ppr.append(level)
        fixed += 1
    return fixed


# ---------------------------------------------------------------------------
# 步骤 1：调 Node 渲染 markdown 为内容 docx
# ---------------------------------------------------------------------------

def _render_md_via_node(
    source_md: Path,
    output_path: Path,
    workspace: Optional[Path] = None,
    style_profile: Optional[Path] = None,
) -> Path:
    """调 docx-cn-engine 渲染 markdown 为完整 docx（含 OMML / 三线表 / 上标）。"""
    # ⛔ 复用 docx_export 已有的 _convert_with_node
    # 不能直接 `from docx_export import ...` — 打包后路径上同时存在
    # routers/docx_export.pyd（不含 _convert_with_node）和 tools/docx_export.pyc，
    # 标准 import 在 sys.modules 缓存被污染时可能拿到 router 的版本导致 ImportError。
    # 用 importlib 从绝对路径加载，注册到独立模块名规避缓存冲突。
    import importlib.util
    import importlib.machinery
    _tools_dir = Path(__file__).resolve().parent
    _internal_name = "_mh_tools_docx_export_fill_view"
    if _internal_name in sys.modules:
        _mod = sys.modules[_internal_name]
    else:
        _src = _tools_dir / "docx_export.py"
        if _src.exists():
            _loader = importlib.machinery.SourceFileLoader(_internal_name, str(_src))
        else:
            _src = _tools_dir / "docx_export.pyc"
            if not _src.exists():
                raise FileNotFoundError(
                    f"docx_export 工具未找到（{_tools_dir}/docx_export.py 和 .pyc 都不存在）"
                )
            _loader = importlib.machinery.SourcelessFileLoader(_internal_name, str(_src))
        _spec = importlib.util.spec_from_loader(_internal_name, _loader, origin=str(_src))
        _mod = importlib.util.module_from_spec(_spec)
        # 手动设置 __file__ 兜底（SourcelessFileLoader 不会自动设置）
        _mod.__file__ = str(_src)
        _mod.__loader__ = _loader
        _mod.__spec__ = _spec
        # 让 docx_export 内部的 from docx import ... 能找到第三方包
        _tools_str = str(_tools_dir)
        if _tools_str not in sys.path:
            sys.path.insert(0, _tools_str)
        sys.modules[_internal_name] = _mod
        try:
            _spec.loader.exec_module(_mod)
        except Exception:
            sys.modules.pop(_internal_name, None)
            raise
    return _mod.markdown_to_docx(source_md, output_path, style_profile=style_profile,
                                 workspace=workspace, engine="node")


# ---------------------------------------------------------------------------
# 步骤 2：把渲染好的 docx 按章节切片
# ---------------------------------------------------------------------------

def _slice_rendered_doc(rendered: Document) -> dict:
    """按章节切渲染好的 docx，返回 lxml 元素列表（深拷贝过的）。

    sections = {
        'title_text': str,         # 论文标题文本
        'abstract': [<w:p>],       # 摘要段落（不含关键词）
        'keywords': <w:p> or None, # 关键词段落
        'body': [<elem>],          # 正文章节元素（含 H1/H2 标题、段落、表格）
        'references': [<w:p>],
        'appendix': [<elem>],
    }
    """
    body = rendered.element.body
    children = []
    for el in body.iterchildren():
        if el.tag.endswith("}sectPr"):
            continue
        children.append(el)

    sections = {
        "title_text": "",
        "abstract": [],
        "keywords": None,
        "en_abstract": [],     # 中文摘要之后的英文摘要（中文期刊常见），单独放到模板的英文摘要位置
        "en_keywords": None,
        "body": [],
        "references": [],
        "appendix": [],
    }

    cur = None
    title_seen = False
    zh_abstract_seen = False

    for el in children:
        is_para = el.tag == f"{{{W_NS}}}p"
        text = _para_text(el) if is_para else ""
        level = _para_heading_level(el) if is_para else 0
        norm = text.replace(" ", "").lower() if text else ""

        # ⛔ 章节切换判定: 用「精确匹配」(去前导编号后, 段落文本必须就是章节名),
        #   不能用子串匹配 —— 否则正文/参考文献/摘要里出现这些词的段落会被误判为章节标题
        #   而被 continue 吃掉丢失。
        #   (历史 bug: 参考文献条目 "[99] ...参考文献..." 或摘要正文含"摘要" → 被当标题丢弃)
        if is_para and text:
            # 去掉前导编号(阿拉伯/中文数字 + 点顿号空格), 不去括号(保留 [99] 这种引用前缀以排除)
            norm_title = re.sub(r"^[\s\d一二三四五六七八九十\.、]+", "", norm)
            if norm_title in ("摘要", "abstract"):
                if norm_title == "abstract" and zh_abstract_seen:
                    cur = "en_abstract"
                else:
                    cur = "abstract"
                    zh_abstract_seen = zh_abstract_seen or norm_title == "摘要"
                continue
            if norm_title in ("参考文献", "references", "reference"):
                cur = "references"
                continue
            if (norm_title in ("附录", "appendix")
                    or re.match(r"^附录[a-z\d一二三四五六]{1,4}$", norm_title)
                    or ((level >= 1 or norm_title.startswith("appendix")) and _is_appendix_heading(text))):
                cur = "appendix"
                continue
            if norm_title in ("致谢",) or norm_title.startswith("acknowledg"):
                cur = "ack"
                sections["body"].append(el)  # 保留致谢标题到正文(内容也并入 body)
                continue

        # 标题：第一个有文本的段（通常是 H1）当作论文标题
        if is_para and text and not title_seen:
            sections["title_text"] = text
            title_seen = True
            continue

        # 普通章节标题（H1/H2/H3）→ body 起点
        if is_para and text and level >= 1:
            cur = "body"
            sections["body"].append(el)
            continue

        # 关键词识别（在 abstract 区域）
        if cur == "abstract" and is_para and _KEYWORDS_RE.match(text):
            sections["keywords"] = el
            continue
        if cur == "en_abstract" and is_para and _KEYWORDS_RE.match(text):
            sections["en_keywords"] = el
            continue

        # 归类
        if cur == "abstract":
            if is_para and not text:
                continue
            sections["abstract"].append(el)
        elif cur == "en_abstract":
            if is_para and not text:
                continue
            sections["en_abstract"].append(el)
        elif cur == "body":
            sections["body"].append(el)
        elif cur == "references":
            # 已进入「参考文献」区: 捕获所有非空段落(不挑编号格式)。
            # 之前只认 ^\[\d+\] 会漏掉 "1." / "1)" / 全角［1］/【1】/ GB7714 无括号等格式,
            # 导致用户的参考文献被静默丢弃。
            if is_para:
                if text.strip():
                    sections["references"].append(el)
            else:
                sections["references"].append(el)
        elif cur == "appendix":
            sections["appendix"].append(el)
        elif cur == "ack":
            # 致谢: 并入正文, 不丢弃(之前直接丢)
            if not (is_para and not text):
                sections["body"].append(el)
        else:
            # cur is None: 标题之后、第一个识别章节之前的游离内容, 也并入正文不丢
            if is_para and text.strip():
                sections["body"].append(el)

    return sections


# ---------------------------------------------------------------------------
# 步骤 3：跨文档复制元素到模板占位位置
# ---------------------------------------------------------------------------

def _clean_style_refs(elem):
    """清理元素中可能引用的不存在的样式 ID（避免 Word 警告）。

    Heading1-6 / Title 这些通用样式名一般在所有 Word 文档中都存在，
    自定义样式 ID 可能冲突，统一保留 Heading 系列，去掉非通用 pStyle。
    """
    KEEP_STYLES = {"Heading1", "Heading2", "Heading3", "Heading4",
                   "Heading5", "Heading6", "Title"}
    for pStyle in list(elem.iter(f"{{{W_NS}}}pStyle")):
        val = pStyle.get(f"{{{W_NS}}}val", "")
        if val not in KEEP_STYLES:
            parent = pStyle.getparent()
            if parent is not None:
                parent.remove(pStyle)
    return elem


def _prepare_for_insert(
    src_el,
    rid_map: dict,
    drawing_id_counter: Optional[list[int]] = None,
):
    """深拷贝元素，清理样式/关系，并分配不冲突的绘图 ID。"""
    new_el = copy.deepcopy(src_el)
    _clean_style_refs(new_el)
    _rewrite_image_rids([new_el], rid_map, drawing_id_counter)
    # Imported pictures keep their inline flow. Explicitly override the target
    # template's fixed Normal spacing, otherwise a 10 cm figure can occupy only
    # a 20 pt line. Cover/header shapes already in the template are untouched.
    for paragraph in new_el.iter(qn("w:p")):
        if not any(True for _ in paragraph.iter(f"{{{WP_NS}}}inline")):
            continue
        ppr = paragraph.get_or_add_pPr()
        spacing = ppr.get_or_add_spacing()
        spacing.set(qn("w:line"), "240")
        spacing.set(qn("w:lineRule"), "auto")
    return new_el


def _document_drawing_id_counter(doc: Document) -> list[int]:
    """Return a counter positioned after every drawing ID already in ``doc``."""
    max_id = 0
    # Headers/footers can carry logos with IDs larger than any body drawing.
    roots = [getattr(part, "_element", None) for part in doc.part.package.parts]
    for root in (root for root in roots if root is not None):
        for tag in (f"{{{WP_NS}}}docPr", f"{{{PIC_NS}}}cNvPr"):
            for drawing in root.iter(tag):
                try:
                    max_id = max(max_id, int(drawing.get("id", "0")))
                except (TypeError, ValueError):
                    # A malformed/missing existing ID must not make export fail;
                    # allocate new IDs above the valid range.
                    continue
    return [max_id + 1]


def _insert_after(anchor_elem, new_elem):
    """在 anchor_elem 之后插入 new_elem，返回 new_elem。"""
    anchor_elem.addnext(new_elem)
    return new_elem


def _replace_placeholder_with_text(p, new_text: str, fonts: dict, size_pt: float = 22,
                                     bold: bool = True, alignment: str = "center"):
    """把段落 p 的内容替换为 new_text（清空原 runs，添加新 run）。"""
    # 清空 runs
    for run_el in list(p._element.iter(f"{{{W_NS}}}r")):
        parent = run_el.getparent()
        if parent is not None:
            parent.remove(run_el)
    # 设置对齐
    align_map = {"center": WD_ALIGN_PARAGRAPH.CENTER, "left": WD_ALIGN_PARAGRAPH.LEFT,
                 "right": WD_ALIGN_PARAGRAPH.RIGHT}
    p.alignment = align_map.get(alignment, WD_ALIGN_PARAGRAPH.CENTER)
    p.paragraph_format.first_line_indent = Pt(0)
    run = p.add_run(new_text)
    run.bold = bold
    run.font.size = Pt(size_pt)
    # 字体
    cn_font = fonts.get("chinese_heading", "SimHei") if bold else fonts.get("chinese_body", "SimSun")
    en_font = fonts.get("latin", "Times New Roman")
    rPr = run._element.get_or_add_rPr()
    rFonts = OxmlElement("w:rFonts")
    rFonts.set(qn("w:ascii"), en_font)
    rFonts.set(qn("w:hAnsi"), en_font)
    rFonts.set(qn("w:eastAsia"), cn_font)
    rPr.append(rFonts)


# ---------------------------------------------------------------------------
# 表格式模板（开题报告表、任务书一类：一张大表，每个格子写一部分）
# ---------------------------------------------------------------------------
# 高校开题报告的学校模板多是表格：封面信息表 + 一张大表，每格一个部分（东南大学本科开题报告样式："一、选题背景和
# 意义：""二、课题关键问题及难点："……最后是指导教师意见、开题审查小组意见）。段落占位找不到位置，以前整篇正文落到
# 表格外面、格子全空（10-12 实测）。这里按格子的标签把 Markdown 的各节（## 一级、### 二级）填进对应格子：
# - 标签与各节标题按同一套说法比对（与 tools/academic_writing_check.py 的 PROPOSAL_PARTS 一致，测试核对）；
# - 一节只对上一个格子：内容写在标签下面（同一格），或标签右边、下一行的空格子；
# - 一格收到几节时保留各节标题（加粗段），只收到一节时不重复写标题；
# - 对不上的节接在上一节的格子里，参考文献没有专门的格子就接在研究现状那格后面，内容不丢；
# - 题目填进"论文题目"格；姓名、学号、导师、课题来源这类信息格，以及意见、签字、评议栏原样留给作者和老师。
_FORM_PARTS = (
    ("background", r"选题依据|立论依据|选题背景|研究背景|选题缘由|选题的由来|选题由来|引言|问题的提出|研究意义|"
                   r"目的(?:和|与|及)意义|课题来源|选题意义|研究目的"),
    ("review", r"研究现状|文献综述|研究综述|研究进展|学术史|研究动态|研究概况|文献回顾|研究述评|研究史|调研报告"),
    ("content", r"研究内容|研究目标|拟解决|关键问题|研究问题|科学问题|主要问题|研究的问题|论点|难点|重点"),
    ("method", r"研究方法|技术路线|研究方案|实施方案|方案论证|研究思路|研究设计|技术方案|实验方案|设计方案|研究手段|"
               r"研究步骤|研究方式|理论基础"),
    ("feasibility", r"可行性"),
    ("innovation", r"创新|特色"),
    ("basis", r"研究基础|工作基础|前期|已有基础|已有工作|已具备|工作条件|研究条件|实验条件|条件保障|经费|已参加"),
    ("prior", r"前期|预研|已完成的?(?:研究)?工作|初步(?:研究|结果|工作)"),
    ("difficulty", r"困难|风险|解决措施|应对措施|对策|解决办法|解决方法"),
    ("schedule", r"进度|时间安排|时间表|工作计划|研究计划|计划安排|日程"),
    ("outcomes", r"预期成果|预期目标|预期结果|成果形式|预期达到|可能达到|预期的成果|工作量"),
    ("outline", r"大纲|结构框架|论文框架|章节安排|章节结构|论文提纲|写作提纲|篇章结构|文章的结构|论文结构|论文的结构"),
    ("references", r"参考文献"),
)
_FORM_PART_RES = tuple((key, re.compile(pattern)) for key, pattern in _FORM_PARTS)
# 对不上同名格子时的退路：困难写进"关键问题及难点"格，可行性写进方案格……
_FORM_AFFINITY = {
    "difficulty": {"content"}, "feasibility": {"method"}, "basis": {"method", "feasibility"}, "prior": {"basis"},
    "outcomes": {"schedule", "content"}, "innovation": {"content"}, "outline": {"content", "method"},
    "references": {"review"},
}
# 留给作者、老师填的格子：意见、签字、评议、成绩……
_FORM_SKIP_RE = re.compile(r"意见|评议|评语|签字|签名|签章|盖章|审核|审批|审查|成绩|评分|负责人|考核|答辩小组|专家组")
# 封面信息格（单独一格的短标签）：留给作者
_FORM_FIELD_RE = re.compile(
    r"^(?:课题来源|课题类型|课题性质|项目来源|项目类型|来源|研究方向|学科|专业|学科专业|专业领域|领域|姓名|研究生姓名|学生姓名|"
    r"学号|导师|指导教师|校外导师|合作导师|学院|院系|所在学院|年级|班级|日期|开题日期|报告日期|电话|联系电话|邮箱|职称|"
    r"入学时间|入学年月|学位类别|类别|学位类型|培养类别|培养方式)$")
_FORM_TITLE_RE = re.compile(r"^(?:论文|课题|学位论文|毕业设计|毕业论文|设计|拟定论文|拟定)?(?:中文)?(?:题目|名称|题名)$")
_FORM_EN_TITLE_RE = re.compile(r"^(?:英文(?:题目|题名|名称)|English\s*Title)$", re.I)
_FORM_INSTRUCTION_RE = re.compile(r"字以上|不少于|不超过|不得少于|可另附页|可附页|可加页|另附页|请填写|填写说明|主要内容包括|"
                                  r"应包括|包括以下|此栏|本栏|篇幅")
_EN_TITLE_LINE_RE = re.compile(r"^\s*(?:英文题目|英文题名|英文标题|English\s*Title)\s*[:：]\s*(.+?)\s*$", re.I)
_LABEL_KEY_RE = re.compile(r"[\s　:：*]+")


def form_families(text: str) -> set[str]:
    """标签或标题文字说的是开题报告的哪几部分（可能不止一个）。"""
    return {key for key, rx in _FORM_PART_RES if rx.search(text or "")}


def _tc_paragraphs(tc) -> list:
    return [c for c in tc if c.tag == f"{{{W_NS}}}p"]


def _is_vmerge_continue(tc) -> bool:
    vm = tc.find(f"{{{W_NS}}}tcPr/{{{W_NS}}}vMerge")
    return vm is not None and vm.get(f"{{{W_NS}}}val") in (None, "continue")


def _is_form_instruction(text: str) -> bool:
    norm = (text or "").strip()
    if not norm or len(norm) > 160:
        return False
    if norm[0] in "（(" and norm[-1] in "）)":
        return True
    return bool(_FORM_INSTRUCTION_RE.search(norm)) or _is_instruction_paragraph(norm)


def _cell_label(tc) -> str:
    for p in _tc_paragraphs(tc):
        text = _para_text(p)
        if text:
            return text
    return ""


def _cell_blankish(tc) -> bool:
    """格子里只有空段、填写说明（嵌套表格不算空）。"""
    if any(c.tag == f"{{{W_NS}}}tbl" for c in tc):
        return False
    return all(not _para_text(p) or _is_form_instruction(_para_text(p)) for p in _tc_paragraphs(tc))


def _looks_like_form(tbl) -> bool:
    """表格像不像一张待填的表（成绩评定、评语、签字……）：有这类字眼，而且有空着等人填的格子。"""
    if not _FORM_SKIP_RE.search("".join(t.text or "" for t in tbl.iter(f"{{{W_NS}}}t"))):
        return False
    return any(_cell_blankish(tc) for tc in tbl.iter(f"{{{W_NS}}}tc") if not _is_vmerge_continue(tc))


def _label_only(tc) -> bool:
    """标签所在的格子除了标签只有空段和填写说明。"""
    texts = [_para_text(p) for p in _tc_paragraphs(tc)]
    texts = [t for t in texts if t]
    return all(_is_form_instruction(t) for t in texts[1:]) and not any(c.tag == f"{{{W_NS}}}tbl" for c in tc)


def _form_grid(doc) -> list[dict]:
    """模板里所有表格的格子（含嵌套表格），按文档顺序。"""
    out = []
    for tbl in doc.element.body.iter(f"{{{W_NS}}}tbl"):
        rows = [tr for tr in tbl if tr.tag == f"{{{W_NS}}}tr"]
        for ri, tr in enumerate(rows):
            tcs = [tc for tc in tr if tc.tag == f"{{{W_NS}}}tc"]
            for ci, tc in enumerate(tcs):
                out.append({"tc": tc, "tbl": tbl, "rows": rows, "ri": ri, "ci": ci, "row": tcs})
    return out


def _right_or_below(cell: dict):
    """标签格子对应的填写格：同一行右边的空格子，或标签独占一行时下一行的那个空格子；都不是返回 None。"""
    row, ci = cell["row"], cell["ci"]
    if ci + 1 < len(row) and _cell_blankish(row[ci + 1]) and not _is_vmerge_continue(row[ci + 1]):
        return row[ci + 1]
    rows, ri = cell["rows"], cell["ri"]
    if len(row) == 1 and ri + 1 < len(rows):
        nxt = [tc for tc in rows[ri + 1] if tc.tag == f"{{{W_NS}}}tc"]
        if len(nxt) == 1 and _cell_blankish(nxt[0]) and not form_families(_cell_label(nxt[0])):
            return nxt[0]
    return None


def table_form_plan(doc) -> Optional[dict]:
    """认出表格式模板的填写格。返回 {"targets": [...], "title": tc 或 None, "title_en": tc 或 None}；
    认出的填写格不到两个（且没有一个包揽几部分的大格子）时返回 None，退回段落占位的填法。"""
    targets, title_tc, title_en_tc = [], None, None
    title_label, title_en_label = None, None
    used = set()
    for cell in _form_grid(doc):
        tc = cell["tc"]
        if tc in used or _is_vmerge_continue(tc):
            continue
        label = _cell_label(tc)
        if not label or len(label) > 90:
            continue
        key = _LABEL_KEY_RE.sub("", label)
        bare = re.sub(r"[（(][^)）]*[)）]", "", key)
        if re.search(r"英文|English", key, re.I) and _FORM_TITLE_RE.match(re.sub(r"英文|English", "", bare, flags=re.I) or "题目"):
            slot = _right_or_below(cell)
            if slot is not None and title_en_tc is None:
                title_en_tc, title_en_label = slot, tc
                used.add(slot)
            continue
        if _FORM_TITLE_RE.match(bare):
            slot = _right_or_below(cell)
            if slot is not None and title_tc is None:
                title_tc, title_label = slot, tc
                used.add(slot)
            continue
        if _FORM_EN_TITLE_RE.match(key):
            slot = _right_or_below(cell)
            if slot is not None and title_en_tc is None:
                title_en_tc, title_en_label = slot, tc
                used.add(slot)
            continue
        if _FORM_FIELD_RE.match(bare) or _FORM_SKIP_RE.search(label):
            continue
        fams = form_families(label)
        if not fams:
            continue
        slot = _right_or_below(cell) if (len(cell["row"]) > 1 or _label_only(tc)) else None
        if slot is not None:
            targets.append({"label": label, "families": fams, "tc": slot, "label_tc": tc, "same_cell": False})
            used.add(slot)
        else:
            targets.append({"label": label, "families": fams, "tc": tc, "label_tc": tc, "same_cell": True})
        used.add(tc)
    if len(targets) >= 2 or (len(targets) == 1 and len(targets[0]["families"]) >= 3):
        return {"targets": targets, "title": title_tc, "title_en": title_en_tc,
                "title_label": title_label, "title_en_label": title_en_label}
    return None


def _rendered_parts(rendered) -> tuple[str, list, list]:
    """渲染好的内容 docx 按标题切开：(题目, 题目和第一节之间的元素, [节])。节 = {title, elems, subs}，
    subs 是 ### 小节 {title, elems}（elems 含小节标题段）。"""
    title, pre, parts = "", [], []
    cur = None
    for el in rendered.element.body.iterchildren():
        if el.tag.endswith("}sectPr"):
            continue
        is_p = el.tag == f"{{{W_NS}}}p"
        text = _para_text(el) if is_p else ""
        level = _para_heading_level(el) if is_p else 0
        if is_p and text and level == 1 and not title and not parts:
            title = text
            continue
        if is_p and text and level == 2:
            cur = {"title": text, "heading": el, "elems": [], "subs": []}
            parts.append(cur)
            continue
        if cur is None:
            if is_p and not text:
                continue
            pre.append(el)
            continue
        if is_p and text and level == 3:
            cur["subs"].append({"title": text, "elems": [el]})
            continue
        (cur["subs"][-1]["elems"] if cur["subs"] else cur["elems"]).append(el)
    return title, pre, parts


def _score(fams: set, target: dict) -> int:
    direct = len(fams & target["families"])
    if direct:
        return 10 * direct
    near = set().union(*(_FORM_AFFINITY.get(f, set()) for f in fams)) if fams else set()
    return 3 * len(near & target["families"])


def _best_target(fams: set, targets: list, used: set) -> Optional[int]:
    best, best_key = None, None
    for i, target in enumerate(targets):
        s = _score(fams, target)
        if s <= 0:
            continue
        key = (s, i not in used, -i)
        if best_key is None or key > best_key:
            best, best_key = i, key
    return best


def assign_form_pieces(parts: list, targets: list) -> list[list[dict]]:
    """每个填写格收到哪些内容块（块 = {heading, title, elems}）。小节对上了更合适、还空着的格子时单独放过去。"""
    plan: list[list[dict]] = [[] for _ in targets]
    used: set[int] = set()
    last = None
    refs_part = None
    for part in parts:
        fams = form_families(part["title"])
        if "references" in fams and len(fams) == 1:
            refs_part = part
            continue
        idx = _best_target(fams, targets, used)
        if idx is None:
            idx = last if last is not None else 0
        own = list(part["elems"])
        moved = []
        for sub in part["subs"]:
            sub_fams = form_families(sub["title"])
            alt = _best_target(sub_fams, targets, used | {idx})
            if (alt is not None and alt != idx and alt not in used
                    and _score(sub_fams, targets[alt]) > _score(sub_fams, targets[idx])):
                moved.append((alt, sub))
            else:
                own.extend(sub["elems"])
        plan[idx].append({"heading": part["heading"], "title": part["title"], "elems": own})
        used.add(idx)
        for alt, sub in moved:
            plan[alt].append({"heading": sub["elems"][0], "title": sub["title"], "elems": sub["elems"][1:]})
            used.add(alt)
        last = idx
    if refs_part is not None:
        idx = next((i for i, t in enumerate(targets) if "references" in t["families"]), None)
        if idx is None:
            idx = next((i for i, t in enumerate(targets) if "review" in t["families"]), None)
        if idx is None:
            idx = last if last is not None else 0
        plan[idx].append({"heading": refs_part["heading"], "title": refs_part["title"],
                          "elems": list(refs_part["elems"])})
    return plan


def _as_bold_paragraph(p) -> None:
    """格子里的小标题：去掉标题样式（模板未必有、且会进目录），改成加粗段。"""
    ppr = p.find(f"{{{W_NS}}}pPr")
    if ppr is not None:
        for st in ppr.findall(f"{{{W_NS}}}pStyle"):
            ppr.remove(st)
        for num in ppr.findall(f"{{{W_NS}}}numPr"):
            ppr.remove(num)
    for r in p.iter(f"{{{W_NS}}}r"):
        rpr = r.find(f"{{{W_NS}}}rPr")
        if rpr is None:
            rpr = OxmlElement("w:rPr")
            r.insert(0, rpr)
        _rpr_child(rpr, "b")


# rPr 子元素的先后（schema 顺序；插错位置，有的 Word 版本按文件损坏处理）
_RPR_ORDER = ("rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps", "strike", "dstrike", "outline", "shadow",
              "emboss", "imprint", "noProof", "snapToGrid", "vanish", "webHidden", "color", "spacing", "w", "kern",
              "position", "sz", "szCs", "highlight", "u", "effect", "bdr", "shd", "fitText", "vertAlign", "rtl", "cs",
              "em", "lang", "eastAsianLayout", "specVanish", "oMath")
_FONT_THEME_ATTRS = {"ascii": "asciiTheme", "hAnsi": "hAnsiTheme", "eastAsia": "eastAsiaTheme", "cs": "cstheme"}
# 段落标记的 rPr 里才有的修订标记，抄到 run 上不合法
_PARA_MARK_ONLY = {"ins", "del", "moveFrom", "moveTo", "rPrChange"}


def _rpr_child(rpr, tag: str):
    """取 rPr 里的子元素，没有就按 schema 顺序插一个。"""
    el = rpr.find(f"{{{W_NS}}}{tag}")
    if el is not None:
        return el
    el = OxmlElement(f"w:{tag}")
    later = set(_RPR_ORDER[_RPR_ORDER.index(tag) + 1:])
    for i, child in enumerate(rpr):
        if child.tag.split("}")[-1] in later:
            rpr.insert(i, el)
            return el
    rpr.append(el)
    return el


def _content_run_defaults(rendered) -> dict:
    """内容 docx 的默认字体和字号（docDefaults，再叠默认段落样式）。

    Node 引擎把正文的宋体、小四写在这里，run 上只写颜色；搬进学校模板后正文就跟了模板的默认字体字号
    （开题实测 10-12：格子里的字一半宋体一半回退字体，学校填表说明要的"小四号宋体"也丢了）。"""
    out: dict = {"fonts": {}, "sz": None, "szCs": None}
    root = rendered.styles.element
    sources = [root.find(f"{{{W_NS}}}docDefaults/{{{W_NS}}}rPrDefault/{{{W_NS}}}rPr")]
    for st in root.findall(f"{{{W_NS}}}style"):
        if st.get(qn("w:type")) == "paragraph" and st.get(qn("w:default")) in ("1", "true", "on"):
            sources.append(st.find(f"{{{W_NS}}}rPr"))
    for rpr in sources:
        if rpr is None:
            continue
        fonts = rpr.find(f"{{{W_NS}}}rFonts")
        if fonts is not None:
            for attr in _FONT_THEME_ATTRS:
                if fonts.get(qn(f"w:{attr}")):
                    out["fonts"][attr] = fonts.get(qn(f"w:{attr}"))
        for tag in ("sz", "szCs"):
            el = rpr.find(f"{{{W_NS}}}{tag}")
            if el is not None and el.get(qn("w:val")):
                out[tag] = el.get(qn("w:val"))
    return out


def _apply_run_defaults(el, defaults: Optional[dict]) -> None:
    """插进格子的每个 run：没写的字体、字号按内容 docx 的默认补上；写了的、用主题字体的不动。"""
    if not defaults or not (defaults.get("fonts") or defaults.get("sz")):
        return
    for r in el.iter(f"{{{W_NS}}}r"):
        rpr = r.find(f"{{{W_NS}}}rPr")
        if rpr is None:
            rpr = OxmlElement("w:rPr")
            r.insert(0, rpr)
        if defaults.get("fonts"):
            fonts = _rpr_child(rpr, "rFonts")
            for attr, val in defaults["fonts"].items():
                if not fonts.get(qn(f"w:{attr}")) and not fonts.get(qn(f"w:{_FONT_THEME_ATTRS[attr]}")):
                    fonts.set(qn(f"w:{attr}"), val)
        for tag in ("sz", "szCs"):
            if defaults.get(tag) and rpr.find(f"{{{W_NS}}}{tag}") is None:
                _rpr_child(rpr, tag).set(qn("w:val"), defaults[tag])


def _cell_width_emu(tc, doc) -> int:
    w = tc.find(f"{{{W_NS}}}tcPr/{{{W_NS}}}tcW")
    try:
        if w is not None and w.get(f"{{{W_NS}}}type") in (None, "dxa"):
            return max(1, int(w.get(f"{{{W_NS}}}w")) - 216) * 635
    except (TypeError, ValueError):
        pass
    sect = doc.sections[-1]
    try:
        return int((sect.page_width - sect.left_margin - sect.right_margin) * 0.92)
    except TypeError:
        return 5400000


def _fit_into_cell(el, max_emu: int) -> None:
    """插进格子的图按格子宽度缩小，表格宽度改成占满格子。"""
    wp = WP_NS
    for holder in list(el.iter(f"{{{wp}}}inline")) + list(el.iter(f"{{{wp}}}anchor")):
        ext = holder.find(f"{{{wp}}}extent")
        try:
            cx, cy = int(ext.get("cx")), int(ext.get("cy"))
        except (AttributeError, TypeError, ValueError):
            continue
        if cx <= max_emu or cx <= 0:
            continue
        ratio = max_emu / cx
        ext.set("cx", str(int(cx * ratio)))
        ext.set("cy", str(int(cy * ratio)))
        for a_ext in holder.iter(f"{{{A_NS}}}ext"):
            try:
                a_ext.set("cx", str(int(int(a_ext.get("cx")) * ratio)))
                a_ext.set("cy", str(int(int(a_ext.get("cy")) * ratio)))
            except (TypeError, ValueError):
                continue
    for tbl in ([el] if el.tag == f"{{{W_NS}}}tbl" else []) + list(el.iter(f"{{{W_NS}}}tbl")):
        tblpr = tbl.find(f"{{{W_NS}}}tblPr")
        if tblpr is None:
            continue
        w = tblpr.find(f"{{{W_NS}}}tblW")
        if w is None:
            w = OxmlElement("w:tblW")
            tblpr.append(w)
        w.set(qn("w:w"), "5000")
        w.set(qn("w:type"), "pct")
        for ind in tblpr.findall(f"{{{W_NS}}}tblInd"):
            tblpr.remove(ind)


def _clear_for_fill(tc, keep_first: bool):
    """清掉填写格里的空段和填写说明；keep_first 时保留标签段，返回插入点（标签段或 None）。"""
    paras = _tc_paragraphs(tc)
    anchor = None
    for p in paras:
        text = _para_text(p)
        if keep_first and anchor is None and text:
            anchor = p
            continue
        if not text or _is_form_instruction(text):
            tc.remove(p)
    if anchor is None and keep_first:
        anchor = next((p for p in _tc_paragraphs(tc)), None)
    if not keep_first:
        rest = [p for p in _tc_paragraphs(tc) if _para_text(p)]
        anchor = rest[-1] if rest else None
    return anchor


def _ensure_tail_paragraph(tc) -> None:
    """表格单元格最后一个元素必须是段落（Word 规定）。"""
    last = [c for c in tc if c.tag in (f"{{{W_NS}}}p", f"{{{W_NS}}}tbl")]
    if not last or last[-1].tag != f"{{{W_NS}}}p":
        tc.append(OxmlElement("w:p"))


def _put_text(tc, text: str, sample_from=None, defaults: Optional[dict] = None) -> None:
    """信息格写一行字（题目）：沿用格子第一段的段落格式；字体字号先照格子自己段落标记的格式（学校预先设好的），
    没有就照标签格子的第一个字，再没写的按内容 docx 的默认补。"""
    paras = _tc_paragraphs(tc)
    p = paras[0] if paras else None
    if p is None:
        p = OxmlElement("w:p")
        tc.append(p)
    for child in list(p):
        if child.tag != f"{{{W_NS}}}pPr":
            p.remove(child)
    for extra in paras[1:]:
        if not _para_text(extra):
            tc.remove(extra)
    r = OxmlElement("w:r")
    sample = p.find(f"{{{W_NS}}}pPr/{{{W_NS}}}rPr")
    if sample is None and sample_from is not None:
        sample = sample_from.find(f".//{{{W_NS}}}r/{{{W_NS}}}rPr")
    if sample is not None:
        rpr = copy.deepcopy(sample)
        for child in list(rpr):
            if child.tag.split("}")[-1] in _PARA_MARK_ONLY | {"b", "bCs"}:
                rpr.remove(child)
        r.append(rpr)
    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    r.append(t)
    p.append(r)
    _apply_run_defaults(r, defaults)
    _ensure_tail_paragraph(tc)


def fill_table_form(doc, rendered, plan: dict, rid_map: dict, drawing_id_counter, report: Optional[dict] = None) -> dict:
    """把渲染好的内容按格子填进表格式模板（原地改 doc），返回做了什么。"""
    targets = plan["targets"]
    title, pre, parts = _rendered_parts(rendered)
    title_en = ""
    rest_pre = []
    for el in pre:
        m = _EN_TITLE_LINE_RE.match(_para_text(el)) if el.tag == f"{{{W_NS}}}p" else None
        if m and not title_en:
            title_en = re.sub(r"[（(][^)）]*写这一行[^)）]*[)）]", "", m.group(1)).strip()
            continue
        rest_pre.append(el)
    pieces = assign_form_pieces(parts, targets)
    defaults = _content_run_defaults(rendered)
    if rest_pre:
        pieces[0].insert(0, {"heading": None, "title": "", "elems": rest_pre})
    done = {"mode": "table", "filled": [], "empty": [], "title": False, "title_en": False}
    for target, items in zip(targets, pieces):
        if not items:
            done["empty"].append(target["label"])
            continue
        tc = target["tc"]
        cursor = _clear_for_fill(tc, keep_first=target["same_cell"])
        max_emu = _cell_width_emu(tc, doc)
        # 一格收到几节：和格子标签说的是同一部分的那一节不重复写标题，其余各节保留标题（加粗段）
        primary = next((i for i, it in enumerate(items)
                        if it.get("heading") is not None and form_families(it["title"]) & target["families"]), None)
        for i, it in enumerate(items):
            show_head = len(items) > 1 and it.get("heading") is not None and i != primary
            elems = ([it["heading"]] if show_head else []) + list(it["elems"])
            for src in elems:
                new_el = _prepare_for_insert(src, rid_map, drawing_id_counter)
                _apply_run_defaults(new_el, defaults)
                if new_el.tag == f"{{{W_NS}}}p" and _para_heading_level(src) >= 1:
                    _as_bold_paragraph(new_el)
                _fit_into_cell(new_el, max_emu)
                if cursor is None:
                    tcpr = tc.find(f"{{{W_NS}}}tcPr")
                    if tcpr is not None:
                        tcpr.addnext(new_el)
                    else:
                        tc.insert(0, new_el)
                else:
                    cursor.addnext(new_el)
                cursor = new_el
        _ensure_tail_paragraph(tc)
        done["filled"].append(target["label"])
    if plan.get("title") is not None and title:
        _put_text(plan["title"], title, plan.get("title_label"), defaults)
        done["title"] = True
    if plan.get("title_en") is not None and title_en:
        _put_text(plan["title_en"], title_en, plan.get("title_en_label"), defaults)
        done["title_en"] = True
    if report is not None:
        report.update(done)
    log.info("Table-form template filled: %d cell(s), empty=%s, title=%s",
             len(done["filled"]), done["empty"], done["title"])
    return done


def _save_docx(doc, output_path: Path) -> None:
    """先存到同目录的临时文件、校验 zip 再替换，半截文件不会顶掉旧版。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    import os
    import zipfile
    with tempfile.TemporaryDirectory(prefix=".docx-fill-", dir=output_path.parent) as build:
        staged = Path(build) / output_path.name
        doc.save(str(staged))
        with zipfile.ZipFile(staged) as archive:
            if archive.testzip():
                raise ValueError("模板填充文件校验失败，未覆盖旧版")
        os.replace(staged, output_path)
    log.info("Filled docx saved: %s (%d bytes)", output_path, output_path.stat().st_size)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

# ────────────────────────────── 格式以要求文档为准（第五轮 5） ──────────────────────────────
# 能改的几项和合理范围：超出范围的多半是解析错了，不往模板里写
_OVERRIDE_KEYS = {
    "page": ("margin_top_cm", "margin_bottom_cm", "margin_left_cm", "margin_right_cm"),
    "fonts": ("chinese_body", "latin", "chinese_heading"),
    "body": ("font_size_pt", "line_spacing", "first_line_indent_chars"),
    "headings": ("level1_pt", "level2_pt", "level3_pt", "level4_pt"),
}
_OVERRIDE_RANGES = {"font_size_pt": (7.0, 22.0), "line_spacing": (0.8, 3.0), "first_line_indent_chars": (0.0, 4.0)}
_MARGIN_RANGE = (0.5, 6.0)
_HEADING_RANGE = (8.0, 36.0)
_CN_LEVEL = "一二三四"


def requirement_overrides(text_profile: dict, derived_profile: dict) -> dict:
    """要求文档解析出的格式（_text_profile.json）里，和从模板量出来的（_derived_profile.json）不一样的那几项。
    解析格式要求那一步是在模板量出来的值上只改要求写到的项，所以“不一样”就是要求写到、和模板冲突的；值不合理的不要。"""
    out: dict = {}
    if not isinstance(text_profile, dict) or not isinstance(derived_profile, dict):
        return out
    for group, keys in _OVERRIDE_KEYS.items():
        new, old = text_profile.get(group), derived_profile.get(group) or {}
        if not isinstance(new, dict) or not isinstance(old, dict):
            continue
        for key in keys:
            value = new.get(key)
            if value is None:
                continue
            if group == "fonts":
                if not isinstance(value, str) or not value.strip() or len(value.strip()) > 40:
                    continue
                value = value.strip()
                if value == str(old.get(key) or "").strip():
                    continue
            else:
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    continue
                low, high = (_MARGIN_RANGE if group == "page" else _HEADING_RANGE if group == "headings"
                             else _OVERRIDE_RANGES[key])
                if not low <= float(value) <= high:
                    continue
                before = old.get(key)
                if isinstance(before, (int, float)) and not isinstance(before, bool) \
                        and abs(float(value) - float(before)) < 1e-6:
                    continue
            out.setdefault(group, {})[key] = value
    return out


def _paragraph_styles(doc) -> list:
    from docx.enum.style import WD_STYLE_TYPE
    return [s for s in doc.styles if getattr(s, "type", None) == WD_STYLE_TYPE.PARAGRAPH]


def _default_paragraph_style(doc):
    """正文样式：标着 w:default="1" 的段落样式（中文 Word 存的模板里它的编号常常是 a，不是 Normal）。"""
    styles = _paragraph_styles(doc)
    for style in styles:
        if style.element.get(qn("w:default")) in ("1", "true", "on"):
            return style
    return next((s for s in styles if str(s.name or "").lower() == "normal"), None)


def _heading_styles(doc, level: int) -> list:
    """第 level 级标题的样式：按名字（heading 1 / 标题 1）或大纲级别认（中文 Word 存的模板编号是 1、2 或 a3 这类）。"""
    out = []
    for style in _paragraph_styles(doc):
        name = re.sub(r"\s+", "", str(style.name or "")).lower()
        ppr = style.element.find(qn("w:pPr"))
        outline = ppr.find(qn("w:outlineLvl")) if ppr is not None else None
        by_outline = outline is not None and outline.get(qn("w:val")) == str(level - 1)
        if name in (f"heading{level}", f"标题{level}", f"标题{_CN_LEVEL[level - 1]}") or by_outline:
            out.append(style)
    return out


def _set_fonts(rpr, *, latin: Optional[str] = None, east: Optional[str] = None) -> None:
    """写字体：同时去掉对应的“主题字体”属性（模板常用主题字体，主题字体比字体名优先，不去掉改了也不生效）。"""
    fonts = rpr.get_or_add_rFonts()
    if latin:
        for attr in ("w:asciiTheme", "w:hAnsiTheme"):
            fonts.attrib.pop(qn(attr), None)
        fonts.set(qn("w:ascii"), latin)
        fonts.set(qn("w:hAnsi"), latin)
    if east:
        fonts.attrib.pop(qn("w:eastAsiaTheme"), None)
        fonts.set(qn("w:eastAsia"), east)


def _set_size(rpr, points: float) -> None:
    half = str(int(round(float(points) * 2)))
    rpr.get_or_add_sz().set(qn("w:val"), half)
    existing = rpr.find(qn("w:szCs"))
    if existing is not None:
        existing.set(qn("w:val"), half)


def _doc_default_rpr(doc):
    """docDefaults 里的 rPr（没有就不建：只有样式没写的才用到它，正文样式改了就够）。"""
    defaults = doc.styles.element.find(qn("w:docDefaults"))
    holder = defaults.find(qn("w:rPrDefault")) if defaults is not None else None
    return holder.find(qn("w:rPr")) if holder is not None else None


def _apply_profile_to_template(doc, overrides: dict) -> list:
    """把要求里和模板冲突的几项写进模板（样式、docDefaults、各节的页边距）。返回写了什么（给报告和步骤说明用）。"""
    applied = []
    page = overrides.get("page") or {}
    if page:
        for section in doc.sections:
            for key, attr in (("margin_top_cm", "top_margin"), ("margin_bottom_cm", "bottom_margin"),
                              ("margin_left_cm", "left_margin"), ("margin_right_cm", "right_margin")):
                if key in page:
                    setattr(section, attr, Cm(float(page[key])))
        names = (("margin_top_cm", "上"), ("margin_bottom_cm", "下"), ("margin_left_cm", "左"), ("margin_right_cm", "右"))
        applied.append("页边距（" + "、".join(f"{label} {page[key]:g} 厘米" for key, label in names if key in page) + "）")
    body = overrides.get("body") or {}
    fonts = overrides.get("fonts") or {}
    normal = _default_paragraph_style(doc)
    if normal is not None and (body or fonts.get("chinese_body") or fonts.get("latin")):
        rpr = normal.element.get_or_add_rPr()
        default_rpr = _doc_default_rpr(doc)
        if "font_size_pt" in body:
            _set_size(rpr, body["font_size_pt"])
            if default_rpr is not None:
                _set_size(default_rpr, body["font_size_pt"])
            applied.append(f"正文字号 {float(body['font_size_pt']):g} 磅")
        if fonts.get("chinese_body") or fonts.get("latin"):
            _set_fonts(rpr, latin=fonts.get("latin"), east=fonts.get("chinese_body"))
            if default_rpr is not None:
                _set_fonts(default_rpr, latin=fonts.get("latin"), east=fonts.get("chinese_body"))
            if fonts.get("chinese_body"):
                applied.append(f"正文中文字体 {fonts['chinese_body']}")
            if fonts.get("latin"):
                applied.append(f"西文字体 {fonts['latin']}")
        if "line_spacing" in body:
            normal.paragraph_format.line_spacing = float(body["line_spacing"])
            applied.append(f"行距 {float(body['line_spacing']):g} 倍")
        if "first_line_indent_chars" in body:
            ind = normal.element.get_or_add_pPr().get_or_add_ind()
            for attr in ("w:firstLine", "w:hanging", "w:hangingChars"):
                ind.attrib.pop(qn(attr), None)
            ind.set(qn("w:firstLineChars"), str(int(round(float(body["first_line_indent_chars"]) * 100))))
            applied.append(f"首行缩进 {float(body['first_line_indent_chars']):g} 字")
    headings = overrides.get("headings") or {}
    for level in range(1, 5):
        size = headings.get(f"level{level}_pt")
        east = fonts.get("chinese_heading")
        if size is None and not east:
            continue
        styles = _heading_styles(doc, level)
        for style in styles:
            rpr = style.element.get_or_add_rPr()
            if size is not None:
                _set_size(rpr, size)
            if east:
                _set_fonts(rpr, east=east)
        if styles and size is not None:
            applied.append(f"{_CN_LEVEL[level - 1]}级标题 {float(size):g} 磅")
    if fonts.get("chinese_heading") and any(_heading_styles(doc, level) for level in range(1, 5)):
        applied.append(f"标题中文字体 {fonts['chinese_heading']}")
    return applied


def fill_template(
    template_path: Path,
    source_md: Path,
    output_path: Path,
    workspace: Optional[Path] = None,
    fonts: Optional[dict] = None,
    style_profile: Optional[Path] = None,
    template_map: Optional[dict] = None,
    report: Optional[dict] = None,
    overrides: Optional[dict] = None,
) -> Path:
    """把 markdown 内容填到用户模板的占位位置。

    表格式模板（开题报告表一类，格子标签认得出两个以上）按格子填，见 table_form_plan / fill_table_form；
    template_map 写了 "table_form": false 时不按格子填。report 传一个 dict 时写入做了什么（mode、filled、empty……）。
    按段落占位填的（mode=paragraph）还写：template_map（given / ok / missing / broken / stale）、title_placed（题目
    换在了模板自己的位置上没有）、body_placed（anchor：填在模板的正文位置；safety_net：模板里找不到正文位置，接在了
    文末；none）、sample_paragraphs_left（填完以后模板自己的段落里还剩几段成段的样例文字）。正文只能接在文末、模板的
    样例文字又还在，就是填乱了（见 filled_out_of_place），调用方不要把这样的成品发布出去。

    template_map: 可选，由 docx-template-map SKILL 输出的占位映射，结构见 SKILL.md。
        如果提供，优先按 idx 精确定位；不提供时退回正则启发式。
    overrides: 可选，格式以要求文档为准时要写进模板的那几项（requirement_overrides 的结果，第五轮 5）；
        report 里记 requirement_overrides（写了什么）。
    """
    if not template_path.exists():
        raise FileNotFoundError(f"模板文件不存在: {template_path}")
    if not source_md.exists():
        raise FileNotFoundError(f"源 Markdown 不存在: {source_md}")
    original_template = template_path     # .dotx 下面会换成转出来的 .docx；占位映射认的是原文件

    # ⛔ .dotx (Word 模板) / .doc (旧版二进制) 兼容
    # python-docx 只能识别 .docx (content-type=document.main+xml)
    # .dotx 与 .docx OOXML 结构相同，只需把 content-type 改一下；其他扩展名直接报错让用户转换
    suffix = template_path.suffix.lower()
    if suffix == ".dotx":
        template_path = _convert_dotx_to_docx(template_path)
        log.info("Converted .dotx to .docx: %s", template_path)
    elif suffix in (".doc", ".rtf", ".odt"):
        raise ValueError(
            f"不支持的模板格式 {suffix}：请用 Word 打开后另存为 .docx 再上传"
        )

    if fonts is None:
        fonts = {
            "chinese_body": "SimSun", "chinese_heading": "SimHei",
            "latin": "Times New Roman", "monospace": "Consolas",
        }

    # === 步骤 1：用 Node 引擎把 markdown 渲染成内容 docx ===
    workspace = workspace or source_md.parent

    # 自动加载工作区的 _template_map.json（如果 caller 没显式传）；是另一份模板的不用（段落序号对不上）
    map_state = "given"
    stamp_map = False       # 照工作区里的映射填成以后，把模板指纹记进映射
    if template_map is None:
        template_map, map_state = usable_template_map(workspace, original_template)
        stamp_map = template_map is not None
        if template_map is not None:
            log.info("Loaded template_map from %s (%d keys)",
                     workspace / "_template_map.json", len(template_map))
        elif map_state == "broken":
            log.warning("_template_map.json 解析失败，退回正则模式")
        elif map_state == "stale":
            log.warning("_template_map.json 是另一份模板的（模板换过，还没重新识别占位），这次不用，退回正则模式")
    with tempfile.TemporaryDirectory(prefix="docx_fill_") as tmp:
        tmp_path = Path(tmp) / "rendered.docx"
        _render_md_via_node(source_md, tmp_path, workspace=workspace,
                             style_profile=style_profile)
        log.info("Node engine rendered markdown to temporary docx (%d bytes)",
                 tmp_path.stat().st_size)

        rendered = Document(str(tmp_path))
        sections = _slice_rendered_doc(rendered)
        log.info("Sliced sections: title=%r abstract=%d body=%d refs=%d appendix=%d",
                 sections["title_text"][:30], len(sections["abstract"]),
                 len(sections["body"]), len(sections["references"]),
                 len(sections["appendix"]))

        # === 步骤 2：打开模板，找占位并替换 ===
        doc = Document(str(template_path))
        if overrides:
            # 格式以要求文档为准：先把要求里和模板冲突的几项写进模板副本（表格式、段落占位两种填法都用这份）
            _applied = _apply_profile_to_template(doc, overrides)
            if report is not None and _applied:
                report["requirement_overrides"] = _applied
        # Both the template and rendered markdown may contain pictures.  Keep
        # drawing IDs unique while inserting rendered elements. This is
        # separate from image spacing and from relationship remapping.
        drawing_id_counter = _document_drawing_id_counter(doc)

        # 收集所有要从 rendered → doc 转移的元素（用于一次性图片关系转移）
        all_transfer_elements = (
            sections["abstract"]
            + ([sections["keywords"]] if sections["keywords"] is not None else [])
            + sections["en_abstract"]
            + ([sections["en_keywords"]] if sections["en_keywords"] is not None else [])
            + sections["body"]
            + sections["references"]
            + sections["appendix"]
        )

        # ⛔ 跨文档转移图片
        rid_map = _transfer_images(rendered, doc, all_transfer_elements)
        if rid_map:
            log.info("Image rId mapping: %s", rid_map)

        # ⛔ 解析 template_map 给的 idx → 实际段落对象
        # template_map 里的 idx 是「段落清单中的位置」，doc.paragraphs 也按 body 顺序
        all_paras = list(doc.paragraphs)
        tmap = template_map or {}
        # 模板里有没有成段的样例文字（带样例的模板）；保存前再数一遍填完还剩多少（见 filled_out_of_place）
        template_paras = [p._element for p in all_paras]
        template_has_sample = sum(1 for p in all_paras if _is_sample_paragraph(p.text)) >= SAMPLE_PARAGRAPHS
        removed_anything = False

        # 表格式模板（开题报告表、任务书一类）：按格子标签填，不走段落占位（段落占位找不到位置，会把整篇正文
        # 落到表格外面、格子全空）
        form_plan = None if tmap.get("table_form") is False else table_form_plan(doc)
        if form_plan is not None:
            fill_table_form(doc, rendered, form_plan, rid_map, drawing_id_counter, report)
            _fix_dangling_headings(doc)
            _save_docx(doc, output_path)
            if stamp_map:
                _stamp_template_map(workspace, original_template)
            return output_path
        if report is not None:
            report.update({"mode": "paragraph"})

        # ⚠ 必须先提取 anchor 段引用（lxml 元素），再做删除！
        # 否则 delete_paragraph_indices 删除后段落会左移，后续 idx 错位
        anchor_keys = [
            "title_anchor_para_idx", "abstract_anchor_para_idx",
            "en_abstract_anchor_para_idx",
            "body_anchor_para_idx", "references_anchor_para_idx",
            "appendix_anchor_para_idx",
        ]
        anchor_refs: dict = {}
        for key in anchor_keys:
            idx = _index(tmap.get(key), key)
            if idx is None:
                anchor_refs[key] = None
                continue
            if 0 <= idx < len(all_paras):
                anchor_refs[key] = all_paras[idx]
            else:
                log.warning("template_map[%s]=%s 超出段落范围 (total=%d)",
                            key, idx, len(all_paras))
                anchor_refs[key] = None

        def _para_by_idx(key: str):
            """返回预先抓取的 anchor 段引用；若 caller 没提供 idx 则返回 None。"""
            return anchor_refs.get(key)

        # ⛔ 留给作者自己填的段（中文期刊的中图分类号、文献标识码、文章编号、收稿日期、基金项目、作者简介、
        #    作者与单位等，docx-template-map 写进 keep_for_user_paragraph_indices）：事实不由软件编，
        #    这些段一律不删、不填，也是摘要清理的停止边界
        keep_elements = set()
        for _ki in _indices(tmap.get("keep_for_user_paragraph_indices"), "keep_for_user_paragraph_indices"):
            if 0 <= _ki < len(all_paras):
                keep_elements.add(all_paras[_ki]._element)
        if keep_elements:
            log.info("Keeping %d paragraph(s) for the authors to fill", len(keep_elements))

        # 预处理：删除 template_map 指定的"删除段"（说明性段、示例段）
        # 此时 anchor_refs 已经持有 lxml 元素，不会因为删除导致 idx 错位
        if tmap and isinstance(tmap.get("delete_paragraph_indices"), list):
            del_indices = _indices(tmap["delete_paragraph_indices"], "delete_paragraph_indices")
            doomed = []
            doomed_elements = set()
            for di in sorted(del_indices, reverse=True):
                if 0 <= di < len(all_paras):
                    pp = all_paras[di]
                    if pp._element.getparent() is not None and pp._element not in doomed_elements:
                        # 不删除被识别为 anchor 的段（防御性）
                        if any(ref is not None and ref._element is pp._element
                               for ref in anchor_refs.values()):
                            log.warning(
                                "delete_paragraph_indices[%d] 与某个 anchor 重合，跳过", di
                            )
                            continue
                        if pp._element in keep_elements:
                            log.warning("delete_paragraph_indices[%d] 是留给作者填的段，跳过", di)
                            continue
                        doomed.append(pp)
                        doomed_elements.add(pp._element)
            # 样例论文式模板：夹在样例段落中间的表格、图片、公式和空行不在段落清单里，趁样例段落还在先把
            # 它们找出来（见 sample_leftovers），再一起删
            leftovers = []
            body_ref = anchor_refs.get("body_anchor_para_idx")
            if doomed and body_ref is not None and body_ref._element.getparent() is not None:
                stops = {ref._element for ref in (anchor_refs.get("references_anchor_para_idx"),
                                                  anchor_refs.get("appendix_anchor_para_idx")) if ref is not None}
                tables = list(doc.tables)
                preserved = {tables[ti]._element
                             for ti in _indices(tmap.get("preserve_table_indices"), "preserve_table_indices")
                             if 0 <= ti < len(tables)}
                leftovers = sample_leftovers(body_ref._element, stops, doomed_elements, keep_elements, preserved)
            for pp in doomed:
                if _holds_section_break(pp._element):
                    # 分节符挂在这一段上（这一节的页面设置、页眉页脚）：删了会改后面的版式，只清掉文字
                    for child in list(pp._element):
                        if child.tag != f"{{{W_NS}}}pPr":
                            pp._element.remove(child)
                else:
                    _delete_paragraph(pp)
            for el in leftovers:
                if el.getparent() is not None:
                    el.getparent().remove(el)
            removed_anything = bool(doomed or leftovers)
            log.info("Deleted %d instructional paragraph(s) by template_map", len(doomed))
            if leftovers:
                n_tables = sum(1 for el in leftovers if el.tag == _TBL_TAG)
                n_objects = sum(1 for el in leftovers if el.tag == _P_TAG and _holds_object(el))
                n_blank = len(leftovers) - n_tables - n_objects
                log.info("Deleted %d sample leftover(s) between them: %d table(s), %d picture / formula "
                         "paragraph(s), %d blank paragraph(s)", len(leftovers), n_tables, n_objects, n_blank)
                if report is not None:
                    report["sample_leftovers"] = {"tables": n_tables, "objects": n_objects, "blank": n_blank}

        # 2.1 标题占位（先用 template_map idx，回退到正则）
        title_p = _para_by_idx("title_anchor_para_idx")
        title_replaced = False
        # ⛔ 各章节放置追踪: 任一章节既无 anchor 又无正则占位符时会被丢弃,
        #    结尾用安全网兜底, 保证用户改的内容(尤其参考文献)不会静默丢失。
        abstract_placed = False
        references_placed = False
        appendix_placed = False
        body_placed = False     # 正文是否已放置(没放置则安全网兜底, 否则正文会整体丢失)
        body_end_cursor = None  # 正文插入末尾元素, 供安全网兜底 references/appendix
        # ⛔ 摘要兜底锚点: 指向「标题之后、正文内容之前」的位置。摘要若没找到占位符,
        #    必须插到正文开头(此锚点), 绝不能 append 到文末(否则摘要会跑到附录代码后面)。
        abstract_fallback_anchor = None
        abstract_fallback_before = None   # 兜底锚点没了时，摘要插在它前面（正文第一段）
        body_first_el = None
        abstract_end_cursor = None   # 中文摘要和关键词放完后的位置（英文摘要没有单独位置时接在这里）
        refs_end_cursor = None       # 参考文献放在模板位置上以后的末尾：模板没有附录位置时，附录接在这后面
        if title_p is not None and title_p._element.getparent() is not None:
            _replace_placeholder_with_text(
                title_p, sections["title_text"] or "未命名论文", fonts,
                size_pt=22, bold=True, alignment="center",
            )
            title_replaced = True
            log.info("Title replaced via template_map: %r",
                      sections["title_text"][:40])
        else:
            for p in list(doc.paragraphs):
                if _is_title_placeholder(p.text):
                    _replace_placeholder_with_text(
                        p, sections["title_text"] or "未命名论文", fonts,
                        size_pt=22, bold=True, alignment="center",
                    )
                    title_replaced = True
                    log.info("Title replaced (regex): %r",
                              sections["title_text"][:40])
                    break

        # 2.2 摘要占位
        # 先看 template_map 有没有给 anchor，没有再走 regex
        abstract_p = _para_by_idx("abstract_anchor_para_idx")
        if abstract_p is None or abstract_p._element.getparent() is None:
            for p in list(doc.paragraphs):
                if _ABSTRACT_RE.match(p.text or ""):
                    abstract_p = p
                    break
        if abstract_p is not None and abstract_p._element.getparent() is not None:
            anchor = abstract_p
            # ⛔ 摘要 anchor 之后的清理：先用 template_map 的下一个 anchor 元素
            #    作为「停止边界」（最准），找不到再退到正则
            stop_elements = set()
            for next_key in ("en_abstract_anchor_para_idx", "body_anchor_para_idx",
                              "references_anchor_para_idx",
                              "appendix_anchor_para_idx"):
                next_p = _para_by_idx(next_key)
                if next_p is not None and next_p._element.getparent() is not None:
                    stop_elements.add(next_p._element)
            to_delete = []
            cur_el = anchor._element.getnext()
            while cur_el is not None:
                # 命中下一个 anchor，或留给作者填的段（分类号、基金……），停
                if cur_el in stop_elements or cur_el in keep_elements:
                    break
                if cur_el.tag == f"{{{W_NS}}}p":
                    next_text = _para_text(cur_el)
                    # 没 anchor 时退到正则匹配（兜底）
                    if (not stop_elements) and (
                            _BODY_PLACEHOLDER_RE.match(next_text)
                            or _REFERENCES_RE.match(next_text)
                            or _is_appendix_heading(next_text)
                            or _ACK_RE.match(next_text)):
                        break
                    to_delete.append(cur_el)
                else:
                    # 非段落（如表格）：如果没有 stop_elements 就保留并继续，
                    # 有 stop_elements 时也只删除段落（表格属于模板原元素，应保留）
                    pass
                cur_el = cur_el.getnext()
            for el in to_delete:
                parent = el.getparent()
                if parent is not None:
                    parent.remove(el)
            cursor = anchor._element
            for src_el in sections["abstract"]:
                new_el = _prepare_for_insert(src_el, rid_map, drawing_id_counter)
                cursor = _insert_after(cursor, new_el)
            if sections["keywords"] is not None:
                new_kw = _prepare_for_insert(sections["keywords"], rid_map, drawing_id_counter)
                cursor = _insert_after(cursor, new_kw)
            abstract_placed = True
            abstract_end_cursor = cursor
            log.info("Abstract (%d paras) + keywords inserted",
                     len(sections["abstract"]))

        # 2.2b 英文摘要（中文期刊）：模板有英文摘要位置就放那里；没有就接在中文摘要和关键词后面，不丢
        en_elems = list(sections["en_abstract"]) + (
            [sections["en_keywords"]] if sections["en_keywords"] is not None else [])
        en_placed = not en_elems
        en_p = _para_by_idx("en_abstract_anchor_para_idx")
        if en_elems and en_p is not None and en_p._element.getparent() is not None:
            en_stop = set()
            for next_key in ("body_anchor_para_idx", "references_anchor_para_idx", "appendix_anchor_para_idx"):
                next_p = _para_by_idx(next_key)
                if next_p is not None and next_p._element.getparent() is not None:
                    en_stop.add(next_p._element)
            en_delete = []
            cur_el = en_p._element.getnext()
            while cur_el is not None and en_stop:
                if cur_el in en_stop or cur_el in keep_elements:
                    break
                if cur_el.tag == f"{{{W_NS}}}p":
                    en_delete.append(cur_el)
                cur_el = cur_el.getnext()
            for el in en_delete:
                if el.getparent() is not None:
                    el.getparent().remove(el)
            cursor = en_p._element
            for src_el in en_elems:
                cursor = _insert_after(cursor, _prepare_for_insert(src_el, rid_map, drawing_id_counter))
            en_placed = True
            log.info("English abstract (%d elems) inserted via template_map", len(en_elems))
        elif en_elems and abstract_placed and abstract_end_cursor is not None \
                and abstract_end_cursor.getparent() is not None:
            _h = doc.add_paragraph()
            _replace_placeholder_with_text(_h, "Abstract", fonts, size_pt=14, bold=True, alignment="left")
            _h_el = _h._element
            if _h_el.getparent() is not None:
                _h_el.getparent().remove(_h_el)
            cursor = _insert_after(abstract_end_cursor, _h_el)
            for src_el in en_elems:
                cursor = _insert_after(cursor, _prepare_for_insert(src_el, rid_map, drawing_id_counter))
            en_placed = True
            log.info("English abstract (%d elems) appended after the abstract (template has no slot)", len(en_elems))

        # 2.3 正文占位
        body_p = _para_by_idx("body_anchor_para_idx")
        if body_p is None or body_p._element.getparent() is None:
            for p in list(doc.paragraphs):
                if _BODY_PLACEHOLDER_RE.match(p.text or ""):
                    body_p = p
                    break
        if body_p is not None and body_p._element.getparent() is not None:
            anchor_el = body_p._element
            cursor = anchor_el
            # ⛔ 标题兜底: 如果标题没能替换进模板(模板无标题占位符且 template_map 无 title_anchor),
            #    把标题作为正文第一段插入, 否则用户在 main.md 改的标题会彻底丢失(被当 title 摘出又没处放)。
            if not title_replaced and (sections.get("title_text") or "").strip():
                _title_p = doc.add_paragraph()
                _replace_placeholder_with_text(
                    _title_p, sections["title_text"], fonts,
                    size_pt=22, bold=True, alignment="center",
                )
                _title_el = _title_p._element
                _tp_parent = _title_el.getparent()
                if _tp_parent is not None:
                    _tp_parent.remove(_title_el)  # 从文末摘出, 移到正文锚点
                cursor = _insert_after(cursor, _title_el)
                title_replaced = True
                log.info("Title inserted at body anchor (fallback): %r",
                         (sections["title_text"] or "")[:40])
            # ⛔ 记录摘要兜底锚点: 此刻 cursor 指向标题(或正文锚点), 正文内容还没插入。
            #    摘要若走安全网, 插到这里 → 标题后、正文前, 而不是文末。
            abstract_fallback_anchor = cursor
            for src_el in sections["body"]:
                new_el = _prepare_for_insert(src_el, rid_map, drawing_id_counter)
                cursor = _insert_after(cursor, new_el)
                if body_first_el is None:
                    body_first_el = new_el
            body_end_cursor = cursor  # 记录正文末尾, 供安全网兜底追加 references/appendix
            body_placed = True
            # 删除占位段（除非 template_map 明确说 keep）
            mode = (tmap or {}).get("body_anchor_mode", "delete")
            if mode == "delete":
                parent = anchor_el.getparent()
                if parent is not None:
                    # 题目换在了模板自己的位置上时，摘要兜底锚点就是这个占位段：删掉以前换成它前面那个元素，前面什么都
                    # 没有就记下正文第一段、插到它前面（10-14 复审：有题目和正文位置、没有摘要位置的模板——课程论文、
                    # 实验报告常见——摘要和关键词排到了正文后面）
                    if abstract_fallback_anchor is anchor_el:
                        abstract_fallback_anchor = anchor_el.getprevious()
                        if abstract_fallback_anchor is None:
                            abstract_fallback_before = body_first_el
                    parent.remove(anchor_el)
            log.info("Body (%d elements) inserted (anchor_mode=%s)",
                     len(sections["body"]), mode)

        # 2.4 参考文献占位
        refs_p = _para_by_idx("references_anchor_para_idx")
        if refs_p is None or refs_p._element.getparent() is None:
            for p in list(doc.paragraphs):
                if _REFERENCES_RE.match(p.text or ""):
                    refs_p = p
                    break
        if refs_p is not None and refs_p._element.getparent() is not None:
            anchor = refs_p
            # 用 template_map 的下一个 anchor 作为停止边界
            stop_elements = set()
            for next_key in ("appendix_anchor_para_idx",):
                next_p = _para_by_idx(next_key)
                if next_p is not None and next_p._element.getparent() is not None:
                    stop_elements.add(next_p._element)
            to_delete = []
            cur_el = anchor._element.getnext()
            while cur_el is not None:
                if cur_el in stop_elements:
                    break
                if cur_el.tag == f"{{{W_NS}}}p":
                    next_text = _para_text(cur_el)
                    # 没 anchor 时退到正则
                    if (not stop_elements) and (
                            _is_appendix_heading(next_text)
                            or _ACK_RE.match(next_text)):
                        break
                    to_delete.append(cur_el)
                cur_el = cur_el.getnext()
            for el in to_delete:
                parent = el.getparent()
                if parent is not None:
                    parent.remove(el)
            cursor = anchor._element
            for src_el in sections["references"]:
                new_el = _prepare_for_insert(src_el, rid_map, drawing_id_counter)
                cursor = _insert_after(cursor, new_el)
            references_placed = True
            refs_end_cursor = cursor
            log.info("References (%d items) inserted",
                     len(sections["references"]))

        # 2.5 附录占位
        if sections["appendix"]:
            app_p = _para_by_idx("appendix_anchor_para_idx")
            if app_p is None or app_p._element.getparent() is None:
                for p in list(doc.paragraphs):
                    if _is_appendix_heading(p.text or ""):
                        app_p = p
                        break
            if app_p is not None and app_p._element.getparent() is not None:
                anchor = app_p
                to_delete = []
                cur_el = anchor._element.getnext()
                while cur_el is not None:
                    if cur_el.tag == f"{{{W_NS}}}p":
                        next_text = _para_text(cur_el).strip()
                        if next_text and not _is_instruction_paragraph(next_text):
                            break
                    to_delete.append(cur_el)
                    cur_el = cur_el.getnext()
                for el in to_delete:
                    parent = el.getparent()
                    if parent is not None:
                        parent.remove(el)
                cursor = anchor._element
                for src_el in sections["appendix"]:
                    new_el = _prepare_for_insert(src_el, rid_map, drawing_id_counter)
                    cursor = _insert_after(cursor, new_el)
                appendix_placed = True
                log.info("Appendix (%d elements) inserted",
                         len(sections["appendix"]))

        # === 步骤 2.6：安全网 — 兜底追加未放置的章节（防止内容被静默丢弃）===
        # 用户上传的模板若缺少某章节的占位符(且 template_map 未检测到 anchor),
        # 上面的 abstract/references/appendix 就不会插入 → 用户改了也"导出没变化"。
        # 这里把任何「有内容但没放进去」的章节追加到正文末尾, 保证不丢。
        def _append_section(elems, name, heading=None):
            nonlocal body_end_cursor
            if not elems:
                return
            # 选插入锚点: 优先正文末尾, 否则文档最后一个 body 子元素
            if body_end_cursor is None or body_end_cursor.getparent() is None:
                body_children = list(doc.element.body)
                # 跳过末尾的 sectPr
                anchor_el = None
                for _c in reversed(body_children):
                    if _c.tag != f"{{{W_NS}}}sectPr":
                        anchor_el = _c
                        break
                if anchor_el is None:
                    return
                body_end_cursor = anchor_el
            cur = body_end_cursor
            # 补章节标题(摘要/参考文献/附录), 因为切分时标题段被跳过了
            if heading:
                _h = doc.add_paragraph()
                _replace_placeholder_with_text(
                    _h, heading, fonts, size_pt=14, bold=True, alignment="left",
                )
                _h_el = _h._element
                _hp = _h_el.getparent()
                if _hp is not None:
                    _hp.remove(_h_el)
                cur = _insert_after(cur, _h_el)
            for src_el in elems:
                new_el = _prepare_for_insert(src_el, rid_map, drawing_id_counter)
                cur = _insert_after(cur, new_el)
            body_end_cursor = cur
            log.warning("Safety-net: appended %s (%d elems) at body tail "
                        "(template had no anchor/placeholder)", name, len(elems))

        # body 没找到锚点时也兜底（否则正文内容会整体丢失到不了文档里）。
        # 模板里没有正文的位置（只有封面、或者只有样式）：题目、摘要、正文按这个顺序接在模板内容后面。
        # （2026-10-14 审查：以前这种模板题目直接没了，摘要排到正文后面去）
        body_by_safety_net = bool(not body_placed and sections.get("body"))
        title_at_anchor = bool(title_replaced)      # 题目换在了模板自己的位置上（接在文末的不算）
        title_appended = False
        if body_by_safety_net and not title_replaced and (sections.get("title_text") or "").strip():
            _title_p = doc.add_paragraph()          # 加在文末（最后的分节设置之前），后面的内容接着它
            _replace_placeholder_with_text(
                _title_p, sections["title_text"], fonts,
                size_pt=22, bold=True, alignment="center",
            )
            body_end_cursor = _title_p._element
            title_replaced = title_appended = True
            log.warning("Safety-net: title appended at body tail (template had no title/body anchor)")

        # ⛔ 摘要兜底: 插到正文最前面(标题之后、正文之前), 绝不放文末。
        #    历史 bug: 摘要 anchor=null 且模板"摘要"在封面表格里(doc.paragraphs 扫不到)时,
        #    摘要被 append 到正文末尾 → 跑到附录代码后面。这里改为插到正文开头。
        if not en_placed and not sections.get("abstract"):
            # 只有英文摘要（中文摘要为空）：当成摘要兜底
            sections["abstract"], sections["keywords"] = sections["en_abstract"], sections["en_keywords"]
            en_placed = True
        if not abstract_placed and sections.get("abstract"):
            _kw = [sections["keywords"]] if sections.get("keywords") is not None else []
            _ab_elems = list(sections["abstract"]) + _kw
            if not en_placed:
                _ab_elems += list(sections["en_abstract"]) + (
                    [sections["en_keywords"]] if sections.get("en_keywords") is not None else [])
                en_placed = True
            _anchor_ok = (abstract_fallback_anchor is not None
                          and abstract_fallback_anchor.getparent() is not None)
            if _anchor_ok or (abstract_fallback_before is not None
                              and abstract_fallback_before.getparent() is not None):
                # 补「摘要」标题(切分时标题段被跳过了)
                _h = doc.add_paragraph()
                _replace_placeholder_with_text(
                    _h, "摘要", fonts, size_pt=14, bold=True, alignment="left")
                _h_el = _h._element
                if _h_el.getparent() is not None:
                    _h_el.getparent().remove(_h_el)
                if _anchor_ok:
                    cur = _insert_after(abstract_fallback_anchor, _h_el)
                else:
                    abstract_fallback_before.addprevious(_h_el)      # 正文第一段前面
                    cur = _h_el
                for src_el in _ab_elems:
                    new_el = _prepare_for_insert(src_el, rid_map, drawing_id_counter)
                    cur = _insert_after(cur, new_el)
                abstract_placed = True
                log.warning("Safety-net: abstract inserted at body START (%d elems) "
                            "(template had no abstract anchor/placeholder)",
                            len(_ab_elems))
            else:
                # 没有正文锚点可参照时, 退回文末追加(极端情况, 至少不丢)
                _append_section(_ab_elems, "abstract", heading="摘要")
                abstract_placed = True
        if body_by_safety_net:
            _append_section(sections["body"], "body")
        if not references_placed and sections.get("references"):
            # ⛔ 智能定位: 竞赛/学术论文标准顺序是 正文→参考文献→附录。
            #    若正文里已有「附录」段, 参考文献插到它**之前**, 而不是无脑追加到文末(否则会跑到附录代码后)。
            _appendix_anchor_el = None
            for _p in doc.paragraphs:
                if _is_appendix_heading(_p.text or ""):
                    _appendix_anchor_el = _p._element
                    break
            if _appendix_anchor_el is not None and _appendix_anchor_el.getparent() is not None:
                _h = doc.add_paragraph()
                _replace_placeholder_with_text(
                    _h, "参考文献", fonts, size_pt=14, bold=True, alignment="left")
                _h_el = _h._element
                if _h_el.getparent() is not None:
                    _h_el.getparent().remove(_h_el)
                _appendix_anchor_el.addprevious(_h_el)  # 插到附录标题前
                _cur = _h_el
                for src_el in sections["references"]:
                    new_el = _prepare_for_insert(src_el, rid_map, drawing_id_counter)
                    _cur.addnext(new_el)
                    _cur = new_el
                references_placed = True
                log.warning("Safety-net: references inserted BEFORE appendix (%d items)",
                            len(sections["references"]))
            else:
                _append_section(sections["references"], "references", heading="参考文献")
        if not appendix_placed and sections.get("appendix"):
            # 参考文献放在了模板自己的位置上：附录接在它后面，不接在正文末尾（10-14 复审：以前排到了参考文献前面）
            if refs_end_cursor is not None and refs_end_cursor.getparent() is not None:
                body_end_cursor = refs_end_cursor
            _append_section(sections["appendix"], "appendix", heading="附录")

        # === 步骤 3：保存 ===
        # 填完以后模板自己的段落里还剩几段成段的样例文字（见 filled_out_of_place）
        sample_left = sum(1 for el in template_paras
                          if el.getparent() is not None and _is_sample_paragraph(_para_text(el)))
        if report is not None:
            report.update({
                "template_map": map_state, "title_placed": title_at_anchor, "title_appended": title_appended,
                "body_placed": ("safety_net" if body_by_safety_net else "anchor") if sections.get("body") else "none",
                "template_has_sample": template_has_sample, "sample_paragraphs_left": sample_left})
        if removed_anything:
            _dropped = _drop_unused_images(doc)
            if _dropped:
                log.info("Dropped %d picture(s) no longer used anywhere in the document", _dropped)
                if report is not None:
                    report["unused_images_dropped"] = _dropped
        _fix_dangling_headings(doc)
        _save_docx(doc, output_path)
        if stamp_map:
            _stamp_template_map(workspace, original_template)
        return output_path


def main():
    parser = argparse.ArgumentParser(description="将 Markdown 内容填充到 .docx 模板")
    parser.add_argument("--template", "-t", type=Path, required=True)
    parser.add_argument("--source", "-s", type=Path, required=True)
    parser.add_argument("--output", "-o", type=Path, required=True)
    parser.add_argument("--workspace", "-w", type=Path, default=None)
    parser.add_argument("--profile", "-p", type=Path, default=None,
                        help="样式 profile JSON（可选，传给 Node 引擎）")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    fill_template(
        args.template, args.source, args.output, args.workspace,
        style_profile=args.profile,
    )
    print(f"OK: filled {args.output}")


if __name__ == "__main__":
    main()
