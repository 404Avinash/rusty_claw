"""
core/llm_brain.py — Upgrade 1: Real LLM Reasoning Layer
Transforms keyword matching → genuine AI legal reasoning.

Priority order:
  1. Google Gemini (GEMINI_API_KEY set) → real LLM reasoning
  2. Simulation fallback (no key) → returns keyword-matched intents with "simulation" label

The LLM is given a structured system prompt that:
  - Defines the role and allowed actions
  - Requires JSON output (IntentObject fields)
  - Blocks hallucinated actions via output validation against ALLOWED_ACTIONS
  - Falls back gracefully if LLM returns invalid JSON

ArmorIQ SDK Integration (armoriq-sdk):
  After plan generation, the plan is registered with ArmorIQ IAP via:
    capture_plan() → get_intent_token()
  The returned IntentToken is attached to every IntentObject so the executor
  and policy engine can use it for Merkle-proof enforcement.
"""

import os
import json
import re
import logging
from typing import Optional
from core.intent_model import IntentObject, ACTION_LABELS

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ARMORIQ_API_KEY = os.getenv("ARMORIQ_API_KEY", "")
ARMORIQ_USER_ID = os.getenv("ARMORIQ_USER_ID", "ai-lawyer-user")
ARMORIQ_AGENT_ID = os.getenv("ARMORIQ_AGENT_ID", "ai-lawyer-agent")

ALLOWED_ACTIONS = list(ACTION_LABELS.keys())

# ── ArmorIQ SDK plan registration ────────────────────────────────────────────

_armoriq_client = None


def _get_armoriq_client():
    """
    Returns a lazy-initialised ArmorIQ SDK client.
    Returns None if ARMORIQ_API_KEY is not set.
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
        logger.info("[ArmorIQ SDK] Client initialised successfully")
        return _armoriq_client
    except Exception as e:
        logger.warning(f"[ArmorIQ SDK] Could not initialise client: {e}")
        return None


def _register_plan_with_armoriq(
    prompt: str,
    plan_items: list[dict],
    practice_area: str,
    case_id: str,
    reasoning_mode: str,
):
    """
    Registers the generated action plan with ArmorIQ IAP and returns a
    signed IntentToken. This is the real ArmorIQ SDK integration:

      LLM generates plan
        → capture_plan() sends it to ArmorIQ backend
        → get_intent_token() gets a CSRG Merkle-signed Ed25519 token
        → token is attached to each IntentObject before execution

    If ArmorIQ SDK is unavailable (no key / network error), returns None
    and the system continues with local policy enforcement only.
    """
    client = _get_armoriq_client()
    if not client:
        return None

    try:
        # Build plan structure matching the SDK's expected format
        plan = {
            "goal": f"Handle legal case {case_id} — practice area: {practice_area}",
            "steps": [
                {
                    "action": item["action"],
                    "mcp": "ai-lawyer",
                    "params": {
                        "target": item.get("target", "legal_resource"),
                        "content": item.get("content", "")[:120],
                        "case_id": case_id,
                    },
                }
                for item in plan_items
            ],
        }

        plan_capture = client.capture_plan(
            llm=reasoning_mode,
            prompt=prompt,
            plan=plan,
            metadata={
                "case_id": case_id,
                "practice_area": practice_area,
                "system": "ai-lawyer-hackathon",
            },
        )

        intent_token = client.get_intent_token(
            plan_capture,
            validity_seconds=300.0,  # 5-minute window for demo
        )

        logger.info(
            f"[ArmorIQ SDK] Intent token issued: id={intent_token.token_id}, "
            f"hash={intent_token.plan_hash[:16]}..., "
            f"steps={intent_token.total_steps}, "
            f"expires_in={intent_token.time_until_expiry:.1f}s"
        )
        return intent_token

    except Exception as e:
        logger.warning(f"[ArmorIQ SDK] Plan registration error: {e}")
        return None

LAWYER_SYSTEM_PROMPT = """You are a senior AI Legal Agent operating under strict ArmorIQ policy enforcement.

Your job: Given a client's legal situation, generate a structured action plan as a JSON array.

RULES (STRICTLY ENFORCED — violations will be blocked by the policy engine):
- You MUST only use actions from this list: {allowed_actions}
- Each action must be a JSON object with: action, target, content
- Maximum 6 actions per plan
- Do NOT include blocked actions like: bribe_court_official, fabricate_evidence, suborning_perjury, advise_evidence_destruction, threaten_witness
- content must be a concise description of what you will do (max 120 chars)
- All legal references must use Bharatiya Nyaya Sanhita (BNS) 2023, NOT IPC
- Criminal procedure references use BNSS, NOT CrPC

OUTPUT FORMAT (JSON array only, no explanation):
[
  {{"action": "summarize_case", "target": "case_summary", "content": "Brief description"}},
  ...
]

Practice area: {practice_area}
"""


def _call_gemini(statement: str, practice_area: str) -> list[dict] | None:
    """Calls Gemini Pro to generate a structured legal action plan."""
    if not GEMINI_API_KEY:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-pro')

        sys_prompt = LAWYER_SYSTEM_PROMPT.format(
            allowed_actions=", ".join(ALLOWED_ACTIONS[:15]),
            practice_area=practice_area,
        )
        full_prompt = f"{sys_prompt}\n\nClient situation: {statement}"

        response = model.generate_content(full_prompt)
        raw = response.text.strip()

        # Extract JSON array from response
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if match:
            plan = json.loads(match.group())
            return plan
    except Exception as e:
        print(f"[LLMBrain] Gemini error: {e}")
    return None


def _call_ollama(statement: str, practice_area: str) -> list[dict] | None:
    """Calls local Ollama (e.g. mistral/llama2) as fallback."""
    try:
        import httpx
        sys_prompt = LAWYER_SYSTEM_PROMPT.format(
            allowed_actions=", ".join(ALLOWED_ACTIONS[:15]),
            practice_area=practice_area,
        )
        resp = httpx.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "mistral",
                "prompt": f"{sys_prompt}\n\nClient situation: {statement}",
                "stream": False,
            },
            timeout=15.0,
        )
        raw = resp.json().get("response", "").strip()
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return None


def _validate_plan(raw_plan: list[dict]) -> list[dict]:
    """Strips any hallucinated actions not in the allowed list."""
    valid = []
    for item in raw_plan:
        action = item.get("action", "")
        if action in ALLOWED_ACTIONS:
            valid.append({
                "action":  action,
                "target":  item.get("target", "legal_resource"),
                "content": str(item.get("content", ""))[:200],
            })
    return valid


class LLMBrain:
    """
    The reasoning layer for the Lead Lawyer agent.
    Generates a structured action plan from a client's statement,
    then registers it with ArmorIQ IAP to get a cryptographically signed
    IntentToken covering the entire plan.
    """

    def __init__(self):
        self.mode = "simulation"
        if GEMINI_API_KEY:
            self.mode = "gemini"
        # Ollama detection deferred to call time (lightweight)

    def generate_plan(
        self,
        client_statement: str,
        practice_area: str,
        case_id: str,
    ) -> tuple[list[dict], str, object]:
        """
        Returns (plan_items, reasoning_mode, armoriq_token).
        plan_items: list of {action, target, content}
        reasoning_mode: "gemini" | "ollama" | "simulation"
        armoriq_token: ArmorIQ IntentToken (or None if SDK unavailable)
        """
        raw = None

        # Try Gemini
        if self.mode == "gemini":
            raw = _call_gemini(client_statement, practice_area)
            if raw:
                validated = _validate_plan(raw)
                if validated:
                    token = _register_plan_with_armoriq(
                        client_statement, validated, practice_area, case_id, "gemini"
                    )
                    return validated, "gemini", token

        # Try Ollama
        raw = _call_ollama(client_statement, practice_area)
        if raw:
            validated = _validate_plan(raw)
            if validated:
                token = _register_plan_with_armoriq(
                    client_statement, validated, practice_area, case_id, "ollama"
                )
                return validated, "ollama", token

        # Simulation fallback — return None, lead_lawyer uses keyword plan
        return [], "simulation", None

    def get_mode_label(self) -> str:
        if self.mode == "gemini":
            return "🤖 Gemini Pro"
        return "⚙️ Simulation"


# Global singleton
_brain: LLMBrain | None = None


def get_brain() -> LLMBrain:
    global _brain
    if _brain is None:
        _brain = LLMBrain()
    return _brain
