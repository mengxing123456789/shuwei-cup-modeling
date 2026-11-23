#!/usr/bin/env python3
"""DrawIO 图视觉自检 — 调 vision LLM 检查 DrawIO 导出的技术路线图/流程图/架构图
是否有文字溢出/节点重叠/连线穿越/布局松散等视觉问题。

drawio_check.py 只解析 XML 结构（有没有三栏表头/箭头数），查不出导出 PDF 后的
真实视觉效果。本脚本读真实渲染图（PDF/PNG）做像素级视觉质检，作为结构自检的补充。

用法:
  python _utils/drawio_vision_check.py <fig.pdf|fig.png>
  （传 PDF 时脚本内部自动转 PNG；转换工具缺失或 API 不可用都会优雅跳过，不阻塞工作流）

环境变量（按优先级）:
  EDITOR_AI_API_KEY + EDITOR_AI_BASE_URL  (editor_ai 配置，通常多模态)
  OPENAI_API_KEY + OPENAI_BASE_URL        (reviewer 配置)

退出码（三个看图脚本一致，判定与记账在 vision_ledger.py）:
  0 = 通过（明确回答 PASS 且没有列出问题）
  1 = 有问题（输出具体问题描述，skill 端据此修复重画）
  2 = 没审成：未配置视觉模型、转换/读图失败、调用失败、空回复或看不懂的回复、同一版本已看满次数。
      记为“视觉审查未完成”，绝不当作通过；不要为此改图或反复手动重试。
同一版图（按文件内容）审过就沿用上次结论、不再付费；传 --source 原图.pdf 时按原图记账。
"""
from __future__ import annotations

import base64
import http.client
import json
import os
import ssl
from trusted_gateway_config import verified_tls_context
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

# 打包运行时是嵌入版 Python（带 ._pth），不会把脚本所在目录放进导入路径：
# 同目录的 vision_ledger 要自己加上，否则每张图都会被记成"没审成"。
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

# vision API 单图通常限制 ~5MB；base64 会放大约 33%，所以原图阈值留到 3.5MB
_MAX_IMG_BYTES = 3_500_000

# 长任务里网关/网络偶发 502、超时、断连很常见。旧逻辑一次失败就退出 2，
# 这张图的视觉审查从此跳过，还被误报成"未配置视觉模型"。
_TRANSIENT_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504, 520, 522, 524, 529})
_RETRY_DELAYS = (4, 12)        # 最多 3 次尝试
_REQUEST_TIMEOUT = 90          # 非流式回复要等整段生成完，60 秒对慢视觉模型偏紧
_TOTAL_BUDGET = 200            # 远小于调用它的 Bash 工具时限，重试不会把整个 bash 块拖超时
# A vision check is a quick look at one figure.  At a reasoning model's default
# (high) effort it can think for minutes and outrun the timeout above (measured on
# Opus 5: >120 s and cut by the provider, versus 15 s at low effort with the same
# findings).  A provider that does not take the field refuses it with 400 before
# generating anything; _call_with_retry then asks once more without it.
_REASONING_EFFORT = "low"
_effort_refused = False


class VisionHTTPError(Exception):
    def __init__(self, status: int, body: str, retry_after: str = ""):
        super().__init__(f"HTTP {status}: {body[:300]}")
        self.status, self.body, self.retry_after = status, body, retry_after


class VisionUnavailable(Exception):
    def __init__(self, error: Exception, attempts: int):
        super().__init__(f"{error}（共尝试 {attempts} 次）")
        self.error, self.attempts = error, attempts


def _retry_safe(exc: Exception, account_mode: bool) -> bool:
    """Key mode retries transient failures of this cheap, read-only check.

    Account mode never replays a POST whose dispatch is unknown: the local
    proxy already retried every provably undispatched attempt, so only a
    refused connection or an explicit not-dispatched / rate-limit rejection
    may be sent again there.
    """
    if isinstance(exc, ConnectionRefusedError):
        return True
    if isinstance(exc, VisionHTTPError):
        if account_mode:
            return exc.status == 429 or "not_dispatched" in exc.body
        return exc.status in _TRANSIENT_STATUS
    if account_mode:
        return False
    # socket timeout / reset / TLS hiccup / truncated body
    return isinstance(exc, (OSError, http.client.HTTPException))


def _call_with_retry(api_base: str, api_key: str, model: str, image_b64: str, mime: str,
                     deadline: float) -> str:
    global _effort_refused
    account_mode = "PAPERKIT_ACCOUNT_DIRECT" in os.environ
    attempts = 0
    while True:
        attempts += 1
        try:
            return _call_vision(api_base, api_key, model, image_b64, mime, timeout=_REQUEST_TIMEOUT)
        except Exception as exc:
            if (not _effort_refused and isinstance(exc, VisionHTTPError) and exc.status == 400
                    and "reasoning" in exc.body.lower()):
                # Refused before any generation: this provider does not take the field.
                _effort_refused = True
                attempts -= 1
                continue
            if attempts > len(_RETRY_DELAYS) or not _retry_safe(exc, account_mode):
                raise VisionUnavailable(exc, attempts) from exc
            delay = _RETRY_DELAYS[attempts - 1]
            retry_after = getattr(exc, "retry_after", "")
            if retry_after.isdigit():
                delay = max(delay, min(int(retry_after), 60))
            if time.monotonic() + delay + _REQUEST_TIMEOUT > deadline:
                raise VisionUnavailable(exc, attempts) from exc
            print(f"Vision API 暂时失败（第 {attempts} 次）：{exc}；{delay} 秒后自动重试",
                  file=sys.stderr, flush=True)
            time.sleep(delay)

# 先逐条描述每条连线、再下结论（vision_ledger 把写了“悬空”的 EDGE 行判为有问题）。
# 2026-10-12 小白实测：研究框架图里“直接路径”是一条两头都没接框的虚线，H4（经中介的间接效应）的标注也写在这条线下；
# 只给检查清单时看图模型直接答 PASS。
PROMPT = (
    "这是一张学术论文中的 DrawIO 技术路线图 / 求解流程图 / 架构图。\n"
    "先逐条描述图里画出来的每一条连线（实线、虚线、折线、汇合线都算），每条一行，没有连线就写一行 EDGE 0: 无：\n"
    "EDGE 1: [起点节点] → [终点节点]；[两端是否接好]；标注：[线上或线旁的文字，没有写 无]\n"
    "两端都碰到节点边框（或并入另一条连线）写“接好”；有一端从空白处开始、或停在空白处，写“悬空”并说明是哪一端。"
    "只写看到的线，不要猜这条线想表达什么，也不要为没有连线的节点补写 EDGE。\n\n"
    "再严格检查以下问题：\n"
    "1. 文字是否被截断、溢出节点边框，或字号过小看不清？\n"
    "2. 节点之间是否重叠、紧贴，或某些节点挤在一起？\n"
    "3. 连线是否穿过了节点或文字？箭头方向是否合理？有没有悬空的箭头、断开的连线？（连线代表研究里的真实关系：只报画出来的线画错了——悬空、断线、穿过节点、方向不对；"
    "某个节点没有连线、两行之间没有箭头都不算问题，有没有这条关系只有作者知道。不要为了对称或“每行都有箭头”建议新增连线）\n"
    "4. 连线上的标注（如判断分支的'是/否'、假设编号）是否与节点或其他线重叠？每个连线标注是否贴在它说的那条线旁边（几条线的标注挤在同一条线下也算问题；分组框、括号上的组名不是连线标注）？\n"
    "5. 整体布局是否居中、均衡？有没有大片空白（如内容左对齐导致右侧大量留白）？\n"
    "6. 对齐是否整齐：本应竖直成一列的节点有没有明显左右错开？本应水平成一行的节点有没有明显上下参差？"
    "竖箭头/连线是否明显歪斜、没接在节点中央（偏到节点一侧）？并列节点大小是否明显不一？"
    "（只报肉眼一眼可见的错位，不必追究几像素的细微差别）\n"
    "7. 配色是否协调专业，有没有刺眼的高饱和色或杂乱的彩虹配色？\n"
    "8. 是否出现了原始 HTML 代码、乱码、黑色背景块等渲染异常？\n"
    "9. 整体是否美观、专业、适合放进学术论文？\n\n"
    "列 ISSUE 前再核对一遍：说某个节点孤立、没有连线、缺少箭头的，不要列（见第 3 条）；"
    "只把需要改图的问题写成 ISSUE，你自己也觉得可以接受、只是建议的，不要写。\n"
    "如果全部没问题，在 EDGE 各行之后单独写一行，只有一个词：PASS\n"
    "如果有问题（上面写了“悬空”的连线也算），逐条列出，每条以 'ISSUE' 开头，给出具体位置和描述：\n"
    "ISSUE 1: [位置] [问题描述]\n"
    "ISSUE 2: [位置] [问题描述]\n"
)


def _pdf_to_png(pdf_path: Path) -> Path | None:
    """把 PDF 第一页转成 PNG，返回 PNG 路径；转换工具缺失/失败返回 None（调用方据此跳过）。"""
    out_dir = Path(tempfile.mkdtemp(prefix="drawio_vcheck_"))
    out_png = out_dir / "page.png"
    # 0) PyMuPDF(fitz)：纯 wheel、自带渲染引擎、不依赖系统 poppler，打包 runtime 必有。
    #    ⛔ 放首选：pdftoppm/pdf2image 都依赖 poppler，打包环境常缺 → 曾导致视觉自检
    #    因"PDF 转不出 PNG"而静默跳过（真实翻车）。fitz 无外部依赖，最可靠。
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(pdf_path))
        doc[0].get_pixmap(matrix=fitz.Matrix(150 / 72, 150 / 72)).save(str(out_png))
        doc.close()
        if out_png.exists():
            return out_png
    except Exception:
        pass
    # 1) pdftoppm（poppler，最常见）
    try:
        import subprocess
        prefix = str(out_dir / "page")
        r = subprocess.run(
            ["pdftoppm", "-png", "-r", "150", "-singlefile", "-f", "1", "-l", "1",
             str(pdf_path), prefix],
            capture_output=True, timeout=60,
        )
        if r.returncode == 0 and out_png.exists():
            return out_png
    except Exception:
        pass
    # 2) pdf2image（依赖 poppler）
    try:
        from pdf2image import convert_from_path
        imgs = convert_from_path(str(pdf_path), dpi=150, first_page=1, last_page=1)
        if imgs:
            imgs[0].save(str(out_png), "PNG")
            if out_png.exists():
                return out_png
    except Exception:
        pass
    # 两种转换都失败：清理空临时目录，避免泄漏
    import shutil
    shutil.rmtree(out_dir, ignore_errors=True)
    return None


def _load_image_b64(img_path: Path) -> tuple[str, str] | None:
    """读取图片→(base64, mime)。超过阈值时用 PIL 等比压缩；PIL 缺失则回退原图。
    返回 None 表示无法读取（调用方据此跳过）。"""
    try:
        data = img_path.read_bytes()
    except Exception:
        return None
    ext = img_path.suffix.lower().lstrip(".")
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(ext, "image/png")

    if len(data) > _MAX_IMG_BYTES:
        try:
            import io
            from PIL import Image
            with Image.open(io.BytesIO(data)) as im:
                if im.mode not in ("RGB", "L"):
                    im = im.convert("RGB")
                max_side = max(im.size)
                if max_side > 2200:
                    ratio = 2200.0 / max_side
                    im = im.resize((max(1, int(im.size[0] * ratio)),
                                    max(1, int(im.size[1] * ratio))))
                buf = io.BytesIO()
                q = 85
                while q >= 50:
                    buf.seek(0); buf.truncate()
                    im.save(buf, format="JPEG", quality=q, optimize=True)
                    if buf.tell() <= _MAX_IMG_BYTES:
                        break
                    q -= 10
                data = buf.getvalue()
                mime = "image/jpeg"
        except Exception:
            # PIL 不可用或压缩失败 → 用原图（可能被 API 拒绝，但由上层 try 兜底跳过）
            pass

    return base64.b64encode(data).decode("ascii"), mime


def _call_vision(api_base: str, api_key: str, model: str,
                 image_b64: str, mime: str, timeout: int = _REQUEST_TIMEOUT) -> str:
    if api_key.startswith(("mxtp_", "mxcp_")):
        from trusted_gateway_config import local_model_proxy_url
        parsed = urlparse(local_model_proxy_url("/v1/chat/completions", api_key))
    else:
        from trusted_gateway_config import api_url
        # Account mode can supply a per-user provider credential plus a loopback
        # base instead of a short mxtp_ ticket; it has no signed gateway document,
        # so the signed-config path would fail with "签名配置缺失".  Older embedded
        # copies of this module lack the helper, so fall back to signed routing.
        try:
            from trusted_gateway_config import backend_loopback_url
        except ImportError:
            backend_loopback_url = lambda *_a, **_k: None
        direct = backend_loopback_url(api_base, "/v1/chat/completions")
        parsed = urlparse(direct or api_url("/v1/chat/completions"))
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if not host:
        raise ValueError(f"Bad API base URL: {api_base}")

    path = parsed.path

    payload = json.dumps({
        "model": model or "gpt-4o",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {
                    "url": f"data:{mime};base64,{image_b64}"
                }},
            ],
        }],
        "max_tokens": 2000,
        "stream": False,
        **({} if _effort_refused else {"reasoning_effort": _REASONING_EFFORT}),
    })

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Content-Length": str(len(payload)),
    }

    conn = None
    try:
        if parsed.scheme == "https":
            # 默认 CERT_REQUIRED + check_hostname，防 MITM（端点已锁定且持有效证书）
            ctx = verified_tls_context()
            conn = http.client.HTTPSConnection(host, port, timeout=timeout, context=ctx)
        else:
            conn = http.client.HTTPConnection(host, port, timeout=timeout)

        conn.request("POST", path, payload, headers)
        res = conn.getresponse()
        data = res.read()

        if res.status != 200:
            raise VisionHTTPError(res.status, data.decode("utf-8", errors="replace"),
                                  res.getheader("Retry-After", "") or "")

        result = json.loads(data.decode("utf-8"))
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"] or ""
        raise Exception("No choices in response")
    finally:
        if conn:
            conn.close()


def _review(img_b64: str, mime: str) -> str:
    """Call the configured vision model once (with transport retries); raise Unreviewable otherwise."""
    from vision_ledger import Unreviewable
    configs = [
        (os.environ.get("EDITOR_AI_API_KEY", ""),
         os.environ.get("EDITOR_AI_BASE_URL", ""),
         os.environ.get("EDITOR_AI_MODEL_ID", "gpt-4o")),
        (os.environ.get("OPENAI_API_KEY", ""),
         os.environ.get("OPENAI_BASE_URL", ""),
         os.environ.get("REVIEWER_MODEL_ID", "gpt-4o")),
    ]
    # Account-mode tickets are two route-scoped credentials for the same
    # payer/model, not independent providers.  Retrying the same image with
    # the second ticket after a transport/refusal error could create a second
    # paid request.  Key mode keeps its historical independent fallback.
    if configs[0][0].startswith(("mxtp_", "mxcp_")):
        configs = configs[:1]

    failures = []
    deadline = time.monotonic() + _TOTAL_BUDGET
    for api_key, api_base, model in configs:
        if not api_key:
            continue
        if failures and time.monotonic() + _REQUEST_TIMEOUT > deadline:
            break  # a slow first provider already used the time budget
        try:
            return _call_with_retry(api_base, api_key, model, img_b64, mime, deadline)
        except VisionUnavailable as e:
            failures.append(e)
            print(f"Vision API error: {e}", file=sys.stderr)
    if failures:
        raise Unreviewable(
            f"视觉服务暂时不可用（{failures[-1]}）",
            f"VISION_UNAVAILABLE: 视觉模型已配置但暂时调用失败（{failures[-1]}）。"
            "本图记为“视觉审查未完成”（不是通过）；网络或模型服务恢复后重跑本脚本即可，"
            "不要为此修改图或反复手动重试。",
            outage=True,
        )
    raise Unreviewable("未配置视觉模型", "NO_VISION_API: no vision-capable LLM configured (need EDITOR_AI_API_KEY or OPENAI_API_KEY) - figure NOT reviewed (recorded as unreviewed)")


def _args() -> tuple[Path | None, Path | None, str | None]:
    """image [--source 原图] [--source-sha256 送审那一刻原图的 SHA-256]."""
    args = list(sys.argv[1:])
    values = {}
    for flag in ("--source-sha256", "--source"):
        if flag in args:
            at = args.index(flag)
            values[flag] = args[at + 1] if at + 1 < len(args) else None
            del args[at:at + 2]
    source = Path(values["--source"]) if values.get("--source") else None
    return (Path(args[0]) if args else None), source, values.get("--source-sha256")


def _ledger():
    try:
        from vision_ledger import Unreviewable, run_check
    except ImportError:
        print("UNREVIEWED: 缺少 vision_ledger.py（运行包不完整），本图视觉审查未完成")
        sys.exit(2)
    return Unreviewable, run_check

def main():
    src, source, digest = _args()
    if src is None:
        print("Usage: python drawio_vision_check.py <fig.pdf|fig.png> [--source fig.pdf]")
        sys.exit(2)
    if not src.exists():
        print(f"File not found: {src}")
        sys.exit(2)
    Unreviewable, run_check = _ledger()

    def call() -> str:
        # PDF → PNG（PNG/JPG 直接用）；转换在确认要付费调用之后才做
        ext = src.suffix.lower()
        tmp_dir = None
        if ext == ".pdf":
            png = _pdf_to_png(src)
            if png is None:
                raise Unreviewable("无法把 PDF 转成图片（缺 PyMuPDF/pdftoppm/pdf2image）",
                                   "NO_CONVERTER: cannot rasterize PDF (need pdftoppm or pdf2image) — 本图视觉审查未完成")
            img_path, tmp_dir = png, png.parent
        elif ext in (".png", ".jpg", ".jpeg"):
            img_path = src
        else:
            raise Unreviewable(f"不支持的图片格式 {ext}", f"UNSUPPORTED: {ext} (need .pdf/.png/.jpg) — 本图视觉审查未完成")
        loaded = _load_image_b64(img_path)
        if tmp_dir is not None:  # 图片已读入内存(b64)，立即清理 PDF 转换产生的临时目录
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)
        if loaded is None:
            raise Unreviewable("读不到图片", "READ_FAIL: cannot read image — 本图视觉审查未完成")
        return _review(*loaded)

    sys.exit(run_check(src, "drawio", source, call, digest=digest))


if __name__ == "__main__":
    main()
