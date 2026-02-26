"""
audit_logger.py — ArmorIQ x OpenClaw Hackathon
Every policy decision is logged to JSONL. This is the traceability layer.
Judges can see every allowed and blocked action with full reasoning and plain-English explanations.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from core.intent_model import IntentObject, PolicyDecision

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "audit_log.jsonl"

# Session ID for this run (changes each time server/demo starts)
_SESSION_ID: str = str(uuid.uuid4())[:8].upper()


def get_session_id() -> str:
    return _SESSION_ID


def new_session() -> str:
    """Rotate the session ID (call at start of each demo run)."""
    global _SESSION_ID
    _SESSION_ID = str(uuid.uuid4())[:8].upper()
    return _SESSION_ID


def _ensure_log_dir():
    LOG_DIR.mkdir(exist_ok=True)


def log_decision(intent: IntentObject, decision: PolicyDecision) -> dict:
    """
    Logs a single policy decision to audit_log.jsonl.
    Returns the log entry dict (used for live display).
    """
    _ensure_log_dir()

    # Derive plain explanation
    plain = decision.plain_explanation or decision.chat_message

    entry = {
        "session_id":      _SESSION_ID,
        "timestamp":       datetime.now().isoformat(),
        "agent":           intent.initiated_by,
        "delegated_by":    intent.delegated_by,
        "case_id":         intent.case_id,
        "action":          intent.action,
        "action_label":    intent.action_label,
        "target":          intent.target,
        "status":          "ALLOWED" if decision.allowed else "BLOCKED",
        "enforcement_type": decision.enforcement_type,
        "reason":          decision.reason,
        "rule_violated":   decision.rule_violated,
        "plain_explanation": plain,
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
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries


def get_session_logs(session_id: str | None = None) -> list[dict]:
    """Returns log entries for a specific session (or current session if not specified)."""
    sid = session_id or _SESSION_ID
    return [e for e in get_all_logs() if e.get("session_id") == sid]


def get_audit_summary() -> dict:
    """Returns a structured summary of the current session's audit log."""
    logs = get_session_logs()
    allowed = [l for l in logs if l["status"] == "ALLOWED"]
    blocked = [l for l in logs if l["status"] == "BLOCKED"]
    return {
        "session_id":      _SESSION_ID,
        "total_decisions": len(logs),
        "allowed":         len(allowed),
        "blocked":         len(blocked),
        "allowed_actions": [l["action_label"] for l in allowed],
        "blocked_actions": [
            {"action": l["action_label"], "rule": l.get("rule_violated", ""), "plain": l.get("plain_explanation", "")}
            for l in blocked
        ],
    }


def clear_logs():
    """Clears the audit log (used at demo start for a clean run)."""
    _ensure_log_dir()
    new_session()  # Also rotate session ID
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("")
