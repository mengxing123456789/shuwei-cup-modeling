# -*- coding: utf-8 -*-
import faulthandler, sys, io
from pathlib import Path
faulthandler.enable()
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import model_skeleton as M
import solve as S

print("loading", flush=True)
ai = M.load_annex_i()
print("loaded I", {k: v["labels"] for k, v in ai.items()}, flush=True)
r1 = S.q1(ai)
print("q1 ok", flush=True)
