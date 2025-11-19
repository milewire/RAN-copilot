"""
Backhaul analyzer for RAN-Copilot.

Parses microwave/fiber backhaul CSV logs and produces:
- time series for modulation, RSSI, latency/jitter
- aggregate error statistics
- a simple impairment score used by the RCA engine.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List
import csv
import io


@dataclass
class BackhaulSample:
    timestamp: str
    modulation: float
    rssi: float
    latency_ms: float
    jitter_ms: float
    tx_errors: float
    rx_errors: float


def _modulation_to_order(raw: str) -> float:
    """
    Map textual modulation schemes (e.g. 'QPSK', '64QAM') to an ordinal value.
    Falls back to float(raw) when possible, otherwise 0.0.
    """
    if raw is None:
        return 0.0
    s = str(raw).strip().upper()
    if not s:
        return 0.0

    # Common microwave / LTE modulations
    mapping = {
        "QPSK": 2.0,
        "4QAM": 2.0,
        "16QAM": 4.0,
        "32QAM": 5.0,
        "64QAM": 6.0,
        "128QAM": 7.0,
        "256QAM": 8.0,
    }
    if s in mapping:
        return mapping[s]

    # Try to strip trailing 'QAM' and parse numeric order
    if s.endswith("QAM"):
        prefix = s[:-3]
        try:
            order = float(prefix)
            # Map constellation size N-QAM to an approximate order metric
            return max(1.0, order / 16.0)
        except ValueError:
            pass

    try:
        return float(s)
    except ValueError:
        return 0.0


def parse_backhaul_csv(content: bytes) -> List[BackhaulSample]:
    """
    Parse a backhaul CSV file with at least:
    - timestamp
    - modulation
    - RSSI
    - latency/jitter
    - TX/RX errors
    """
    text = content.decode(errors="ignore")
    reader = csv.DictReader(io.StringIO(text))

    samples: List[BackhaulSample] = []

    def norm(name: str) -> str:
        return name.strip().lower().replace(" ", "").replace("_", "")

    for row in reader:
        if not row:
            continue
        cols = {norm(k): v for k, v in row.items()}

        ts = cols.get("timestamp") or cols.get("time") or ""
        modulation_raw = cols.get("modulation", "") or ""
        modulation = _modulation_to_order(modulation_raw)

        def to_float(key: str, *aliases: str) -> float:
            for k in (key, *aliases):
                if k in cols and cols[k] not in (None, ""):
                    try:
                        return float(str(cols[k]).strip())
                    except ValueError:
                        return 0.0
            return 0.0

        rssi = to_float("rssi")
        latency = to_float("latency", "latencyms")
        jitter = to_float("jitter", "jitterms")
        tx_err = to_float("txerrors", "tx_err")
        rx_err = to_float("rxerrors", "rx_err")

        if not ts:
            ts = datetime.utcnow().isoformat()

        samples.append(
            BackhaulSample(
                timestamp=ts,
                modulation=modulation,
                rssi=rssi,
                latency_ms=latency,
                jitter_ms=jitter,
                tx_errors=tx_err,
                rx_errors=rx_err,
            )
        )

    return samples


def summarize_backhaul(samples: List[BackhaulSample]) -> Dict[str, Any]:
    """
    Build summary statistics and a heuristic "impairment_score" between 0 and 1.
    """
    if not samples:
        return {
            "total_samples": 0,
            "impairment_score": 0.0,
            "modulation_trend": [],
            "rssi_trend": [],
            "latency_jitter_trend": [],
            "error_summary": {"tx_errors": 0.0, "rx_errors": 0.0},
        }

    modulation_trend = []
    rssi_trend = []
    latency_jitter_trend = []
    total_tx_err = 0.0
    total_rx_err = 0.0

    low_mod_count = 0
    high_latency_count = 0
    high_jitter_count = 0

    for s in samples:
        modulation_trend.append({"timestamp": s.timestamp, "modulation": s.modulation})
        rssi_trend.append({"timestamp": s.timestamp, "rssi": s.rssi})
        latency_jitter_trend.append(
            {"timestamp": s.timestamp, "latency_ms": s.latency_ms, "jitter_ms": s.jitter_ms}
        )

        total_tx_err += s.tx_errors
        total_rx_err += s.rx_errors

        if s.modulation < 4:  # heuristic: low modulation order indicates impairment
            low_mod_count += 1
        if s.latency_ms > 50:
            high_latency_count += 1
        if s.jitter_ms > 20:
            high_jitter_count += 1

    n = float(len(samples))
    impairment_score = min(
        1.0,
        (low_mod_count / n) * 0.4
        + (high_latency_count / n) * 0.3
        + (high_jitter_count / n) * 0.3,
    )

    return {
        "total_samples": len(samples),
        "impairment_score": impairment_score,
        "modulation_trend": modulation_trend,
        "rssi_trend": rssi_trend,
        "latency_jitter_trend": latency_jitter_trend,
        "error_summary": {
            "tx_errors": total_tx_err,
            "rx_errors": total_rx_err,
        },
    }


