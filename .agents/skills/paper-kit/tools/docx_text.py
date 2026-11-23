"""本机自建：Markdown 读取 + 文本度量，替代原软件里的 `docx_text`。

原 `docx_text.pyc` 只导出一个 `read_markdown(path)` 和一个异常类
`DocumentEncodingError`，本文件按同样签名重写，供 `docx_export.py` 使用。

    read_markdown(path) -> str
        读 Markdown 源文件。编码按 UTF-8 → UTF-8-SIG → GB18030 依次试，
        全失败抛 DocumentEncodingError（与原行为一致：不静默乱码）。
"""

from __future__ import annotations

from pathlib import Path


class DocumentEncodingError(Exception):
    """文件编码既不是 UTF-8 也不是 GB18030，无法安全解码。"""


_ENCODINGS = ("utf-8", "utf-8-sig", "gb18030")


def read_markdown(path) -> str:
    p = Path(path)
    raw = p.read_bytes()
    for enc in _ENCODINGS:
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise DocumentEncodingError(
        f"{p} 无法解码：试过 {'/'.join(_ENCODINGS)}，可能是二进制文件或其它编码"
    )
