# -*- coding: utf-8 -*-
"""Batch OCR/transcribe images through the local gateway, in parallel.

Two callers:
  python ocr_batch.py --out result.json IMG [IMG ...]
  python ocr_batch.py --frames DIR --out result.json --limit 12

The gateway tolerates ~6 concurrent requests; more just queues. Failures are
recorded verbatim instead of being retried forever, because a silent retry loop
turns a broken endpoint into an apparently slow one.
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import pathlib
import sys
from concurrent.futures import ThreadPoolExecutor

import urllib.request

URL = "http://127.0.0.1:3425/v1/chat/completions"
MODEL = "auto/glm-5.3-flash"

PROMPT = (
    "这是一张中文数学建模竞赛（数维杯 2026 C 题：无人超市补货运营的状态估计与"
    "决策优化）的讲解截图。请逐字转写图中所有可读文字：标题、小标题、表格标题"
    "与表头、公式、指标名、结论句。保留原文措辞，不要总结、不要翻译、不要补充"
    "图上没有的内容。看不清的地方写 [unreadable]。若图中主要是人像而非文字，"
    "只写 [talking-head]。"
)


def b64(path: pathlib.Path) -> tuple[str, str]:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return mime, base64.b64encode(path.read_bytes()).decode()


def call(path: pathlib.Path) -> str:
    mime, data = b64(path)
    body = {
        "model": MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}},
            ],
        }],
        "max_tokens": 900,
        "temperature": 0.0,
    }
    req = urllib.request.Request(
        URL, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer sk-local"},
    )
    with urllib.request.urlopen(req, timeout=240) as r:
        j = json.loads(r.read())
    return (j["choices"][0]["message"].get("content") or "").strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="*")
    ap.add_argument("--frames", default=None)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--every", type=int, default=1)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()

    paths: list[pathlib.Path] = [pathlib.Path(p) for p in a.images]
    if a.frames:
        fr = sorted(pathlib.Path(a.frames).glob("f*.jpg"))[:: a.every]
        if a.limit:
            fr = fr[: a.limit]
        paths += fr
    if not paths:
        print("nothing to do")
        return 2

    out = pathlib.Path(a.out)
    done = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}

    def job(p: pathlib.Path) -> tuple[str, str]:
        key = str(p)
        if done.get(key):
            return key, done[key]
        try:
            return key, call(p)
        except Exception as exc:                        # noqa: BLE001
            return key, f"[error] {type(exc).__name__}: {exc}"

    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        for key, text in pool.map(job, paths):
            done[key] = text
            print(f"{pathlib.Path(key).name} {len(text)}ch", flush=True)
    out.write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {out} ({len(done)} entries)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
