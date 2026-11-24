#!/usr/bin/env bash
# apmcm-start.sh — 亚太杯（APMCM）开赛一键入口
# 生成：2026-11-24，源自数维杯 2026 秋季赛 C 题完整工作区 + Modex 逆向契约五件套。
# 用法：
#   ./apmcm-start.sh <题目目录> <题号A-F> <题面txt路径>
# 例：
#   ./apmcm-start.sh E:\数学建模\APMCM2026_Q  A  "E:\下载\2026_A_Problem.txt"
# 前置（一次性）：
#   1) Python 带 numpy/pandas/matplotlib（或设 MM_PY 指向它）
#   2) MiKTeX（xelatex 在 PATH，或装好后新开终端）
#   3) 本仓库根 = 数学建模工作区（含 .agents/skills、corpus/、docs/pitfalls/）
set -euo pipefail

DIR="${1:-}"
LETTER="${2:-}"
PROB="${3:-}"

if [[ -z "${DIR}" || -z "${LETTER}" || -z "${PROB}" ]]; then
  echo "用法: $0 <题目目录> <题号A-F> <题面txt路径>"
  exit 2
fi

# 仓库根 = 含 .agents/skills 的那一层：脚本可能放在仓库根，也可能放在子目录
HERE="$(cd "$(dirname "$0")" && pwd)"
if [[ -d "${HERE}/.agents/skills/mathmodeling/scripts" ]]; then
  WS="${HERE}"
elif [[ -d "${HERE}/../.agents/skills/mathmodeling/scripts" ]]; then
  WS="$(cd "${HERE}/.." && pwd)"
else
  echo "找不到 .agents/skills/mathmodeling/scripts——请把本脚本放在数学建模工作区内"
  exit 2
fi
SCRIPTS="${WS}/.agents/skills/mathmodeling/scripts"

# 1) 解释器解析（MM_PY > 当前 > 工作区 venv > PATH），与 run_all.py 同源
PY="${MM_PY:-}"
if [[ -z "${PY}" ]]; then
  for cand in \
    "${WS}/envs/mathmodel/python.exe" \
    "$(command -v python3 || true)" \
    "$(command -v python || true)"; do
    [[ -n "${cand}" && -x "${cand}" ]] && PY="${cand}" && break
  done
fi
echo "[0/5] 解释器: ${PY:-未找到——请设 MM_PY}"
"${PY}" -c "import numpy,pandas,matplotlib" || {
  echo "  该解释器缺 numpy/pandas/matplotlib，先 pip install 或设 MM_PY"; exit 2; }

# 2) 题面 sanity：非空 + 有 "Problem" 字样（防拿错文件）
[[ -s "${PROB}" ]] || { echo "题面文件不存在或为空: ${PROB}"; exit 2; }
grep -qi "problem" "${PROB}" || echo "  [warn] 题面里没有 'problem' 字样，确认拿对文件"

# 3) 契约五件套（Modex 复用：CONTRACT/PLAN/LOG/FINDINGS/PAPER_PLAN）
echo "[1/5] 契约五件套 -> ${DIR}/contracts"
"${PY}" "${WS}/.agents/skills/contracts/contracts/scaffold_contracts.py" "${DIR}" || true

# 4) 一条命令：骨架(apmcmthesis) -> 题面 -> 八步二十门(s1 起步会停在校验，正常)
#    --skip-dispatch 必加：否则会派单给 DSH Web 挂死。
echo "[2/5] run_all（骨架 + 题面 + s1 赛题分析）"
"${PY}" "${SCRIPTS}/run_all.py" "${DIR}" --type "${LETTER}" --cls apmcm \
        --problem-file "${PROB}" --skip-dispatch

# 5) 语料对标：历年获奖论文与真题（corpus/，2019-2025）
echo "[3/5] 真题语料索引"
"${PY}" "${SCRIPTS}/corpus_index.py" --query-file "${DIR}/problem/problem.txt" | head -40 || true

echo "[4/5] 同题/同型获奖论文枚举"
"${PY}" "${SCRIPTS}/corpus_index.py" --stats | head -20 || true

echo "[5/5] 开赛检查表"
cat <<'EOF'
  □ RESEARCH_CONTRACT.md 的 Core Claims 是否已写实（- C1: 起头）
  □ EXPERIMENT_PLAN 的 MUST-RUN 是否只留保底管线
  □ M0 sanity（用 1/10 数据把全链跑通）排了吗
  □ find 命令防手滑：git status / 数据只进 data/、报告只进 review/
  □ 三条纪律：证据优先 / 最小改动 / 改完必验证（AGENTS.md）
EOF
echo "done. 下一步：人工审 s1 产出（out/00-problem.md），再继续 s2+。"
