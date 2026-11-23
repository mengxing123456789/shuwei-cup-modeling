# 数维杯 — 备赛资料与官方文件

> 这不是某道题的工程，而是**打任何一道数维杯题都需要的东西**：官方规则、历年赛题、获奖写法提炼、实战演练、评分复盘、模板工具。

## 六层结构

```
数维杯/
  00_官网与规则/      官方格式规范、承诺书、提交流程、Word 模版、LaTeX 模板（2025 + 2026 两套）
  01_往年赛题/        2021–2025 赛题与 LaTeX 模板
  02_一等奖论文_参考/  一等奖论文写法提炼.md（8.5 KB）
  03_实战演练/        2021 B 题极端降雨的完整实战
  04_评分与复盘/      评分细则_v1.md、自主评分报告_2021B.md、复盘_2021B.md
  05_模板与工具/      extract_pdf.py、fetch_ghcn.py、inspect_paper.py、latex/ 骨架
  99_归档/           2021B_final（历史收口版）
  refs/              official_standard.json（47.9 KB，机器可读规则）
```

## 开赛前必读的三份

1. **`00_官网与规则/论文格式规范.pdf`** — 3 页，四条硬约束：正文 ≤25 页（含摘要页与目录页）、12 号 Times New Roman、全英文、表标题在上图标题在下且图中不得有中文。
2. **`00_官网与规则/论文提交流程.pdf`** — 4 页，三件分别上传（PDF / 承诺书 cns / 支撑材料 fj），必须点「点击提交」看到「已提交」。
3. **`02_一等奖论文_参考/一等奖论文写法提炼.md`** — 从 AsterLink 的 48 篇获奖稿里提炼的共性：独立 Problem analysis 章（77%）、Assumptions 独立章（98%）、Strengths & Weakness（69% / 65%）、framework 图。

## `refs/official_standard.json`

机器可读的官方规则（47.9 KB），`new_paper.py` 用它给新论文定基准带、`gauntlet_check.py` 用它判格式。结构大致是 `{"format": {...}, "deadlines": {...}, "naming": {...}, "awards": [...]}`。

## `05_模板与工具/`

| 脚本 | 用途 |
| --- | --- |
| `extract_pdf.py` | 从 PDF 抽纯文本（题面 grep 用） |
| `fetch_ghcn.py` | 抓 NOAA GHCN 气象数据（2021 B 题用过） |
| `inspect_paper.py` | 统计一篇论文的页数/图数/词数/文献数（对标用） |
| `paper_profile.py` | 同上，输出 JSON |
| `latex/build.ps1` | 一键编译骨架 |
| `latex/main_en.tex`、`main_zh.tex` | 中英文骨架 |
| `latex/official/demo.tex` | 官方模板原样拷贝 |

## 注意

`03_实战演练` 与 `99_归档` 里有 3.96 MB ×2 的同一份 xlsx（2021 B 题附件），**故意留两份**——两个目录都要能独立跑。

`.venv/`（493 MB）与 `_downloads/`（283 MB，6 个第三方 GitHub 仓库）已被 `.gitignore` 排除，不在仓库里。
