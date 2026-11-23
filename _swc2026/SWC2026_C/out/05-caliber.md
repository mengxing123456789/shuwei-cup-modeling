BYTES 2964
# 05 口径审计：同一个词有没有被两种算法用过

审计对象：`main.tex` 101,731 B / `main.pdf` 58 页（正文 25 / 附录 33），2026-11-21 版本。
审计方法：机器硬项（`code/../../caliber_check.py`，按数字紧邻单位分组）+ 人工语义复核（六类）。

## 1 机器硬项（现算，非快照）

```text
报告: out/15-caliber-machine.md   硬项 0 / 提示 0   VERDICT: PASS
```

判据：同一数值字面量（必须带小数点或千分位）在同一份 `main.tex` 里紧跟两种不同量纲后缀 → 硬项 FAIL。
本次 0 硬项、0 提示，说明**不存在“同一个数一会儿是 % 一会儿是万元”这类机械冲突**。

## 2 人工复核（六类语义口径）

| # | 口径族 | 检查方式 | 结论 |
|---|---|---|---|
| 1 | **页数**：正文 vs 附录 vs 总计 | `code/page_report.py` 现算 | body 25 / appendix 33 / total 58；全文只说“正文 ≤25 页”，附录不计入，与官方规范一致 |
| 2 | **记录单位**：record / environment / segment | 检索 `\benvironment\b` 与 `\brecord\b` 的上下文 | split 一律按 **environment**（16/4/4）；`69` 只用于 record 数、`24` 只用于 environment 数、`349/343` 只用于 segment，三者不互换 |
| 3 | **P3 名义 vs 敏感性**：α/β | 检索 `nominal` 与 `\alpha`/`\beta` | 所有主表标题写明 `α=1, β=0.5 (nominal)`；敏感性表逐行标 α/β，不存在“同一列混两种映射” |
| 4 | **P2 缺失长度**：L 的秒数 vs 帧数 | 检索 `L=0.2` / `6 frames` | 每个 L 同时给秒与帧（0.2 s = 6 帧 @30 Hz），换算在正文第一次出现处给出，后文只用一个单位 |
| 5 | **距离**：cm vs m | 检索 `cm` 与 `\text{m}` | 预测误差统一 cm；共形区间统一 m，并在首次出现处换算说明；不存在同表混用 |
| 6 | **效果量**：百分点 vs 百分比 | 检索 `percentage points` 与 `\%` | 提升一律写“percentage points”，相对变化才写 `\%`；P3 的 +0.219 / +0.243 明确标为 on-time rate 的绝对差（percentage points） |

## 3 已核对的高风险表述

- **“25 pages”**：只指正文（`BodyLastPage`），不是总页数；已用 `page_report.py` 复核。
- **“58 pages”**：只在封面/元数据出现，指总页数；正文不拿它当“篇幅”。
- **“109 claims / 118 checks”**：这两个数不写进论文正文，只出现在工具输出与本审计；论文里不引用工具计数，避免自指。
- **“±10%”**：只用于敏感性扫描的扰动幅度，不用于任何结果的置信区间；置信区间一律写 95% CI 并给半宽。

## 4 未决项

无。六类全部有结论；机器硬项 0、提示 0。

## 5 复核命令

```powershell
E:\Mini\envs\mathmodel\python.exe E:\数学建模\.agents\skills\mathmodeling\scripts\caliber_check.py E:\数学建模\_swc2026\SWC2026_C
E:\Mini\envs\mathmodel\python.exe code\page_report.py
```

VERDICT: PASS
