import io, re, sys

t = io.open("slots.tex", encoding="utf-8").read()
names = set(re.findall(r"\\newcommand\{\\(slot\w+)\}", t))
want = sys.argv[1:] or [
    "slotVHigh", "slotVLow", "slotAGrasp", "slotTArrange", "slotSlackDecay",
    "slotBMin", "slotReserveQ", "slotChangeOver", "slotFusionWeight",
]
for w in want:
    print("%-22s %s" % (w, "OK" if w in names else "MISSING"))
print("total slots", len(names))
