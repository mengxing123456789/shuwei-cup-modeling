#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""配置视觉审查通道，写进 `paper-kit/vision.json`（G11 读它）。

本机 magpie 网关上的免费 VL 模型（`opencode-zen-free/nemotron-3.5-super-vl-free`）
在 2026-11-18 实测两次打到 `429 FreeUsageLimitError`；`auto/*` 路由吃图片会超时。
所以这条通道需要一把**有额度的 key**，本脚本只负责把它写对地方，
不猜、不试、不把 key 写进任何论文目录。

用法：
    python set_vision.py --api-key sk-xxx [--base https://api.openai.com/v1] [--model gpt-4o-mini]
    python set_vision.py --show        # 只看现在配的是谁（key 打码）
    python set_vision.py --clear       # 清掉，G11 回到 NA

写文件后在 `vision.json` 里存明文 key —— 这是本机单用户工具，文件权限沿用用户目录；
不要把它提交进任何仓库，`check_no_peek.py` 也会跳过 `.json` 之外的路径。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CFG = Path(r"E:\数学建模\.agents\skills\paper-kit\vision.json")


def _mask(k: str) -> str:
    return k[:6] + "…" + k[-4:] if len(k) > 12 else "***"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="配置 G11 视觉审查通道")
    ap.add_argument("--api-key", default="", help="有视觉额度的 key")
    ap.add_argument("--base", default="https://api.openai.com/v1", help="OpenAI 兼容 base_url")
    ap.add_argument("--model", default="gpt-4o-mini", help="视觉模型名")
    ap.add_argument("--show", action="store_true", help="只看现状")
    ap.add_argument("--clear", action="store_true", help="清掉配置")
    a = ap.parse_args(argv)

    if a.clear:
        if CFG.exists():
            CFG.unlink()
            print(f"已删除 {CFG}；G11 会回到 NA（不适用）")
        else:
            print("本来就没有配置")
        return 0

    if a.show or not a.api_key:
        if not CFG.exists():
            print(f"未配置（{CFG} 不存在）→ G11 会判 NA")
            return 0
        cfg = json.loads(CFG.read_text(encoding="utf-8"))
        print(f"{CFG}")
        print(f"  base_url = {cfg.get('base_url')}")
        print(f"  model    = {cfg.get('model')}")
        print(f"  api_key  = {_mask(str(cfg.get('api_key', '')))}")
        return 0

    CFG.parent.mkdir(parents=True, exist_ok=True)
    cfg = {"base_url": a.base.rstrip("/"), "api_key": a.api_key.strip(), "model": a.model.strip()}
    CFG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"已写入 {CFG}")
    print(f"  base_url = {cfg['base_url']}")
    print(f"  model    = {cfg['model']}")
    print(f"  api_key  = {_mask(cfg['api_key'])}")
    print("\n下一步：python pipeline.py <paper> --only s5 --force s5 --skip-dispatch   # 只重跑图与 G11")
    return 0


if __name__ == "__main__":
    sys.exit(main())