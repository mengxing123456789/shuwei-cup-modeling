# -*- coding: utf-8 -*-
"""生成论文用图（数据示例，赛时替换为真实结果）。
运行： & 'E:\\Mini\\envs\\mathmodel\\python.exe' gen_figures.py
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "axes.linewidth": 0.8,
    "font.size": 9,
    "figure.dpi": 150,
    "savefig.dpi": 300,
    # 关键：默认 pdf.fonttype=3 会把文字写成 Type3 位图轮廓，
    # pdffonts 里显示为 Type 3，很多竞赛/期刊的自动检查会判"字体未正确嵌入"。
    # 42 = TrueType 子集嵌入，文字可复制、可搜索、体积更小。
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

# ---- Fig.1 灵敏度：目标函数随参数变化 ----
x = np.linspace(0.2, 3.0, 240)
fig, ax = plt.subplots(figsize=(3.4, 2.5))
for k, ls, lab in ((1.0, "-", r"$\alpha=0.5$"), (1.6, "--", r"$\alpha=1.0$"), (2.4, "-.", r"$\alpha=1.5$")):
    ax.plot(x, np.exp(-k * x) + 0.18 * x ** 1.5, ls, lw=1.1, label=lab)
ax.set_xlabel(r"Decision parameter $\theta$")
ax.set_ylabel(r"Objective $J(\theta)$")
ax.xaxis.set_major_locator(MaxNLocator(5))
ax.legend(frameon=False, fontsize=8)
ax.grid(alpha=0.25, lw=0.5)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig_sensitivity.pdf"))
fig.savefig(os.path.join(OUT, "fig_sensitivity.png"), bbox_inches="tight")
plt.close(fig)

# ---- Fig.2 收敛曲线 ----
it = np.arange(1, 201)
fig, ax = plt.subplots(figsize=(3.4, 2.5))
ax.semilogy(it, 1.0 / it ** 0.85 + 0.004 * np.random.RandomState(0).rand(len(it)), "-", lw=1.1, label="GA (ours)")
ax.semilogy(it, 1.0 / it ** 0.55, "--", lw=1.1, label="Baseline")
ax.set_xlabel("Iteration")
ax.set_ylabel("Relative gap")
ax.legend(frameon=False, fontsize=8)
ax.grid(alpha=0.25, lw=0.5, which="both")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig_convergence.pdf"))
fig.savefig(os.path.join(OUT, "fig_convergence.png"), bbox_inches="tight")
plt.close(fig)

print("FIGURES OK ->", OUT)
for f in sorted(os.listdir(OUT)):
    print("  ", f, os.path.getsize(os.path.join(OUT, f)), "bytes")