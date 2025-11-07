"""
AI Feature A - GPT-Based RCA Summary
Generates human-readable summaries of RCA results using local or remote LLM.
"""
import os
from typing import Dict, Any, List, Optional


def generate_ai_summary(
    kpi_data: List[Dict[str, Any]],
    rca_result: Dict[str, Any],
    anomalies: Dict[str, Any],
    drift: Dict[str, Any],
    use_local: bool = True
) -> str:
    """
    Generate an AI-powered summary of RCA analysis results.
    
    Args:
        kpi_data: List of KPI measurements
        rca_result: Deterministic RCA results
        anomalies: Anomaly detection results
        drift: Parameter drift detection results
        use_local: Use local LLM (default) or remote GPT
    
    Returns:
        Human-readable summary string
    """
    # Check if cloud is allowed
    allow_cloud = os.getenv("ALLOW_CLOUD", "0") == "1"
    
    if not use_local and allow_cloud:
        return _generate_remote_summary(kpi_data, rca_result, anomalies, drift)
    else:
        return _generate_local_summary(kpi_data, rca_result, anomalies, drift)


def _generate_local_summary(
    kpi_data: List[Dict[str, Any]],
    rca_result: Dict[str, Any],
    anomalies: Dict[str, Any],
    drift: Dict[str, Any]
) -> str:
    """
    Generate summary using local template-based approach (no external LLM).
    This provides a structured, human-readable summary without requiring cloud services.
    """
    root_cause = rca_result.get("root_cause", "Unknown")
    severity = rca_result.get("severity", "low")
    evidence = rca_result.get("evidence", {})
    recommendations = rca_result.get("recommendations", [])
    
    # Build summary
    summary_parts = []
    
    # Header
    summary_parts.append(f"## Root Cause Analysis Summary")
    summary_parts.append(f"\n**Primary Issue:** {root_cause}")
    summary_parts.append(f"**Severity Level:** {severity.upper()}")
    
    # Evidence summary
    if evidence:
        summary_parts.append(f"\n### Key Performance Indicators")
        for kpi, stats in list(evidence.items())[:5]:  # Top 5 KPIs
            mean_val = stats.get("mean", 0)
            summary_parts.append(f"- **{kpi}**: Average value {mean_val:.2f}")
    
    # Anomaly summary
    if anomalies.get("flags"):
        anomaly_count = sum(anomalies.get("flags", []))
        if anomaly_count > 0:
            summary_parts.append(f"\n### Anomaly Detection")
            summary_parts.append(f"- **{anomaly_count}** anomalous time periods detected")
            max_score = max(anomalies.get("scores", [0]), default=0)
            summary_parts.append(f"- Maximum anomaly score: {max_score:.2f}")
    
    # Drift summary
    if drift.get("drift_score", 0) > 0.3:
        drift_score = drift.get("drift_score", 0)
        summary_parts.append(f"\n### Parameter Drift Detection")
        summary_parts.append(f"- Drift score: {drift_score:.2f} (threshold: 0.3)")
        params = drift.get("parameters_of_interest", [])
        if params:
            summary_parts.append(f"- Parameters showing drift: {', '.join(params[:3])}")
    
    # Recommendations
    if recommendations:
        summary_parts.append(f"\n### Recommended Actions")
        for i, rec in enumerate(recommendations[:5], 1):  # Top 5 recommendations
            summary_parts.append(f"{i}. {rec}")
    
    # Conclusion
    summary_parts.append(f"\n### Analysis Conclusion")
    if severity == "high":
        summary_parts.append("Immediate attention required. Critical performance issues detected.")
    elif severity == "medium":
        summary_parts.append("Moderate performance degradation observed. Monitoring recommended.")
    else:
        summary_parts.append("System operating within normal parameters with minor observations.")
    
    return "\n".join(summary_parts)


def _generate_remote_summary(
    kpi_data: List[Dict[str, Any]],
    rca_result: Dict[str, Any],
    anomalies: Dict[str, Any],
    drift: Dict[str, Any]
) -> str:
    """
    Generate summary using remote GPT API (only if ALLOW_CLOUD=1).
    For now, falls back to local summary as cloud integration requires API keys.
    """
    # In production, this would call OpenAI API or similar
    # For now, use local summary
    return _generate_local_summary(kpi_data, rca_result, anomalies, drift)

