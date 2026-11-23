#!/usr/bin/env python3
"""数据图视觉自检 — 调 vision LLM 检查 matplotlib 数据图（柱状/折线/散点/热力/箱线等）
是否有坐标轴标签截断、图例压数据、刻度重叠等【影响阅读的硬伤】。

⛔ 与 tikz_vision_check.py（查流程/架构图布局）的区别：数据图关心的是坐标系可读性
   （轴标签/刻度/图例/子图挤压），而非节点连线布局。PROMPT 专为数据图定制，且刻意
   宽容——只报明确影响阅读的硬伤，不挑审美、不对 Sankey/3D/热力图等非常规图型苛求，
   把误报压到最低（数据图形态千奇百怪，误报会白烧额度、逼出无谓的重跑）。

用法:
  python _utils/data_fig_vision_check.py <image.png> [--source fig.pdf]
  python _utils/data_fig_vision_check.py <image.png> --ai-figure-spec SPEC.json [--report OUT.json]
      美赛 AI 生图核对：看图模型逐字转写 → 与图规格 strings 确定性比对（缺字/多字/写坏字/
      数值坐标轴/AI 感渲染）。看图模型不可用时可加 --transcription T.json，用执行模型亲眼
      看图抄下的文字走同一套比对。

环境变量（按优先级）:
  EDITOR_AI_API_KEY + EDITOR_AI_BASE_URL  (editor_ai 配置)
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
import re
import ssl
import unicodedata
from trusted_gateway_config import verified_tls_context
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

# 打包运行时是嵌入版 Python（带 ._pth），不会把脚本所在目录放进导入路径：
# 同目录的 vision_ledger 要自己加上，否则每张图都会被记成"没审成"。
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

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
                     deadline: float, prompt: str | None = None) -> str:
    global _effort_refused
    account_mode = "PAPERKIT_ACCOUNT_DIRECT" in os.environ
    attempts = 0
    while True:
        attempts += 1
        try:
            if prompt is None:
                return _call_vision(api_base, api_key, model, image_b64, mime, timeout=_REQUEST_TIMEOUT)
            return _call_vision(api_base, api_key, model, image_b64, mime, timeout=_REQUEST_TIMEOUT,
                                prompt=prompt)
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


PROMPT = (
    "这是一张学术论文里的【数据图】（柱状图/折线图/散点图/热力图/箱线图/子图组合等，由 "
    "matplotlib/seaborn 生成）。请只检查【明确影响阅读的硬伤】，不要挑审美，也不要对 "
    "Sankey/3D/网络图/自定义布局等非常规图型苛求。逐项核对：\n"
    "1. 坐标轴标签、刻度数字是否被截断、超出画布、或被裁掉一半？\n"
    "2. 图例（legend）是否压住了数据（曲线/柱子/散点）、panel 编号、短注释或统计框，"
    "或者跑到画布外被截断？即使角落没有数据点，盖住文字也算硬伤。\n"
    "3. x/y 轴刻度标签是否互相重叠、叠成一团看不清（尤其长文字或日期）？\n"
    "4. 多子图之间是否严重挤压、子图标题与相邻子图内容重叠？\n"
    "5. 数据在灰度打印下是否完全无法区分（多条同色系曲线且无不同线型/marker）？\n"
    "6. 任意数字、短注释或阈值标签是否被曲线、边框、柱子边缘穿过，或压在数据点上而难以辨认？"
    "不透明白底若盖住了曲线/数据也算遮挡，不能当作已经修好。\n"
    "7. 文字（尤其柱顶数字、容差带标签、浅色系列旁的注释）与其实际背景是否对比不足，"
    "看起来发白、融入色块或无法稳定辨认？白字放在深色块上不算问题。\n"
    "8. inset/局部放大图、统计框、图例是否在同一 panel 叠成多层，遮住主图关键数据、刻度，"
    "或跨到相邻 panel？顶部/右侧边际分布若压在主图上也算硬伤。\n"
    "9. 对数轴的次刻度是否密集到连成黑色梳齿，或双 y 轴两侧刻度/标签挤成一团？"
    "普通且可分辨的刻度密度不算问题。\n"
    "10. panel 编号是否压在坐标轴脊线/图例上；柱顶值、容差值或底部 callout 是否挤在边界而互相覆盖？\n"
    "11. 是否是空图、纯白图、或明显的渲染异常（大片乱码/黑块/报错文字）？\n\n"
    "⛔ 判定从宽：只要图能正常读懂、上述硬伤都没有，就判通过。轻微留白、配色偏好、"
    "一般刻度密度等【不影响读懂】的都不算问题；但已经形成黑梳子、文字互盖或关键数据被遮住时"
    "必须报出。不确定算不算硬伤时，一律判通过。\n\n"
    "如果没有上述硬伤，第一行只回答一个词：PASS\n"
    "如果确有硬伤，逐条列出，每条以 ISSUE 开头，给出具体位置和该怎么改：\n"
    "ISSUE 1: [位置] [问题描述] [修复建议]\n"
    "ISSUE 2: [位置] [问题描述] [修复建议]\n"
)

def _load_image_b64(img_path: Path):
    """读取图片→(base64, mime)。超过阈值时用 PIL 等比压缩，避免超 vision API 单图限制；
    PIL 缺失或压缩失败则回退原图。返回 None 表示无法读取（调用方据此跳过）。"""
    # vision API 单图通常限制 ~5MB；base64 放大约 33%，原图阈值留到 3.5MB
    _MAX_IMG_BYTES = 3_500_000
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
            pass  # PIL 不可用/压缩失败 → 用原图，由上层调用的 try 兜底跳过

    return base64.b64encode(data).decode("ascii"), mime


def _call_vision(api_base: str, api_key: str, model: str,
                 image_b64: str, mime: str, timeout: int = _REQUEST_TIMEOUT,
                 prompt: str | None = None) -> str:
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
                {"type": "text", "text": prompt or PROMPT},
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
            return result["choices"][0]["message"]["content"]
        raise Exception("No choices in response")
    finally:
        if conn:
            conn.close()


AI_FIGURE_PROMPT = (
    "This image is a schematic or architecture figure for an academic paper. Answer ONLY with one "
    "JSON object, no other text.\n"
    '- "texts": every piece of visible text in reading order, one string per label or line, transcribed '
    "exactly as drawn (keep math symbols as you see them; do not fix spelling).\n"
    '- "garbled": characters or words that look malformed, misspelled, accidentally duplicated or '
    "unreadable (empty list if none).\n"
    '- "data_axes": true only if the image shows numbers as data: tick values or other digits along an axis, '
    "a colour bar with values, or numeric data labels; small schematic plots whose axes carry only text labels "
    "(no digits) count as false.\n"
    '- "rendering": any of "3d", "texture", "photorealistic", "watercolor", "hand-drawn" that clearly apply '
    '(empty list if none).\n'
    '- "double_headed": every arrow or connector line that has an arrowhead at BOTH ends, named by the labels '
    'it joins (empty list if none).\n'
    'Format: {"texts": [...], "garbled": [...], "data_axes": false, "rendering": [...], "double_headed": [...]}'
)


# "seen" 写在 "holds" 前面：先描述再下结论。10-10 第二次出图实测 claude-sonnet-5 先给结论时，常写出
# "seen: 阴影在上限线上方" 却配 holds=false 这种自相矛盾的回答。
_RELATION_RULE = (
    'one item per numbered statement below, {"n": <number>, "seen": "<what the image actually shows there, at most '
    '15 words>", "holds": true or false}; write "seen" first, looking at the elements the statement names, then set '
    '"holds" from what you wrote; judge only what is visibly drawn (which labels an arrow joins and which way it '
    'points, order, crossings, relative sizes); when unsure, answer false.'
)


def _numbered(relations: list) -> str:
    return "Statements:\n" + "\n".join(f"{i}. {statement}" for i, statement in enumerate(relations, 1))


def ai_figure_prompt(relations: list | None = None) -> str:
    """看图转写提示词。图规格带关系断言（箭头从哪到哪、哪两条线交叉、哪根柱子最短……）时，把 "relations"
    作为与 texts 并列的一项写进同一个 JSON 的格式里，让看图模型逐条判。

    10-10 实验里文字全对、却画错关系的图（α 的箭头指向不该指的存量、连线两头都有箭头、台阶和柱子
    对不上），文字比对一张都抓不到。实测把关系问题附在末尾时，claude-sonnet-5 有时拆成几段 JSON、
    有时干脆不答，所以做成正式的一项；仍没答的由 main_ai_figure 单独追问一次。
    """
    if not relations:
        return AI_FIGURE_PROMPT
    head = AI_FIGURE_PROMPT.rsplit("Format:", 1)[0]
    return (head + '- "relations": ' + _RELATION_RULE + "\n" + _numbered(relations) + "\n"
            'Format: {"texts": [...], "garbled": [...], "data_axes": false, "rendering": [...], '
            '"double_headed": [...], "relations": [{"n": 1, "seen": "...", "holds": true}]}')


def relations_only_prompt(relations: list) -> str:
    """第一次回答漏了关系时的单独追问：只问关系，只要一个 JSON。"""
    return ("This image is a schematic figure for an academic paper. Answer ONLY with one JSON object "
            '{"relations": [...]}, no other text. "relations": ' + _RELATION_RULE + "\n" + _numbered(relations))


def relations_recheck_prompt(numbered: list) -> str:
    """第一遍判不成立的关系单独复核：只问这几条（保留原编号），先描述再下结论，看不清的小出入不算错。

    10-10 第二次出图 6 张全部因关系不成立被拦。逐张人工看，多数是看图模型一次读 30 条文字加 6 条关系时判错：
    写着阴影在上限线上方却判不成立、箭头头部离卡片边差一点就判没到、箭头只指进上排五格却说也指进了下排。
    复核只给两条看图惯例，不许往"成立"上偏：试过加一句"只有明显不符才判不成立"，复核就把画反的箭头
    （seen 写着从年卡片指向日卡片）判成了成立。
    """
    return ("This image is a schematic figure for an academic paper. Check the numbered statements below carefully, "
            "one at a time. For each, first find the elements it names in quotes and describe exactly what is drawn "
            "there: which element each arrow starts at and which element its arrowhead points at, the order, the "
            "relative sizes. Then compare your description with the statement: holds is true only if they agree, "
            "including the direction of every arrow. Reading conventions: an arrow whose head points at a box and "
            "stops at or near its edge ends at that box; a region drawn against a line lies on the side of the line "
            "where it is drawn. Answer ONLY with one JSON object "
            '{"relations": [{"n": <number>, "seen": "<what is drawn, at most 20 words>", "holds": true or false}]}, '
            "no other text.\nStatements:\n" + "\n".join(f"{n}. {statement}" for n, statement in numbered))


def glyph_recheck_prompt(items: list) -> str:
    """形近字母复核：把规格里可能读混的希腊字母遮成 ?，让看图模型自己认图里画的是希腊字母还是拉丁字母。
    不把答案递给它——递了它会照抄（看图转写本来就爱把字"改对"）。"""
    masked = ["".join("?" if ch in _GREEK_LOOKALIKE else ch for ch in item) for item in items]
    return ("This image is a schematic figure for an academic paper. Find each label below in the image; each ? hides "
            "one letter. Copy the whole label exactly as drawn, character by character. The hidden letters are easy to "
            "confuse in italic serif type (Greek α ν ρ χ ω κ ι ο υ γ versus Latin a v p x w k i o u y): look closely "
            "and write a Greek letter only if the glyph is drawn as that Greek letter. Answer ONLY with one JSON object "
            '{"labels": [{"n": <number>, "text": "<the label exactly as drawn>"}]}, no other text.\nLabels:\n'
            + "\n".join(f'{n}. "{m}"' for n, m in enumerate(masked, 1)))


def read_glyph_answers(items: list, reply: str) -> dict:
    """形近字母复核的回答 → {规格文字: {"ok": 第二遍是否读出了规格里的希腊字母, "seen": 第二遍抄的原文}}。没答的不列。"""
    decoder, labels, i = json.JSONDecoder(), None, 0
    while labels is None:
        i = reply.find("{", i)
        if i < 0:
            break
        try:
            obj, end = decoder.raw_decode(reply, i)
        except json.JSONDecodeError:
            i += 1
            continue
        if isinstance(obj, dict) and isinstance(obj.get("labels"), list):
            labels = obj["labels"]
        i = end
    out = {}
    for entry in labels or []:
        if not isinstance(entry, dict):
            continue
        try:
            n = int(entry.get("n"))
        except (TypeError, ValueError):
            continue
        if not 1 <= n <= len(items):
            continue
        item, text = items[n - 1], str(entry.get("text") or "")[:200]
        sk, got = _skeleton(item), _skeleton(text)
        out[item] = {"ok": bool(got) and (sk in got or bool(_MATH_HINT.search(item) and _contains_all(sk, got))),
                     "seen": text}
    return out

_GREEK_NAMES = {
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε", "varepsilon": "ε",
    "zeta": "ζ", "eta": "η", "theta": "θ", "kappa": "κ", "lambda": "λ", "mu": "μ", "nu": "ν",
    "xi": "ξ", "pi": "π", "rho": "ρ", "sigma": "σ", "tau": "τ", "phi": "φ", "varphi": "φ",
    "chi": "χ", "psi": "ψ", "omega": "ω", "Delta": "Δ", "Gamma": "Γ", "Lambda": "Λ",
    "Sigma": "Σ", "Phi": "Φ", "Omega": "Ω", "sum": "Σ",
}
# 手绘线描感只提醒、不退回（用户 10-09 定）：美赛真实试跑里背景图两次都只因 hand-drawn 被退成程序画，
# AI 图内容和文字全对，退回的程序画反而更粗糙。立体、纹理、照片感、水彩仍判不通过。
_FAIL_RENDERING = {"3d", "texture", "photorealistic", "watercolor"}
# 渐变、阴影不再问也不再提醒（10-15）：看图模型几乎张张都报（第四轮 20 次核对 18 次），按框下边缘量真带投影的只有 2%；
# 生图提示词已明令不画，留着这条提醒只会让人以为每张都有问题。万一还报了（旧提示词、亲眼转写）也不出提醒。
_IGNORED_RENDERING = {"gradient", "shadow"}
_MATH_HINT = re.compile(r"[=~^_/(){}\\]|[^\x00-\x7f]")
# 骨架最后统一小写，所以英文名一律按小写查：Delta / delta / DELTA 都是 δ
_GREEK_LOWER = {name.lower(): letter.lower() for name, letter in _GREEK_NAMES.items()}
_BARE_GREEK = re.compile(r"(?<![A-Za-z])(" + "|".join(sorted(_GREEK_LOWER, key=len, reverse=True))
                         + r")(?![A-Za-z])", re.I)
# 转写偶尔用 LaTeX：算子名保留成字母，\mathcal \left \frac 这类排版命令只丢命令名、保留花括号里的内容
_LATEX_KEEP = {"ln", "log", "exp", "sin", "cos", "tan", "max", "min", "arg", "lim", "det", "sup", "inf", "mod", "Pr"}


def _skeleton(text: str) -> str:
    """只留字母、数字、希腊字母，统一大小写与写法：'σ_j²' / '\\sigma_j^2' / 'sigma_j^2' 都成 'σj2'，
    'ΔV' / 'Delta V' / '\\Delta V' 都成 'δv'（转写常把希腊字母拼成英文名）。"""
    t = unicodedata.normalize("NFKC", str(text)).replace("∑", "Σ").replace("∼", "~")
    t = re.sub(r"\\([A-Za-z]+)", lambda m: _GREEK_NAMES.get(m.group(1))
               or (m.group(1) if m.group(1) in _LATEX_KEEP else " "), t)
    t = _BARE_GREEK.sub(lambda m: _GREEK_LOWER[m.group(1).lower()], t)
    # str.lower() 会把词尾的 Σ 变成 ς（如 "xΣ_j"），统一回 σ
    return "".join(ch for ch in t.lower().replace("ς", "σ") if ch.isalnum())


def _words(text: str) -> set[str]:
    plain = re.sub(r"\\[A-Za-z]+", " ", unicodedata.normalize("NFKC", str(text)))   # \mathcal \left 不是图里的字
    return {w for w in re.findall(r"[A-Za-z]{3,}", plain.lower())}


_GREEK_WORDS = {name.lower() for name in _GREEK_NAMES}


def _contains_all(sk: str, corpus: str) -> bool:
    """数学式近似：转写里某一小段含有 sk 的全部字符，只多出求和下标之类、或上下标换了顺序。
    少字、换字都不算——写坏的字形（10-08 实验 S1 公式里的 k）在转写里就是"换字"。"""
    from collections import Counter
    need = Counter(sk)
    if need - Counter(corpus):
        return False
    n = len(sk)
    for width in range(n, min(len(corpus), n + max(2, n // 3)) + 1):
        for i in range(len(corpus) - width + 1):
            if not need - Counter(corpus[i:i + width]):
                return True
    return False


def _assembled(sk: str, pieces: list) -> bool:
    """一条规格文字被转写拆成 2–3 行、且这几行没挨着读出来：能用完整的转写条目拼出来也算有。"""
    pieces = [p for p in pieces if p]

    def walk(rest: str, depth: int, used: frozenset) -> bool:
        if not rest:
            return depth >= 2
        if depth == 3:
            return False
        return any(rest.startswith(p) and walk(rest[len(p):], depth + 1, used | {i})
                   for i, p in enumerate(pieces) if i not in used)
    return walk(sk, 0, frozenset())


# 求和、极值这类运算符的下标在行间公式里写在符号正下方（如 max 下面的 j），看图转写常漏读这一个字母
# （10-10 实测 "min max_j V_j / K_j" 转成 "min max V_j / K_j"）。去掉这类下标后能对上，就降为近似（人工看），不判缺字。
_OP_LIMIT = re.compile(r"(?<![A-Za-z])(argmax|argmin|max|min|sup|inf|lim|sum|prod|Σ|∑|Π|∏)_(\{[^{}]*\}|[^\s{}/()=+\-·,]+)")


def _matches(sk: str, item: str, corpus: str, pieces: list) -> bool:
    return sk in corpus or _assembled(sk, pieces) or bool(_MATH_HINT.search(item) and _contains_all(sk, corpus))


# 形近字母：斜体衬线里 α/a、ν/v、ρ/p、χ/x、ω/w、κ/k、ι/i、ο/o、υ/u、γ/y 几乎一样。生图真写错过
# （10-08 ρ 画成 p、10-10 第一轮 α 写成 a），看图转写也读错过（10-10 第三轮 "x = (C, τ, h, a, α)" 写对了，
# 转写成 "a, a"）。所以只差这类字母的仍算缺字，但另列 lookalike，主流程把这几个字母遮住单独再认一次：
# 两遍都读成拉丁字母才拦，第二遍认出希腊字母就降为 WARN、交给人放大看。
_LOOKALIKE = str.maketrans({"α": "a", "ν": "v", "ρ": "p", "χ": "x", "ω": "w", "κ": "k", "ι": "i", "ο": "o",
                            "υ": "u", "γ": "y"})
_GREEK_LOOKALIKE = frozenset("ανρχωκιουγ")


def compare_ai_figure_text(expected: list, found: list) -> dict:
    """确定性比对：expected=图规格 strings，found=看图模型转写的文字。

    - 缺字：expected 的骨架在全部转写拼接后的骨架里找不到，也拼不出来（拆成几行分开读出也算有）。
      数学式另允许"近似"（见 _contains_all）：只容忍转写多出字符或换序，少字、换字都算缺。
      骨架少于 2 个字符的单字母变量不核（转写不稳）。
    - 多字：转写里出现、但任何 expected 都没有的英文单词（≥3 字母；希腊字母的英文名不算）。
    - 形近字母：规格里的希腊字母只被读成形近的拉丁字母（见 _LOOKALIKE）时仍算缺字，另列进 lookalike 供复核。
    - 盲区：骨架不分大小写（k 与 K 分不出）；标签指的位置对不对比不出来，靠看图模型报 garbled。
    """
    pieces = [_skeleton(x) for x in found]
    corpus = _skeleton(" ".join(str(x) for x in found))
    folded_pieces = [p.translate(_LOOKALIKE) for p in pieces]
    folded_corpus = corpus.translate(_LOOKALIKE)
    missing, approx, lookalike = [], [], []
    for item in expected:
        sk = _skeleton(item)
        if len(sk) < 2 or sk in corpus or _assembled(sk, pieces):
            continue
        if _MATH_HINT.search(item) and _contains_all(sk, corpus):
            approx.append(item)
            continue
        bare = _OP_LIMIT.sub(lambda m: m.group(1), item)
        if bare != item and len(_skeleton(bare)) >= 2 and _matches(_skeleton(bare), bare, corpus, pieces):
            approx.append(item)
            continue
        if (any(ch in _GREEK_LOOKALIKE for ch in sk)
                and _matches(sk.translate(_LOOKALIKE), item, folded_corpus, folded_pieces)):
            lookalike.append(item)
        missing.append(item)
    vocab = set()
    for item in expected:
        vocab |= _words(item)
    extras = sorted({w for x in found for w in _words(x)} - vocab - _GREEK_WORDS)
    return {"missing": missing, "approx": approx, "lookalike": lookalike, "extras": extras}


def _merge_split_reply(reply: str) -> dict | None:
    """看图模型偶尔把一个回答拆成几段 JSON（10-10 实测 claude-sonnet-5：主体一段、relations 另起一段，
    或者把每条关系各写成一个对象）。逐段解码后合并：texts 取第一段带 texts 的，relations 收齐各段。"""
    decoder = json.JSONDecoder()
    objects, i = [], 0
    while True:
        i = reply.find("{", i)
        if i < 0:
            break
        try:
            obj, end = decoder.raw_decode(reply, i)
        except json.JSONDecodeError:
            i += 1
            continue
        if isinstance(obj, dict):
            objects.append(obj)
        i = end
    main = next((o for o in objects if isinstance(o.get("texts"), list)), None)
    if main is None:
        return None
    merged = dict(main)
    relations = list(main["relations"]) if isinstance(main.get("relations"), list) else []
    for obj in objects:
        if obj is main:
            continue
        if isinstance(obj.get("relations"), list):
            relations += obj["relations"]
        elif "n" in obj and "holds" in obj:
            relations.append(obj)
    merged["relations"] = relations
    return merged


def _near_word(word: str, vocab: set) -> bool:
    """转写里多出的词和规格里的某个词只差一两个字母（插字、少字、换一个字），多半是图里写坏了。"""
    for v in vocab:
        short, long_ = sorted((word, v), key=len)
        if len(long_) - len(short) <= 2 and short in long_:
            return True
        if len(word) == len(v) and sum(a != b for a, b in zip(word, v)) == 1:
            return True
    return False


def parse_ai_figure_reply(reply: str) -> dict | None:
    """从看图模型回复里取出第一个 JSON 对象；格式不对返回 None（按"无法判定"处理）。"""
    start, end = reply.find("{"), reply.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(reply[start:end + 1])
    except json.JSONDecodeError:
        data = None
    if not isinstance(data, dict) or not isinstance(data.get("texts"), list):
        data = _merge_split_reply(reply)
    if data is None:
        return None

    def _list(key):
        value = data.get(key, [])
        return value if isinstance(value, list) else []

    relations = []
    for item in _list("relations"):
        if not isinstance(item, dict):
            continue
        try:
            n = int(item.get("n"))
        except (TypeError, ValueError):
            continue
        relations.append({"n": n, "holds": item.get("holds") is True, "seen": str(item.get("seen") or "")[:200]})
    return {
        "texts": [str(x) for x in _list("texts") if isinstance(x, (str, int, float))],
        "garbled": [str(x) for x in _list("garbled") if isinstance(x, (str, int, float))],
        "data_axes": data.get("data_axes") is True,
        "rendering": [str(x).strip().lower() for x in _list("rendering") if isinstance(x, str)],
        "double_headed": [str(x) for x in _list("double_headed") if isinstance(x, (str, int, float))],
        "relations": relations,
    }


def ai_figure_verdict(expected: list, parsed: dict, relations: list | None = None,
                      allow_two_way: bool = False, recheck: dict | None = None, glyphs: dict | None = None) -> dict:
    """合并比对结果与看图模型的标记，给出 PASS/FAIL 和逐条原因。

    relations：图规格里的关系断言，看图模型（或执行模型亲自看图）要逐条答 holds；缺答或不成立都判不通过。
    allow_two_way：图规格明确要双向箭头时才放行两头都有箭头的连线。
    recheck：第一遍判不成立的关系单独复核的回答 {n: {"holds", "seen"}}。复核仍不成立（或没答）才判不通过；
    复核判成立的不拦，写成 WARN 交给执行模型亲自看图定夺。
    glyphs：形近字母复核的回答（见 read_glyph_answers）。第二遍认出了规格里的希腊字母的，不再算缺字，写成 WARN。
    """
    cmp = compare_ai_figure_text(expected, parsed["texts"])
    reasons, warnings = [], []
    checked = glyphs or {}
    cleared = [item for item in cmp["lookalike"] if checked.get(item, {}).get("ok")]
    if cleared:
        cmp["missing"] = [item for item in cmp["missing"] if item not in cleared]
        warnings.append("形近字母两遍读法不同（请放大看）: "
                        + " | ".join(f"{item}（复核读作：{checked[item]['seen']}）" for item in cleared))
    vocab = set()
    for item in expected:
        vocab |= _words(item)
    near = [w for w in cmp["extras"] if _near_word(w, vocab)]
    if near:   # 公式近似匹配会放过插进去的字母（10-10 实测 A^alt 画成 A^xalt），这里补上
        reasons.append("疑似写坏的字（和规格里的词只差一两个字母）: " + ", ".join(near))
    double_headed = parsed.get("double_headed") or []
    if double_headed and not allow_two_way:
        reasons.append("连线两头都有箭头、方向说不清: " + " | ".join(double_headed[:6]))
    answered = {item["n"]: item for item in parsed.get("relations") or []}
    rechecked = recheck or {}
    for n, statement in enumerate(relations or [], 1):
        item = answered.get(n)
        second = rechecked.get(n)
        if item is None:
            reasons.append(f"关系没有核对: {n}. {statement}")
        elif item["holds"]:
            continue
        elif second is not None and second["holds"]:
            warnings.append(f"关系两遍核对结论不同（请亲自看图确认）: {n}. {statement}"
                            f"（第一遍：{item['seen'] or '未说明'}；复核：{second['seen'] or '未说明'}）")
        else:
            again = f"；复核：{second['seen'] or '未说明'}" if second is not None else ""
            reasons.append(f"关系不成立: {n}. {statement}（图中：{item['seen'] or '未说明'}{again}）")
    if cmp["missing"]:
        reasons.append("图中缺少或写错规格文字: " + " | ".join(cmp["missing"]))
    if len(cmp["extras"]) >= 3:
        reasons.append("图中多出规格之外的文字: " + ", ".join(cmp["extras"][:12]))
    elif cmp["extras"]:
        warnings.append("可能多出的文字（转写噪声或 AI 自加）: " + ", ".join(cmp["extras"]))
    if parsed["garbled"]:
        reasons.append("看图模型报告写坏或重复的字: " + " | ".join(parsed["garbled"][:8]))
    if parsed["data_axes"]:
        reasons.append("示意图里出现了数值坐标轴或数据（像结果，禁止）")
    bad_render = sorted(set(parsed["rendering"]) & _FAIL_RENDERING)
    if bad_render:
        reasons.append("出现 AI 感渲染: " + ", ".join(bad_render))
    soft = sorted(set(parsed["rendering"]) - _FAIL_RENDERING - _IGNORED_RENDERING)
    if soft:
        warnings.append("渲染提示: " + ", ".join(soft))
    if cmp["approx"]:
        warnings.append("数学式近似匹配（请人工留意）: " + " | ".join(cmp["approx"]))
    return {"verdict": "FAIL" if reasons else "PASS", "reasons": reasons, "warnings": warnings,
            **cmp, "garbled": parsed["garbled"], "data_axes": parsed["data_axes"],
            "rendering": parsed["rendering"], "double_headed": double_headed,
            "relations": [{"statement": s, **answered.get(n, {"n": n, "holds": None, "seen": ""}),
                           **({"recheck": {"holds": rechecked[n]["holds"], "seen": rechecked[n]["seen"]}}
                              if n in rechecked else {})}
                          for n, s in enumerate(relations or [], 1)],
            **({"glyph_recheck": checked} if glyphs is not None else {}),
            "transcription": parsed["texts"]}


def _vision_configs():
    configs = [
        (os.environ.get("EDITOR_AI_API_KEY", ""),
         os.environ.get("EDITOR_AI_BASE_URL", ""),
         os.environ.get("EDITOR_AI_MODEL_ID", "gpt-4o")),
        (os.environ.get("OPENAI_API_KEY", ""),
         os.environ.get("OPENAI_BASE_URL", ""),
         os.environ.get("REVIEWER_MODEL_ID", "gpt-4o")),
    ]
    # 账号模式下这是同一付费方的两张票，不是两个可安全重试的供应商。
    if configs[0][0].startswith(("mxtp_", "mxcp_")):
        configs = configs[:1]
    return configs


def main_ai_figure(argv: list) -> int:
    """python data_fig_vision_check.py IMAGE --ai-figure-spec SPEC.json [--report OUT.json]

    退出码：0 = PASS；1 = FAIL（调用方退回底稿）；2 = 无法判定（视觉模型不可用/回复不是 JSON）。
    """
    import argparse
    parser = argparse.ArgumentParser(prog="data_fig_vision_check.py")
    parser.add_argument("image")
    parser.add_argument("--ai-figure-spec", required=True)
    parser.add_argument("--report", default=None)
    parser.add_argument("--transcription", default=None,
                        help="看图模型不可用时，执行模型亲自看图抄下的文字 JSON；比对仍由本脚本确定性完成")
    args = parser.parse_args(argv)

    def _write(report: dict) -> None:
        if args.report:
            Path(args.report).parent.mkdir(parents=True, exist_ok=True)
            Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    try:
        spec = json.loads(Path(args.ai_figure_spec).read_text(encoding="utf-8"))
        expected = [str(s) for s in spec.get("strings", []) if isinstance(s, str) and s.strip()]
        relations = [str(s).strip() for s in (spec.get("relations") or []) if isinstance(s, str) and s.strip()]
        allow_two_way = spec.get("allow_two_way") is True
    except (OSError, json.JSONDecodeError, AttributeError) as exc:
        print(f"SPEC_INVALID: {exc}")
        return 2
    if not expected:
        print("SPEC_INVALID: 图规格没有 strings")
        return 2
    prompt = ai_figure_prompt(relations)
    if args.transcription:
        try:
            parsed = parse_ai_figure_reply(Path(args.transcription).read_text(encoding="utf-8"))
        except OSError as exc:
            print(f"TRANSCRIPTION_INVALID: {exc}")
            return 2
        if parsed is None or not parsed["texts"]:
            print("TRANSCRIPTION_INVALID: 需要 {\"texts\": [...], \"garbled\": [...], ...}")
            _write({"verdict": "UNAVAILABLE", "reasons": ["转写文件格式不对或为空"]})
            return 2
        report = {**ai_figure_verdict(expected, parsed, relations, allow_two_way), "transcriber": "executor"}
        _write(report)
        print(report["verdict"])
        for line in report["reasons"]:
            print(f"ISSUE: {line}")
        for line in report["warnings"]:
            print(f"WARN: {line}")
        return 0 if report["verdict"] == "PASS" else 1
    img_path = Path(args.image)
    loaded = _load_image_b64(img_path) if img_path.exists() else None
    if loaded is None:
        print("READ_FAIL: cannot read image")
        _write({"verdict": "UNAVAILABLE", "reasons": ["图片读不了"]})
        return 2
    img_b64, mime = loaded
    failures = []
    deadline = time.monotonic() + _TOTAL_BUDGET
    for api_key, api_base, model in _vision_configs():
        if not api_key:
            continue
        if failures and time.monotonic() + _REQUEST_TIMEOUT > deadline:
            break
        try:
            reply = _call_with_retry(api_base, api_key, model, img_b64, mime, deadline, prompt=prompt)
        except VisionUnavailable as e:
            failures.append(e)
            print(f"Vision API error: {e}", file=sys.stderr)
            continue
        parsed = parse_ai_figure_reply(reply)
        if parsed is None:
            print("VISION_UNPARSABLE: 看图模型没有按 JSON 回复，本图无法判定")
            _write({"verdict": "UNAVAILABLE", "reasons": ["看图模型回复不是 JSON"], "raw": reply[:2000]})
            return 2
        if relations and not parsed["relations"]:
            # 漏答关系：单独追问一次（同一个模型、同一张图，只问关系）。追问也失败就交给执行模型亲眼核对。
            try:
                follow = _call_with_retry(api_base, api_key, model, img_b64, mime, deadline,
                                          prompt=relations_only_prompt(relations))
            except VisionUnavailable as e:
                print(f"VISION_UNAVAILABLE: 关系核对的追问没有完成（{e}）")
                _write({"verdict": "UNAVAILABLE", "reasons": ["关系核对的追问没有完成"], "raw": reply[:2000]})
                return 2
            merged = _merge_split_reply('{"texts": []} ' + follow) or {}
            parsed["relations"] = parse_ai_figure_reply(json.dumps(
                {"texts": [], "relations": merged.get("relations", [])}))["relations"]
            reply = reply + "\n\n[relations follow-up]\n" + follow
        recheck, recheck_note = None, ""
        first = {item["n"]: item for item in parsed["relations"]}
        failed = sorted(n for n, item in first.items() if not item["holds"] and 1 <= n <= len(relations))
        if failed:
            # 第一遍判不成立的关系单独复核一次（同一个模型、同一张图，只问这几条）。两遍都不成立才算不通过，
            # 结论不同的写成 WARN 交给执行模型亲自看图；复核调不通就按第一遍判。
            try:
                second = _call_with_retry(api_base, api_key, model, img_b64, mime, deadline,
                                          prompt=relations_recheck_prompt([(n, relations[n - 1]) for n in failed]))
            except VisionUnavailable as e:
                print(f"Vision API error: {e}", file=sys.stderr)
                recheck_note = f"关系复核没有完成（{e}），按第一遍判"
            else:
                merged = _merge_split_reply('{"texts": []} ' + second) or {}
                answers = parse_ai_figure_reply(json.dumps(
                    {"texts": [], "relations": merged.get("relations", [])}))["relations"]
                recheck = {item["n"]: item for item in answers if item["n"] in failed}
                reply = reply + "\n\n[relations recheck]\n" + second
        glyphs, glyph_note = None, ""
        suspects = compare_ai_figure_text(expected, parsed["texts"])["lookalike"]
        if suspects:
            # 只差形近字母（α 读成 a 这类）的文字：遮住这几个字母单独再认一次，两遍都读成拉丁字母才拦。
            try:
                answer = _call_with_retry(api_base, api_key, model, img_b64, mime, deadline,
                                          prompt=glyph_recheck_prompt(suspects))
            except VisionUnavailable as e:
                print(f"Vision API error: {e}", file=sys.stderr)
                glyph_note = f"形近字母复核没有完成（{e}），按第一遍判"
            else:
                glyphs = read_glyph_answers(suspects, answer)
                reply = reply + "\n\n[glyph recheck]\n" + answer
        report = {**ai_figure_verdict(expected, parsed, relations, allow_two_way, recheck, glyphs),
                  "transcriber": "vision_model", "model": model, "raw": reply[:6000]}
        for note in (recheck_note, glyph_note):
            if note:
                report["warnings"].append(note)
        _write(report)
        print(report["verdict"])
        for line in report["reasons"]:
            print(f"ISSUE: {line}")
        for line in report["warnings"]:
            print(f"WARN: {line}")
        return 0 if report["verdict"] == "PASS" else 1
    _write({"verdict": "UNAVAILABLE", "reasons": [str(failures[-1]) if failures else "未配置视觉模型"]})
    if failures:
        print(f"VISION_UNAVAILABLE: 视觉模型已配置但暂时调用失败（{failures[-1]}）")
    else:
        print("NO_VISION_API: No vision-capable LLM configured (need EDITOR_AI_API_KEY or OPENAI_API_KEY)")
    return 2


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
    raise Unreviewable("未配置视觉模型", "NO_VISION_API: No vision-capable LLM configured (need EDITOR_AI_API_KEY or OPENAI_API_KEY) - figure NOT reviewed (recorded as unreviewed)")


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
    if any(a == "--ai-figure-spec" or a.startswith("--ai-figure-spec=") for a in sys.argv[1:]):
        sys.exit(main_ai_figure(sys.argv[1:]))
    img_path, source, digest = _args()
    if img_path is None:
        print("Usage: python data_fig_vision_check.py <image.png> [--source fig.pdf]")
        sys.exit(2)
    if not img_path.exists():
        print(f"File not found: {img_path}")
        sys.exit(2)
    Unreviewable, run_check = _ledger()

    def call() -> str:
        # 读取图片（超大图自动压缩，防超 vision API 单图限制）
        loaded = _load_image_b64(img_path)
        if loaded is None:
            raise Unreviewable("读不到图片", "READ_FAIL: cannot read image — 本图视觉审查未完成")
        return _review(*loaded)

    sys.exit(run_check(img_path, "datafig", source, call, digest=digest))


if __name__ == "__main__":
    main()
