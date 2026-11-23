"""Free the page the new answer table costs: compress the two masked-arm paragraphs whose
findings now also appear in the rejected-moves table, keeping every number in place."""

import io
import os

MAIN = r"E:\数学建模\_swc2026\SWC2026_C\main.tex"
t = io.open(MAIN, encoding="utf-8", newline="").read()

old = r"""An obvious repair answers the question the statement raises but does not quantify:
whether training for missing input actually helps. It does not, at this horizon. Three
arms share the architecture, the seed and the windows --- a clean-input model, one with a
mask-aware channel filled by the previous value, and one filled by linear interpolation.
At no masked frames they read \slotPCleanZero{}, \slotPLocfZero{} and \slotPInterpZero{}
cm per coordinate. At six masked frames, \slotPCleanSix{}, \slotPLocfSix{} and
\slotPInterpSix{}, so the gap stays under two millimetres at every mask length and the
clean arm is anchored to the published baseline rather than to a fresh one.
"""
new = r"""Training for missing input does not help at this horizon. Three arms share the
architecture, the seed and the windows: clean input, a mask-aware channel filled by the
previous value, and one filled by linear interpolation. At no masked frame they read
\slotPCleanZero{}, \slotPLocfZero{} and \slotPInterpZero{} cm per coordinate; at six masked
frames, \slotPCleanSix{}, \slotPLocfSix{} and \slotPInterpSix{}. The gap stays under two
millimetres at every mask length, and the clean arm is anchored to the published baseline.
"""
assert t.count(old) == 1, "mask paragraph: %d" % t.count(old)
t = t.replace(old, new)

old = r"""The reliability score does not fare better as a training weight. Restricting the fit to
windows with no bad frame discards the very frames the score is about, so we widen the
training set to every window and let the weight carry the information: the clean fraction
of a window replaces the hard filter, and a third arm drops the filter with no weight at
all. The three arms read \slotPRelArmA{}, \slotPRelArmB{} and \slotPRelArmC{}~cm, and the
paired change from the filter to the soft weight is \slotPRelAtoB{}~cm with an interval of
\slotPRelAtoBCI{}. The chain from Part~I to this part therefore exists and is measured, and
it moves the number by millimetres. We report both nulls as one finding: at this horizon
"""
new = r"""The reliability score does not fare better as a training weight. Restricting the fit to
windows with no bad frame discards the frames the score is about, so we widen the training
set to every window and let the clean fraction of a window replace the hard filter, with a
third arm dropping both. The arms read \slotPRelArmA{}, \slotPRelArmB{} and
\slotPRelArmC{}~cm, and the paired change from filter to weight is \slotPRelAtoB{}~cm with
an interval of \slotPRelAtoBCI{}. The chain is measured and moves the number by millimetres.
We report both nulls as one finding: at this horizon
"""
assert t.count(old) == 1, "reliability paragraph: %d" % t.count(old)
t = t.replace(old, new)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("written", os.path.getsize(MAIN), "bytes")