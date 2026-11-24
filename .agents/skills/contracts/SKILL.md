# name: contracts
# description: 建模赛前期契约五件套（源自 Modex 逆向，已独立验证 11 PASS）：RESEARCH_CONTRACT / EXPERIMENT_PLAN / EXPERIMENT_LOG / FINDINGS / PAPER_PLAN。开赛定题后立即运行，为全队建立「主张—证据—章节」的可追溯骨架；会话恢复/换人交接时只读 CONTRACT 不读全部原始材料。
# disable-model-invocation: false
# allowed-tools: Bash(python *), Write, Read
# argument-hint: [工作目录]（默认当前目录；将创建 contracts/ 子目录）

# 契约五件套脚手架（Modex 复用）

你在为一次数学建模比赛（默认亚太杯 APMCM，也适用于数维杯/美赛）建立**前期契约文件系统**。
参照物是 Modex 3.0.2 的科研线模板（逆向报告 `E:\数学建模\_modex_re_work\RE-MODEX-FULL-REPORT.md` §7），
已由 `test_modex_reuse_patterns.py` 验证可独立运行（11 PASS / 0 FAIL）。

## 你的工作

1. 在 `$ARGUMENTS` 给的目录（缺省为当前目录）下创建 `contracts/` 子目录。
2. 用本技能自带的生成器写五份文件（不要手写全文，保证结构稳定）：

   ```bash
   python "<skill_dir>/contracts/scaffold_contracts.py" "<目标目录>"
   ```

   脚本位于本技能目录的 `contracts/scaffold_contracts.py`，退出码 0 即成功。

3. 五份文件各自的角色（写内容时严格照此分工，**不要越界**）：

   | 文件 | 角色 | 谁写、何时 |
   |---|---|---|
   | `RESEARCH_CONTRACT.md` | **选定题目的独立工作文档**。会话恢复/交接时**只读它**，不重读全部原始材料。核心字段：Selected Idea / Core Claims（`- C1:` 起头，供矩阵引用）/ Method Summary / Experiment Design / Baselines 表 / Key Decisions / Status checklist（M0 sanity → M1 baselines → M2 main → M3 ablation） | 定题后立即写第一版；之后每有重大决定就更新 Key Decisions |
   | `EXPERIMENT_PLAN.md` | 执行计划：Claim Map 表（claim↔evidence↔section）/ Blocks（MUST-RUN vs NICE-TO-HAVE）/ Run Order（M0→M1→M2→M3，**M2 后设 Decision Gate**）/ Compute Budget / Risks | 与 CONTRACT 同批写；每开新实验前回看 |
   | `EXPERIMENT_LOG.md` | 每个实验一节：Setup / Results 表 / Verdict（Supports claim?）/ Reproduction 命令。**tracker（执行清单）与 log（永久记录）分离**——执行状态勾在 CONTRACT 的 checklist，结论写这里 | 每跑完一个实验立刻追加 |
   | `FINDINGS.md` | Research Findings + Engineering Findings 双区。**会话恢复必读**。示例条目风格：「小数据集上 X 无效」「Y 组合梯度爆炸」「Z 不值额外开销」 | 有负结果/意外发现随手记 |
   | `PAPER_PLAN.md` | Claims-Evidence Matrix（C#→Evidence→Section）/ Section Plan（每节页数）/ Figure Plan / Key References | 写作前完成；正文写作以它为大纲 |

4. **硬规则（写进文件头注释，也要遵守）**：
   - Core Claims 必须用 `- C1:`、`- C2:` 编号——EXPERIMENT_PLAN 的 Claim Map 与 PAPER_PLAN 的矩阵都靠这个 id 关联。
   - PAPER_PLAN 的矩阵里，每个 C# 至少对应一条**已存在**的证据（实验/图表/引理），没有证据的 claim 标 `UNSUPPORTED`。
   - 会话恢复时：只读 CONTRACT + FINDINGS + PAPER_PLAN 三件，即可继续工作，不重读题面全文。
   - 正文里的每个结果数字必须能回溯到 EXPERIMENT_LOG 的某一节（与我们 G12 数字溯源一致）。

5. 全部写完后向用户报告：五份文件路径 + 提醒「M0 sanity 实验开始前先把 CONTRACT 的 Claims 写实」。

## 边界

- 本技能只建骨架与规则，**不替用户选题、不写实验结论**。
- 若目标目录已有 `contracts/`，不覆盖，提示已存在并退出。
