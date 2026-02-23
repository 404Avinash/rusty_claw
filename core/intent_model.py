"""
intent_model.py — ArmorIQ x OpenClaw Hackathon
Structured intent model: agents PROPOSE, never execute directly.
Every action becomes a typed IntentObject before reaching the executor.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime
import json


@dataclass
class IntentObject:
    """
    The atomic unit of agent intent.
    Every proposed action must be expressed as an IntentObject.
    Agents never call tools directly — they build IntentObjects.
    The PolicyEngine validates these before execution is allowed.
    """
    action: str                          # e.g. "draft_document", "contact_opposing_party_directly"
    initiated_by: str                    # "lead_lawyer" | "research_agent"
    target: str                          # recipient, filename, resource
    content: str                         # summary of what will be done
    case_id: str                         # case context
    delegated_by: Optional[str] = None  # None for lead agent; "lead_lawyer" for sub-agents
    metadata: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def __str__(self) -> str:
        delegated_str = f" [delegated by: {self.delegated_by}]" if self.delegated_by else ""
        return (
            f"IntentObject(\n"
            f"  action      : {self.action}\n"
            f"  initiated_by: {self.initiated_by}{delegated_str}\n"
            f"  target      : {self.target}\n"
            f"  content     : {self.content[:80]}{'...' if len(self.content) > 80 else ''}\n"
            f"  case_id     : {self.case_id}\n"
            f"  timestamp   : {self.timestamp}\n"
            f")"
        )


@dataclass
class PolicyDecision:
    """
    The result of a PolicyEngine.validate() call.
    Contains the allow/block verdict + full reasoning.
    """
    allowed: bool
    reason: str
    rule_violated: Optional[str]         # e.g. "Rule 4.2", "attorney_client_privilege"
    enforcement_type: str                # "ALLOWED" | "HARD_BLOCK" | "DELEGATION_EXCEEDED"
    intent: Optional[IntentObject] = None

    def __str__(self) -> str:
        icon = "✅" if self.allowed else "🚫"
        return (
            f"{icon} PolicyDecision(\n"
            f"  allowed          : {self.allowed}\n"
            f"  enforcement_type : {self.enforcement_type}\n"
            f"  reason           : {self.reason}\n"
            f"  rule_violated    : {self.rule_violated or 'None'}\n"
            f")"
        )
