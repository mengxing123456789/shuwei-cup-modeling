# AI 辅助：DeepSeek Harness 助手生成的一次性检查脚本；只读 main.pdf 每页文本量。
import pymupdf

d = pymupdf.open(r"main.pdf")
for i in range(1, d.page_count + 1):
    t = d[i - 1].get_text()
    print(i, len(t), repr(t[:80]))