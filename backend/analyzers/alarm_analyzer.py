"""
Alarm analyzer wrapper.

Re-exports alarm parsing and summarization from `engine.alarm_analyzer`.
"""

from typing import Any, Dict, List

from engine.alarm_analyzer import (  # type: ignore
    parse_alarm_file,
    summarize_alarms,
    alarms_to_dicts,
)

__all__ = ["parse_alarm_file", "summarize_alarms", "alarms_to_dicts"]


