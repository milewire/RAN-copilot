"""
KPI analyzer wrapper.

Re-exports the KPI summarization logic from the existing `engine.kpi_analyzer`
module so other backend components can depend on `backend.analyzers`.
"""

from typing import Any, Dict, List, Tuple

from engine.kpi_analyzer import summarize_kpis  # type: ignore

__all__ = ["summarize_kpis"]


def analyze_kpis(kpi_data: List[Dict[str, Any]]) -> Tuple[Dict[str, Dict[str, float]], List[Dict[str, Any]], Dict[str, Dict[str, List[float]]]]:
    """
    Thin wrapper to keep a stable facade within `backend.analyzers`.
    """
    return summarize_kpis(kpi_data)


