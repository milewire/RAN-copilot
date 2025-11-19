"""
Alarm analyzer for RAN-Copilot.

Parses ENM/FM alarm logs from XML, CSV, or plain-text formats and produces:
- normalized alarm records
- summary statistics (by severity, site/MO, alarm type, time bucket)

This module is intentionally tolerant of multiple Ericsson FM export formats.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import csv
import io
import re
import xml.etree.ElementTree as ET


SEVERITY_ORDER = ["CRITICAL", "MAJOR", "MINOR", "WARNING", "INDETERMINATE", "CLEARED", "INFO"]


@dataclass
class AlarmRecord:
    timestamp: str
    severity: str
    alarm_type: str
    mo: str
    alarm_id: str
    additional_text: str


def _normalise_severity(value: str) -> str:
    if not value:
        return "INDETERMINATE"
    v = value.strip().upper()
    # Common Ericsson severities
    mapping = {
        "CRIT": "CRITICAL",
        "MAJ": "MAJOR",
        "MIN": "MINOR",
        "WARN": "WARNING",
        "INDET": "INDETERMINATE",
        "CLEARED": "CLEARED",
        "CLEAR": "CLEARED",
        "INFO": "INFO",
    }
    return mapping.get(v, v)


def _parse_timestamp(value: str) -> str:
    if not value:
        return datetime.utcnow().isoformat()
    value = value.strip()
    # Strip trailing Z
    if value.endswith("Z"):
        value = value[:-1]
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).isoformat()
        except ValueError:
            continue
    # Fallback: return as-is
    return datetime.utcnow().isoformat()


def parse_alarm_file(content: bytes, filename: str) -> List[AlarmRecord]:
    """
    Parse an alarm file (XML, CSV, or text) into normalized AlarmRecord objects.
    """
    name = filename.lower()
    if name.endswith(".xml"):
        return _parse_alarm_xml(content)
    if name.endswith(".csv"):
        return _parse_alarm_csv(content)
    # Fallback: treat as text log
    return _parse_alarm_text(content.decode(errors="ignore"))


def _parse_alarm_xml(content: bytes) -> List[AlarmRecord]:
    records: List[AlarmRecord] = []
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return records

    # Ericsson FM exports often use "alarm" or "notification" elements
    for elem in root.iter():
        tag = elem.tag.split("}")[-1]
        if tag not in {"alarm", "notification", "fault"}:
            continue

        # Try common field names
        severity = (
            _get_text(elem, "perceivedSeverity")
            or _get_text(elem, "severity")
            or _get_text(elem, "severityText")
        )
        alarm_type = (
            _get_text(elem, "alarmType")
            or _get_text(elem, "probableCause")
            or _get_text(elem, "specificProblem")
        )
        mo = (
            _get_text(elem, "managedObject")
            or _get_text(elem, "managedObjectInstance")
            or _get_text(elem, "objectOfReference")
            or _get_attr(elem, "mo")
        )
        timestamp = (
            _get_text(elem, "eventTime")
            or _get_text(elem, "raisedTime")
            or _get_text(elem, "time")
        )
        alarm_id = (
            _get_text(elem, "alarmId")
            or _get_text(elem, "notificationId")
            or _get_attr(elem, "id")
        )
        additional_text = (
            _get_text(elem, "additionalText")
            or _get_text(elem, "additionalInformation")
            or _get_text(elem, "description")
        )

        rec = AlarmRecord(
            timestamp=_parse_timestamp(timestamp),
            severity=_normalise_severity(severity or ""),
            alarm_type=(alarm_type or "UNKNOWN"),
            mo=(mo or "UNKNOWN"),
            alarm_id=(alarm_id or ""),
            additional_text=(additional_text or ""),
        )
        records.append(rec)

    return records


def _parse_alarm_csv(content: bytes) -> List[AlarmRecord]:
    records: List[AlarmRecord] = []
    text = content.decode(errors="ignore")
    reader = csv.DictReader(io.StringIO(text))

    # Normalise column names
    def norm(s: str) -> str:
        return s.strip().lower().replace(" ", "").replace("_", "")

    for row in reader:
        if not row:
            continue

        cols = {norm(k): v for k, v in row.items()}

        severity = cols.get("severity") or cols.get("perceivedseverity") or ""
        alarm_type = cols.get("alarmtype") or cols.get("alarmclass") or cols.get("probablecause") or ""
        mo = cols.get("mo") or cols.get("managedobject") or cols.get("objectofreference") or ""
        timestamp = cols.get("timestamp") or cols.get("eventtime") or cols.get("raisedtime") or ""
        alarm_id = cols.get("alarmid") or cols.get("notificationid") or ""
        additional_text = cols.get("additionaltext") or cols.get("additionalinformation") or cols.get("description") or ""

        records.append(
            AlarmRecord(
                timestamp=_parse_timestamp(timestamp),
                severity=_normalise_severity(severity),
                alarm_type=alarm_type or "UNKNOWN",
                mo=mo or "UNKNOWN",
                alarm_id=alarm_id or "",
                additional_text=additional_text or "",
            )
        )

    return records


def _parse_alarm_text(text: str) -> List[AlarmRecord]:
    """
    Very tolerant line-based parser for pasted log snippets.
    Expects one alarm per line, tries to extract severity, timestamp, MO, and description.
    """
    records: List[AlarmRecord] = []
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    # Example patterns:
    # 2025-01-01 12:00:00 CRITICAL ERBS-41001/Cell-1 ALARM_ID=1234 Text...
    pattern = re.compile(
        r"^(?P<ts>\d{4}[-/]\d{2}[-/]\d{2}[ T]\d{2}:\d{2}:\d{2})\s+"
        r"(?P<sev>\w+)\s+"
        r"(?P<mo>\S+)\s+"
        r"(?P<rest>.+)$"
    )

    for line in lines:
        m = pattern.match(line)
        if not m:
            # If we cannot match, treat whole line as description
            records.append(
                AlarmRecord(
                    timestamp=datetime.utcnow().isoformat(),
                    severity="INDETERMINATE",
                    alarm_type="TEXT_LOG",
                    mo="UNKNOWN",
                    alarm_id="",
                    additional_text=line,
                )
            )
            continue

        ts = m.group("ts")
        sev = m.group("sev")
        mo = m.group("mo")
        rest = m.group("rest")

        # Try to extract an alarm ID token
        alarm_id_match = re.search(r"(ALARM_ID|alarmId|id)=(\S+)", rest, re.IGNORECASE)
        alarm_id = alarm_id_match.group(2) if alarm_id_match else ""

        records.append(
            AlarmRecord(
                timestamp=_parse_timestamp(ts),
                severity=_normalise_severity(sev),
                alarm_type="TEXT_LOG",
                mo=mo,
                alarm_id=alarm_id,
                additional_text=rest,
            )
        )

    return records


def _get_text(elem: ET.Element, tag: str) -> Optional[str]:
    child = elem.find(f".//{tag}")
    if child is not None and child.text:
        return child.text.strip()
    return None


def _get_attr(elem: ET.Element, attr: str) -> Optional[str]:
    return elem.attrib.get(attr)


def summarize_alarms(records: List[AlarmRecord]) -> Dict[str, Any]:
    """
    Build summary statistics used by the Alarms dashboard and RCA engine.
    """
    if not records:
        return {
            "total_count": 0,
            "by_severity": {},
            "by_mo": {},
            "timeline": [],
        }

    by_severity: Dict[str, int] = {}
    by_mo: Dict[str, int] = {}
    timeline: Dict[str, int] = {}

    for rec in records:
        sev = rec.severity or "INDETERMINATE"
        by_severity[sev] = by_severity.get(sev, 0) + 1

        mo = rec.mo or "UNKNOWN"
        by_mo[mo] = by_mo.get(mo, 0) + 1

        # Bucket timeline by hour
        try:
            dt = datetime.fromisoformat(rec.timestamp)
            bucket = dt.replace(minute=0, second=0, microsecond=0).isoformat()
        except Exception:
            bucket = rec.timestamp
        timeline[bucket] = timeline.get(bucket, 0) + 1

    # Order severities
    ordered_severity = {
        sev: by_severity[sev] for sev in SEVERITY_ORDER if sev in by_severity
    }
    # Convert timeline dict to sorted list
    timeline_list = [
        {"timestamp": ts, "count": count}
        for ts, count in sorted(timeline.items(), key=lambda x: x[0])
    ]

    return {
        "total_count": len(records),
        "by_severity": ordered_severity,
        "by_mo": by_mo,
        "timeline": timeline_list,
        "sample": [asdict(r) for r in records[:200]],  # cap for UI
    }


def alarms_to_dicts(records: List[AlarmRecord]) -> List[Dict[str, Any]]:
    """Helper to convert dataclass objects into plain dicts for JSON responses."""
    return [asdict(r) for r in records]


