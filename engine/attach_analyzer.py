"""
Attach log analyzer for RAN-Copilot.

Parses attach/ERAB logs (typically CSV) and produces:
- per-IMSI attach success statistics
- classification of dominant failure categories
- simple trend data.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Tuple
import csv
import io
from collections import defaultdict


@dataclass
class AttachRecord:
    imsi: str
    apn: str
    tac: str
    attach_reject_cause: str
    erab_setup_cause: str
    failure_category: str  # APN_QCI, TAC, RF, Congestion, Other, or SUCCESS


def parse_attach_csv(content: bytes) -> List[AttachRecord]:
    text = content.decode(errors="ignore")
    reader = csv.DictReader(io.StringIO(text))

    def norm(s: str) -> str:
        return s.strip().lower().replace(" ", "").replace("_", "")

    records: List[AttachRecord] = []

    for row in reader:
        if not row:
            continue

        cols = {norm(k): v for k, v in row.items()}

        imsi = cols.get("imsi", "").strip()
        apn = cols.get("apn", "").strip()
        tac = cols.get("tac", "").strip()
        attach_cause = cols.get("attachrejectcause", cols.get("attach_cause", "")).strip()
        erab_cause = cols.get("erabsetupcause", cols.get("erab_cause", "")).strip()
        failure_cat = cols.get("failurecategory", "").strip()

        # Normalize failure category if not explicitly provided
        if not failure_cat:
            failure_cat = classify_failure(attach_cause, erab_cause)

        records.append(
            AttachRecord(
                imsi=imsi or "UNKNOWN",
                apn=apn or "UNKNOWN",
                tac=tac or "UNKNOWN",
                attach_reject_cause=attach_cause,
                erab_setup_cause=erab_cause,
                failure_category=failure_cat,
            )
        )

    return records


def classify_failure(attach_cause: str, erab_cause: str) -> str:
    text = f"{attach_cause} {erab_cause}".lower()
    if not text.strip():
        return "SUCCESS"
    if any(x in text for x in ["apn", "qci", "pdn", "service not subscribed"]):
        return "APN_QCI"
    if any(x in text for x in ["tac", "tracking area", "roaming not allowed"]):
        return "TAC"
    if any(x in text for x in ["radio", "rf", "coverage", "signal", "sinr"]):
        return "RF"
    if any(x in text for x in ["congestion", "resource unavailable", "no resource"]):
        return "Congestion"
    return "Other"


def summarize_attach(records: List[AttachRecord]) -> Dict[str, Any]:
    if not records:
        return {
            "overall_attach_success_rate": None,
            "per_imsi": {},
            "per_apn": {},
            "per_tac": {},
            "failure_categories": {},
            "dominant_failure_category": None,
        }

    per_imsi_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: {"success": 0, "fail": 0})
    per_apn_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: {"success": 0, "fail": 0})
    per_tac_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: {"success": 0, "fail": 0})
    failure_cats: Dict[str, int] = defaultdict(int)

    total = 0
    success = 0

    for rec in records:
        total += 1
        is_success = rec.failure_category == "SUCCESS"
        if is_success:
            success += 1

        key = "success" if is_success else "fail"
        per_imsi_counts[rec.imsi][key] += 1
        per_apn_counts[rec.apn][key] += 1
        per_tac_counts[rec.tac][key] += 1

        if not is_success:
            failure_cats[rec.failure_category] += 1

    overall_rate = (success / total) * 100.0 if total > 0 else None

    def to_rate_dict(counter: Dict[str, Dict[str, int]]) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        for k, val in counter.items():
            total_local = val["success"] + val["fail"]
            rate = (val["success"] / total_local) * 100.0 if total_local > 0 else None
            out[k] = {"success": val["success"], "fail": val["fail"], "success_rate": rate}
        return out

    per_imsi = to_rate_dict(per_imsi_counts)
    per_apn = to_rate_dict(per_apn_counts)
    per_tac = to_rate_dict(per_tac_counts)

    dominant_failure = None
    if failure_cats:
        dominant_failure = max(failure_cats.items(), key=lambda x: x[1])[0]

    return {
        "overall_attach_success_rate": overall_rate,
        "per_imsi": per_imsi,
        "per_apn": per_apn,
        "per_tac": per_tac,
        "failure_categories": dict(failure_cats),
        "dominant_failure_category": dominant_failure,
    }


