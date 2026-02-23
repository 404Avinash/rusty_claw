"""
research_agent.py — ArmorIQ x OpenClaw Hackathon
DELEGATED sub-agent. Spawned by the lead lawyer with SCOPED permissions.

Delegation design:
- The research agent has a SUBSET of the lead lawyer's permissions
- Its scope is defined in legal_rules.json → delegation_rules.research_agent
- Any attempt to exceed that scope → DELEGATION_EXCEEDED block
- This is the "delegation bonus" requirement of the hackathon

Demo moment: research agent tries to send_communication → HARD BLOCKED.
"""

from core.intent_model import IntentObject
from core.executor import Executor, PolicyViolationError
from memory.case_store import CaseStore


class ResearchAgent:
    """
    Research sub-agent with bounded delegation.
    Can: search_case_law, read_case_files, summarize_precedents
    Cannot: draft_document, send_communication, advise_client, etc.
    """

    ROLE = "research_agent"

    def __init__(self, executor: Executor, case_store: CaseStore, delegated_by: str, case_id: str | None):
        self.executor = executor
        self.case_store = case_store
        self.delegated_by = delegated_by
        self.current_case_id = case_id

    def research(self, case_id: str, query: str) -> list[dict]:
        """
        Main research flow: searches case law and summarizes.
        All actions are validated against the delegated scope.
        """
        self.current_case_id = case_id
        results = []

        # ALLOWED: search for case law
        intent_search = IntentObject(
            action="search_case_law",
            initiated_by=self.ROLE,
            delegated_by=self.delegated_by,
            target="legal_database",
            content=f"Research: {query}",
            case_id=case_id,
        )
        try:
            outcome = self.executor.execute(intent_search)
            results.append({"intent": intent_search, "decision": "ALLOWED", **outcome})
        except PolicyViolationError as e:
            results.append({"intent": intent_search, "decision": "BLOCKED", "reason": e.decision.reason})

        return results

    def attempt_unauthorized_action(self, case_id: str, action: str, target: str, content: str) -> dict:
        """
        Demo method: deliberately attempts an out-of-scope action.
        Used in the demo to show delegation enforcement in action.
        """
        intent = IntentObject(
            action=action,
            initiated_by=self.ROLE,
            delegated_by=self.delegated_by,
            target=target,
            content=content,
            case_id=case_id,
        )
        try:
            outcome = self.executor.execute(intent)
            return {"intent": intent, "decision": "ALLOWED", **outcome}
        except PolicyViolationError as e:
            return {
                "intent": intent,
                "decision": "BLOCKED",
                "enforcement_type": e.decision.enforcement_type,
                "reason": e.decision.reason,
                "rule_violated": e.decision.rule_violated,
            }
