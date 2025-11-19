"""
KPI analyzer for RAN-Copilot.

Extracts KPI statistics and threshold-based anomalies from parsed PM data.
This module generalizes the KPI aggregation logic originally implemented
in the RCA engine so that it can be reused by the multi-signal RCA engine.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Tuple
import statistics

# Local copy of KPI thresholds to avoid circular import with engine.rca
THRESHOLDS: Dict[str, Dict[str, Any]] = {
    "RRC_Setup_Success_Rate": {"min": 95.0, "unit": "%"},
    "ERAB_Setup_Success_Rate": {"min": 98.0, "unit": "%"},
    "PRB_Utilization_Avg": {"max": 70.0, "unit": "%"},
    "PRB_Utilization_P95": {"max": 85.0, "unit": "%"},
    "SINR_Avg": {"min": 5.0, "unit": "dB"},
    "SINR_P10": {"min": 0.0, "unit": "dB"},
    "BLER_P95": {"max": 10.0, "unit": "%"},
    "Paging_Success_Rate": {"min": 95.0, "unit": "%"},
    "S1_Setup_Failure_Rate": {"max": 1.0, "unit": "%"},
    "Cell_Availability": {"min": 99.0, "unit": "%"},
}


def summarize_kpis(kpi_data: List[Dict[str, Any]]) -> Tuple[Dict[str, Dict[str, float]], List[Dict[str, Any]], Dict[str, Dict[str, List[float]]]]:
    """
    Build KPI evidence, anomalies, and per-site grouping from raw KPI samples.

    Returns:
        evidence: per-KPI statistics (mean/min/max/median/stdev/count)
        anomalies: list of threshold violations with severities
        kpi_by_site: nested dict site -> kpi -> list[values]
    """
    kpi_by_name = defaultdict(list)
    kpi_by_site = defaultdict(lambda: defaultdict(list))

    for entry in kpi_data:
        kpi_name = entry.get("kpi")
        site = entry.get("site", "UNKNOWN")
        value = entry.get("value")

        if kpi_name is None or value is None:
            continue

        kpi_by_name[kpi_name].append(value)
        kpi_by_site[site][kpi_name].append(value)

    evidence: Dict[str, Dict[str, float]] = {}
    anomalies: List[Dict[str, Any]] = []

    for kpi_name, values in kpi_by_name.items():
        if not values:
            continue

        stats = {
            "mean": statistics.mean(values),
            "min": min(values),
            "max": max(values),
            "count": len(values),
        }

        if len(values) > 1:
            try:
                stats["median"] = statistics.median(values)
                stats["stdev"] = statistics.stdev(values) if len(values) > 1 else 0.0
            except Exception:
                stats["median"] = stats["mean"]
                stats["stdev"] = 0.0

        evidence[kpi_name] = stats

        # Threshold-based anomalies
        threshold = THRESHOLDS.get(kpi_name)
        if not threshold:
            continue

        if "min" in threshold:
            if stats["mean"] < threshold["min"]:
                anomalies.append(
                    {
                        "kpi": kpi_name,
                        "type": "below_threshold",
                        "value": stats["mean"],
                        "threshold": threshold["min"],
                        "severity": "high"
                        if stats["mean"] < threshold["min"] * 0.8
                        else "medium",
                    }
                )

        if "max" in threshold:
            if stats["mean"] > threshold["max"]:
                anomalies.append(
                    {
                        "kpi": kpi_name,
                        "type": "above_threshold",
                        "value": stats["mean"],
                        "threshold": threshold["max"],
                        "severity": "high"
                        if stats["mean"] > threshold["max"] * 1.2
                        else "medium",
                    }
                )

    return evidence, anomalies, kpi_by_site


