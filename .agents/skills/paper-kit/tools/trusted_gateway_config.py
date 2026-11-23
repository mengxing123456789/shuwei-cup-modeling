"""本机自建：把「网关地址解析 + TLS 上下文」这一层自己实现，不依赖任何外部软件。

为什么要有这个文件：
    搬过来的几个脚本（`tikz_vision_check` / `data_fig_vision_check` /
    `drawio_vision_check` / `gpt_image` / `scholar_fetch`）原本从
    `trusted_gateway_config` 里取四样东西：TLS 上下文、端点地址、loopback 直连、
    HTTPS 连接对象。那个模块是原软件的一部分，随软件一起消失。

    本文件按它们的**调用签名**重写一份等价实现，只用标准库 + 环境变量，
    所以脚本可以完全独立跑，不指向任何安装目录。

对外提供的函数（与原模块同名同参）：
    verified_tls_context()                      -> ssl.SSLContext
    api_url(endpoint, snapshot=None)            -> str
    backend_loopback_url(api_base, path)        -> str | None
    local_model_proxy_url(path, api_key)        -> str
    https_connection(host, port, timeout=..., context=...) -> HTTPSConnection

地址从哪来（按优先级）：
    1. 显式参数 `snapshot`（dict，取 base_url / api_base_url 键）
    2. 环境变量：VISION_BASE_URL > OPENAI_BASE_URL > EDITOR_AI_BASE_URL
    3. 兜底 https://api.openai.com

用法示例（本机 magpie 网关）：
    set OPENAI_BASE_URL=http://127.0.0.1:3425/v1
    set OPENAI_API_KEY=sk-local
    set REVIEWER_MODEL_ID=group/deepseek-v4.1-flash
    python run_tool.py tikz_vision_check.py fig.png
"""

from __future__ import annotations

import http.client
import os
import ssl
from urllib.parse import urljoin, urlparse

__all__ = [
    "verified_tls_context",
    "api_url",
    "backend_loopback_url",
    "local_model_proxy_url",
    "https_connection",
]

_ENV_ORDER = ("VISION_BASE_URL", "OPENAI_BASE_URL", "EDITOR_AI_BASE_URL", "GPT_IMAGE_BASE_URL")
_DEFAULT_BASE = "https://api.openai.com"
_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1", "[::1]"}


def _base_from_env() -> str:
    for name in _ENV_ORDER:
        val = (os.environ.get(name) or "").strip()
        if val:
            return val
    return _DEFAULT_BASE


def _base_from_snapshot(snapshot) -> str:
    if isinstance(snapshot, dict):
        for key in ("base_url", "api_base_url", "api_base", "endpoint"):
            val = snapshot.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    if isinstance(snapshot, str) and snapshot.strip():
        return snapshot.strip()
    return ""


def _join(base: str, endpoint: str) -> str:
    """把 endpoint（以 / 开头）接到 base 后面，避免出现 /v1/v1 这种重复。"""
    base = base.rstrip("/")
    endpoint = "/" + endpoint.lstrip("/")
    parsed = urlparse(base)
    if parsed.path.rstrip("/").endswith("/v1") and endpoint.startswith("/v1/"):
        endpoint = endpoint[3:]
    return base + endpoint


def verified_tls_context() -> ssl.SSLContext:
    """默认做证书校验的 TLS 上下文（CERT_REQUIRED + check_hostname）。

    原来那份会额外校验签名网关的指纹；本机不需要——只连自己配的地址。
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    return ctx


def api_url(endpoint: str, snapshot=None) -> str:
    """按配置拼出完整 URL。endpoint 形如 `/v1/chat/completions`。"""
    base = _base_from_snapshot(snapshot) or _base_from_env()
    return _join(base, endpoint)


def backend_loopback_url(api_base: str, path: str) -> str | None:
    """若 api_base 指向本机（http + 127.0.0.1/localhost），返回直连 URL；否则 None。

    原实现要求 http、无凭据、无 query/fragment；这里同样严格，只是不再剥 /v1。
    """
    if not api_base:
        return None
    parsed = urlparse(api_base.strip())
    if parsed.scheme != "http":
        return None
    if parsed.username or parsed.password:
        return None
    if parsed.query or parsed.fragment:
        return None
    host = (parsed.hostname or "").lower()
    if host not in _LOOPBACK_HOSTS:
        return None
    base = f"http://{host}"
    if parsed.port:
        base += f":{parsed.port}"
    if parsed.path and parsed.path != "/":
        base += parsed.path.rstrip("/")
    return _join(base, path)


def local_model_proxy_url(path: str, api_key: str) -> str:
    """原实现把 mxtp_/mxcp_ 票据换成后端本地代理地址；本机没有代理，直接按配置拼。"""
    del api_key  # 本机网关不校验票据
    return api_url(path)


def https_connection(host: str, port: int, *, timeout: float = 60, context=None):
    """构造 HTTPSConnection；context 为空就用默认校验上下文。"""
    if context is None:
        context = verified_tls_context()
    return http.client.HTTPSConnection(host, port, timeout=timeout, context=context)


def connection_for(url: str, timeout: float = 60):
    """便捷入口：给完整 URL，返回 (conn, path)。http/https 自动分派。"""
    parsed = urlparse(url)
    if not parsed.hostname:
        raise ValueError(f"Bad URL: {url}")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query
    if parsed.scheme == "https":
        return https_connection(parsed.hostname, port, timeout=timeout), path
    return http.client.HTTPConnection(parsed.hostname, port, timeout=timeout), path
