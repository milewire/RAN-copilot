"""
Correlation engine for RAN-Copilot.

Provides helper functions to describe relationships between:
- KPI anomalies
- alarm bursts
- backhaul impairments
- attach failures
"""

from __future__ import annotations

from typing import Any, Dict, List


def describe_kpi_backhaul_correlation(
    kpi_anomalies: List[Dict[str, Any]],
    backhaul_summary: Dict[str, Any],
) -> List[str]:
    """
    Produce human-readable correlation statements between KPI anomalies
    and backhaul impairments.
    """
    if not backhaul_summary or backhaul_summary.get("impairment_score", 0) <= 0.2:
        return []

    statements: List[str] = []

    has_bler = any("BLER" in a.get("kpi", "") for a in kpi_anomalies)
    has_erab = any("ERAB" in a.get("kpi", "") for a in kpi_anomalies)

    if has_bler:
        statements.append(
            "Backhaul impairment detected while BLER anomalies are present; "
            "modulation drops and degraded RSSI may be contributing to high BLER."
        )
    if has_erab:
        statements.append(
            "Elevated ERAB setup anomalies coincide with degraded backhaul "
            "conditions; investigate jitter, latency, and error counters on the affected link."
        )
    if not statements:
        statements.append(
            "Backhaul impairment is present; verify whether KPI anomalies align with periods of "
            "low modulation, high latency, or high jitter."
        )

    return statements


def describe_kpi_alarm_correlation(
    kpi_anomalies: List[Dict[str, Any]],
    alarm_summary: Dict[str, Any],
) -> List[str]:
    if not alarm_summary or alarm_summary.get("total_count", 0) == 0:
        return []

    by_sev = alarm_summary.get("by_severity", {})
    crit_maj = by_sev.get("CRITICAL", 0) + by_sev.get("MAJOR", 0)
    if crit_maj == 0:
        return []

    return [
        "Critical/major alarms are active during KPI degradation; "
        "check ENM alarm browser for transport, radio, or license alarms on the affected sites."
    ]


def describe_attach_failures_correlation(attach_summary: Dict[str, Any]) -> List[str]:
    if not attach_summary:
        return []

    overall = attach_summary.get("overall_attach_success_rate")
    if overall is None or overall >= 95.0:
        return []

    dominant = attach_summary.get("dominant_failure_category")
    if dominant == "APN_QCI":
        return [
            "Attach failures are dominated by APN/QCI-related causes; "
            "verify APN provisioning, QCI mappings, and PDN/GGSN configuration for SCADA/CPE devices."
        ]
    if dominant == "TAC":
        return [
            "Attach failures are dominated by TAC-related causes; "
            "review TAC assignments and mobility restrictions for the affected UEs and cells."
        ]
    if dominant == "RF":
        return [
            "Attach failures are dominated by RF-related causes; "
            "check coverage, RSRP/SINR, and interference for the impacted sectors."
        ]
    if dominant == "Congestion":
        return [
            "Attach failures are dominated by congestion-related causes; "
            "correlate attach failures with PRB utilization and throughput peaks."
        ]

    return ["Attach failures are elevated; further drill-down by IMSI, APN, and TAC is recommended."]


__all__ = [
    "describe_kpi_backhaul_correlation",
    "describe_kpi_alarm_correlation",
    "describe_attach_failures_correlation",
]


