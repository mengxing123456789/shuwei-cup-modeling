"""文件级真实性核验：把「我下载到了」变成「我核过，能算数」。

为什么需要它
    2026-11-19，用户把 2023 A–D 与 2025 A–D 的原件从网盘下到了
    `C:\\Users\\29900\\Downloads\\AsterLink`，另有 9 份附录 xlsx 与 4 份 docx。
    下载的件有两个隐患，肉眼都看不出来：
      1. 网盘给的是"能打开的空壳"：PDF 只有扫描图没有文本层，xlsx 表名对但数据被裁过；
      2. 同名不同源：`(1).zip`、`_20241024_105850.pdf` 这种重命名副本，内容与主件是否一致没人验。
    这两个隐患直接决定「优秀论文里的数字能不能被引用」和「附录数据能不能进模型」。
    所以每一份进来的文件都要过一遍：sha256 + 结构自检 + 结论三档，落成台账。

判据（每条都给理由，不搞"看着没问题"）
    PDF   : pymupdf 能开 → 页数 > 0；首页可抽取字符 >= 200 才算有文本层。
            抽取字符 < 200 且页数 > 0 → SUSPECT（扫描件，模板/正文引用都会失败）。
            加密或开不了 → BROKEN。
    xlsx  : 至少 1 个工作表，且某表 max_row >= 2（只有表头说明数据没下全）→ OK。
    docx  : 段落字符 >= 100，或有表格 → OK。
    zip   : 条目数 >= 1 且能逐个列出 → OK；嵌套 zip 递归一层（2024 题目包就是套娃）。
    rar   : 7z l 能列出条目 → OK。7z 找不到时判 SUSPECT 并写明原因，不假装通过。

结论三档（只有 OK 才能进语料与论文引用）
    OK      / SUSPECT（能用但要人看一眼）/ BROKEN（别用）

产出
    <root>\\.asterlink-cache\\manifest.json   机器可读台账（每份文件一条）
    <root>\\_PROVENANCE.md                     人可读台账：总数 + 年份×题号覆盖矩阵 + 每份一行

用法
    python ...\\scripts\\authenticity_check.py --build
    python ...\\scripts\\authenticity_check.py --build --verbose
    python ...\\scripts\\authenticity_check.py --only pdf,xlsx
    from mmkit.authenticity import build, load
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import corpus

CACHE_DIRNAME = ".asterlink-cache"
MANIFEST_NAME = "manifest.json"
MD_NAME = "_PROVENANCE.md"
LETTERS = "ABCDE"


# ------------------------------------------------------------------ 基础

def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            blob = fh.read(chunk)
            if not blob:
                break
            h.update(blob)
    return h.hexdigest()


def _fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.2f} {unit}"
        n /= 1024.0
    return f"{n:.2f} GB"


# ------------------------------------------------------------------ 结构自检

def check_pdf(path: Path) -> dict:
    """PDF：页数 + 文本层。返回 {pages, chars, chars_p1, images_p1, encrypted, note}"""
    try:
        import pymupdf
    except ImportError:                                   # pragma: no cover
        import fitz as pymupdf
    out = {"pages": 0, "chars": 0, "chars_p1": 0, "images_p1": 0,
           "encrypted": False, "note": "", "text_head": ""}
    try:
        doc = pymupdf.open(path)
    except Exception as exc:                              # noqa: BLE001
        out["note"] = f"打不开：{type(exc).__name__}: {exc}"
        return out
    try:
        out["pages"] = doc.page_count
        out["encrypted"] = bool(doc.is_encrypted)
        total = 0
        for i in range(min(doc.page_count, 2)):
            page = doc.load_page(i)
            text = page.get_text() or ""
            total += len(re.sub(r"\s+", "", text))
            if i == 0:
                out["chars_p1"] = len(re.sub(r"\s+", "", text))
                out["images_p1"] = len(page.get_images(full=True))
                out["text_head"] = re.sub(r"[ \t]+", " ",
                                          corpus._clean_keep_lines(text))[:600]
        out["chars"] = total
    finally:
        doc.close()
    return out


def check_xlsx(path: Path) -> dict:
    """xlsx：工作表名、行列数、首行表头。返回 {sheets:[{name,rows,cols,header}], note}"""
    out = {"sheets": [], "note": ""}
    try:
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception as exc:                              # noqa: BLE001
        out["note"] = f"打不开：{type(exc).__name__}: {exc}"
        return out
    try:
        for ws in wb.worksheets:
            header: list[str] = []
            try:
                for row in ws.iter_rows(min_row=1, max_row=1, values_only=True):
                    header = [str(c).strip() for c in row if c is not None][:8]
                    break
            except Exception:                             # noqa: BLE001
                pass
            out["sheets"].append({
                "name": ws.title,
                "rows": int(ws.max_row or 0),
                "cols": int(ws.max_column or 0),
                "header": header,
            })
    finally:
        wb.close()
    return out


def check_docx(path: Path) -> dict:
    """docx：段落字符与表格数。返回 {paragraphs, tables, chars, note}"""
    out = {"paragraphs": 0, "tables": 0, "chars": 0, "note": ""}
    try:
        import docx
        d = docx.Document(str(path))
    except Exception as exc:                              # noqa: BLE001
        out["note"] = f"打不开：{type(exc).__name__}: {exc}"
        return out
    paras = [p.text.strip() for p in d.paragraphs if p.text and p.text.strip()]
    out["paragraphs"] = len(paras)
    out["tables"] = len(d.tables)
    out["chars"] = sum(len(re.sub(r"\s+", "", t)) for t in paras)
    return out


def check_zip(path: Path, depth: int = 0) -> dict:
    """zip：条目数；递归一层嵌套 zip（2024 题目包是 zip 套 zip）。"""
    out = {"entries": 0, "nested": 0, "pdf": 0, "xlsx": 0, "note": ""}
    try:
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
    except Exception as exc:                              # noqa: BLE001
        out["note"] = f"打不开：{type(exc).__name__}: {exc}"
        return out
    out["entries"] = len(names)
    for n in names:
        low = n.lower()
        if low.endswith(".pdf"):
            out["pdf"] += 1
        elif low.endswith(".xlsx"):
            out["xlsx"] += 1
        elif low.endswith(".zip") and depth < 1:
            out["nested"] += 1
    return out


def check_rar(path: Path) -> dict:
    """rar：靠 7z 列表。7z 缺失时判 SUSPECT 并写明，不假装通过。"""
    out = {"entries": 0, "note": ""}
    # SEVEN_ZIP 是候选路径列表（Program Files / x86 / WindowsApps 三个），必须先解析出真身；
    # 直接 subprocess.run(str(SEVEN_ZIP)) 会拼出 "[WindowsPath(...)]" 这种串，CreateProcess 报 WinError 2。
    exe = corpus._seven_zip()
    if exe is None:
        out["note"] = "找不到 7z，无法开 rar（不代表文件坏）"
        return out
    try:
        proc = subprocess.run([str(exe), "l", "-ba", str(path)],
                              capture_output=True, timeout=180)
    except Exception as exc:                              # noqa: BLE001
        out["note"] = f"7z 调用失败：{type(exc).__name__}: {exc}"
        return out
    if proc.returncode != 0:
        out["note"] = f"7z 退出码 {proc.returncode}：{proc.stderr[:120].decode('utf-8', 'replace')}"
        return out
    text = proc.stdout.decode("utf-8", errors="replace")
    out["entries"] = sum(1 for ln in text.splitlines() if ln.strip())
    if out["entries"] == 0:
        out["note"] = "7z 列出的条目为 0"
    return out


# ------------------------------------------------------------------ 结论

def verdict_check(ext: str, chk: dict) -> tuple[str, str]:
    """把自检结果折成 OK / SUSPECT / BROKEN + 一句理由。"""
    ext = ext.lower()
    if chk.get("note") and "打不开" in chk["note"]:
        return "BROKEN", chk["note"]
    if ext == ".pdf":
        if chk["pages"] <= 0:
            return "BROKEN", "页数为 0"
        if chk["encrypted"]:
            return "SUSPECT", "文档加密，抽取可能不全"
        if chk["chars_p1"] < 200:
            return "SUSPECT", (f"首页仅 {chk['chars_p1']} 字符、图片 {chk['images_p1']} 张"
                               f" → 疑似扫描件，模板/数字提取会失败")
        return "OK", f"{chk['pages']} 页，首页 {chk['chars_p1']} 字符有文本层"
    if ext == ".xlsx":
        if not chk["sheets"]:
            return "BROKEN", "没有工作表"
        rows = max(s["rows"] for s in chk["sheets"])
        if rows < 2:
            return "SUSPECT", "所有工作表只有表头，数据没下全"
        shape = "; ".join(f"{s['name']} {s['rows']}×{s['cols']}" for s in chk["sheets"][:4])
        return "OK", f"{len(chk['sheets'])} 表：{shape}"
    if ext == ".docx":
        if chk["chars"] < 100 and chk["tables"] == 0:
            return "SUSPECT", f"仅 {chk['chars']} 字符、无表格，疑似空壳"
        return "OK", f"{chk['paragraphs']} 段 {chk['chars']} 字符 / {chk['tables']} 表"
    if ext in (".zip", ".rar"):
        if chk["entries"] <= 0:
            # 条目为 0 有两种：包真的坏，或我们的工具没跑起来（7z 缺失/报错）。
            # 后者不能判 BROKEN——判错会让一份好文件被丢掉重下。
            return ("SUSPECT", chk["note"] or "条目数为 0") if chk.get("note") \
                else ("BROKEN", "压缩包条目数为 0 且无解析失败记录")
        return "OK", f"{chk['entries']} 条目" + (f"，嵌套 zip {chk['nested']}" if chk.get("nested") else "")
    return "OK", ""


def source_status(path: Path, root: Path) -> str:
    """官方原件 / 整理版 / 副本。判据只看路径与文件名，不改动任何内容。"""
    name = path.name
    rel = str(path.relative_to(root))
    if "整理版" in rel or "题面整理" in name or "中文译稿" in name or "未获取" in name:
        return "整理版"
    if "官方原件" in name:
        return "官方原件"
    if re.search(r"\(\d\)|_\d{8}_\d{6}", name):
        return "副本"
    return "官方原件"


# ------------------------------------------------------------------ 建台账

@dataclass
class Entry:
    rel: str
    name: str
    ext: str
    size: int
    mtime: str
    sha256: str
    year: str = ""
    problem: str = ""
    status: str = ""
    verdict: str = ""
    reason: str = ""
    detail: dict = field(default_factory=dict)

    def as_row(self) -> dict:
        d = asdict(self)
        return d


_CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8,
           "九": 9, "十": 10, "十一": 11, "十二": 12}
YEAR_RE_TEXT = re.compile(r"(20[12]\d)")


def _year_from_text(text: str) -> str:
    """从 PDF 首页推年份：先认「第十一届」（2014+n），再认 20xx 字样。

    为什么需要它：2025 那批题面的文件名是 `Problem B：Research on Crop Leaf Disease.pdf`，
    既没有年份也没有「B_Problem」这种前缀；只靠文件名会把它们漏在年份矩阵之外。
    """
    if not text:
        return ""
    # ① 题面首页几乎都以 `2025_“ShuWei Cup”` 开头，这是最干净的信号
    m = re.search(r"(20[12]\d)\s*[“\"']?\s*ShuWei", text)
    if m and 2019 <= int(m.group(1)) <= 2030:
        return m.group(1)
    # ② 中文届数：第十一届 = 2025（2014+n）
    m = re.search(r"第(\S{1,3}?)届", text)
    if m and m.group(1) in _CN_NUM:
        y = 2014 + _CN_NUM[m.group(1)]
        if 2019 <= y <= 2030:
            return str(y)
    # ③ 正文里的 20xx 取**第一个**：2025 C 题正文讲「2024 年 10–12 月的海水倒灌」，
    #    按出现频次投票会把它判成 2024 年（实测过），第一个才是抬头年份。
    for x in YEAR_RE_TEXT.findall(text):
        if 2019 <= int(x) <= 2030:
            return x
    return ""


def _meta(path: Path, root: Path, text: str = "") -> tuple[str, str]:
    year, problem = corpus._meta_from_name(path.name)
    if not year:
        year = corpus._meta_from_dir(path)[0]
    if not problem:
        # 三种写法都要认：`B_Problem` / `Problem B：…` / `Annex I-…`
        for pat in (r"(?:^|[^A-Za-z])([A-E])[\s_\-]*(?:Problem|Annex|Appendix)",
                    r"Problem\s*([A-E])[\s：:_\-]",
                    r"([A-E])\s*题"):
            m = re.search(pat, path.name)
            if m:
                problem = m.group(1).upper()
                break
    if not year and text:
        year = _year_from_text(text)
    return year, problem


def check_file(path: Path, root: Path) -> Entry:
    ext = path.suffix.lower()
    chk: dict = {}
    if ext == ".pdf":
        chk = check_pdf(path)
    elif ext == ".xlsx":
        chk = check_xlsx(path)
    elif ext == ".docx":
        chk = check_docx(path)
    elif ext == ".zip":
        chk = check_zip(path)
    elif ext == ".rar":
        chk = check_rar(path)
    elif ext in (".md", ".txt", ".json", ".csv"):
        chk = {"chars": 0, "note": ""}
    verdict, reason = verdict_check(ext, chk)
    year, problem = _meta(path, root, chk.get("text_head", ""))
    st = path.stat()
    return Entry(
        rel=str(path.relative_to(root)).replace("\\", "/"),
        name=path.name, ext=ext, size=st.st_size,
        mtime=datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        sha256=sha256_file(path), year=year, problem=problem,
        status=source_status(path, root), verdict=verdict, reason=reason, detail=chk,
    )


SKIP_DIRS = {".asterlink-cache", ".venv", "__pycache__", "_extracted", ".git"}


def build(root: Path | None = None, only: set[str] | None = None,
          verbose: bool = False) -> dict:
    root = root or corpus.corpus_root()
    entries: list[Entry] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in sorted(filenames):
            p = Path(dirpath) / fn
            ext = p.suffix.lower()
            if only and ext.lstrip(".") not in only and ext not in only:
                continue
            if ext not in (".pdf", ".xlsx", ".docx", ".zip", ".rar", ".md", ".csv", ".json", ".txt"):
                continue
            try:
                e = check_file(p, root)
            except Exception as exc:                      # noqa: BLE001
                e = Entry(rel=str(p.relative_to(root)).replace("\\", "/"), name=fn,
                          ext=ext, size=p.stat().st_size if p.exists() else 0,
                          mtime="", sha256="", verdict="BROKEN",
                          reason=f"核验异常：{type(exc).__name__}: {exc}")
            entries.append(e)
            if verbose:
                print(f"  {e.verdict:8s} {e.rel}", flush=True)
    cover = coverage(entries)
    counts = {}
    for e in entries:
        counts[e.verdict] = counts.get(e.verdict, 0) + 1
    return {
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "root": str(root),
        "count": len(entries),
        "verdicts": counts,
        "coverage": cover,
        "entries": [e.as_row() for e in entries],
    }


def coverage(entries: list[Entry]) -> dict:
    """年份×题号 矩阵：题面级 PDF/md 的覆盖情况。

    两条来源都要算：
      1. 散装文件（2019 之后用户逐年下载的题面 PDF / 我整理的 md）；
      2. 压缩包内部（2019–2024 的题面都在 zip 里，只看散装会把 2019–2022、2024 全判成缺）。
    第二条从语料索引里取——索引已经递归解过 zip，且标了 kind=problem。
    """
    mat: dict[str, dict[str, str]] = {}

    def put(year: str, problem: str, tag: str) -> None:
        if not year or problem not in LETTERS:
            return
        cell = mat.setdefault(year, {})
        prev = cell.get(problem, "")
        if prev and "官方" in prev:
            return
        cell[problem] = tag

    for e in entries:
        if e.ext not in (".pdf", ".md"):
            continue
        # 排除论文（队号式文件名）
        if corpus.PAPER_RE.match(Path(e.name).stem.strip()):
            continue
        tag = "官方" if e.status in ("官方原件", "副本") else "整理"
        put(e.year, e.problem, tag)

    idx = Path(str(corpus.corpus_path()))
    if idx.exists():
        try:
            obj = json.loads(idx.read_text(encoding="utf-8"))
        except Exception:                                 # noqa: BLE001
            obj = {}
        for r in obj.get("records", []):
            if r.get("kind") != "problem":
                continue
            put(str(r.get("year") or ""), str(r.get("problem") or ""), "官方")

    years = sorted(y for y in mat if y)
    return {"years": years,
            "matrix": {y: {L: mat[y].get(L, "") for L in LETTERS} for y in years}}


def save(obj: dict, root: Path | None = None) -> Path:
    root = root or corpus.corpus_root()
    cache = root / CACHE_DIRNAME
    cache.mkdir(parents=True, exist_ok=True)
    p = cache / MANIFEST_NAME
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    return p


def load(root: Path | None = None) -> dict:
    root = root or corpus.corpus_root()
    p = root / CACHE_DIRNAME / MANIFEST_NAME
    if not p.exists():
        return {"count": 0, "entries": [], "verdicts": {}, "coverage": {"matrix": {}}}
    return json.loads(p.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ 人读台账

def to_markdown(obj: dict) -> str:
    lines = []
    lines.append("# 语料真实性台账")
    lines.append("")
    lines.append(f"核验时间（UTC）：{obj['built_at']}　根目录：`{obj['root']}`")
    v = obj.get("verdicts") or {}
    lines.append("")
    lines.append(f"共 {obj['count']} 份："
                 + "　".join(f"{k} {v.get(k,0)}" for k in ("OK", "SUSPECT", "BROKEN")))
    lines.append("")
    lines.append("判据：PDF 首页可抽取 ≥200 字符（否则判扫描件）；xlsx 至少一表 >1 行；"
                 "docx ≥100 字符或有表格；zip/rar 条目 >0。只有 OK 的数字可以进论文。")
    lines.append("")
    lines.append("## 年份 × 题号 覆盖")
    lines.append("")
    cover = obj.get("coverage") or {}
    matrix = cover.get("matrix") or {}
    if matrix:
        lines.append("| 年份 | " + " | ".join(LETTERS) + " |")
        lines.append("| --- |" + " --- |" * len(LETTERS))
        for y in cover.get("years", []):
            row = [matrix[y].get(L) or "—" for L in LETTERS]
            lines.append(f"| {y} | " + " | ".join(row) + " |")
        lines.append("")
        lines.append("`官方` = 官方原件 PDF；`整理` = 我据获奖论文与公开题面整理的复述稿。")
        lines.append("")
    lines.append("## 逐份明细")
    lines.append("")
    lines.append("| 结论 | 年 | 题 | 状态 | 大小 | 相对路径 | 依据 |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    order = {"BROKEN": 0, "SUSPECT": 1, "OK": 2}
    for e in sorted(obj["entries"], key=lambda x: (order.get(x["verdict"], 9), x["rel"])):
        lines.append("| {v} | {y} | {p} | {s} | {sz} | `{r}` | {why} |".format(
            v=e["verdict"], y=e["year"] or "", p=e["problem"] or "", s=e["status"],
            sz=_fmt_size(e["size"]), r=e["rel"], why=e["reason"].replace("|", "/")))
    lines.append("")
    bad = [e for e in obj["entries"] if e["verdict"] != "OK"]
    if bad:
        lines.append("## 需要处理的")
        lines.append("")
        for e in bad:
            lines.append(f"- **{e['verdict']}** `{e['rel']}` — {e['reason']}")
        lines.append("")
    return "\n".join(lines)


def write_markdown(obj: dict, out: Path | None = None) -> Path:
    out = out or (Path(obj["root"]) / MD_NAME)
    out.write_text(to_markdown(obj), encoding="utf-8")
    return out