"""
Multi-signal RCA engine for RAN-Copilot.

Combines:
- KPI statistics and anomalies
- Alarm patterns
- Backhaul impairments
- Attach failure profiles

into a single ranked root-cause assessment and recommendation list.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .kpi_analyzer import summarize_kpis
from . import rca as legacy_rca


def analyze_rca(
    kpi_data: List[Dict[str, Any]],
    alarm_summary: Optional[Dict[str, Any]] = None,
    backhaul_summary: Optional[Dict[str, Any]] = None,
    attach_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Modern RCA entry point that combines KPI, alarm, backhaul, and attach signals.

    This function is intentionally backward compatible with the previous
    KPI-only RCA: when no additional summaries are provided it behaves like
    the original engine.
    """
    if not kpi_data:
        return {
            "root_cause": "No Data",
            "severity": "low",
            "evidence": {},
            "anomalies": [],
            "recommendations": ["No KPI data available for analysis"],
        }

    evidence, anomalies, kpi_by_site = summarize_kpis(kpi_data)

    # Start with legacy KPI-based classification
    base_root_cause, base_severity = legacy_rca.determine_root_cause(
        evidence, anomalies, kpi_by_site
    )
    recommendations = legacy_rca.generate_recommendations(
        base_root_cause, evidence, anomalies
    )

    # Enrich with alarms / backhaul / attach signals
    root_cause, severity = _combine_with_additional_signals(
        base_root_cause,
        base_severity,
        anomalies,
        alarm_summary=alarm_summary,
        backhaul_summary=backhaul_summary,
        attach_summary=attach_summary,
    )

    # Add extra recommendations based on additional signals
    recommendations.extend(
        _extra_recommendations(
            alarm_summary=alarm_summary,
            backhaul_summary=backhaul_summary,
            attach_summary=attach_summary,
        )
    )

    # Deduplicate recommendations
    recommendations = sorted(set(recommendations))

    return {
        "root_cause": root_cause,
        "severity": severity,
        "evidence": evidence,
        "anomalies": anomalies,
        "recommendations": recommendations,
    }


def _combine_with_additional_signals(
    base_root_cause: str,
    base_severity: str,
    anomalies: List[Dict[str, Any]],
    alarm_summary: Optional[Dict[str, Any]] = None,
    backhaul_summary: Optional[Dict[str, Any]] = None,
    attach_summary: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str]:
    """
    Heuristic fusion of KPI-based RCA with alarms/backhaul/attach context.
    """
    severity_score = {"low": 1, "medium": 2, "high": 3}.get(base_severity, 1)

    root_cause = base_root_cause

    # Alarm-driven escalations
    if alarm_summary and alarm_summary.get("total_count", 0) > 0:
        by_sev = alarm_summary.get("by_severity", {})
        crit_maj = by_sev.get("CRITICAL", 0) + by_sev.get("MAJOR", 0)
        if crit_maj > 0:
            # If there are transport/timing KPI anomalies, strongly bias toward a transport fault
            if any(a["kpi"] in ("S1_Setup_Failure_Rate",) for a in anomalies):
                root_cause = "Transport/TIMING Fault (Alarms corroborated)"
                severity_score = max(severity_score, 3)
            else:
                # Generic alarm-driven issue
                if base_root_cause == "Normal Operation":
                    root_cause = "Active Network Alarms"
                else:
                    root_cause = f"{base_root_cause} with Active Alarms"
                severity_score = max(severity_score, 2)

    # Backhaul-driven interpretations (placeholder, will be enriched when backhaul module is added)
    if backhaul_summary and backhaul_summary.get("impairment_score", 0) > 0.5:
        if "Microwave" in base_root_cause or "Transport" in base_root_cause:
            root_cause = "Backhaul Impairment (Microwave/Fiber)"
        elif base_root_cause == "Normal Operation":
            root_cause = "Backhaul Impairment"
        severity_score = max(severity_score, 3)

    # Attach-failure context
    if attach_summary and attach_summary.get("overall_attach_success_rate") is not None:
        success = attach_summary["overall_attach_success_rate"]
        if success < 95.0:
            if attach_summary.get("dominant_failure_category") == "APN_QCI":
                root_cause = "CPE Attach Failures - APN/QCI Configuration"
            elif attach_summary.get("dominant_failure_category") == "TAC":
                root_cause = "CPE Attach Failures - TAC / Mobility Configuration"
            elif attach_summary.get("dominant_failure_category") == "RF":
                root_cause = "CPE Attach Failures - RF / Coverage"
            elif attach_summary.get("dominant_failure_category") == "Congestion":
                root_cause = "CPE Attach Failures - Congestion Driven"
            severity_score = max(severity_score, 3)

    # Map numeric severity score back to label
    severity = "low"
    if severity_score >= 3:
        severity = "high"
    elif severity_score == 2:
        severity = "medium"

    return root_cause, severity


def _extra_recommendations(
    alarm_summary: Optional[Dict[str, Any]] = None,
    backhaul_summary: Optional[Dict[str, Any]] = None,
    attach_summary: Optional[Dict[str, Any]] = None,
) -> List[str]:
    recs: List[str] = []

    if alarm_summary and alarm_summary.get("total_count", 0) > 0:
        recs.append("Review active CRITICAL/MAJOR alarms in ENM for impacted MOs.")
        recs.append("Verify whether alarms coincide with KPI degradation periods.")

    if backhaul_summary and backhaul_summary.get("impairment_score", 0) > 0.5:
        recs.append("Investigate microwave/fiber backhaul modulation drops and high jitter.")
        recs.append("Correlate backhaul RSSI and error counters with BLER and ERAB failures.")

    if attach_summary and attach_summary.get("overall_attach_success_rate") is not None:
        success = attach_summary["overall_attach_success_rate"]
        if success < 95.0:
            recs.append(
                f"Investigate attach failures; overall attach success rate is {success:.1f}%."
            )
            dominant = attach_summary.get("dominant_failure_category")
            if dominant == "APN_QCI":
                recs.append(
                    "Check APN, QCI, and bearer configuration for impacted IMSIs and APNs."
                )
            elif dominant == "TAC":
                recs.append("Verify TAC assignment and mobility configuration for affected cells.")
            elif dominant == "RF":
                recs.append(
                    "Check RF coverage, SINR, and interference around sites with high attach failures."
                )
            elif dominant == "Congestion":
                recs.append(
                    "Correlate attach failures with congestion indicators (PRB utilization, throughput)."
                )

    return recs


