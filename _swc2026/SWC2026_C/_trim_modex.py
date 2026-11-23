"""Trim one page out of the paper after the Modex structural additions.

Every anchor must match exactly once; nothing is written unless all edits land.
Also wraps the three problem headings so their digits stop counting as prose
numerals.
"""
import pathlib
import sys

P = pathlib.Path(r"E:\数学建模\_swc2026\SWC2026_C\main.tex")
src = P.read_text(encoding="utf-8")
out = src
done = []


def sub(name, old, new, count=1):
    global out
    n = out.count(old)
    if n != count:
        print(f"FAIL {name}: expected {count}, found {n}")
        sys.exit(1)
    out = out.replace(old, new, count)
    done.append(name)


# ---- 1. numeral-ok around the three problem headings
for k in ("1", "2", "3"):
    sub(f"mark-{k}",
        "\\section{Problem %s:" % k,
        "%% numerals-ok: begin\n\\section{Problem %s:" % k)
# close each marker right after the heading line's end (before \label)
for k, lab in (("1", "\\label{sec:partone}"), ("2", "\\label{sec:parttwo}"), ("3", "\\label{sec:partthree}")):
    sub(f"close-{k}", lab, lab + "\n% numerals-ok: end")

# ---- 2. the format paragraph repeated the table's counts
sub("trim-formats",
    r"""The package mixes three formats. EgoDemo contributes \slotDemoRecords{} recordings
and \slotDemoTS{} timestamps in JSON, Parquet and MP4, with both wrist views on a
subset of the recordings. EgoPro contributes \slotProRecords{} recordings and
\slotProTS{} timestamps in per-hand CSV tables plus MP4 video, with head stereo and
both wrist views. EgoStandard contributes \slotStdRecords{} recordings and
\slotStdTS{} timestamps in the same CSV-plus-video layout with head stereo only. Across the three we count \slotNRecords{} recordings,
\slotNTimestamps{} frames and \slotSizeGB{} GB. Each hand carries
\slotNKeypoints{} annotated three-dimensional keypoints, and the wrist-camera world extrinsics are
absent, so the four wrist views are not commonly calibrated. We therefore work in
the head frame and never compare absolute positions across datasets.""",
    r"""The package mixes three formats, and Table~\ref{tab:data} gives their scale.
EgoDemo ships JSON, Parquet and MP4 with both wrist views on a subset of recordings;
EgoPro and EgoStandard ship per-hand CSV tables plus MP4, the first with head stereo and
both wrist views, the second with head stereo only. Each hand carries
\slotNKeypoints{} annotated three-dimensional keypoints, and the wrist-camera world
extrinsics are absent, so the wrist views are not commonly calibrated. We therefore
work in the head frame and never compare absolute positions across datasets.""")

# ---- 3. the mapping paragraph repeated the adaptive-rule caveat
sub("trim-map",
    r"""No
scheduler-only change moves the rate by that much, which is why the mapping stays in the
paper as the dominant factor. The adaptive rule reported here holds the mapping at the
nominal one and buys its gain from the reservation rule and the fifteen-seed selection. A variant that estimates the mapping online was measured separately and did not carry
over to the test seeds, so it is not part of the reported policy.""",
    r"""No
scheduler-only change moves the rate by that much, which is why the mapping stays in the
paper as the dominant factor; the adaptive rule reported here holds it at the nominal
one, and its online-estimating variant did not carry over to the test seeds.""")

P.write_text(out, encoding="utf-8")
print("WROTE", P.name, len(src), "->", len(out), "chars  (saved", len(src) - len(out), ")")
print("edits:", ", ".join(done))