"""
policy_engine.py — ArmorIQ x OpenClaw Hackathon
THE enforcement layer. Reads legal_rules.json at runtime.
Validates every IntentObject before execution is allowed.

Upgrade 2: CSRG Merkle tree integration — every decision added to the chain
Upgrade 3: Time-based policy constraints checked before allow/block list
ArmorIQ SDK: Real cryptographic intent token verification via armoriq-sdk

BNS 2023 throughout — Bharatiya Nyaya Sanhita replaces IPC.
"""

import json
import os
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
from core.intent_model import IntentObject, PolicyDecision
from core.audit_logger import log_decision

POLICY_FILE = Path("policies/legal_rules.json")
ARMORIQ_API_KEY = os.getenv("ARMORIQ_API_KEY", "")
ARMORIQ_USER_ID = os.getenv("ARMORIQ_USER_ID", "ai-lawyer-user")
ARMORIQ_AGENT_ID = os.getenv("ARMORIQ_AGENT_ID", "ai-lawyer-agent")

# IST timezone
IST = timezone(timedelta(hours=5, minutes=30))


# ── ArmorIQ SDK client (lazy singleton) ────────────────────────────────────

_armoriq_client = None


def _get_armoriq_client():
    """
    Returns a lazy-initialised ArmorIQ SDK client.
    Returns None if ARMORIQ_API_KEY is not set (local-only enforcement mode).
    Also returns None if the SDK cannot connect (fail-open for IAP, since
    local policy engine is always authoritative).
    """
    global _armoriq_client
    if _armoriq_client is not None:
        return _armoriq_client
    if not ARMORIQ_API_KEY:
        return None
    try:
        from armoriq_sdk import ArmorIQClient
        _armoriq_client = ArmorIQClient(
            api_key=ARMORIQ_API_KEY,
            user_id=ARMORIQ_USER_ID,
            agent_id=ARMORIQ_AGENT_ID,
            context_id="legal-hackathon",
        )
        return _armoriq_client
    except Exception as e:
        # SDK init failure (bad key, no network, etc.) → fall back to local token
        import warnings
        warnings.warn(f"[ArmorIQ SDK] Could not initialise client: {e}")
        return None

# IST timezone
IST = timezone(timedelta(hours=5, minutes=30))


def _load_policy() -> dict:
    if not POLICY_FILE.exists():
        raise FileNotFoundError(f"Policy file missing: {POLICY_FILE}")
    with open(POLICY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _get_intent_token(intent: IntentObject) -> str:
    """Local SHA-256 intent token fallback (used when ArmorIQ SDK is unavailable)."""
    payload = f"{intent.action}:{intent.initiated_by}:{intent.case_id}:{intent.timestamp}"
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


def _verify_with_armoriq_sdk(intent: IntentObject, session_token=None) -> tuple[bool, str, str]:
    """
    Verifies intent using the real ArmorIQ SDK.

    The SDK flow:
      capture_plan() → get_intent_token() → (invoke() called later in executor)

    Here in the policy engine, we only verify that either:
      (a) a valid IntentToken already exists for this session plan (attached via session_token), OR
      (b) we issue a single-action token for this intent for standalone demos.

    Returns (verified: bool, token_str: str, mode: str)
    where mode is "sdk" | "local".
    """
    # If a pre-issued IntentToken was passed from LLMBrain, just validate it
    if session_token is not None:
        try:
            client = _get_armoriq_client()
            if client and not session_token.is_expired:
                verified = client.verify_token(session_token)
                return verified, session_token.plan_hash[:32], "sdk"
        except Exception:
            pass

    # No pre-issued token — issue a single-action token via SDK
    client = _get_armoriq_client()
    if not client:
        return True, _get_intent_token(intent), "local"

    try:
        plan = {
            "goal": f"Legal action: {intent.action} for case {intent.case_id}",
            "steps": [
                {
                    "action": intent.action,
                    "mcp": "ai-lawyer",
                    "params": {
                        "agent": intent.initiated_by,
                        "target": intent.target,
                        "case_id": intent.case_id,
                    },
                }
            ],
        }
        plan_capture = client.capture_plan(
            llm="simulation",
            prompt=intent.content or intent.action,
            plan=plan,
        )
        token = client.get_intent_token(plan_capture, validity_seconds=120.0)
        verified = client.verify_token(token)
        return verified, token.plan_hash[:32], "sdk"
    except Exception as e:
        # Fail-open: local policy engine is always authoritative
        import warnings
        warnings.warn(f"[ArmorIQ SDK] Token issuance error: {e}")
        return True, _get_intent_token(intent), "local"


class PolicyEngine:
    """
    The ArmorIQ enforcement brain.

    validate(intent) → PolicyDecision

    Pipeline:
    1. Load policy rulebook (legal_rules.json)
    2. Time constraint check (Upgrade 3)
    3. Delegation scope check (if delegated agent)
    4. Blocked action check (hard block)
    5. Allowed action check
    6. Optional ArmorIQ IAP cryptographic verification
    7. Add to CSRG Merkle tree (Upgrade 2)
    8. Audit log
    9. Return PolicyDecision
    """

    def __init__(self, merkle_tree=None):
        self.policy = _load_policy()
        self._merkle_tree = merkle_tree  # Injected from server on create

    def set_merkle_tree(self, tree):
        self._merkle_tree = tree

    def reload_policy(self):
        self.policy = _load_policy()

    def validate(self, intent: IntentObject) -> PolicyDecision:
        # Step 1: Time constraint check (Upgrade 3)
        time_decision = self._check_time_constraint(intent)
        if time_decision:
            time_decision.intent = intent
            time_decision.plain_explanation = self._get_plain_explanation(intent, time_decision)
            log_decision(intent, time_decision)
            if self._merkle_tree:
                self._merkle_tree.add(intent, time_decision)
            return time_decision

        # Step 2: Delegated vs lead agent
        if intent.delegated_by:
            decision = self._validate_delegated(intent)
        else:
            decision = self._validate_lead_agent(intent)

        # Step 3: ArmorIQ SDK cryptographic intent token verification
        # Uses the real armoriq-sdk: capture_plan → get_intent_token → verify_token
        # Attach any pre-issued session IntentToken from LLMBrain if present
        session_token = getattr(intent, '_armoriq_token', None)
        if decision.allowed:
            sdk_ok, token_str, sdk_mode = _verify_with_armoriq_sdk(intent, session_token)
            decision.metadata = {
                "intent_token": token_str,
                "iap_verified": "sdk" if sdk_mode == "sdk" else "local",
                "sdk_mode": sdk_mode,
            }
            if not sdk_ok:
                decision = PolicyDecision(
                    allowed=False,
                    reason="ArmorIQ SDK cryptographic verification failed — intent token rejected by IAP",
                    rule_violated="armoriq_sdk_rejection",
                    enforcement_type="HARD_BLOCK",
                    plain_explanation="The ArmorIQ platform rejected the cryptographic intent token for this action.",
                )

        # Step 4: Attach plain explanation and intent
        if not decision.plain_explanation:
            decision.plain_explanation = self._get_plain_explanation(intent, decision)
        decision.intent = intent

        # Step 5: CSRG Merkle tree (Upgrade 2)
        if self._merkle_tree:
            self._merkle_tree.add(intent, decision)

        # Step 6: Audit log
        log_decision(intent, decision)

        return decision

    # ── Validation paths ─────────────────────────────────────────────────────

    def _validate_lead_agent(self, intent: IntentObject) -> PolicyDecision:
        agent_role = intent.initiated_by
        agent_policy = self.policy.get(agent_role, self.policy.get("lead_lawyer"))
        blocked = agent_policy.get("blocked_actions", [])
        allowed = agent_policy.get("allowed_actions", [])

        if intent.action in blocked:
            rule = self._get_ethical_rule(intent.action)
            return PolicyDecision(
                allowed=False,
                reason=self._get_block_reason(intent.action, rule),
                rule_violated=rule,
                enforcement_type="HARD_BLOCK",
            )
        if intent.action in allowed:
            return PolicyDecision(
                allowed=True,
                reason=f"Action '{intent.action}' is within authorised scope for {agent_role}",
                rule_violated=None,
                enforcement_type="ALLOWED",
            )
        return PolicyDecision(
            allowed=False,
            reason=f"Action '{intent.action}' not in authorised actions list — denied by default (fail-closed)",
            rule_violated="implicit_denial",
            enforcement_type="HARD_BLOCK",
        )

    def _validate_delegated(self, intent: IntentObject) -> PolicyDecision:
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
                    f"Authorised scope: {allowed_scope}"
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
        return PolicyDecision(
            allowed=False,
            reason=(
                f"Action '{intent.action}' not within delegated scope for '{intent.initiated_by}'. "
                f"Authorised: {allowed_scope}"
            ),
            rule_violated="delegation_scope_exceeded",
            enforcement_type="DELEGATION_EXCEEDED",
        )

    # ── Upgrade 3: Time constraint ────────────────────────────────────────────

    def _check_time_constraint(self, intent: IntentObject) -> PolicyDecision | None:
        """
        Checks if the action is allowed at the current time (IST).
        Returns None if no constraint applies, or a block PolicyDecision if violated.
        """
        tc = self.policy.get("time_constraints", {})
        if not tc.get("enabled", False):
            return None

        blocked_after_hours = tc.get("blocked_actions_after_hours", [])
        if intent.action not in blocked_after_hours:
            return None

        now_ist = datetime.now(IST)
        current_time = now_ist.strftime("%H:%M")

        allowed_hours = tc.get("allowed_hours_ist", {})
        start = allowed_hours.get("start", "09:00")
        end = allowed_hours.get("end", "21:00")

        # Simple string comparison works for HH:MM format
        if start <= current_time <= end:
            return None  # Within allowed hours — no block

        msg = tc.get("message", "This action is restricted outside business hours.")
        return PolicyDecision(
            allowed=False,
            reason=(
                f"TIME CONSTRAINT VIOLATED: Action '{intent.action}' is only permitted between "
                f"{start}–{end} IST. Current time: {current_time} IST. {msg}"
            ),
            rule_violated="time_constraint_violation",
            enforcement_type="TIME_RESTRICTED",
            plain_explanation=(
                f"⏰ Time restriction: Your lawyer cannot file court documents outside business hours "
                f"({start}–{end} IST). Current time is {current_time} IST. Please retry during business hours."
            ),
        )

    # ── Rule & reason mappings ────────────────────────────────────────────────

    def _get_ethical_rule(self, action: str) -> str:
        return {
            "contact_opposing_party_directly":  "Bar Council Rule 4.2 — No Contact with Represented Person",
            "share_privileged_info_externally":  "Bar Council Rule 7 — Attorney-Client Privilege",
            "advise_evidence_destruction":       "BNS Section 238 — Causing Disappearance of Evidence",
            "fabricate_evidence":                "BNS Section 228 — Fabricating False Evidence",
            "suborning_perjury":                 "BNS Section 227 — Giving False Evidence (Subornation)",
            "act_outside_jurisdiction":          "Bar Council Rule 10 — Geographic Jurisdiction",
            "file_frivolous_motion":             "CPC Order 7 Rule 11 — Frivolous / Vexatious Filings",
            "threaten_witness":                  "BNS Section 353 — Threatening a Witness",
            "bribe_court_official":              "Prevention of Corruption Act, 1988 + BNS Section 61",
            "conceal_relevant_facts":            "Bar Council Rule 14 — Duty to Court: No Suppression of Facts",
            "misrepresent_law":                  "Bar Council Rule 15 — Duty to Court: No Misrepresentation",
            "advise_illegal_activity":           "Bar Council Rule 22 — No Assistance in Illegal Acts",
        }.get(action, "General Ethical Violation — Bar Council of India Rules")

    def _get_block_reason(self, action: str, rule: str) -> str:
        return {
            "contact_opposing_party_directly":  "Direct contact with a represented opposing party is prohibited (Bar Council Rule 4.2). Route via opposing counsel.",
            "share_privileged_info_externally":  "Attorney-client privilege protects all client communications. Sharing externally violates Bar Council Rule 7.",
            "advise_evidence_destruction":       "Advising evidence destruction is obstruction of justice — BNS Section 238.",
            "fabricate_evidence":                "Fabricating evidence is a criminal offence under BNS Section 228.",
            "suborning_perjury":                 "Coaching anyone to give false evidence is a criminal offence under BNS Section 227.",
            "act_outside_jurisdiction":          "This matter falls outside the agent's authorised jurisdiction.",
            "file_frivolous_motion":             "The motion lacks legal merit — violates CPC Order 7 Rule 11.",
            "threaten_witness":                  "Threatening a witness is a criminal offence under BNS Section 353.",
            "bribe_court_official":              "Bribing any court official or judge is a serious criminal offence under Prevention of Corruption Act 1988 + BNS Section 61.",
            "conceal_relevant_facts":            "Concealing relevant facts violates the duty of candour under Bar Council Rule 14.",
            "misrepresent_law":                  "Deliberately misrepresenting the law violates Bar Council Rule 15.",
            "advise_illegal_activity":           "Advising any illegal action violates Bar Council Rule 22.",
        }.get(action, f"Action '{action}' violates: {rule}")

    def _get_plain_explanation(self, intent: IntentObject, decision: PolicyDecision) -> str:
        return decision.chat_message if decision.intent else intent.plain_english

    @property
    def metadata(self):
        return {}
