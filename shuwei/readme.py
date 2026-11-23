
def _corpus_root():
    """语料根：MM_CORPUS_ROOT > 向上找含 corpus/problems 的一级 > 旧 AsterLink 兜底。"""
    import os as _os
    from pathlib import Path as _P
    env = _os.environ.get("MM_CORPUS_ROOT")
    if env:
        return env
    for _probe in _P(__file__).resolve().parents:
        if (_probe / "corpus" / "problems").is_dir():
            return str(_probe / "corpus")
    return r"C:\Users\29900\Downloads\AsterLink"

﻿# -*- coding: utf-8 -*-
import os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
p=_corpus_root() + r'\README_题面补全说明.md'
t='''# AsterLink 数维杯资料：完整性说明（题面补全版）

整理日期：2026-11-19。本说明只描述**现在这个文件夹里到底有什么、哪些能读、哪些是整理版**。

---

## 1. 一句话结论

- **2019 / 2020 / 2021 / 2022 / 2024 题目：官方原件齐全，压缩包完好，PDF 全部有文本层，可正常提取。**
- **2023 题目：官方原件未获取**，已用「公开解题文章 + 本地优秀论文的 Problem Restatement」复原为题面整理版（4 个 md）。
- **2025 秋季赛题目：A 题拿到官方英文原件**；B/C 为据优秀论文复原的题面整理版；**D 题内容未知**（该届优秀论文包内无 D 题论文）。

## 2. 年份 × 题目 × 论文 对照表

| 年份 | 赛事 | 题目文件 | 论文 | 可读性 |
|---|---|---|---|---|
| 2019 | 第五届国际赛 | 官方 zip：A/B/C + 承诺书 + 格式规范 | 22 篇（zip） | ✅ 全部可解析 |
| 2020 | 第六届国际赛 | 官方 zip：A/B/C/D + 数据（内嵌 Data.zip） | 15 篇 | ✅ 全部可解析 |
| 2021 | 第七届国际赛 | 官方 zip：A/B/C/D | 16 篇散装 PDF（A1/B7/C5/D3） | ✅ 全部可解析 |
| 2022 | 第八届国际赛 | 官方 .rar：A/B/C/D + 地震数据（402 txt + 2 xlsx） | 17 篇散装 PDF | ✅ 全部可解析 |
| 2023 | 第九届国际赛 | ⚠️ **缺失 → 见 `2023第九届数维杯国际赛题目（整理版）\\`** | 18 篇（zip，另有一份完全重复的 "(1)" 副本） | ✅ 论文可解析 |
| 2024 | 第十届国际赛 | 官方 zip（内嵌二层 zip）：A/B/C/D | 15 篇散装 PDF | ✅ 全部可解析 |
| 2025 秋 | 第十一届（秋季赛） | A 官方原件；B/C 整理版；**D 缺失** → 见 `2025年数维杯秋季赛题目\\` | 21 篇（A12/B4/C5，**无 D**） | ✅ 论文可解析 |

核查方式：10 个压缩包全部 `7z t` 通过；PDF 一律用 pypdf 抽取文本层，前两页字符数 4500–9700，**无扫描件/无空文本**。

## 3. 本次补进去的 7 个文件

### `2023第九届数维杯国际赛题目（整理版）\\` — 4 个 md

| 文件 | 题名 | 可信度 |
|---|---|---|
| A_Problem（题面整理）.md | Modeling and Optimal Control of a Compound Helicopter（复合直升机建模与优化控制） | 中文译稿级完整（含 7 个控制量、低/高速模式、4 问全部初始条件）；**附录 I 空气动力系数表缺失** |
| B_Problem（题面整理）.md | Catalytic Pyrolysis of Cotton Stalk（棉花秸秆热解催化） | 完整（5 问 + 混合比 10/100…100/100 + 气体成分清单）；**附件 I/II 两个 xlsx 缺失** |
| C_Problem（题面整理）.md | Detection of AI-Generated Text（AI 生成文本识别） | 由优秀论文 Problem Restatement 复原，4 问任务明确；**附录 I–IV 缺失** |
| D_Problem（题面整理）.md | Mathematics of Washing（洗涤数学） | 由优秀论文问题分析复原，4 问结构与约束明确；**4 个附件表缺失、措辞非逐字原文** |

### `2025年数维杯秋季赛题目\\` — 3 个新增

| 文件 | 内容 |
|---|---|
| 2025_ShuWei Cup A_Problem（官方原件）.pdf | 官方英文原版，230,490 字节（来源：GitHub Riyer4ever/2025SHUWEICUPAutumn，与官方命名一致） |
| 2025_ShuWei Cup A_Problem（中文译稿）.md | A 题中文译稿 4,678 字节 |
| B_Problem（题面整理）.md | Crop Leaf Disease Recognition，4 个 Task（61 类/≤50M/每类 10 张 ≤20M/严重度 Grad-CAM/多任务） |
| C_Problem（题面整理）.md | 海岸带海水入侵风险评估与治理规划，5 问 |
| D_Problem（未获取）.md | 说明 D 题为何拿不到 + 4 条获取途径 |

## 4. 仍然缺的东西（按重要性）

1. **2023 A 题附录 I（空气动力系数与机身参数表）** —— 没有它 A 题无法数值求解，只有题面。
2. **2023 B 题附件 I/II 两个 xlsx** —— 热解产品产量、热解气体产量。
3. **2023 C 题附录 I–IV** —— 20 篇文本、待判段落、待查重图片与公式。
4. **2023 D 题 4 个附件表** —— 污渍、洗涤剂、材质、混洗限制。
5. **2025 秋季赛 B/C 题官方数据包**（图像数据集 json + 图像；海平面/潮位/沉降/土壤数据）。
6. **2025 秋季赛 D 题题面与数据**。
7. 2025 A 题的官方数据附件（若有）。

## 5. 这些缺失件的获取途径（已验证过渠道现状）

官网 nmmcm.org.cn 在 2026 年改版后**旧文章已清理，赛题一律走百度网盘**，没有直链 PDF。可走：
1. 官网当届通知文章里的网盘链接（需提取码）；
2. 报名队号登录后的赛题下载页；
3. 微信公众号「数维杯」开赛推文（题面常以图片附出）；
4. 参赛队公开仓库：GitHub 搜 `2025SHUWEICUPAutumn`、`ShuWeiCup` 等（2025 A 题即由此取得）。

## 6. 引用注意

- 每个整理版文件的头部都有「来源与可信度」引用块，说明它来自哪篇文章/哪篇论文、哪些附件缺失。
- **整理版不是官方原文**：写论文引用题目时，请以官方 PDF 为准；用整理版做思路梳理与复现是安全的。
- 表格里的数据统计（如 2025 B 题的 36,258→31,541 张、类别不平衡 2,798:1）来自**参赛论文自述**，不是官方口径。
'''
open(p,'w',encoding='utf-8').write(t); print('written',p,len(t))
