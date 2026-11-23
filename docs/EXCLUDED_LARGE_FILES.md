# 被排除的大文件清单

仓库跟踪面 291.1 MB；被排除的 4,035 MB 全在这里，逐项说明**是什么、多大、怎么重新生成**。

原则：**能重跑的就不存，能重下的就不存，重复的只留一份。**

---

## 一、原始数据（从官方渠道重新下载，不要进仓库）

| 路径 | 大小 | 内容 | 怎么拿回来 |
|---|---|---|---|
| `_swc2026/cdata/` | **440.4 MB** / 805 文件 | EgoPro / EgoStandard / EgoDemo 三套原始手部数据：`*_hand_keypoints.csv`、`*_timestamps.csv`、`*_panel_*.csv`、`*_quality_flags.csv` | 官方数据包（题面附件）。C 题原始压缩包在 `数维杯/2026年第十二届…赛题/` 下 |
| `_swc2026/SWC2026_C/data/raw/` | 与上一项同源 | 工程内的软链接/副本 | 同上 |
| `SHUWEI2026_C/data/raw/` | **441.0 MB** / 820 文件 | 2026 C 题早期副本的原始数据，与 `cdata/` 逐字节相同 | 同上（**这一份完全可以删掉**） |
| `数维杯/_downloads/` | **283.4 MB** / 233 文件 | 6 个 GitHub 仓库快照（`971851309__shuwei-cup-modeling`、`eric-gitta-moore__2022nmmcm-international`、`Hello-Mr-Crab__ShuWeiCup-D`、`Primer-1-wy__2022-ShuWeiCup-C`、`shyz2006__2026-ShuWei-Spring-B`、`WANG123-A11Y__shuwei-modeling`）+ `noaa` | `git clone` 对应仓库即可 |
| `refs/contest-code/` | **73.2 MB** / 6,585 文件 | 往年竞赛代码：`.mat` 21 MB / 74、`.yuv` 14.6 MB / 6、`.bmp` 11.9 MB / 5,373、`.m` 4.3 MB / 840 | 原竞赛数据集（部分已不可考） |
| `_swc2026/bili-C/`、`_swc2026/bili-BV1Zzsv6fELo/` | 74.2 + 66.8 MB | B 站上 C 题讲解视频与抽帧图 | 按 BV 号重新下载；**结论已写进 `C题各家思路评估.md` 与 `48-官网通知逐条核对与AIGC风险.md`** |

---

## 二、可重跑的二进制中间件（`_swc2026/SWC2026_C/data/`，共 289 MB `.npz` + 3.1 MB `.pt`）

| 文件 | 大小 | 内容 | 重跑命令 |
|---|---|---|---|
| `pre_cache.npz` | **102.4 MB** | 全量预计算特征缓存（66,070 帧 × 多组特征） | `python code/p1_state.py` → 再 `python code/precompute.py` |
| `panel.npz` | 29.8 MB | 统一 panel：184 视频对齐后的关键点张量 | `python code/p1_state.py` |
| `up2_p1a_feats.npz` | 22.2 MB | 第二轮 P1-a 特征矩阵 | `python code/up2_p1a_seg.py` |
| `up2_p1a_cache.npz` | 19.1 MB | 第二轮 P1-a 训练缓存 | 同上 |
| `state.npz` | 18.3 MB | 主导出：`fl/fr/gl/gr/validL/validR/rec/t/dom/badL/badR` | `python code/p1_state.py` |
| `state_anchor_wrist.npz` / `_palm.npz` / `_tips.npz` | 各 18.3 MB | 三种代表点下的同一份状态表（用于代表点重训实验） | `python code/up13a_rebuild_anchor_state.py` |
| `state_layer.npz` | 16.4 MB | 阶段序列与状态层输出 | `python code/state_layer.py` |
| `up_p2_quantile_pred_L{6,18,30,60}.npz` | 3.2–4.5 MB ×4 | 分位 GRU 四个掩码长度的预测张量 | `python code/p2_quantile.py` |
| `p1b_probs.npz` | 1.7 MB | P1-b 检测器逐帧概率 | `python code/up2_p1b_v2.py --configs V8` |
| `models/*.pt` | 3.1 MB / 8 个 | P1-a bi-TCN 与 P1-b V8 的权重（3 seeds） | 同上两条 |

> **注意**：`state.npz` 与三个 `state_anchor_*.npz` 的 `fl/fr/gl/gr/validL/validR/rec/t/dom/badL/badR` 字段逐位相同（wrist 锚与主表 SHA256 一致），所以四个文件里只有 `state.npz` 是必需的；其余三个只服务于"代表点重训"那个实验，实验结论已写进附录 N 的 `tab:p1-anchor`。

**保留在仓库里的小体积 CSV**（论文引用，`!*.csv` 放行）：

- `data/v3_video_features.csv` 8.2 MB（10 Hz 视频统计，59,864 行）
- `data/v2_video_features.csv` 1.7 MB（2 Hz）
- `data/prefix_progress_features.csv` 1.9 MB
- `data/record_split.csv` 9.4 KB（16/4/4 记录划分，复现必需）

---

## 三、虚拟环境与编译产物

| 路径 | 大小 | 说明 |
|---|---|---|
| `数维杯/.venv/` | **493.5 MB** / 16,796 文件 | 2021 B 题演练用的独立 venv。重建：`python -m venv .venv && .venv\Scripts\pip install -r requirements.txt`（根 `requirements.txt` 覆盖主链） |
| `__pycache__/`、`*.pyc` | 145.3 MB / 6,842 文件 | Python 字节码缓存 |
| `*.pyd`、`*.dll` | 147.4 + 61.3 MB | Modex 编译模块（`workflow_engine.cp311-win_amd64.pyd` 5.4 MB 等）与 site-packages |
| `*.aux/.log/.out/.toc/.fls/...` | 20 MB / 435 文件 | LaTeX 中间件；`main.toc` 会被 `code/add_pdf_outline.py` 读取，所以复现顺序是**先编译再生成大纲** |

---

## 四、一次性工作目录

| 路径 | 大小 | 里面是什么 |
|---|---|---|
| `_swc2026/_scratch/` | 123.4 MB / 1,228 文件 | 全部临时探针：`fix_cover_teamid.py`、`outline_named_hex.py`、`pdfium_toc.py`、`audit_freshness.py`、`rebuild_from_zip.py`、`zhuque_detect.py`、DOCX 链路（`preprocess_pandoc.py`、`build_docx.py`、`style_docx.py`…）。**其中 `code/add_pdf_outline.py` 已把书签修复固化，DOCX 链路若要复用需从这里捞** |
| `_swc2026/_pkit/` | 含 `paper/data/` 整份拷贝 | 是 `SWC2026_C/data/` 的副本（`state.npz` 重复 12 份），**最大的重复来源** |
| `_swc2026/_pkgtest2/`、`_pkgfinal/`、`_verify_pkg/` | 各约 33 MB | 支撑包解压验证的三个副本 |
| `_swc2026/_bench/`、`_bench_txt/` | 21.8 MB | 编译耗时基准与文本导出 |
| `_swc2026/_pages/`、`_audit_pages/` | 4.4 + 7.9 MB | 逐页 PNG 审查图 |
| `_swc2026/_frozen_v1/` | 6.9 MB | 第一轮冻结快照 |
| `_swc2026/SWC2026_C/code.bak_20261122_1540/` | 3.6 MB / 336 文件 | `code/` 的整份备份 |
| `_swc2026/SWC2026_C/` 根 24 个 `main.tex.bak_*` | 约 2.4 MB | 压缩正文过程中的快照 |

---

## 五、重复文件（可安全删除，只留一份）

实测：≥200 KB 的 1,969 个文件里有 **610 组重复，浪费 1,592.0 MB**。最大的几组：

| 重复组 | 份数 | 单份大小 | 建议 |
|---|---|---|---|
| `state.npz` | 12 | 18.3 MB | 只留 `_swc2026/SWC2026_C/data/state.npz` |
| `pre_cache.npz` | 2 | 102.4 MB | 只留 `_swc2026/SWC2026_C/data/` |
| `panel.npz` | 3 | 29.8 MB | 同上 |
| `v3_video_features.csv` | 5 | 8.24 MB | 同上 |
| `SHUWEI2026_C/data/raw/EgoStandard/*` vs `_swc2026/cdata/EgoStandard/*` | 2 | 441 MB | 删 `SHUWEI2026_C/data/raw/` |
| `SHUWEI2025_A/logs/_awards/` vs `_swc2026/award_corpus_2025/` | 2 | ~90 MB | 已 gitignore |

---

## 六、复现顺序（排除项重建）

```powershell
cd 'E:\数学建模\_swc2026\SWC2026_C'
$PY = 'E:\Mini\envs\mathmodel\python.exe'

# 0. 原始数据放回 cdata/（从官方数据包解压）
# 1. 状态层（生成 panel.npz / state.npz / state_layer.npz）
& $PY code\p1_state.py
& $PY code\state_layer.py
# 2. 预测层（生成 up_p2_quantile_pred_*.npz）
& $PY code\p2_predict.py
& $PY code\p2_quantile.py
# 3. 检测器（生成 models/*.pt 与 p1b_probs.npz）
& $PY code\up2_p1b_v2.py --configs V8
# 4. 数字 → 宏 → 编译 → 大纲
& $PY code\fill_numbers.py
& $PY code\prune_slots.py
xelatex main.tex; xelatex main.tex
& $PY code\page_report.py
& $PY code\add_pdf_outline.py
```

一键版见 `_swc2026/SWC2026_C/snippets/reproduce.ps1`（`-Full` 追加第二轮 `up2_/up3_/up4_/up6_/up10–up15` 与附录生成器）。

---

## 七、如果将来想把这些也纳入版本管理

推荐 **Git LFS**（`.gitattributes`）：

```
*.npz filter=lfs diff=lfs merge=lfs -text
*.pt  filter=lfs diff=lfs merge=lfs -text
*.pdf filter=lfs diff=lfs merge=lfs -text
```

GitHub 单文件上限 100 MB、仓库建议 <1 GB。当前跟踪面 291.1 MB 在无 LFS 的情况下可用，但 `award_corpus_2025`（91 MB 的获奖论文 PDF）属于**第三方版权内容**，开公开仓库前建议先移出（见根 `README.md` 末节）。
