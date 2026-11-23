import pathlib, sys
P = pathlib.Path("main.tex"); t = P.read_text(encoding="utf-8")
edits = [
# 1) §2.5 首句删除
("""Everything that follows is about one object. Let $z_t=(x_t,\\varphi_t,d)$ be the
state of a work unit after $t$ seconds of its own service: the hand configuration""",
 """Let $z_t=(x_t,\\varphi_t,d)$ be the state of a work unit after $t$ seconds of its own
service: the hand configuration"""),
# 2) §6 开头压缩
("""Two quantities bound Part III: what the instance allows even with $p$ known, and what our
information allows. Table~\\ref{tab:limits} separates them by running the reservation rule
with and without the true duration, and placing the adaptive rule beside both.""",
 """Two quantities bound Part III: what the instance allows with $p$ known, and what our
information allows; Table~\\ref{tab:limits} separates them by running the reservation rule
with and without the true duration."""),
# 3) §6 First 段尾句删除
("""the weighted work misses its due date under this reservation rule on this instance, and a
near-perfect claim would be a claim about the instance rather than the method.""",
 """the weighted work misses its due date under this reservation rule on this instance."""),
# 4) §5 校准段压缩
("""The residual optimism is
\\slotPCFShiftTrain{} with a train-fitted law and \\slotPCFShiftAll{} with a law fitted on
all splits, so a third of it is the train-to-validation shift in the duration pool and the
rest is the selection induced by executing only the jobs that can still start before the
horizon.""",
 """Residual optimism is
\\slotPCFShiftTrain{} with a train-fitted law and \\slotPCFShiftAll{} with a law fitted on
all splits: a third is the train-to-validation shift in the duration pool, the rest the
selection induced by executing only jobs that can still start."""),
]
for old, new in edits:
    if t.count(old) != 1:
        print("MISS (%d):" % t.count(old), old[:50].replace("\n"," ")); sys.exit(1)
    t = t.replace(old, new)
P.write_text(t, encoding="utf-8", newline="\n")
print("edits applied:", len(edits))
