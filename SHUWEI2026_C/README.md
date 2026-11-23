# `SHUWEI2026_C` — 2026 年 C 题的早期勘察

**这是开工第一周的版本，不是最终稿。** 最终稿在 `_swc2026/SWC2026_C/`。留它的原因只有一个：这里的**数据勘察与基线**在最终稿里被复用了，但代码散在别处，原始输出只在这里。

## 与最终稿的分工

| 这里有的 | 最终稿里对应什么 |
| --- | --- |
| `code/analyze_data.py` / `deep_stats.py` / `profile_data.py` | 被 `_swc2026/SWC2026_C/code/` 的正式统计脚本取代 |
| `code/audit_all_data.py` | `data_inventory.py` + `audit/` |
| `code/baseline_p3.py` | `up2_p3_final.py` 的前身（朴素 EDF 基线） |
| `code/check_no_peek.py` | 防偷看检查（确认没有用 test 集调参） |
| `code/verify_numbers.py` | 最小断言脚本，后来演进成 136 条 |
| `data/*.json` | 数据画像、全量审计、视频审计、P3 基线试验结果 |
| `out/00-problem.md` | 逐句抄出的题目要求（G1 的产物） |
| `out/15-benchmark.md` | 真题对标（G20 的产物） |
| `out/data-analysis.md` | 数据画像报告 |
| `problem/*.pdf` | C 题题面 + 数据集说明（**最终稿里也有一份**） |
| `refs/official_standard.json` | 官方格式规范的结构化版本（**最终稿里也有一份**） |
| `BUILD.md` / `HANDOFF.md` / `NO_PEEK.md` | 构建说明、交接单、防偷看承诺 |

## 为什么不直接删

`data/` 里的四份 JSON 是**只有这里才有**的原始输出：

- `data_profile.json` — 69 条记录的字段完整率、时长分布、缺测模式
- `full_audit.json` — 184 个视频逐条的可解码性、帧数、分辨率
- `video_audit.json` — 视频与面板的时间对齐检查
- `results_baseline_p3.json` — 朴素 EDF 在三个 case 上的原始试验（后来论文里的 slack 基线就是从这里起步的）

最终稿复用了这些结论，但**没有重跑**，所以原始输出只此一份。删掉就再也算不出来了。

## 已删除的部分

`main.tex` / `swmcmthesis.cls` / `swmcmthesis.cfg` 曾是未编译的空骨架，会导致 `find_paper()` 误选它（`main.pdf` 不存在 → `gauntlet` 报 `total 0`），已删除。`data/constraints/` 的 7 个文件与 `_swc2026/SWC2026_C/problem/Restocking_Problem_and_Data_EN/Restocking_Tasks_and_Constraints/` **sha256 全部相同**，已去重删除。`data/raw/{EgoDemo,EgoPro,EGOStandard}/` 是 5.57 GB 原始视频包，已在 `.gitignore` 里排除。

## 什么时候看它

想知道「最初是怎么看这批数据的」——即没有任何模型假设之前的纯统计画像。论文里的数据画像段落（§2）就是从这里写起的。
