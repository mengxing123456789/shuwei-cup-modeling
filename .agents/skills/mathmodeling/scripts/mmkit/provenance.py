"""Shared data-access layer for the APMCM 2025 Problem C study.

Design rules
------------
1. Every number used in the paper must come from an official API and carry a
   provenance record (URL, fetch time, SHA-256 of the raw response).
2. Responses are cached on disk keyed by URL, so reruns are free and stable.
3. Failures are logged, never silently replaced by invented values.

Sources: UN Comtrade (trade), FRED (US macro), U.S. Treasury Fiscal Data
(customs duties), World Bank (macro aggregates).
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = DATA / "cache"
FIG = ROOT / "figures"
for p in (DATA, CACHE, FIG):
    p.mkdir(parents=True, exist_ok=True)

UA = "APMCM-2025C-academic-model/1.0 (reproducible research)"


@dataclass
class Provenance:
    source: str
    url: str
    indicator: str
    period: str
    n_records: int
    sha256: str
    fetched_at: str
    cached: bool = False

    def as_row(self) -> dict:
        return asdict(self)


class Ledger:
    def __init__(self) -> None:
        self.rows: list[Provenance] = []

    def add(self, source: str, url: str, indicator: str, period: str,
            n: int, digest: str, cached: bool) -> None:
        self.rows.append(Provenance(
            source=source, url=url, indicator=indicator, period=period,
            n_records=n, sha256=digest,
            fetched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            cached=cached))

    def save(self, path: Path | None = None, merge: bool = False) -> Path:
        """Write the ledger.

        merge=True appends to an existing ledger instead of replacing it.
        Without it a partial re-run (e.g. fetching only one dataset) silently
        destroys the provenance records of every other source -- the file is
        the audit trail for the whole paper, so this must be opt-in per call.
        """
        path = path or DATA / "ledger.json"
        rows = list(self.rows)
        if merge and path.exists():
            try:
                prev = json.loads(path.read_text(encoding="utf-8"))
                seen = {(r.url, r.period, r.indicator) for r in rows}
                for s in prev.get("sources", []):
                    key = (s["url"], s["period"], s["indicator"])
                    if key not in seen:
                        rows.append(Provenance(**s))
                        seen.add(key)
            except (json.JSONDecodeError, KeyError, TypeError):
                pass        # corrupt/legacy file: keep only what we have
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "n_sources": len(rows),
            "n_records": sum(r.n_records for r in rows),
            "sources": [r.as_row() for r in rows],
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path


def _cache_path(url: str) -> Path:
    return CACHE / (hashlib.sha256(url.encode()).hexdigest()[:20] + ".bin")


def get(url: str, retries: int = 5, timeout: int = 60,
        pause: float = 2.2) -> tuple[bytes, str, bool]:
    """Cached GET. Returns (body, sha256, was_cached). Retries 429/5xx."""
    p = _cache_path(url)
    if p.exists():
        body = p.read_bytes()
        return body, hashlib.sha256(body).hexdigest(), True
    last = None
    for attempt in range(retries):
        try:
            # requests/urllib3 is markedly more robust than urllib through the
            # local HTTP proxy on this machine (urllib occasionally stalls on
            # FRED TLS reads while curl/requests succeed).
            try:
                import requests
                r = requests.get(url, headers={"User-Agent": UA},
                                 timeout=timeout)
                r.raise_for_status()
                body = r.content
            except ImportError:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    body = r.read()
            p.write_bytes(body)
            time.sleep(pause)
            return body, hashlib.sha256(body).hexdigest(), False
        except Exception as e:  # noqa: BLE001
            last = e
            code = getattr(e, "code", 0)
            wait = 4.0 * (attempt + 1) if code == 429 else 1.5 * (attempt + 1)
            time.sleep(wait)
    raise RuntimeError(f"GET failed: {url[:140]} ({last})")


def get_json(url: str, **kw) -> tuple[object, str, bool]:
    body, digest, cached = get(url, **kw)
    return json.loads(body), digest, cached


# ---------------------------------------------------------------------------
# UN Comtrade
# ---------------------------------------------------------------------------
COMTRADE = "https://comtradeapi.un.org/public/v1/preview/C/{freq}/HS"

M49 = {"USA": 842, "CHN": 156, "BRA": 76, "ARG": 32, "JPN": 392,
       "DEU": 276, "MEX": 484, "CAN": 124, "KOR": 410, "TWN": 490,
       "MYS": 458, "VNM": 704, "WORLD": 0}


def comtrade(reporter: int | list[int], period: str | int,
             partners: list[int], cmds: list[str], flow: str,
             freq: str = "C", ledger: Ledger | None = None,
             tag: str = "") -> list[dict]:
    """One annual/monthly Comtrade query. Lists are comma-joined (verified)."""
    def _csv(x):
        return ",".join(str(v) for v in (x if isinstance(x, list) else [x]))

    url = (COMTRADE.format(freq="A" if freq == "A" else "M")
           + "?" + urllib.parse.urlencode({
               "reporterCode": _csv(reporter), "period": str(period),
               "partnerCode": _csv(partners), "cmdCode": _csv(cmds),
               "flowCode": flow}))
    data, digest, cached = get_json(url, pause=2.4)
    rows = data.get("data", []) if isinstance(data, dict) else []
    if ledger is not None:
        ledger.add("UN Comtrade", url, f"{tag} flow={flow} cmd={_csv(cmds)}",
                   str(period), len(rows), digest, cached)
    out = []
    for r in rows:
        out.append({
            "freq": freq, "period": str(r.get("period")),
            "reporter": r.get("reporterCode"), "partner": r.get("partnerCode"),
            "cmd": r.get("cmdCode"), "flow": r.get("flowCode"),
            "value_usd": r.get("primaryValue"),
            "net_wgt_kg": r.get("netWgt"),
            "qty": r.get("qty"), "qty_unit": r.get("qtyUnitCode"),
            "cif_usd": r.get("cifvalue"), "fob_usd": r.get("fobvalue"),
        })
    return out


# ---------------------------------------------------------------------------
# FRED (CSV endpoint, no API key)
# ---------------------------------------------------------------------------
def fred(series: str, ledger: Ledger | None = None) -> dict[str, float]:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
    local = DATA / "fred" / f"{series}.csv"
    if local.exists():
        body, digest, cached = local.read_bytes(), hashlib.sha256(local.read_bytes()).hexdigest(), True
    else:
        body, digest, cached = get(url, pause=0.8)
    text = body.decode("utf-8", "replace")
    reader = csv.reader(io.StringIO(text))
    header = next(reader)
    out: dict[str, float] = {}
    for row in reader:
        if len(row) < 2 or not row[1].strip() or row[1] in (".", "NA"):
            continue
        try:
            out[row[0]] = float(row[1])
        except ValueError:
            continue
    if ledger is not None:
        ledger.add("FRED", url, series, f"{min(out)}..{max(out)}" if out else "",
                   len(out), digest, cached)
    return out


# ---------------------------------------------------------------------------
# U.S. Treasury Monthly Treasury Statement: Customs Duties
# ---------------------------------------------------------------------------
def treasury_customs(ledger: Ledger | None = None) -> list[dict]:
    base = ("https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
            "/v1/accounting/mts/mts_table_9")
    params = {"filter": "classification_desc:eq:Customs Duties",
              "page[size]": "10000", "sort": "record_date"}
    url = base + "?" + urllib.parse.urlencode(params)
    data, digest, cached = get_json(url, pause=1.0)
    rows = data.get("data", []) if isinstance(data, dict) else []
    out = []
    for r in rows:
        try:
            amt = float(r.get("current_month_rcpt_outly_amt") or "nan")
        except ValueError:
            continue
        out.append({"date": r.get("record_date"), "amount_usd": amt,
                    "fiscal_year": r.get("record_fiscal_year")})
    if ledger is not None:
        ledger.add("U.S. Treasury Fiscal Data (MTS Table 9)", url,
                   "Customs Duties, monthly", "2015-2026", len(out), digest, cached)
    return out


# ---------------------------------------------------------------------------
# World Bank
# ---------------------------------------------------------------------------
def worldbank(indicator: str, countries: list[str], period: str,
              ledger: Ledger | None = None,
              label: str = "") -> list[dict]:
    url = ("https://api.worldbank.org/v2/country/" + ";".join(countries)
           + f"/indicator/{indicator}?format=json&date={period}&per_page=1000")
    data, digest, cached = get_json(url, pause=1.0)
    rows = data[1] if isinstance(data, list) and len(data) > 1 else []
    out = [{"country": r["country"]["id"], "year": r["date"],
            "value": r["value"]} for r in rows if r.get("value") is not None]
    if ledger is not None:
        ledger.add("World Bank Open Data", url, label or indicator, period,
                   len(out), digest, cached)
    return out


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = fields or list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def save_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def pct(x: float, nd: int = 1) -> str:
    return f"{100 * x:.{nd}f}\\%"