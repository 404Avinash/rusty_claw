"""
audit_logger.py — ArmorIQ x OpenClaw Hackathon
Every policy decision is logged to JSONL. This is the traceability layer.
Judges can see every allowed and blocked action with reasons.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from core.intent_model import IntentObject, PolicyDecision


LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "audit_log.jsonl"


def _ensure_log_dir():
    LOG_DIR.mkdir(exist_ok=True)


def log_decision(intent: IntentObject, decision: PolicyDecision) -> dict:
    """
    Logs a single policy decision to audit_log.jsonl.
    Returns the log entry dict (used for live display).
    """
    _ensure_log_dir()

    entry = {
        "timestamp": datetime.now().isoformat(),
        "agent": intent.initiated_by,
        "delegated_by": intent.delegated_by,
        "case_id": intent.case_id,
        "proposed_action": intent.action,
        "target": intent.target,
        "status": "ALLOWED" if decision.allowed else "BLOCKED",
        "enforcement_type": decision.enforcement_type,
        "reason": decision.reason,
        "rule_violated": decision.rule_violated,
    }

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    return entry


def get_all_logs() -> list[dict]:
    """Returns all log entries as a list of dicts."""
    _ensure_log_dir()
    if not LOG_FILE.exists():
        return []
    entries = []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def clear_logs():
    """Clears the audit log (used at demo start for a clean run)."""
    _ensure_log_dir()
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("")
