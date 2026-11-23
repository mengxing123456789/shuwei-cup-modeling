#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""市调大赛报告交付：正文、附录各导出一份 Word，尽可能更新目录、另存 PDF、统计页数。

  1. 用 Node 引擎按 docx_style_profiles/market_survey_zh.json（全国统一排版要求）导出
     paper/main.md → paper/main.docx、paper/appendix.md → paper/appendix.docx；
  2. 渲染器（按顺序尝试）：
       Word（COM）    打开 → 更新目录域 → 保存 → 另存 PDF → 统计页数（最准确）
       WPS（COM）     同上（WPS 文字的自动化接口与 Word 兼容）
       LibreOffice    转 PDF 后用 PyMuPDF 数页；目录域不更新（Word 打开时会提示更新），页数可能差 1 页
       都没有         只出 Word，页数记为未知，由合规检查提示人工确认
  3. 正文排好后检查分页：一张图放不下被挤到下一页、上一页底部空出一大块时，把图后紧跟的一段正文
     挪到图前再排一遍（相当于 LaTeX 的浮动体；只改导出用的副本，paper/main.md 不动），没变好就退回；
  4. 写 paper/EXPORT_MANIFEST.json：文件清单、正文页数、渲染器、目录是否已更新、版面调整、警告。
演示作品（统计结果 demo=true 或数据来源 demo_synthetic）：正文、附录每页页眉标注"演示样例 · 数据为程序模拟生成 · 不得用于参赛"。

工作流的 docx-export 原生步骤（模板 survey_market）调用 deliver()；survey-review skill 改稿后用命令行重导：
  python "$MH_TOOLS_DIR/survey_docx_deliver.py" --workspace .
退出码：0 成功；1 导出失败；2 缺少 paper/main.md。
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import time
import sys
import tempfile
import zipfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
DEFAULT_PROFILE = HERE / "docx_style_profiles" / "market_survey_zh.json"
COM_TIMEOUT = 240
DEMO_HEADER = "演示样例 · 数据为程序模拟生成 · 不得用于参赛"
FLOAT_GAP = 0.22        # 页底空白超过正文区高度的 22%，且下一页以图开头，才挪正文补位
FLOAT_PASSES = 2        # 最多再排两遍（每遍多跑一次 Word）
_NOTE = re.compile(r"^(注|资料来源|数据来源)\s*\d*\s*[：:]")
_NOT_BODY = re.compile(r"^(#|!\[|\||\*\*表|[-*+] |\d+[.)] |\$\$|<!--|```|>)")


# Word 转换器（同目录 docx_export.py / .pyc）不能按名字 import：打包后后台进程里，编译好的网页接口
# routers/docx_export.pyd 载入时按编译时的模块名把自己也登记成 sys.modules['docx_export']，按名字 import
# 拿到的是它，报“module 'routers.docx_export' has no attribute 'markdown_to_docx'”（2026-10-23 用户 3.0.0
# 市调报告导出全失败）。按本目录的绝对路径、用独立模块名加载；名字和 services/docx_tool_loader 一样，进程里共用一份。
_ENGINE_MODULE = "_mh_tools_docx_export"


def _docx_engine():
    import importlib.machinery
    import importlib.util
    loaded = sys.modules.get(_ENGINE_MODULE)
    if loaded is not None and hasattr(loaded, "markdown_to_docx"):
        return loaded
    for name, loader_type in (("docx_export.py", importlib.machinery.SourceFileLoader),
                              ("docx_export.pyc", importlib.machinery.SourcelessFileLoader)):
        path = HERE / name
        if path.exists():
            break
    else:
        raise FileNotFoundError(f"找不到 Word 导出引擎：{HERE / 'docx_export.py'}")
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))  # 转换器自己还要 import 同目录的工具
    loader = loader_type(_ENGINE_MODULE, str(path))
    spec = importlib.util.spec_from_loader(_ENGINE_MODULE, loader, origin=str(path))
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(path)
    sys.modules[_ENGINE_MODULE] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(_ENGINE_MODULE, None)
        raise
    if not hasattr(module, "markdown_to_docx"):
        sys.modules.pop(_ENGINE_MODULE, None)
        raise ImportError(f"{path} 里没有 markdown_to_docx，可能是安装包损坏")
    return module


def _export(source: Path, output: Path, profile: Path, workspace: Path) -> Path:
    return _docx_engine().markdown_to_docx(source, output, profile, workspace, engine="node")


def _strip_update_fields(docx_path: Path) -> None:
    """渲染器会替我们更新目录，去掉"打开时更新域"的提示，避免评委打开时弹窗。"""
    tmp = docx_path.with_suffix(".tmp-strip")
    with zipfile.ZipFile(docx_path) as src, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename == "word/settings.xml":
                text = data.decode("utf-8")
                import re
                text = re.sub(r"<w:updateFields[^>]*/>", "", text)
                data = text.encode("utf-8")
            dst.writestr(item, data)
    os.replace(tmp, docx_path)


# 盲评：Word 更新目录、保存时把电脑的用户名写进“最后修改者”，学校正版 Office 还会在“公司”写学校名（曾随参赛文件交出去）
_PERSONAL = [("docProps/core.xml", re.compile(r"<dc:creator>.*?</dc:creator>|<dc:creator\s*/>", re.S), ""),
             ("docProps/core.xml", re.compile(r"<cp:lastModifiedBy>.*?</cp:lastModifiedBy>|<cp:lastModifiedBy\s*/>", re.S), ""),
             ("docProps/app.xml", re.compile(r"<Company>.*?</Company>", re.S), "<Company></Company>"),
             ("docProps/app.xml", re.compile(r"<Manager>.*?</Manager>", re.S), "<Manager></Manager>")]


def _scrub_personal_info(docx_path: Path) -> None:
    """清掉 Word 文件属性里的作者、最后修改者、公司、经理；正文和其余属性不动。"""
    with zipfile.ZipFile(docx_path) as src:
        items = [(item, src.read(item.filename)) for item in src.infolist()]
    changed = False
    for i, (item, data) in enumerate(items):
        rules = [(pattern, repl) for part, pattern, repl in _PERSONAL if part == item.filename]
        if not rules:
            continue
        text = data.decode("utf-8")
        for pattern, repl in rules:
            text = pattern.sub(repl, text)
        if text.encode("utf-8") != data:
            items[i], changed = (item, text.encode("utf-8")), True
    if not changed:
        return
    tmp = docx_path.with_suffix(".tmp-scrub")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as dst:
        for item, data in items:
            dst.writestr(item, data)
    os.replace(tmp, docx_path)


def _powershell() -> str | None:
    return shutil.which("powershell") or shutil.which("pwsh")


def _com_render(progid: str, docx_path: Path, pdf_path: Path) -> dict | None:
    """用 Word/WPS 的 COM 接口更新目录、保存、另存 PDF、数页。失败返回 None。"""
    if os.name != "nt":
        return None
    ps = _powershell()
    if not ps:
        return None
    src = str(docx_path.resolve()).replace("'", "''")
    pdf = str(pdf_path.resolve()).replace("'", "''")
    script = f"""
$ErrorActionPreference = 'Stop'
$app = $null; $doc = $null
try {{
  $app = New-Object -ComObject {progid}
  try {{ $app.Visible = $false }} catch {{}}
  try {{ $app.DisplayAlerts = 0 }} catch {{}}
  $doc = $app.Documents.Open('{src}', $false, $false)
  $toc = 0
  try {{ foreach ($t in $doc.TablesOfContents) {{ $t.Update(); $toc++ }} }} catch {{}}
  try {{ [void]$doc.Fields.Update() }} catch {{}}
  $doc.Save()
  $doc.ExportAsFixedFormat('{pdf}', 17)
  $pages = $doc.ComputeStatistics(2)
  Write-Output ("MHRESULT " + $pages + " " + $toc)
}} finally {{
  if ($doc -ne $null) {{ try {{ $doc.Close($false) }} catch {{}} }}
  if ($app -ne $null) {{ try {{ $app.Quit() }} catch {{}} }}
}}
"""
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    try:
        result = subprocess.run([ps, "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
                                capture_output=True, text=True, timeout=COM_TIMEOUT, encoding="utf-8", errors="replace")
    except (OSError, subprocess.TimeoutExpired):
        return None
    line = next((ln for ln in (result.stdout or "").splitlines() if ln.startswith("MHRESULT")), None)
    if result.returncode != 0 or not line or not pdf_path.is_file():
        return None
    _, pages, toc = line.split()
    return {"pages": int(pages), "toc_updated": int(toc) > 0}


def _soffice() -> Path | None:
    candidates = []
    for name in ("soffice", "soffice.exe", "libreoffice"):
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))
    if os.name == "nt":
        for root in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
            if root:
                candidates.append(Path(root) / "LibreOffice" / "program" / "soffice.exe")
    return next((c for c in candidates if c.is_file()), None)


def _pdf_pages(pdf: Path) -> int | None:
    try:
        import fitz  # PyMuPDF，客户端运行环境内置
        with fitz.open(str(pdf)) as doc:
            return doc.page_count
    except Exception:
        return None


def _libreoffice_render(docx_path: Path, pdf_path: Path) -> dict | None:
    exe = _soffice()
    if not exe:
        return None
    with tempfile.TemporaryDirectory(prefix="mh-lo-") as tmp:
        profile = Path(tmp) / "profile"
        try:
            subprocess.run([str(exe), "--headless", f"-env:UserInstallation={profile.resolve().as_uri()}",
                            "--convert-to", "pdf", "--outdir", tmp, str(docx_path)],
                           capture_output=True, timeout=COM_TIMEOUT)
        except (OSError, subprocess.TimeoutExpired):
            return None
        built = Path(tmp) / f"{docx_path.stem}.pdf"
        if not built.is_file():
            return None
        shutil.copyfile(built, pdf_path)
    return {"pages": _pdf_pages(pdf_path), "toc_updated": False}


def _render(docx_path: Path) -> tuple[dict | None, str | None]:
    pdf_path = docx_path.with_suffix(".pdf")
    if pdf_path.exists():
        pdf_path.unlink()
    for name, progid in (("word", "Word.Application"), ("wps", "KWps.Application")):
        backup = docx_path.read_bytes()
        _strip_update_fields(docx_path)
        # 连着导出正文、附录时，上一个 Word 进程偶尔还没退干净，第二次调用会失败：隔几秒再试一次
        for attempt in range(2):
            res = _com_render(progid, docx_path, pdf_path)
            if res:
                return res, name
            if attempt == 0 and os.name == "nt" and _powershell():
                time.sleep(3)
        docx_path.write_bytes(backup)  # 失败时还原（保留"打开时更新目录"）
    res = _libreoffice_render(docx_path, pdf_path)
    if res:
        return res, "libreoffice"
    return None, None


def _page_layout(pdf: Path, margin_pt: float = 72.0) -> list[dict] | None:
    """每页正文区底部空白占正文区高度的比例，以及该页是不是以图开头（返回页首图的图号）。
    正文区按上下页边距 2.54 cm（72 磅）算，页眉、页码不计。没有 PyMuPDF 时返回 None。"""
    try:
        import fitz  # PyMuPDF，客户端运行环境内置
    except ImportError:
        return None
    pages = []
    try:
        with fitz.open(str(pdf)) as doc:
            for page in doc:
                top, bottom = margin_pt, page.rect.height - margin_pt
                blocks = [b for b in page.get_text("blocks") if b[1] >= top - 6 and b[3] <= bottom + 4]
                images = sorted((im["bbox"] for im in page.get_image_info() if im["bbox"][3] <= bottom + 4),
                                key=lambda bb: bb[1])
                ys = [b[3] for b in blocks] + [bb[3] for bb in images]
                ys += [d["rect"].y1 for d in page.get_drawings() if top - 6 <= d["rect"].y0 and d["rect"].y1 <= bottom + 4]
                gap = (bottom - max(ys)) / (bottom - top) if ys else 1.0
                first_fig = None
                if images and images[0][1] <= top + 40 and not any(b[3] <= images[0][1] for b in blocks):
                    # 图题所在的文字块常和图片段落并成一块（块顶比图片底边略高）：按块底边找图下第一块
                    below = sorted((b for b in blocks if b[3] > images[0][3]), key=lambda b: b[1])
                    m = re.search(r"(?:^|\n)\s*图\s*(\d+)", below[0][4]) if below else None
                    first_fig = int(m.group(1)) if m else None
                pages.append({"gap": max(gap, 0.0), "first_fig": first_fig})
    except Exception:
        return None
    return pages


def _float_text_before_figure(md: str, fig_no: int) -> str | None:
    """把图 fig_no 后面紧跟的一段正文挪到图前（图下紧跟的“注：”跟着图走；紧挨着的几张图当一组，正文挪到组前）。
    只挪普通正文段：后面是标题、表、列表、公式时不挪（不跨标题、不打乱图表顺序）。挪不了返回 None。"""
    lines = md.split("\n")
    idx = next((i for i, ln in enumerate(lines) if re.match(rf"^!\[\s*图\s*{fig_no}(?!\d)", ln.strip())), None)
    if idx is None:
        return None

    def skip_blank(k: int) -> int:
        while k < len(lines) and not lines[k].strip():
            k += 1
        return k

    j = idx
    while True:                                                   # 图（连同图注）一张接一张时整组一起
        j = skip_blank(j + 1)
        if j < len(lines) and _NOTE.match(lines[j].strip()):      # 图注跟着图走
            while j < len(lines) and lines[j].strip():
                j += 1
            j = skip_blank(j)
        if j < len(lines) and lines[j].strip().startswith("!["):
            continue
        break
    if j >= len(lines) or _NOT_BODY.match(lines[j].strip()):
        return None
    k = j
    while k < len(lines) and lines[k].strip():
        k += 1
    figure = lines[idx:j]
    while figure and not figure[-1].strip():
        figure.pop()
    rest = lines[k:]
    return "\n".join(lines[:idx] + lines[j:k] + [""] + figure + ([""] if rest and rest[0].strip() else []) + rest)


def _balance_figures(src: Path, out: Path, profile: Path, workspace: Path, res: dict) -> tuple[dict, list[int]]:
    """正文排好后：上一页底部空白超过 FLOAT_GAP、下一页以图开头时，把该图后的一段正文挪到图前，
    重新导出、排版。页数变多或大块空白没减少就退回上一版。返回（最终排版结果，挪过的图号）。"""
    pdf = out.with_suffix(".pdf")
    layout = _page_layout(pdf)
    if not layout or not res.get("pages"):
        return res, []

    def badness(pages: list[dict]) -> float:
        return sum(p["gap"] for p in pages[:-1] if p["gap"] > FLOAT_GAP)

    md = src.read_text(encoding="utf-8")
    moved: list[int] = []
    for _ in range(FLOAT_PASSES):
        targets = [layout[i + 1]["first_fig"] for i in range(len(layout) - 1)
                   if layout[i]["gap"] > FLOAT_GAP and layout[i + 1]["first_fig"]]
        new_md, done = md, []
        for fig in targets:
            changed = _float_text_before_figure(new_md, fig)
            if changed:
                new_md, done = changed, done + [fig]
        if not done:
            break
        backup = {p: p.read_bytes() for p in (out, pdf) if p.is_file()}
        with tempfile.TemporaryDirectory(prefix="mh-layout-") as tmp:
            staged = Path(tmp) / src.name
            staged.write_text(new_md, encoding="utf-8")
            _export(staged, out, profile, workspace)
        new_res, _renderer = _render(out)
        new_layout = _page_layout(pdf) if new_res else None
        if (not new_res or not new_layout or not new_res.get("pages") or new_res["pages"] > res["pages"]
                or badness(new_layout) >= badness(layout)):
            for p, data in backup.items():
                p.write_bytes(data)
            break
        md, res, layout = new_md, new_res, new_layout
        moved += [n for n in done if n not in moved]
    return res, moved


def _is_demo(workspace: Path) -> bool:
    for rel, check in (("STATISTICAL_RESULTS.json", lambda d: d.get("demo") is True),
                       ("data/PROVENANCE.json", lambda d: d.get("kind") == "demo_synthetic")):
        try:
            if check(json.loads((workspace / rel).read_text(encoding="utf-8"))):
                return True
        except (OSError, ValueError, AttributeError):
            continue
    return False


def _demo_profile(profile: Path, workspace: Path) -> Path:
    data = json.loads(profile.read_text(encoding="utf-8"))
    data["header_text"] = DEMO_HEADER
    target = workspace / ".mh" / "demo_export_profile.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def deliver(workspace: Path, profile: Path | None = None, render: bool = True) -> dict:
    workspace = Path(workspace).resolve()
    profile = Path(profile) if profile else DEFAULT_PROFILE
    paper = workspace / "paper"
    main_md, appendix_md = paper / "main.md", paper / "appendix.md"
    if not main_md.is_file():
        raise FileNotFoundError(f"缺少正文 {main_md}")
    warnings: list[str] = []
    manifest = {"schema": "paperkit.survey.export/v1", "profile": profile.name,
                "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
                "files": {}, "body_pages": None, "appendix_pages": None, "renderer": None,
                "toc_updated": False, "warnings": warnings}
    if _is_demo(workspace):
        profile = _demo_profile(profile, workspace)
        manifest["demo"] = True
        warnings.append("演示作品：数据为程序模拟生成，每页已标注，不得用于参赛")
    targets = [("main", main_md, paper / "main.docx")]
    if appendix_md.is_file():
        targets.append(("appendix", appendix_md, paper / "appendix.docx"))
    else:
        warnings.append("没有附录 paper/appendix.md（正文与附录必须分开提交）")
    for key, src, out in targets:
        _export(src, out, profile, workspace)
        manifest["files"][f"{key}_docx"] = out.relative_to(workspace).as_posix()
        if not render:
            continue
        res, renderer = _render(out)
        if res and key == "main":
            res, moved = _balance_figures(src, out, profile, workspace, res)
            if moved:
                manifest["layout_adjusted"] = [f"图{n}放不下、上一页底部空白较大：图后一段正文移到图前排（paper/main.md 未改）"
                                               for n in moved]
        _scrub_personal_info(out)          # Word 保存过以后再清（保存时才写进用户名）
        if res:
            manifest["renderer"] = manifest["renderer"] or renderer
            manifest["files"][f"{key}_pdf"] = out.with_suffix(".pdf").relative_to(workspace).as_posix()
            manifest["body_pages" if key == "main" else "appendix_pages"] = res["pages"]
            if key == "main":
                manifest["toc_updated"] = res["toc_updated"]
        else:
            warnings.append(f"{out.name}：没能用 Word/WPS/LibreOffice 生成 PDF（本机没装，或调用失败），无法精确数页；"
                            "请用 Word 打开后右键目录“更新域”，再另存为 PDF")
    if manifest["renderer"] == "libreoffice":
        warnings.append("用 LibreOffice 渲染：目录域未更新，正文页数可能相差 1 页；请用 Word/WPS 打开更新目录后再核对页数")
    rules_path = workspace / ".mh" / "contest_rules.json"
    if rules_path.is_file():
        try:
            limit = json.loads(rules_path.read_text(encoding="utf-8")).get("max_body_pages")
        except json.JSONDecodeError:
            limit = None
        manifest["max_body_pages"] = limit
        if limit and manifest["body_pages"] and manifest["body_pages"] > limit:
            warnings.append(f"正文 {manifest['body_pages']} 页，超过上限 {limit} 页")
    (paper / "EXPORT_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="市调报告正文/附录导出 Word 与 PDF")
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--profile")
    ap.add_argument("--no-render", action="store_true", help="只导出 Word，不调用 Word/WPS/LibreOffice")
    args = ap.parse_args(argv)
    try:
        manifest = deliver(Path(args.workspace), Path(args.profile) if args.profile else None, not args.no_render)
    except FileNotFoundError as exc:
        print(f"❌ {exc}")
        return 2
    except Exception as exc:
        print(f"❌ 导出失败：{type(exc).__name__}: {exc}")
        return 1
    files = "、".join(manifest["files"].values())
    print(f"✅ 已导出：{files}；渲染器：{manifest['renderer'] or '无'}；正文页数：{manifest['body_pages'] or '未知'}")
    for w in manifest["warnings"]:
        print(f"⚠️ {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
