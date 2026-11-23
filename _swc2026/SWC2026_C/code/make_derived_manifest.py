# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# -*- coding: utf-8 -*-
"""Write data/derived_manifest.json: sha256, bytes and mtime for every result ledger."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
OUT = DATA / "derived_manifest.json"
SKIP = {OUT.name}

files = {}
for p in sorted(DATA.glob("*.json")):
    if p.name in SKIP:
        continue
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    st = p.stat()
    files[p.name] = {
        "bytes": st.st_size,
        "sha256": h.hexdigest(),
        "mtime_utc": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(timespec="seconds"),
    }

payload = {
    "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "note": "Every JSON result ledger in data/. Values printed by the paper are traced to these files through code/fill_numbers.py.",
    "n_files": len(files),
    "total_bytes": sum(v["bytes"] for v in files.values()),
    "files": files,
}
OUT.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"wrote {OUT} ({len(files)} files, {payload['total_bytes']} bytes)")
