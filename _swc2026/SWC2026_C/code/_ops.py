# -*- coding: utf-8 -*-
# AI 辅助：DeepSeek Harness 助手生成（DeepSeek，2026-11-22）。
"""List the computed-slot operations fill_numbers.py supports."""
import io
import re
import sys

sys.path.insert(0, "code")
import fill_numbers as F  # noqa: E402

t = io.open("code/fill_numbers.py", encoding="utf-8").read()

print("SPEC   :", len(F.SPEC))
print("SLOTS  :", len(F.SLOTS))
print("COMPUTED:", len(F.COMPUTED))

ops = sorted(set(v[1] for v in F.COMPUTED.values()))
print("computed ops in use:", ops)

print("\n--- SPEC sample (declared constants) ---")
for k in list(F.SPEC)[:5]:
    print("  %-18s %r" % (k, F.SPEC[k]))

print("\n--- COMPUTED sample ---")
for k in list(F.COMPUTED)[:5]:
    print("  %-18s %r" % (k, F.COMPUTED[k]))

print("\n--- how main() emits SPEC entries ---")
i = t.find("for name in sorted(SPEC)")
print(t[i:i + 260])
