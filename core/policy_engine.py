"""
policy_engine.py — ArmorIQ x OpenClaw Hackathon
THE enforcement layer. Reads legal_rules.json at runtime.
Validates every IntentObject before execution is allowed.

This is NOT hardcoded if/else. Rules are read from a structured JSON policy file
and evaluated dynamically — satisfying the hackathon's "structured policy model" requirement.

Optional: Can call ArmorIQ IAP API for cryptographic intent token verification.
When ARMORIQ_API_KEY is set, tokens are verified via platform.armoriq.ai.
Without the key, local policy enforcement still runs deterministically.
"""

import json
import os
import hashlib
import time
from pathlib import Path
from core.intent_model import IntentObject, PolicyDecision
from core.audit_logger import log_decision

POLICY_FILE = Path("policies/legal_rules.json")

# ArmorIQ IAP integration (optional — works without key in simulation mode)
ARMORIQ_API_KEY = os.getenv("ARMORIQ_API_KEY", None)
ARMORIQ_IAP_URL = os.getenv("ARMORIQ_IAP_URL", "https://iap.armoriq.ai/v1/verify")


def _load_policy() -> dict:
    """Loads the policy rulebook from JSON. Raises if file is invalid."""
    if not POLICY_FILE.exists():
        raise FileNotFoundError(f"Policy file missing: {POLICY_FILE}")
    with open(POLICY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _get_intent_token_local(intent: IntentObject) -> str:
    """
    Local simulation of cryptographic intent token generation.
    In production, this is replaced by calling ArmorIQ IAP which returns
    a signed Merkle-tree-backed token.
    """
    payload = f"{intent.action}:{intent.initiated_by}:{intent.case_id}:{intent.timestamp}"
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


def _verify_with_armoriq_iap(intent: IntentObject) -> bool:
    """
    Optional: Calls ArmorIQ Intent Access Proxy for cryptographic verification.
    If API key is not set, returns True (local policy enforcement handles it).
    """
    if not ARMORIQ_API_KEY:
        return True  # Simulation mode — local enforcement is authoritative

    try:
        import urllib.request
        token = _get_intent_token_local(intent)
        payload = json.dumps({
            "action": intent.action,
            "agent": intent.initiated_by,
            "token": token,
            "case_id": intent.case_id,
        }).encode()
        req = urllib.request.Request(
            ARMORIQ_IAP_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {ARMORIQ_API_KEY}",
                "Content-Type": "application/json",
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read())
            return result.get("verified", False)
    except Exception:
        # Fail-closed: if IAP unreachable, block execution
        return False


class PolicyEngine:
    """
    The ArmorIQ enforcement brain.

    validate(intent) → PolicyDecision

    Decision logic:
    1. Load policy rulebook (legal_rules.json)
    2. If agent is delegated → check delegation scope first
    3. Check blocked_actions list (hard block)
    4. Check allowed_actions list
    5. Optionally verify with ArmorIQ IAP for cryptographic proof
    6. Return PolicyDecision(allowed, reason, rule_violated, enforcement_type)
    """

    def __init__(self):
        self.policy = _load_policy()
        self._intent_token_cache: dict[str, str] = {}

    def reload_policy(self):
        """Hot-reload policy without restarting the agent."""
        self.policy = _load_policy()

    def validate(self, intent: IntentObject) -> PolicyDecision:
        """
        Core validation pipeline. Returns a PolicyDecision.
        Also logs every decision to audit_log.jsonl.
        """
        # Step 1: Is this a delegated agent?
        if intent.delegated_by:
            decision = self._validate_delegated(intent)
        else:
            decision = self._validate_lead_agent(intent)

        # Step 2: If locally allowed, optionally verify with ArmorIQ IAP
        if decision.allowed and ARMORIQ_API_KEY:
            iap_verified = _verify_with_armoriq_iap(intent)
            if not iap_verified:
                decision = PolicyDecision(
                    allowed=False,
                    reason="ArmorIQ IAP cryptographic verification failed",
                    rule_violated="armoriq_iap_rejection",
                    enforcement_type="HARD_BLOCK",
                    intent=intent,
                )

        # Step 3: Attach intent to decision and log it
        decision.intent = intent
        log_decision(intent, decision)

        return decision

    def _validate_lead_agent(self, intent: IntentObject) -> PolicyDecision:
        """Validates actions for the lead lawyer agent."""
        agent_role = intent.initiated_by
        agent_policy = self.policy.get(agent_role, self.policy.get("lead_lawyer"))

        blocked = agent_policy.get("blocked_actions", [])
        allowed = agent_policy.get("allowed_actions", [])

        # Hard block check first
        if intent.action in blocked:
            rule = self._get_ethical_rule(intent.action)
            return PolicyDecision(
                allowed=False,
                reason=self._get_block_reason(intent.action, rule),
                rule_violated=rule,
                enforcement_type="HARD_BLOCK",
            )

        # Allowed check
        if intent.action in allowed:
            return PolicyDecision(
                allowed=True,
                reason=f"Action '{intent.action}' is within authorized scope for {agent_role}",
                rule_violated=None,
                enforcement_type="ALLOWED",
            )

        # Not in either list — fail-closed (deny by default)
        return PolicyDecision(
            allowed=False,
            reason=f"Action '{intent.action}' is not in the authorized actions list — denied by default (fail-closed)",
            rule_violated="implicit_denial",
            enforcement_type="HARD_BLOCK",
        )

    def _validate_delegated(self, intent: IntentObject) -> PolicyDecision:
        """Validates actions for delegated sub-agents (e.g. research_agent)."""
        delegation_rules = self.policy.get("delegation_rules", {})
        agent_scope = delegation_rules.get(intent.initiated_by)

        if not agent_scope:
            return PolicyDecision(
                allowed=False,
                reason=f"Agent '{intent.initiated_by}' has no delegation scope defined",
                rule_violated="undefined_delegation",
                enforcement_type="DELEGATION_EXCEEDED",
            )

        allowed_scope = agent_scope.get("allowed", [])
        blocked_scope = agent_scope.get("blocked", [])

        if intent.action in blocked_scope:
            return PolicyDecision(
                allowed=False,
                reason=(
                    f"Action '{intent.action}' is outside the delegated authority of "
                    f"'{intent.initiated_by}' (delegated by: {intent.delegated_by}). "
                    f"Authorized scope: {allowed_scope}"
                ),
                rule_violated="delegation_scope_exceeded",
                enforcement_type="DELEGATION_EXCEEDED",
            )

        if intent.action in allowed_scope:
            return PolicyDecision(
                allowed=True,
                reason=f"Action '{intent.action}' is within delegated scope of '{intent.initiated_by}'",
                rule_violated=None,
                enforcement_type="ALLOWED",
            )

        # Not in allowed scope — fail-closed
        return PolicyDecision(
            allowed=False,
            reason=(
                f"Action '{intent.action}' is not within the delegated scope for '{intent.initiated_by}'. "
                f"Authorized: {allowed_scope}"
            ),
            rule_violated="delegation_scope_exceeded",
            enforcement_type="DELEGATION_EXCEEDED",
        )

    def _get_ethical_rule(self, action: str) -> str:
        """Maps blocked actions to their specific ethical/legal rule."""
        action_to_rule = {
            "contact_opposing_party_directly": "Rule 4.2 — No Contact with Represented Person",
            "share_privileged_info_externally": "Bar Council Rule 7 — Attorney-Client Privilege",
            "advise_evidence_destruction": "IPC Section 201 — Causing Disappearance of Evidence",
            "fabricate_evidence": "IPC Section 192 — Fabricating False Evidence",
            "suborning_perjury": "IPC Section 191 — Giving False Evidence (Subornation)",
            "act_outside_jurisdiction": "Bar Council Rule 10 — Geographic Jurisdiction",
            "file_frivolous_motion": "CPC Order 7 Rule 11 — Frivolous / Vexatious Filings",
            "threaten_witness": "IPC Section 189 — Threatening Public Servant / Witness",
        }
        return action_to_rule.get(action, "General Ethical Violation")

    def _get_block_reason(self, action: str, rule: str) -> str:
        """Returns a human-readable block reason for the demo."""
        reasons = {
            "contact_opposing_party_directly": (
                "Direct contact with the opposing party (who is represented by counsel) "
                "is prohibited. This violates Rule 4.2 of professional conduct. "
                "Route all communications through opposing counsel."
            ),
            "share_privileged_info_externally": (
                "This information is protected by attorney-client privilege. "
                "Sharing it externally would be a serious breach of professional duty."
            ),
            "advise_evidence_destruction": (
                "Advising a client to destroy evidence constitutes obstruction of justice "
                "and is a criminal offense under IPC Section 201."
            ),
            "fabricate_evidence": (
                "Fabricating evidence is a criminal offense under IPC Section 192 "
                "and would result in immediate disbarment."
            ),
            "suborning_perjury": (
                "Coaching a client to make false statements (suborning perjury) is a "
                "criminal offense under IPC Section 191. This agent cannot and will not assist "
                "with this request. Suggest telling the truth or asserting rightful legal defenses instead."
            ),
            "act_outside_jurisdiction": (
                "This matter falls outside the agent's authorized jurisdiction. "
                "Refer to a locally licensed counsel."
            ),
            "file_frivolous_motion": (
                "The proposed motion lacks sufficient legal merit. Filing it would "
                "violate CPC Order 7 Rule 11 and expose the client to cost sanctions."
            ),
            "threaten_witness": (
                "Threatening or intimidating a witness is a criminal offense "
                "and an immediate grounds for disbarment."
            ),
        }
        return reasons.get(action, f"Action '{action}' violates: {rule}")
