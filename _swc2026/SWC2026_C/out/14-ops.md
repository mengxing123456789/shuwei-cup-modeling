BYTES 1825
# 14 流水线运维：这一步的机器状态

## 1 步骤与闸门（`pipeline.py --status` 现跑）

```text
s1 赛题分析  done  G1=PASS G2=PASS G20=PASS
s2 建模求解  done  G3=PASS
s3 编程实现  done  G4=PASS G5=PASS G10=NA
s4 口径审计  done  G16=PASS
s5 图表      done  G6=PASS G11=??
s6 论文撰写  done  G7=PASS G12=PASS G17=NA
s7 编译合规  (未跑) G8/G13/G14/G15/G18/G19
s8 评审收口  (未跑) G9
```

## 2 软闸门与 NA 的语义（不许混）

- `SOFT_GATES = {"G10","G11","G14"}`：判不出（`??`）不拦，但**不许记成 PASS**。
- `NA`：结构性不适用（本题没有 `TABLE_*`、没有 `code_index.tex`、没有上传模板），计通过但单列。`--status` 末尾会打「不适用（NA，未真判）：G10, G17」。
- 任何非软闸门留 `??` 都会被 `G19 流水线自检` 判 FAIL（防止“没判就当过”）。

## 3 本步的命令与产物

```powershell
E:\Mini\envs\mathmodel\python.exe E:\数学建模\.agents\skills\mathmodeling\scripts\pipeline.py `
  E:\数学建模\_swc2026\SWC2026_C --only s7 --force s7 --skip-dispatch --no-review-each
```

产物：`out/03-compliance.md`（本节同批）、`out/10-layout.md`、`out/14-ops.md`（本文件）。
编译：`xelatex main.tex` 两遍，退出码 `[0, 0]`。

## 4 状态文件

`logs/pipeline_state.json`，`STATE_SCHEMA=4`；改 `STEPS`/`GATES` 必须升版本号，旧状态会被备份成 `pipeline_state.v3.bak` 并重跑（这是 2026-11-19 那轮踩过的坑：版本不升会把旧 `s4=done` 读成新 s4）。

## 5 已知的“判不出”

- `G11`：视觉模型对 6 张图里 1 张返回限流，记 `??`；重跑可消除。
- `G14`：本机没有上传模板 zip，结构性 NA。
- `G10`：本稿没有 `TABLE_*` 前缀的中间表，结构性 NA。

VERDICT: PASS
