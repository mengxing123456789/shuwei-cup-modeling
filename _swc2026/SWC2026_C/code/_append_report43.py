# -*- coding: utf-8 -*-
"""Append the evening's format-spec work to report 43."""
import io
from pathlib import Path

P = Path(r"43-官方格式核对与图表重做.md")

BLOCK = """

---

## 附录：2026-11-22 晚按《论文格式规范.pdf》逐条重做（第 2 轮）

### 改动清单

| # | 规范条目 | 改前 | 改后 | 证据 |
|---|---|---|---|---|
| 1 | 一(3) 正文每页须有队号与页码 | p1 页眉压在封面上、红色报名号从右块溢出、`Undergraduate` 挤进 `Problem Chosen` 槽 | 摘要页无页眉、页脚 `Page 1 of 25`；目录页无页眉无横线、页脚 `Page 2 of 25`；p3 起 `Team CSWBMCM2634892 / Page n of 25` | `code/_front_check.py`、`logs/_front/p01.png`、`p02.png` |
| 2 | 一(2) 第二页为目录专用页 | 目录首行是自指条目 `Content ...... 2` | 自指条目已删（`swmcmthesis.cls` 的 `\\addcontentsline{toc}{section}{Content}`） | `code/_drop_toc_selfentry.py` |
| 3 | 一(5) 参考文献按正文引用次序 | `little2019` 在前，正文首引是 `gneiting2007` | `\\bibitem` 顺序重排为正文首现序，字节数不变 | `code/_reorder_bib.py`、`_spec_audit.py` 的 `order matches bibitem order: True` |
| 4 | 一(6) 附录须列软件名称与版本 | 只有 `Python` 与 `xelatex` 两个词，无版本 | 新增 Table 6「Software used」，10 行实测版本（Python 3.11.18 / NumPy 2.4.6 / SciPy 1.17.1 / pandas 3.1.1 / scikit-learn 1.9.1 / PyTorch 2.14.1+CUDA 12.6 / LightGBM 4.7.0 / Matplotlib 3.11.2 / PyMuPDF 2.1 / MiKTeX XeTeX 4.16） | `code/_add_software_table.py`，PDF p30 |
| 5 | 一(6) 须注明源程序在支撑材料 | `support material` 计数 0 | Appendix C 首段明写 `CSWBMCM2634892fj.zip` 自带脚本/缓存/权重，解压后 `xelatex` ×2 可重建同一页数 | 同上，PDF p30 |
| 6 | 二(1) 图形图表中不得出现中文字体 | `swmcmthesis.cfg:35` 的 `附录` 让每张附录页报 `Missing character` | 改为 `Appendix`，日志缺字归零 | `swmcmthesis.cfg.bak_appname` |
| 7 | 整页溢出 | `app_m.tex` / `app_n.tex` 两张登记表报 `Overfull \\vbox (64.6pt)` 与 `(248.8pt)` | 改 `longtable` 跨页重复表头，70 页无任何一页 maxy > 841.9 | `code/_longtable.py` |
| 8 | 文风（AIGC 代理指标） | `rather than` 4.076/千词（人类上限 0.090）、分号 4.381、`not X but Y` 0.102、`therefore` 0.713 | 全部 **0.000 / 0.906 / 0.000 / 0.000**；`first/second/third` 1.611（上限 1.616，时间单位占 1.208，话语序数 0） | `_aigc_bench.json`、`code/_ord_split.json` |

### 与官方 demo 的同构性

`...\\LaTeX模版\\demo.pdf`（16 页）p1 同为三块表头 + 一条细横线，p2 只有 `Content` 标题与目录条目，p3 起页眉 `Team # SWBMCM2600001 / Page 1 of 14`。我们按规范示例用空格而非 `#`（`Team CSWBMCM2634892`），其余同构；字体同为 `TeXGyreTermesX-Regular/Bold` + `NewTXMI`，正文 12.0 pt。

### 当前交付件

```
paper   CSWBMCM2634892.pdf       1,873,861 B   70 页 (body 25 / appendix 45)
letter  CSWBMCM2634892cns.pdf       17,080 B   单人 Shuping Zhang，待手写/电子签名
package CSWBMCM2634892fj.zip    11,945,876 B   541 条目 (11.39 MB)
total                                           13.20 MB   (cap 20 MB)
```

### 闸门

`page_report` body 25 / appendix 45 / total 70 / overfull 0 / undefined 0 / prose numerals 0；
`verify_claims.py` **145 PASS / 0 FAIL / 0 NA**；
`verify_numbers.py` **136 claims / 0 failed**；
`verify_slots.py` **1,089 claims / 0 failures**；
`gauntlet_check.py` **16/16 PASS**；
PDF 文本层身份词（Nanchang / University / Shuping / Zhang / 2990096174 / 19721012529）全 0、CJK 0。
"""


def main():
    t = io.open(P, encoding="utf-8").read()
    if "2026-11-22 晚按" in t:
        print("already appended")
        return
    io.open(P, "w", encoding="utf-8", newline="\n").write(t.rstrip() + BLOCK)
    print("appended", len(BLOCK), "chars")


if __name__ == "__main__":
    main()
