"""
LTE Band 41 Root Cause Analysis Engine
Implements RCA logic for detecting network anomalies and performance issues.
"""
from typing import List, Dict, Any, Optional
from collections import defaultdict
import statistics


# RCA Thresholds (LTE B41 specific)
THRESHOLDS = {
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


def analyze_rca(kpi_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Perform Root Cause Analysis on KPI data.
    
    Args:
        kpi_data: List of KPI measurements from parser
    
    Returns:
        Dictionary with:
        - root_cause: Primary root cause classification
        - severity: low | medium | high
        - evidence: KPI values and statistics
        - anomalies: List of detected anomalies
        - recommendations: List of recommended actions
    """
    if not kpi_data:
        return {
            "root_cause": "No Data",
            "severity": "low",
            "evidence": {},
            "anomalies": [],
            "recommendations": ["No KPI data available for analysis"]
        }
    
    # Group KPIs by name and site
    kpi_by_name = defaultdict(list)
    kpi_by_site = defaultdict(lambda: defaultdict(list))
    
    for entry in kpi_data:
        kpi_name = entry["kpi"]
        site = entry["site"]
        value = entry["value"]
        
        kpi_by_name[kpi_name].append(value)
        kpi_by_site[site][kpi_name].append(value)
    
    # Calculate statistics for each KPI
    evidence = {}
    anomalies = []
    
    for kpi_name, values in kpi_by_name.items():
        if not values:
            continue
        
        stats = {
            "mean": statistics.mean(values),
            "min": min(values),
            "max": max(values),
            "count": len(values)
        }
        
        if len(values) > 1:
            try:
                stats["median"] = statistics.median(values)
                stats["stdev"] = statistics.stdev(values) if len(values) > 1 else 0
            except:
                stats["median"] = stats["mean"]
                stats["stdev"] = 0
        
        evidence[kpi_name] = stats
        
        # Check against thresholds
        threshold = THRESHOLDS.get(kpi_name)
        if threshold:
            if "min" in threshold:
                if stats["mean"] < threshold["min"]:
                    anomalies.append({
                        "kpi": kpi_name,
                        "type": "below_threshold",
                        "value": stats["mean"],
                        "threshold": threshold["min"],
                        "severity": "high" if stats["mean"] < threshold["min"] * 0.8 else "medium"
                    })
            
            if "max" in threshold:
                if stats["mean"] > threshold["max"]:
                    anomalies.append({
                        "kpi": kpi_name,
                        "type": "above_threshold",
                        "value": stats["mean"],
                        "threshold": threshold["max"],
                        "severity": "high" if stats["mean"] > threshold["max"] * 1.2 else "medium"
                    })
    
    # Determine root cause
    root_cause, severity = determine_root_cause(evidence, anomalies, kpi_by_site)
    
    # Generate recommendations
    recommendations = generate_recommendations(root_cause, evidence, anomalies)
    
    return {
        "root_cause": root_cause,
        "severity": severity,
        "evidence": evidence,
        "anomalies": anomalies,
        "recommendations": recommendations
    }


def determine_root_cause(
    evidence: Dict[str, Dict[str, float]],
    anomalies: List[Dict[str, Any]],
    kpi_by_site: Dict[str, Dict[str, List[float]]]
) -> tuple[str, str]:
    """
    Determine primary root cause based on evidence and anomalies.
    
    Returns:
        Tuple of (root_cause, severity)
    """
    if not anomalies:
        return ("Normal Operation", "low")
    
    # Count anomalies by type
    high_severity_count = sum(1 for a in anomalies if a.get("severity") == "high")
    medium_severity_count = sum(1 for a in anomalies if a.get("severity") == "medium")
    
    # Determine overall severity
    if high_severity_count > 0:
        severity = "high"
    elif medium_severity_count > 2:
        severity = "high"
    elif medium_severity_count > 0:
        severity = "medium"
    else:
        severity = "low"
    
    # Root cause classification logic
    rrc_anomaly = any(a["kpi"] == "RRC_Setup_Success_Rate" for a in anomalies)
    erab_anomaly = any(a["kpi"] == "ERAB_Setup_Success_Rate" for a in anomalies)
    s1_anomaly = any(a["kpi"] == "S1_Setup_Failure_Rate" for a in anomalies)
    prb_anomaly = any("PRB" in a["kpi"] for a in anomalies)
    sinr_anomaly = any("SINR" in a["kpi"] for a in anomalies)
    bler_anomaly = any("BLER" in a["kpi"] for a in anomalies)
    paging_anomaly = any("Paging" in a["kpi"] for a in anomalies)
    
    # Transport/TIMING faults
    if s1_anomaly and (rrc_anomaly or erab_anomaly):
        return ("Transport/TIMING Fault", severity)
    
    # Microwave ACM drops
    if s1_anomaly and prb_anomaly:
        return ("Microwave ACM Fade", severity)
    
    # TDD frame misalignment
    if sinr_anomaly and bler_anomaly and not prb_anomaly:
        return ("TDD Frame Misalignment", severity)
    
    # Sector overshoot / interference
    if sinr_anomaly and bler_anomaly and prb_anomaly:
        return ("RF Interference / Sector Overshoot", severity)
    
    # Congestion signatures
    if prb_anomaly and rrc_anomaly and not sinr_anomaly:
        return ("Congestion", severity)
    
    # RF quality degradation
    if sinr_anomaly and bler_anomaly:
        return ("RF Quality Degradation", severity)
    
    # Parameter mismatches
    if rrc_anomaly or erab_anomaly:
        if not s1_anomaly and not prb_anomaly:
            return ("Parameter Mismatch", severity)
    
    # New-site integration issues
    if paging_anomaly and rrc_anomaly:
        return ("New-Site Integration Issue", severity)
    
    # CPE-specific
    if bler_anomaly and not sinr_anomaly:
        return ("CPE-Specific Issue", severity)
    
    # Default classification
    if high_severity_count > 0:
        return ("Multiple Anomalies Detected", severity)
    else:
        return ("Minor Performance Degradation", severity)


def generate_recommendations(
    root_cause: str,
    evidence: Dict[str, Dict[str, float]],
    anomalies: List[Dict[str, Any]]
) -> List[str]:
    """Generate actionable recommendations based on root cause"""
    recommendations = []
    
    if root_cause == "Transport/TIMING Fault":
        recommendations.extend([
            "Check S1 interface connectivity and latency",
            "Verify timing source (GPS/GNSS) synchronization",
            "Review transport network path and QoS settings",
            "Check for packet loss or jitter on backhaul links"
        ])
    
    elif root_cause == "Microwave ACM Fade":
        recommendations.extend([
            "Check microwave link availability and ACM thresholds",
            "Review weather conditions and path clearance",
            "Verify antenna alignment and signal levels",
            "Consider adaptive modulation adjustments"
        ])
    
    elif root_cause == "TDD Frame Misalignment":
        recommendations.extend([
            "Verify TDD frame configuration across sectors",
            "Check timing advance parameters",
            "Review uplink/downlink subframe allocation",
            "Validate synchronization source accuracy"
        ])
    
    elif root_cause == "RF Interference / Sector Overshoot":
        recommendations.extend([
            "Perform RF drive test to identify interference sources",
            "Review antenna tilt and azimuth settings",
            "Check for co-channel interference",
            "Consider power reduction or antenna adjustments"
        ])
    
    elif root_cause == "Congestion":
        recommendations.extend([
            "Review PRB utilization trends and peak hours",
            "Consider capacity expansion or load balancing",
            "Check for traffic offloading opportunities",
            "Review admission control parameters"
        ])
    
    elif root_cause == "RF Quality Degradation":
        recommendations.extend([
            "Perform RF optimization and site survey",
            "Check antenna system integrity",
            "Review power levels and coverage planning",
            "Validate neighbor cell configuration"
        ])
    
    elif root_cause == "Parameter Mismatch":
        recommendations.extend([
            "Review RRC and ERAB configuration parameters",
            "Check for parameter drift or misconfiguration",
            "Validate against network standards",
            "Compare with baseline configuration"
        ])
    
    elif root_cause == "New-Site Integration Issue":
        recommendations.extend([
            "Verify new site integration checklist completion",
            "Check paging configuration and TAC assignment",
            "Review neighbor relations and handover parameters",
            "Validate core network connectivity"
        ])
    
    elif root_cause == "CPE-Specific Issue":
        recommendations.extend([
            "Review CPE firmware versions and capabilities",
            "Check for device-specific issues or limitations",
            "Validate CPE configuration and parameters",
            "Consider CPE replacement or upgrade"
        ])
    
    else:
        recommendations.append("Review all KPI metrics and perform detailed analysis")
        recommendations.append("Check for any recent configuration changes")
        recommendations.append("Monitor trends over next 24 hours")
    
    # Add specific recommendations based on anomalies
    for anomaly in anomalies:
        kpi = anomaly["kpi"]
        if "RRC" in kpi and anomaly.get("severity") == "high":
            recommendations.append("Immediate attention required for RRC setup failures")
        if "ERAB" in kpi and anomaly.get("severity") == "high":
            recommendations.append("Immediate attention required for ERAB setup failures")
        if "S1" in kpi:
            recommendations.append("Investigate S1 interface connectivity issues")
    
    return list(set(recommendations))  # Remove duplicates

