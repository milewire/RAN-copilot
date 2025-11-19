"""
Parameter utilities for LTE Band 41/8 RAN-Copilot.

Provides shared thresholds and simple helper functions for analyzers.
"""

from typing import Dict, Any

# Reuse the KPI thresholds from the original RCA engine for convenience.
from engine.rca import THRESHOLDS  # type: ignore


def get_kpi_thresholds() -> Dict[str, Dict[str, Any]]:
    """Return a copy of the KPI threshold dictionary."""
    return dict(THRESHOLDS)


__all__ = ["THRESHOLDS", "get_kpi_thresholds"]


