import io, re

P = r"46-整体测评与一等奖判定.md"
t = io.open(P, encoding="utf-8").read()

block = r"""

---

## 10. 执行结果（本轮已落地，替换第 7 节的计划状态）

第 7 节列出的 A1–A8 已执行完毕，机器读数如下（全部来自本轮实际编译与闸门，不是估计）。

### 10.1 呈现层指标（正文，对标 5 篇获奖稿）

| 指标 | 改造前 | 改造后 | 获奖 5 篇区间（均值） | 判定 |
|---|---:|---:|---|---|
| words | 8,932 | **10,340** | 6,922–11,991（9,050） | 在区间内，高于均值 |
| figures | 3 | **6** | 8–34（17.2） | 仍偏少，但已进入同一量级 |
| inline images | 4 | **7** | 13–38（23.0） | 仍偏少 |
| display equations | 4 | **11** | 0–86（28.0） | 落入区间（有获奖稿为 0） |
| tables | 13 | **4** | 0–24（8.8） | 低于均值（大表移入附录，见 10.3） |
| subsections | 39 | 39 | 31–96（53.8） | 在区间内 |

### 10.2 结构层（对标获奖稿共性）

- 新增独立 **Problem analysis** 小节（§1.2），含 framework 图（Figure 1），对应获奖稿的
  "Problem Analysis + Framework of the paper"。
- §7 由 25 词的摆设扩为三节：7.1 未达标项与反转条件、7.2 Strengths and weaknesses、
  并把 leakage 控制与单一标注者威胁显式写出。
- 题面术语补齐：`time interval`（§2.2 定义 record 与 half-open interval）、`product state`
  （§3.4 新增 "What the hand state is not" 段）、`wait time`、`computational cost`
  （新增段，含 ridge 闭式复杂度与实测 0.0005 s / 0.0002 ms per window）、
  `valid protocol`（§5.2）、`21 keypoints`（§2.1）。
- P3 十一项官方指标成表（`tab:p3score`，7 策略 × 11 列 × 2 case），正文引导段写明
  "the statement asks for eleven measures for every method"；表体在 Appendix N，
  正文保留指针句以守页数。

### 10.3 新增实测（不是重排文字）

- **P3 三指标补进引擎并逐位校验**：`reserved_idle_s`、`observed_overrun_s`、
  `censored_units` 在 `code/up_p3_vectorized.py` 与 `code/up2_p3_engine.py` 同步实现，
  与未改动的 `code/p3_stochastic_schedule.py` 逐 seed 对照 30 seeds × S2/S3，
  `worst_max_abs = 1.42e-14`（`data/up16_p3_official_metrics_check.json`）。
- **十一项指标首次给出机制**：我们的规则把 reserved idle 压到 3.53 s（S2）/3.34 s（S3），
  低于 slack 的 6.81/9.10，但 overrun 升到 30.81/41.28 s —— "预留偏紧"第一次被量化，
  与命题 B 一致（`data/p3_scorecard.json`）。
- **计算开销实测**：`code/up18_p2_timing.py` 用 2,207 窗 × 36 特征实测
  ridge 拟合 0.002235 s、打分 0.000499 s / split、0.000226 ms / window
  （`data/up18_p2_timing.json`），不是引述。

### 10.4 闸门与交付件

| 项 | 结果 |
|---|---|
| 正文 / 附录 / 总页 | **25 / 45 / 70** |
| overfull / undefined / prose numerals | **0 / 0 / 0** |
| `audit/verify_claims.py` | **141 PASS / 0 FAIL / 0 NA** |
| `code/verify_numbers.py` | **122 claims / 0 failed** |
| `gauntlet_check.py` | **16/16 PASS**（R-V14 min 5.98 pt、violations 0） |
| `slots.tex` | 定义 **598**、正文用 **592**、未用 6、未定义 0 |
| 身份泄漏 / CJK | 全 0（`Nanchang`/`University`/`Shuping`/电话/邮箱） |
| 页眉 | p2–p25 `Page n of 25`，p26 起 `Appendix, p. n` |
| 交付件 | `CSWBMCM2634892.pdf` **1,870,870 B / 70 页**、`…cns.pdf` 17,080 B、`…fj.zip` **11,907,427 B / 532 条目**，合计 **13.16 MB** |

### 10.5 仍然存在的差距（如实列出）

1. **图数 6 < 获奖均值 17.2**。正文已顶满 25 页，每加一张图必须等量删字；可搬的图只剩
   `fig10_value_ladder.png` 与 `fig11_video_gain.png` 两张，都在附录且有正文引用。
2. **表格从 13 降到 4**，是主动把大表移入附录换页面给图的结果；获奖稿表格均值 8.8，
   若评委按"正文表多=工作量大"计分，这是净损失。这是呈现层的真实权衡，不是遗漏。
3. **R-V09 仍有 105 对 stale artefact**（脚本 mtime 晚于产物，多为一次性探针与旧 JSON）。
   已确认无正文引用，属已知 open。
4. **承诺书签名**按要求暂不处理（单人队伍，仅 `1. Shuping Zhang`）。
"""

if "## 10. 执行结果" not in t:
    t = t.rstrip() + block
    io.open(P, "w", encoding="utf-8", newline="").write(t)
    print("appended section 10")
else:
    print("section 10 already present")
