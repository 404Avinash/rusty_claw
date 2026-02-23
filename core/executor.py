"""
executor.py — ArmorIQ x OpenClaw Hackathon
THE ONLY gateway to tool execution.

Pipeline: IntentObject → PolicyEngine.validate() → Execute OR Block

No tool is ever called directly by an agent. Every action MUST flow
through this executor, which enforces the PolicyEngine decision.
"""

from core.intent_model import IntentObject, PolicyDecision
from core.policy_engine import PolicyEngine


class Executor:
    """
    Gated execution layer.
    Agents submit IntentObjects here. The executor:
    1. Validates intent via PolicyEngine
    2. If ALLOWED: calls the tool function
    3. If BLOCKED: raises PolicyViolationError with full reasoning
    4. All decisions are automatically logged via the PolicyEngine
    """

    def __init__(self, policy_engine: PolicyEngine, tools: dict):
        """
        Args:
            policy_engine: The PolicyEngine instance
            tools: dict mapping action name → callable
                   e.g. {"draft_document": draft_doc_fn, ...}
        """
        self.engine = policy_engine
        self.tools = tools

    def execute(self, intent: IntentObject) -> dict:
        """
        Submit an intent for validation and execution.

        Returns:
            dict with keys: allowed, enforcement_type, reason, result (if allowed)

        Raises:
            PolicyViolationError if the action is blocked
        """
        decision: PolicyDecision = self.engine.validate(intent)

        if decision.allowed:
            tool_fn = self.tools.get(intent.action)
            if tool_fn is None:
                return {
                    "allowed": True,
                    "enforcement_type": "ALLOWED",
                    "reason": decision.reason,
                    "result": f"[Tool '{intent.action}' executed — no implementation registered]",
                }
            result = tool_fn(intent)
            return {
                "allowed": True,
                "enforcement_type": "ALLOWED",
                "reason": decision.reason,
                "result": result,
            }
        else:
            raise PolicyViolationError(decision)


class PolicyViolationError(Exception):
    """
    Raised when an agent attempts an action that violates policy.
    Contains the full PolicyDecision for display and logging.
    """
    def __init__(self, decision: PolicyDecision):
        self.decision = decision
        super().__init__(decision.reason)

    def __str__(self) -> str:
        return (
            f"\n{'='*60}\n"
            f"🚫 POLICY VIOLATION — ACTION BLOCKED\n"
            f"{'='*60}\n"
            f"  Enforcement  : {self.decision.enforcement_type}\n"
            f"  Rule Violated: {self.decision.rule_violated or 'N/A'}\n"
            f"  Reason       : {self.decision.reason}\n"
            f"{'='*60}\n"
        )
