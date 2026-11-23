"""Register the Part II cost-sweep slots in code/fill_numbers.py (idempotent)."""
from __future__ import annotations

import io
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "code" / "fill_numbers.py"

ANCHOR = (
    'add("PScaleDoubling", "up19_borrowed_alt", ["scaling", "doubling_factor"], "f3")'
)

NEW = [
    ('PEconSpan', 'up21_p2_cost_sweep', ["summary", "T_star_span_s"], "f2"),
    ('PEconTMin', 'up21_p2_cost_sweep', ["summary", "T_star_min_s"], "f2"),
    ('PEconTMax', 'up21_p2_cost_sweep', ["summary", "T_star_max_s"], "f2"),
    ('PEconNCell', 'up21_p2_cost_sweep', ["summary", "n_cells"], "int"),
    ('PEconInterior', 'up21_p2_cost_sweep', ["summary", "n_interior"], "int"),
    ('PEconAtEdge', 'up21_p2_cost_sweep', ["summary", "n_at_left_edge"], "int"),
    ('PEconCZeroSpan', 'up21_p2_cost_sweep',
     ["summary", "one_at_a_time", "@knob=C0", "span_s"], "f2"),
    ('PEconCOneSpan', 'up21_p2_cost_sweep',
     ["summary", "one_at_a_time", "@knob=C1", "span_s"], "f2"),
    ('PEconLamSpan', 'up21_p2_cost_sweep',
     ["summary", "one_at_a_time", "@knob=lambda", "span_s"], "f2"),
]


def main() -> int:
    text = io.open(TARGET, encoding="utf-8").read()
    if 'add("PEconSpan"' in text:
        print("already registered")
        return 0
    if ANCHOR not in text:
        raise SystemExit("anchor missing")
    lines = [ANCHOR]
    for name, jfile, path, tag in NEW:
        lines.append(
            f'add("{name}", "{jfile}", {path!r}, "{tag}")'
        )
    text = text.replace(ANCHOR, "\n".join(lines))
    io.open(TARGET, "w", encoding="utf-8", newline="\n").write(text)
    print(f"registered {len(NEW)} slots")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
