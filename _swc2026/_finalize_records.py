# -*- coding: utf-8 -*-
"""Align the shipped support records (out/*.md, review/*.md) with the delivered
111-page revised main.tex. Exact substring patches assert count==1; full rewrites
replace the two documents whose identity was entirely from an older draft.
Every md with a `BYTES n` first line is then put through the byte-count fixed point.
"""
from __future__ import annotations

import pathlib
import sys

WS = pathlib.Path(r"E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP")


def patch(rel: str, rules: list[tuple[str, str]]) -> None:
    p = WS / rel
    txt = p.read_text(encoding="utf-8")
    for old, new in rules:
        n = txt.count(old)
        if n != 1:
            print(f"  !! {rel}: count={n} for {old[:60]!r}")
            raise SystemExit(2)
        txt = txt.replace(old, new, 1)
    p.write_bytes(txt.encode("utf-8"))
    print(f"  patched {rel}: {len(rules)} rules")


def rewrite(rel: str, body: str) -> None:
    p = WS / rel
    p.write_bytes(body.encode("utf-8"))
    print(f"  rewrote {rel}: {len(body.encode('utf-8'))} B")


def fix_bytes() -> None:
    total = 0
    for d in ("out", "review"):
        for p in sorted((WS / d).glob("*.md")):
            raw = p.read_bytes()
            lines = raw.decode("utf-8").split("\n")
            if not lines or not lines[0].startswith("BYTES"):
                continue
            body = "\n".join(lines[1:])
            reported = -1
            for _ in range(12):
                n = len(body.encode("utf-8")) + len(f"BYTES {reported}\n".encode("utf-8"))
                if n == reported:
                    break
                reported = n
            text = f"BYTES {reported}\n{body}"
            p.write_bytes(text.encode("utf-8"))
            ok = len(text.encode("utf-8")) == reported
            print(f"  {'OK ' if ok else 'BAD'} {d}/{p.name:24s} {reported:7d} B")
            if not ok:
                raise SystemExit(3)
            total += 1
    print(f"  {total} BYTES fixed points done")


# ---------------------------------------------------------------------------
# 1. out/01-model.md — the old file described a superseded model (single lambda,
#    MAP run length -> 0, EM, stratified resampling, eps=0.2, median train
#    durations). Rewrite it as an accurate modelling report for the delivered
#    paper. VERDICT: PASS + BYTES first line are kept.
# ---------------------------------------------------------------------------
MODEL = """BYTES 0
# Modelling Report — SWC2026_C_ALT_BACKUP (backup paper)

This report describes the model that is actually delivered in `main.tex`. It is
a different construction from the primary paper `SWC2026_C` (which uses a
supervised ridge + conformal predictor and a fixed decision threshold); here
all three questions are built on Bayesian/state-space estimators with honest
negative results. `main.tex` and the JSON products in `data/` are authoritative;
where an earlier design brief disagreed, it was superseded.

## 0. One line per question

1. **Q1** — a recording is segmented by a BOCPD run-length posterior over the
   speed of the fingertip centroid (resampled to 5 Hz); each segment carries a
   hierarchical Beta-Binomial posterior on its usable probability `rho = 1 - theta`.
2. **Q2** — the hand is a damped constant-velocity target (126-dimensional
   state) observed through a single wrist camera; the value of a paid look is a
   derived price from the marginal posterior trace reduction.
3. **Q3** — restocking is a stochastic scheduling problem; a scenario
   chance-constrained CP-SAT program chooses order and reservation and is rolled
   forward after each job, with a deterministic EDF fallback on solver timeout.

## 1. Data layer

The corpus is three archives with three containers. After unification the panel
is keyed by `(record, t)` and carries, per hand, 21 keypoints in 3D in the head
frame, a bad-frame quality flag, and for some records a wrist camera. The split
is environment-level, 16 train / 4 validation / 4 test, so no environment is
shared between fitting and evaluation. The record identifier is not the
directory name: the true `episode_uuid` lives in `session_metadata.csv` (MCAP)
or `meta/episodes/*.parquet` (EgoDemo). The 1.2 s eligibility threshold in
`source_segment_index.csv` is subject to floating-point subtraction: a 1e-9
tolerance gives 343 eligible of 349 annotated segments, matching the statement.
`out/alt_p2.md` and `data/alt_full_audit.json` hold the full audit.

## 2. Q1 — change points and reliability

### 2.1 BOCPD
Within a regime the centroid speed is a noisy constant with unknown mean and
variance; the conjugate Normal-Inverse-Gamma prior gives a Student-t predictive,
and the run-length posterior is updated recursively with hazard `1/lambda`.
Four settings are fixed before any evaluation: smoothing `sigma = 0.40 s`,
hazard `lambda = 4.0 s` (the median annotated training segment length), merge
threshold `3.0 s`, drop fraction `0.30`. A boundary is declared when the
run-length posterior falls below 30% of its running peak; the raw `P(r_t = 0)`
never exceeds 0.119, so a literal "return to zero" rule would almost never fire.
Segments shorter than 3.0 s are merged. `code/alt_p1_bocpd.py` is the producer.

### 2.2 Hierarchical reliability
For segment `i` with `y_i` bad frames out of `n_i`:
`y_i ~ Binomial(n_i, theta_i)`, `theta_i ~ Beta(mu*kappa, (1-mu)*kappa)`,
`mu ~ Beta(a0, b0)`. The posterior of `mu` is computed on a grid; each segment
is reported by its posterior mean and one-sided 2.5% lower bound on
`rho_i = 1 - theta_i`. The retention rule `q_0.025(rho_i) >= 0.90` keeps 333 of
349 annotated segments (95.4%, 95.70% duration-weighted).

### 2.3 The honest negative result
The kinematic detector **loses** to a fixed speed-threshold baseline at strict
tolerance (boundary F1 0.183 vs 0.219 at +/-0.5 s), because annotated boundaries
are semantic subtask changes while the detector finds motion regime changes.
The reliability layer, not the segmentation layer, is the deliverable; its
within-record AUC reverses to 0.076 under leave-one-segment-out, which is
reported rather than hidden. A record-level AUC of 0.914 is exposed as an
artefact of aggregation. `data/alt_p1.json` holds all four diagnostics.

## 3. Q2 — damped Kalman filter and value of information

### 3.1 Filter
State `[p_t, v_t]` with `v_{t+1} = alpha*v_t + w_t`; `alpha = 0.6` is chosen on
the validation split. `Q` and `R` are estimated by the **method of moments** on
visible training prefixes (`q = Var(v)(1 - alpha^2)`, `r` from the 10th
percentile of squared second differences / 6); expectation-maximisation
degenerates to the numerical floor (`R` median 1.6e-9) and was abandoned.

### 3.2 Value of information
In a linear-Gaussian model the posterior covariance is observation-independent,
so the expected trace reduction is the same for every record: VOI collapses to
a step (0 or 2 looks, no interior solution). The threshold `lambda* = 1158.0
cm^2` per look (= 1.61 cm RMSE) is a **derived price** from the marginal
posterior trace reduction, not a calibrated hyperparameter. Masked-window error
follows `e(L) = 10.07 L^0.741` (R^2 = 0.967). Baselines are last-state hold,
constant-velocity extrapolation, and a linear fit on the same windows and seeds.
`data/alt_p2.json` holds the tables; the delivered paper also reports the
measured scaling law and the fair-prefix comparison.

## 4. Q3 — chance-constrained scheduling

### 4.1 Scenarios
`S = 20` scenarios are built from the 5-95% quantile grid of residuals of all
343 eligible segments (246 train, 35 validation, 62 test), grouped by family x
observation prefix, with per-unit rank de-correlation by CRC32 so scenarios are
not comonotone. Pooling all three splits is a leakage; a train-only ablation
(`data/alt_p3_sweep.json`) bounds it and leaves the ranking unchanged.

### 4.2 Program
Chance constraint on **completion feasibility** `P(C_j^omega > H) <= epsilon =
0.50`, enforced by the scenario count `floor(epsilon*S)`; the big-M constant is
used only on ordering arcs. Start times `s_j = max(r_j, s_{j-} +
max(p_{j-}^omega, b_{j-}) + D + 0.5)`; the device is released at
`s_j + max(p_j, b_j)` and the clock advances to that release. Objective:
`1e4` weighted on-time + `3e3` completion - truncated (10 s) tardiness -
`10*S*lambda*cost` with `lambda = 0.01`. Solved to feasibility within a 1.0 s
CP-SAT limit with a deterministic EDF fallback; solver fallbacks are counted in
the trials and reported in the paper.

### 4.3 Result, stated as measured
The rolling program beats EDF but **does not beat SLACK**; the best policy on
the declared metric is `slack_old`, not our program. A six-level `epsilon` sweep
(0.20-0.70) and a train-only residual bank leave that ranking unchanged.
Baselines are EDF and SLACK with prediction-based and pressure-adaptive reserves
(the official `p3_stochastic_schedule.py`), on the same 30 seeds. The
opportunity-constraint MIP's one-shot rows in S2/S3 fall back to EDF on every
seed, which is disclosed. `data/alt_p3.json` is the record; the frozen read-only
dependencies are in `code/vendor/`.

## 5. Verification
`code/verify_numbers.py` binds every printed number to a key in `data/*.json`
(221 claims, including all 60 cells of Table~`tab:p3` cell by cell) and fails on
any unbound token; it also asserts the measured `epsilon` sweep, paired 30-seed
confidence intervals and fallback counts. `data/alt_p3_sweep.json` is produced
by `code/alt_p3_sweep.py`. The six judgement/figure/appendix records in `out/`
and `review/` were aligned to this 111-page revision in the same round.

VERDICT: PASS
"""

# ---------------------------------------------------------------------------
# 2. review/00-plan.md — closing review for the 111-page revision
# ---------------------------------------------------------------------------
PLAN = """BYTES 0
# 评审收口 — SWC2026_C_ALT_BACKUP（111 页修订稿）

本稿与主稿 `SWC2026_C` 方法完全不同：BOCPD + 分层 Beta-Binomial / 阻尼常速度
卡尔曼 + VOI / 场景机会约束 CP-SAT + 滚动重排。本轮不是重新建模，而是把一份
已经可交的备用稿做「真实化」：用只读审读 + 机器对账逐条查正文，把过期口径、
无产物支撑的宣称、与代码不一致的公式全部按实测改写，并补上三条原本缺的实测。

## 1. 被测件身份（现算，非记忆）

| 文件 | 大小 | sha256 前 16 |
|---|---|---|
| `main.pdf` | 903,797 B / 111 页 | `f38d0662dec95683` |
| `main.tex` | 58,168 B | `b6ee617aaed4433d` |

物理页 3–23 = 正文 21 页（<= 25 页上限），页 24 起附录 A，24–111 = 88 页；
页眉 `Page n of 109`（109 带页眉 + 2 前置页）。`main.pdf` CJK 字符 0，
`Overfull \\hbox` 0，undefined reference 0，xelatex 两遍 PASS。

## 2. 机器判据现状（本轮实测）

- `code/verify_numbers.py`：**221 claims / 0 failures**（其中 60 条逐格绑
  `tab:p3`，另有 14 条字面量、1 条 RANGES）。修订前是 92 条且 `p3.` 前缀 0 条
  —— P3 分支是死代码（`P3["summary"]` 是 list，`if best and best in sm` 永假）。
- `gauntlet_check.py` 16/16 PASS；`caliber_check.py` 硬项 0 / 提示 6 PASS；
  `submission_gate --only venue` 0 项要你处理；六张图视觉闸通过。
- `pipeline.py` 本轮重跑 20 门（见第 5 节）。

## 3. 本轮修掉的事实错误（A1–A19 摘要，全部有源码/JSON 证据）

- **公式层（Q3 整块重写）**：`epsilon=0.2` -> 实测 `0.50`；机会约束从
  `C_j>d_j` 改为代码里的 `P(C_j^omega > H) <= eps`（completion feasibility），
  `floor(eps*S)` 计数；目标补 `3e3` 完成项、截断 10 s tardiness、`10*S*lambda`
  成本；递推补 `max(p,b)`；时钟改「推进到设备释放」；big-M 只用于排序弧。
- **无产物宣称清零**：删「earlier run at eps=0.25 gave 0.542/0.594」（全库无
  对应 trials，`fill_p3.py` 硬编码）、删「merge/drop 使 F1 变 <0.01」（根本没
  重跑）、删「solved to optimality」（1.0 s CP-SAT limit + 每 seed 回退）。
- **泄漏口径**：场景库从「343 eligible train / stratified resampling / every
  family and zone」改为「all 343 (246/35/62), 5–95% 分位网格, per prefix x
  family, CRC32 去相关」，并明写这是泄漏、用 train-only 消融界定。摘要删
  「no test environment is used for tuning」的绝对措辞。
- **Q2 事实**：EM -> method of moments；自相关 0.878/0.519/0.220/-0.013 ->
  JSON 实测 0.940/0.897/0.875/0.817，论证方向从「半秒衰减为无用」反转；
  `lambda` 从「validation 校准」改为「trace 边际解析得出的价格」；删不存在的
  「one look every 1.5 s」基线，补 hold/cv/linear 三基线（表加 Linear 列）。
- **Q1/全文**：`marked point process` -> BOCPD run-length posterior；
  「349 eligible」->「349 annotated」；「within-record AUC exactly 0.500」->
  两条常量分数 0.500 / posterior bound 0.565 / LOOO 0.076；「21 keypoints at
  5 Hz」-> 30 Hz（5 Hz 只是 Q1 降采样）；「95% lower bound」-> one-sided 97.5%；
  摘要「21.50 cm (last-state)」-> (constant-velocity)；`ref4`/`ref5` 引用落点；
  删「no number is typed by hand」，附录补 5 个 fill/verifier/sweep listing。
- **声明依赖**：`code/alt_p3_ccmip.py` 对主稿 `code/`/`data/` 的只读硬依赖
  （`OFFICIAL_CODE`/`OFFICIAL_DATA`）用 `code/vendor/` 冻结副本落地，正文/附录
  如实声明，不再产生「卸载主稿后数字会变」的路径依赖。

## 4. 本轮新增的三条实测（不是叙述，是 `data/*.json`）

| 编号 | 内容 | 落点 |
|---|---|---|
| M1 | **六档 `epsilon` 扫描**（0.20/0.30/0.40/0.50/0.60/0.70，8 seeds，135 cells，728.9 s）+ **train-only 残差库消融**：六档与 train-only 的 `best` 全是 `slack_old`（0.821），rolling 峰值 0.804 @ 0.50 | 替换编造的 eps=0.25 段，`data/alt_p3_sweep.json` |
| M2 | **30-seed 配对 CI**：rolling-oneshot 三 case `[0.043,0.153]/[0.016,0.173]/[0.030,0.139]` 全在 0 右；slack-rolling `[-0.001,0.013]/[-0.006,0.092]/[-0.015,0.074]` 全跨 0（与「trails SLACK」一致） | Q3 敏感性段 |
| M3 | **solver fallbacks 分层**：rolling S2 84/30、S3 245/30 seeds 全非零；oneshot S2/S3 每 seed 回退；`r(cost,reviews)=0.083` 推翻「cost tracks paid looks」 | 新增「Solver fallbacks are measured, not hidden」段 |

## 5. 修订前 -> 修订后

| 项 | 修订前（81 页） | 修订后（111 页） |
|---|---|---|
| verify_numbers | 92 claims，Q3 表 0 绑定 | 221 claims，60 格全绑 |
| `epsilon` | 「not swept / open question」 | 六档实测 + train-only 消融 |
| Q3 公式 | 与代码 5 处不符 | 按 `:275,301-303,322-339,356-359,549` 重写 |
| 最优宣称 | 「solved to optimality」 | 「solved to feasibility within 1.0 s + 计数回退」 |
| 依赖 | 硬指主稿目录 | `code/vendor/` 冻结只读副本 |

## 6. 还不许动（沿用上一轮，仍有效）

1. 不许为指标删节或注水；band 是参照不是目标。
2. 不许把 `best_policy=slack_old` 改写成「我们的方法最好」。
3. 不许删 BOCPD 输给阈值基线那两行——它是全文最有信息量的负面结果。
4. 不许删 `main.tex` 的 `\\setcounter{page}{1}`。
5. 不许把「固定排期胜出」写成「自适应更好」：数据是反的。

## 7. 结论

本轮把备用稿从「数字大体对、但有多处口径/公式/宣称与自身代码和 JSON 不符」
修成「逐条可复算、负面结果如实、依赖已冻结」的稿子：221 claims 全过、
16/16 gauntlet、venue 0 项、CJK 0、111 页（正文 21）在 25 页内。它仍是**备用
稿**：主稿 `SWC2026_C` 的进一步优化与两稿对比按用户指令留待之后，本轮未动。

VERDICT: PASS
"""


def main() -> int:
    print("== rewrites ==")
    rewrite("out/01-model.md", MODEL)
    rewrite("review/00-plan.md", PLAN)

    print("== patches ==")
    patch("out/03-compliance.md", [
        ("pages 3–74 each carry", "pages 3–111 each carry"),
        ("`Page n of 72`; page 1", "`Page n of 109`; page 1"),
        ("74 submitted pages of which 17 are body — inside the ceiling",
         "111 submitted pages of which 21 are body (88 appendix pages, unlimited) — inside the ceiling"),
        ("Appendix A lists 5 scripts verbatim", "Appendix A lists 11 scripts verbatim"),
        ("0 CJK spans in the five figure PDFs", "0 CJK spans in the six figure PDFs"),
        ("- `code/verify_numbers.py`: 51 claims, 0 failures.",
         "- `code/verify_numbers.py`: 221 claims, 0 failures (60 of them bind the Q3 table cell by cell)."),
    ])
    patch("out/05-caliber.md", [
        ("`submitted pages` = 74 (everything", "`submitted pages` = 111 (everything"),
        ("`body pages` = 17 (summary", "`body pages` = 21 (summary"),
        ("= `n` over 72, which", "= `n` over 109, which"),
        ('figure "17 body pages" appears', 'figure "21 body pages" appears'),
        ("## Open, not resolved\n\n"
         "The chance level `ε = 0.5` in the final run was not swept; an earlier run at 0.25\n"
         "with one seed per cell gave visibly lower completion, so the dependence exists but is\n"
         "not measured. The paper says so rather than presenting `ε = 0.5` as a tuned value.",
         "## Resolved this round: the chance level is now a measured curve\n\n"
         "The earlier note that `ε` \"was not swept\" no longer holds. A six-level sweep\n"
         "(`ε` in {0.20, 0.30, 0.40, 0.50, 0.60, 0.70}, 8 paired seeds, 135 cells,\n"
         "728.9 s of solver time) and a train-only residual-bank ablation are recorded in\n"
         "`data/alt_p3_sweep.json` and summarised in the body. Across all six levels and the\n"
         "train-only bank the best policy stays `slack_old` (mean weighted on-time 0.821);\n"
         "the rolling program peaks at 0.804 at `ε = 0.50`. No unmeasured \"earlier run at\n"
         "0.25\" is cited anywhere; `code/verify_numbers.py` asserts the swept numbers."),
    ])
    patch("out/alt_p2.md", [
        ("选择阻尼项的理由不是拟合误差，而是训练集上速度自相关衰减很快：lag-1 = 0.878、lag-3 = 0.519、lag-5 = 0.220、lag-10 ≈ -0.013（见 JSON `model.velocity_autocorr`）。纯 CV 会把这一衰减误当成持续速度，长掩蔽段严重外推。",
         "阻尼项不是靠「速度自相关衰减很快」选的：训练集实测 lag-1/2/3/5/10 = 0.940/0.905/0.897/0.875/0.817（JSON `model.velocity_autocorr`），到 lag-10 仍很高，所以纯常速度在最短掩蔽档仍有竞争力（0.2 s 上 cv 2.914 对 Kalman 2.862 cm）。选 `alpha=0.6` 是验证集上的长掩蔽表现：纯 CV 在掩蔽超过 0.4 s 后持续外推，阻尼抑制了这一点。旧稿这里曾硬编码 0.878/0.519/0.220/-0.013 一组与 JSON 不符的数字，已按 `model.velocity_autocorr` 修正。"),
    ])
    patch("review/07-figures.md", [
        ("被测件：`E:\\数学建模\\_swc2026\\SWC2026_C_ALT_BACKUP\\main.pdf`（74 页，印刷页码 \"Page n of 72\"）",
         "被测件（历史审读记录）：`E:\\数学建模\\_swc2026\\SWC2026_C_ALT_BACKUP\\main.pdf`（当时的 5 图 74 页稿，印刷页码 \"Page n of 72\"）。注：本报告是那一轮的图表审读证据，其中列出的缺陷已在本轮修订中逐条处理；当前交付稿为 111 页 / 6 图 / \"Page n of 109\"，以 `main.tex` 与 `review/00-metrics.md` 为准。"),
    ])

    print("== BYTES fixed points ==")
    fix_bytes()
    print("FINALIZE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
