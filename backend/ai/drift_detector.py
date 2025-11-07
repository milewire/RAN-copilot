"""
AI Feature C - Parameter Drift Detection
Detects parameter drift for new site post-integration and daily O&M comparison.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from collections import defaultdict
import os
import json
from pathlib import Path


# Baseline storage path
BASELINE_DIR = Path("baselines")
BASELINE_DIR.mkdir(exist_ok=True)


def detect_drift(
    current_kpis: List[Dict[str, Any]],
    baseline_kpis: Optional[List[Dict[str, Any]]] = None,
    site_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Detect parameter drift between current KPIs and baseline.
    
    Args:
        current_kpis: Current KPI measurements
        baseline_kpis: Baseline KPI measurements (optional, will load from file if not provided)
        site_id: Site identifier for baseline storage
    
    Returns:
        Dictionary with:
        - drift_score: 0.0 to 1.0 (higher = more drift)
        - parameters_of_interest: List of KPIs showing significant drift
        - drift_details: Detailed drift information per KPI
    """
    if not current_kpis:
        return {
            "drift_score": 0.0,
            "parameters_of_interest": [],
            "drift_details": {}
        }
    
    # Load or create baseline
    if baseline_kpis is None and site_id:
        baseline_kpis = load_baseline(site_id)
    
    # If no baseline exists, create one from current data
    if baseline_kpis is None or len(baseline_kpis) == 0:
        if site_id:
            save_baseline(site_id, current_kpis)
        return {
            "drift_score": 0.0,
            "parameters_of_interest": [],
            "drift_details": {},
            "message": "Baseline created from current data"
        }
    
    # Convert to DataFrames for easier comparison
    current_df = pd.DataFrame(current_kpis)
    baseline_df = pd.DataFrame(baseline_kpis)
    
    # Group by KPI and calculate statistics
    current_stats = _calculate_kpi_stats(current_df)
    baseline_stats = _calculate_kpi_stats(baseline_df)
    
    # Compare statistics
    drift_details = {}
    parameters_of_interest = []
    drift_scores = []
    
    all_kpis = set(current_stats.keys()) | set(baseline_stats.keys())
    
    for kpi in all_kpis:
        if kpi not in current_stats or kpi not in baseline_stats:
            continue
        
        curr_mean = current_stats[kpi].get("mean", 0)
        base_mean = baseline_stats[kpi].get("mean", 0)
        curr_std = current_stats[kpi].get("std", 0)
        base_std = baseline_stats[kpi].get("std", 0)
        
        if base_mean == 0:
            continue
        
        # Calculate drift metrics
        mean_drift = abs(curr_mean - base_mean) / (abs(base_mean) + 1e-6)
        std_drift = abs(curr_std - base_std) / (abs(base_std) + 1e-6)
        
        # Combined drift score for this KPI
        kpi_drift = (mean_drift + std_drift) / 2
        
        drift_details[kpi] = {
            "mean_drift": mean_drift,
            "std_drift": std_drift,
            "current_mean": curr_mean,
            "baseline_mean": base_mean,
            "drift_score": kpi_drift
        }
        
        drift_scores.append(kpi_drift)
        
        # Flag significant drift (threshold: 0.2 = 20% change)
        if kpi_drift > 0.2:
            parameters_of_interest.append(kpi)
    
    # Overall drift score (average of all KPI drifts)
    overall_drift = np.mean(drift_scores) if drift_scores else 0.0
    
    return {
        "drift_score": float(overall_drift),
        "parameters_of_interest": parameters_of_interest,
        "drift_details": drift_details
    }


def _calculate_kpi_stats(df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    """Calculate statistics for each KPI."""
    stats = {}
    
    if df.empty or 'kpi' not in df.columns or 'value' not in df.columns:
        return stats
    
    for kpi in df['kpi'].unique():
        kpi_values = df[df['kpi'] == kpi]['value']
        if len(kpi_values) > 0:
            stats[kpi] = {
                "mean": float(kpi_values.mean()),
                "std": float(kpi_values.std()) if len(kpi_values) > 1 else 0.0,
                "min": float(kpi_values.min()),
                "max": float(kpi_values.max()),
                "count": len(kpi_values)
            }
    
    return stats


def save_baseline(site_id: str, kpi_data: List[Dict[str, Any]]) -> None:
    """Save baseline KPI data for a site."""
    baseline_file = BASELINE_DIR / f"{site_id}_baseline.json"
    with open(baseline_file, 'w') as f:
        json.dump(kpi_data, f, indent=2)


def load_baseline(site_id: str) -> Optional[List[Dict[str, Any]]]:
    """Load baseline KPI data for a site."""
    baseline_file = BASELINE_DIR / f"{site_id}_baseline.json"
    if baseline_file.exists():
        with open(baseline_file, 'r') as f:
            return json.load(f)
    return None

