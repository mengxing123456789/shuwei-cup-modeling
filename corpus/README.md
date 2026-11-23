# corpus — 历年真题与一等奖论文

> 这是本仓库**唯一权威的语料副本**。原先散在 `C:\Users\29900\Downloads\AsterLink`（约 6 GB），已导入、解压、压平、去重、删原包，现在完全自包含。

## 结构

```
corpus/
  problems/<year>/        2019–2025 历年真题题面、附件、官方模板
  awards/<year>/          2019–2025 一等奖论文 PDF
  rules/2025/             官方格式规范、承诺书、提交流程、Word 模版
  _extracted_text/2023/   18 篇 2023 获奖稿的纯文本（供 grep）
  _PROVENANCE.md          每份文件的 sha256 与核验判据
  _DATA-2025.md           2025 A 题官方数据的 sha256 与表结构
```

## 年份覆盖

| 年份 | 一等奖 PDF | 真题/附件文件数 |
| --- | ---: | ---: |
| 2019 | 22 | 8 |
| 2020 | 15 | 186 |
| 2021 | 16 | 20 |
| 2022 | 17 | 427 |
| 2023 | 18 | 4 |
| 2024 | 15 | 59 |
| 2025 | 21 | 16 |
| 合计 | **124** | **720** |

`awards/` 的文件名就是 `<题号><队伍ID>.pdf`，例如 `A2023101419943.pdf`。

## 怎么用

```powershell
# 机器可读索引（229 条记录，按 kind/year/problem 分组）
$PY = python
& $PY '.agents\skills\mathmodeling\scripts\corpus_index.py' --stats

# 拿题面当查询，找结构最像的往年论文
& $PY '.agents\skills\mathmodeling\scripts\corpus_index.py' --query-file 'problem\problem.txt'

# 枚举某年某题的全部论文
& $PY '.agents\skills\mathmodeling\scripts\corpus_index.py' --year 2023 --problem B --kind paper --list
```

索引文件在 `.mh/corpus.json`，`roots` 已指向本目录（不是 AsterLink）。索引过期时 `corpus_index.py --build` 重建。

## 为什么不放原始数据包

`AsterLink/C_Problem_Data/` 里的 `EgoDemo.zip`（1.82 GB）、`EgoPro.zip`（1.84 GB）、`EgoStandard.zip`（1.91 GB）共 5.57 GB，赛方官网可重新下载。它们解出来的 `data/panel.npz`、`v3_video_features.csv` 等中间产物也不在仓库里，但**生成它们的脚本在** `_swc2026/SWC2026_C/code/`。

## 核验

`_PROVENANCE.md` 记录 2026-11-19T08:49:16Z 的核验结果：**9 份 OK / 0 SUSPECT / 0 BROKEN**。判据是「PDF 首页可抽取 ≥200 字符、xlsx 至少一表 >1 行、docx ≥100 字符或有表格、zip/rar 条目 >0」。

压缩包已全部解开并删除原包（用 `7z x`，因为它能正确还原 GBK 成员名，Python `zipfile` 不能）。`problems/2022/` 的原件是 `.rar`，NanaZip 7.0 也成功解出 427 个文件。

<!-- path-note -->
