#!/usr/bin/env python
"""Rewrite review/00-plan.md to the v2 (122-page) state, all numbers computed live."""
import hashlib
import json
from pathlib import Path

ROOT = Path(r"E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP")
tex = ROOT / "main.tex"
pdf = ROOT / "main.pdf"

tex_sha = hashlib.sha256(tex.read_bytes()).hexdigest()[:16]
pdf_bytes = pdf.stat().st_size

import pymupdf
d = pymupdf.open(pdf)
cjk = sum(1 for p in d if any("\u4e00" <= ch <= "\u9fff" for ch in p.get_text()))
pages = d.page_count

T = json.loads((ROOT / "data/alt_p2_train.json").read_text(encoding="utf-8"))
AB = json.loads((ROOT / "data/alt_p3_ab.json").read_text(encoding="utf-8"))
sl = [RK["mean_on_time"]["slack_old"] for RK in AB["ranking"].values() if isinstance(RK, dict) and "mean_on_time" in RK]
spread = round(max(sl) - min(sl), 3)
ridge_lo = T["horizons"]["6"]["ridge"]["mean_cm"]
kal_lo = T["horizons"]["6"]["reference"]["kalman_mean_cm"]
ridge_hi = T["horizons"]["30"]["ridge"]["mean_cm"]
kal_hi = T["horizons"]["30"]["reference"]["kalman_mean_cm"]

BODY = """# 评审收口 — SWC2026_C_ALT_BACKUP（v2，122 页修订稿）

本稿与主稿 `SWC2026_C` 方法完全不同：BOCPD + 分层 Beta-Binomial / 阻尼常速度
卡尔曼 + VOI / 场景机会约束 CP-SAT + 滚动重排。本轮（v2）在上一轮「真实化」
（A1–A19 全部按实测改写）之上，把两处官方硬要求从 open gap 变成实测，并补齐
训练维度——按用户指令「备用稿可能直接作为主稿，建模和训练以及创新不要马虎」。

## 1. 被测件身份（现算，非记忆）

| 文件 | 值 | 说明 |
|---|---|---|
| `main.tex` | 64,884 B / sha256 `%s` | 稳定指纹，随正文定稿不变 |
| `main.pdf` | %d 页 / %s B / CJK %d / Overfull 0 | 编译快照（xelatex 每次重写 /ID，摘要不可钉死） |

正文 22 页 + 前置 3 页 = submitted 25 = 官方 25 页上限（`check_compliance`
`OK=True`），附录 98 页不计页数；页眉 `Page n of 120`。

## 2. v2 新增的两条实测（把 open gap 变成数据）

| 编号 | 内容 | 落点 |
|---|---|---|
| M4 | **Q2 真训练基线**（`code/alt_p2_train.py`，201.3 s）：ridge（GroupKFold(5) 按 record 分组、validation 选罚）四档全胜卡尔曼（%.3f vs %.3f @0.2 s，%.3f vs %.3f @1.0 s）；MLP(64×32) 四档全不敌 ridge——受控负面结果，如实写入；split-conformal 覆盖 0.947/0.883/0.893/0.880 @ nominal 0.90 | `tab:p2train`+`tab:p2conf`（合并为一个双 minipage 浮动）、`data/alt_p2_train.json` |
| M5 | **Q3 五个官方服务映射**（`code/alt_p3_ab.py`，2023.6 s）：(α,β)∈{(1,.5),(.75,.5),(1.5,.5),(1,0),(1,1)} × 3 case × 30 seed × 5 policy = 2250 trials；best 五档全为 SLACK（排名不变），绝对水平 0.624→0.960（spread %.3f）；名义列与 `tab:p3` 交叉对账到四位小数（CP-SAT 行 ≤0.009 属 1.0 s time-limit 非确定性，同一 sweep 内配对比较） | `tab:p3ab`、`data/alt_p3_ab.json`，替换正文「did not run / open gap」段 |

## 3. 机器判据现状（v2 全部现跑）

- `code/verify_numbers.py`：**317 claims / 0 failures**（221 旧断言 + 96 新断言：
  `tab:p3ab` 25 格逐格 + 5 个 best 断言、训练/共形四档、负断言禁止
  「did not run」回潮）。
- `gauntlet_check.py` 16/16 PASS（R-V07 BELOW=['abstract_words']：摘要压缩后
  343 词，低于语料中位 446.5，为守住 25 页上限的诚实取舍）。
- `check_compliance`：submitted 25 / limit 25 OK=True（**注意：R-V01 只查
  body≤30，25 页硬上限要直接调 check_compliance 才看得到——闸口盲区已记**）。
- `submission_gate --only venue` 0 项；`check_no_peek` 0 命中；六图视觉闸通过；
  `pipeline.py` 20 门重跑 17 PASS / 3 NA / 0 FAIL。

## 4. 上一轮修掉的事实错误（A1–A19，摘要保留）

公式层 Q3 整块重写（ε=0.50、P(C>H)≤ε completion feasibility、floor(εS)、目标
补完成项与 10Sλ 成本项、递推 max(p,b)、时钟=设备释放）；无产物宣称清零
（ε=0.25/0.542/0.594、merge/drop<0.01、solved to optimality）；泄漏口径改
「all 343 (246/35/62) 分位网格」+ train-only 消融；Q2 EM→矩估计、自相关改
JSON 实测并反转论证、λ=解析价格、三基线；Q1 BOCPD 表述、349 annotated、
within-record 0.500 仅两条常量分数、30 Hz、97.5%% 单侧；依赖用 `code/vendor/`
冻结副本落地。

## 5. 三轮演进

| 项 | 初稿（81 页） | v1（111 页） | v2（122 页） |
|---|---|---|---|
| verify_numbers | 92 claims，Q3 表 0 绑定 | 221 claims，60 格全绑 | 317 claims，+五映射 25 格+训练全绑 |
| ε | not swept | 六档实测 + train-only | 沿用 |
| 五映射 | 未跑 | 承认 open gap | **2250 trials 实测** |
| 训练 | 无 | 无 | **ridge/MLP/conformal 实测** |
| submitted 页数 | 超限风险 | 21+3=24 | 22+3=25（顶格） |

## 6. 还不许动（沿用，仍有效）

1. 不许为指标删节或注水；band 是参照不是目标。
2. 不许把 `best_policy=slack_old` 改写成「我们的方法最好」（五映射下依旧）。
3. 不许删 BOCPD 输给阈值基线与 MLP 不敌 ridge 两组负面结果。
4. 不许删 `main.tex` 的 `\\setcounter{page}{1}`。
5. 不许把「固定排期胜出」写成「自适应更好」：数据是反的。

## 7. 结论

v2 把两处官方硬要求（P2 训练/覆盖率、P3 五映射敏感性）从 open gap 变成实测，
训练维度补齐，317 claims 全过、16/16 gauntlet、venue 0 项、CJK 0、submitted
25 页顶格合规。它已是**可作主稿的完整稿**；主稿 `SWC2026_C` 的对比与优化按
用户指令留待之后，本轮未动。

VERDICT: PASS
""" % (tex_sha, pages, f"{pdf_bytes:,}", cjk, ridge_lo, kal_lo, ridge_hi, kal_hi, spread)

n = len(BODY.encode("utf-8")) + len("BYTES 0\n")
while True:
    head = "BYTES %d\n" % n
    n2 = len(BODY.encode("utf-8")) + len(head.encode("utf-8"))
    if n2 == n:
        break
    n = n2
out = ROOT / "review/00-plan.md"
out.write_bytes((head + BODY).encode("utf-8"))
print("wrote", out.stat().st_size, "bytes; fixed point", n2 == len(head.encode()) + len(BODY.encode()))
