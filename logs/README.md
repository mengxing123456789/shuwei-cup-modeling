# `logs/` — 小队运行记录

十人建稿队与十三人评审队每次派单的运行账本，由 `run_squad.py` / `run_review.py` 写入。

| 文件 | 内容 |
| --- | --- |
| `_crew_cfg.json` | 上次派单的配置（工作区、论文目录、波次范围） |
| `_crew_bodies.json` | 每个成员的 brief 正文快照（改过 brief 后用来 diff） |
| `_crew_run_<epoch>.json` | 一次完整运行的账本：每个成员的开始/结束时间、退出码、产物路径 |

## 什么时候看它

- 派单后某步一直 FAIL 说「缺文件」→ 看 `_crew_run_*.json` 里那个成员的 `rc` 与 `stderr`，判断是会话没落地还是脚本报错。
- 改了 `squads/main/NN-*.md` 的 brief → 与 `_crew_bodies.json` 里的旧版 diff，确认改动生效。

## 为什么只有 3 个文件

每次运行会覆盖同名文件（`_crew_cfg.json`、`_crew_bodies.json`），只有 `_crew_run_<epoch>.json` 按时间戳累积。这是有意的：`_crew_bodies.json` 是「当前 brief」的快照，不是历史。

## 别放进来的东西

成员的 stdout 全文不落这里（会到几十 MB）。要留证据就存到对应论文目录的 `logs/` 下，那里按成员名分文件。
