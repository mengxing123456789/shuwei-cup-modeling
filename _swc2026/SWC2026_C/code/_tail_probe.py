# AI 辅助：DeepSeek Harness 助手生成的页面内容探针（看最后一页还剩什么）。
# -*- coding: utf-8 -*-
import sys

import fitz

doc = fitz.open(sys.argv[1] if len(sys.argv) > 1 else "main.pdf")
body_last = int(sys.argv[2]) if len(sys.argv) > 2 else 26
for pno in range(max(0, body_last - 2), min(len(doc), body_last + 1)):
    txt = doc[pno].get_text()
    print(f"--- page {pno+1}: {len(txt)} chars ---")
    print(txt.strip()[:700].replace("\n", " | "))