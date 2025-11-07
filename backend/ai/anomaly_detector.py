"""
AI Feature B - Anomaly Detection Model
Uses IsolationForest to detect unexpected behavior from PM counter patterns.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from sklearn.ensemble import IsolationForest


def detect_anomalies(kpi_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Detect anomalies in KPI data using IsolationForest.
    
    Args:
        kpi_df: DataFrame with columns: timestamp, site, kpi, value
                Should be aggregated by hour for best results
    
    Returns:
        Dictionary with:
        - scores: List of anomaly scores (lower = more anomalous)
        - flags: List of boolean flags (True = anomaly detected)
        - anomaly_count: Total number of anomalies
        - anomaly_periods: List of timestamps with anomalies
    """
    if kpi_df.empty:
        return {
            "scores": [],
            "flags": [],
            "anomaly_count": 0,
            "anomaly_periods": []
        }
    
    # Pivot data to have KPIs as columns, timestamps as rows
    try:
        # Group by timestamp and pivot
        pivot_df = kpi_df.pivot_table(
            index='timestamp',
            columns='kpi',
            values='value',
            aggfunc='mean'
        ).fillna(0)
        
        if pivot_df.empty or len(pivot_df) < 2:
            return {
                "scores": [0.0] * len(kpi_df),
                "flags": [False] * len(kpi_df),
                "anomaly_count": 0,
                "anomaly_periods": []
            }
        
        # Prepare features for IsolationForest
        X = pivot_df.values
        
        # Train IsolationForest
        # contamination: expected proportion of anomalies (auto-detect)
        iso_forest = IsolationForest(
            contamination=0.1,  # Expect ~10% anomalies
            random_state=42,
            n_estimators=100
        )
        
        # Fit and predict
        anomaly_flags = iso_forest.fit_predict(X)
        anomaly_scores = iso_forest.score_samples(X)
        
        # Convert to boolean flags (-1 = anomaly, 1 = normal)
        flags = (anomaly_flags == -1).tolist()
        
        # Normalize scores (lower scores = more anomalous)
        # IsolationForest returns negative scores for anomalies
        normalized_scores = [-score for score in anomaly_scores]
        
        # Get anomaly periods
        anomaly_periods = pivot_df.index[flags].tolist() if isinstance(pivot_df.index, pd.Index) else []
        
        return {
            "scores": normalized_scores,
            "flags": flags,
            "anomaly_count": sum(flags),
            "anomaly_periods": [str(ts) for ts in anomaly_periods]
        }
    
    except Exception as e:
        # Fallback: simple statistical outlier detection
        return _simple_anomaly_detection(kpi_df)


def _simple_anomaly_detection(kpi_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Fallback anomaly detection using statistical methods (Z-score).
    """
    if kpi_df.empty:
        return {
            "scores": [],
            "flags": [],
            "anomaly_count": 0,
            "anomaly_periods": []
        }
    
    flags = []
    scores = []
    
    # Group by KPI and detect outliers
    for kpi in kpi_df['kpi'].unique():
        kpi_subset = kpi_df[kpi_df['kpi'] == kpi]['value']
        if len(kpi_subset) < 3:
            continue
        
        mean = kpi_subset.mean()
        std = kpi_subset.std()
        
        if std == 0:
            continue
        
        # Z-score > 3 or < -3 is considered anomaly
        z_scores = np.abs((kpi_subset - mean) / std)
        kpi_flags = (z_scores > 3).tolist()
        kpi_scores = z_scores.tolist()
        
        # Map back to original dataframe indices
        kpi_indices = kpi_df[kpi_df['kpi'] == kpi].index
        for idx, flag, score in zip(kpi_indices, kpi_flags, kpi_scores):
            if idx < len(flags):
                flags[idx] = flags[idx] or flag
                scores[idx] = max(scores[idx], score)
            else:
                flags.append(flag)
                scores.append(score)
    
    # Fill remaining indices
    while len(flags) < len(kpi_df):
        flags.append(False)
        scores.append(0.0)
    
    return {
        "scores": scores[:len(kpi_df)],
        "flags": flags[:len(kpi_df)],
        "anomaly_count": sum(flags),
        "anomaly_periods": []
    }


def prepare_hourly_data(kpi_data: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Convert KPI data list to hourly aggregated DataFrame.
    
    Args:
        kpi_data: List of KPI measurements
    
    Returns:
        DataFrame with hourly aggregated KPIs
    """
    if not kpi_data:
        return pd.DataFrame()
    
    df = pd.DataFrame(kpi_data)
    
    # Convert timestamp to datetime if needed
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        # Round to nearest hour
        df['timestamp'] = df['timestamp'].dt.floor('H')
    
    return df

