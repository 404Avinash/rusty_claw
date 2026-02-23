"""
lead_lawyer.py — ArmorIQ x OpenClaw Hackathon
The main reasoning agent. Powered by LLM (or simulation mode).

Key design principle:
    The lead lawyer NEVER executes tools directly.
    It PROPOSES actions as IntentObjects.
    The Executor validates each one via the PolicyEngine before running.

This enforces clear SEPARATION between REASONING and EXECUTION.
"""

import os
import time
from core.intent_model import IntentObject
from core.policy_engine import PolicyEngine
from core.executor import Executor, PolicyViolationError
from memory.case_store import CaseStore


# LLM Integration (optional — simulation mode works without API key)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", None)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", None)


class LeadLawyer:
    """
    The principal legal agent.
    Handles: case intake → analysis → strategy → action proposals → execution.
    """

    ROLE = "lead_lawyer"

    def __init__(self, executor: Executor, case_store: CaseStore):
        self.executor = executor
        self.case_store = case_store
        self.use_llm = bool(OPENAI_API_KEY or GEMINI_API_KEY)

    def intake_case(self, client_statement: str, case_id: str) -> dict:
        """
        Step 1: Receive and store the client's case description.
        """
        case_data = {
            "case_id": case_id,
            "client_statement": client_statement,
            "status": "intake",
        }
        self.case_store.save(case_id, case_data)
        return case_data

    def analyze_and_act(self, case_id: str, client_instruction: str) -> list[dict]:
        """
        Main reasoning loop.
        1. Understand what the client wants
        2. Generate a list of proposed IntentObjects (the "plan")
        3. Submit each to the Executor
        4. Collect allowed/blocked results
        """
        results = []
        proposed_intents = self._generate_plan(case_id, client_instruction)

        for intent in proposed_intents:
            try:
                outcome = self.executor.execute(intent)
                results.append({
                    "intent": intent,
                    "decision": "ALLOWED",
                    "enforcement_type": outcome["enforcement_type"],
                    "reason": outcome["reason"],
                    "result": outcome.get("result", ""),
                })
            except PolicyViolationError as e:
                results.append({
                    "intent": intent,
                    "decision": "BLOCKED",
                    "enforcement_type": e.decision.enforcement_type,
                    "reason": e.decision.reason,
                    "rule_violated": e.decision.rule_violated,
                })

        return results

    def spawn_research_agent(self, case_id: str) -> "ResearchAgent":
        """
        Delegation: spawns a research sub-agent with a constrained policy scope.
        The research agent inherits its permissions from the delegation_rules
        in legal_rules.json — NOT a copy of the lead lawyer's full permissions.
        """
        from agents.research_agent import ResearchAgent
        return ResearchAgent(
            executor=self.executor,
            case_store=self.case_store,
            delegated_by=self.ROLE,
            case_id=None,
        )

    def _generate_plan(self, case_id: str, client_instruction: str) -> list[IntentObject]:
        """
        Translates a client instruction into a list of proposed IntentObjects.
        In LLM mode: calls GPT/Gemini with a structured prompt.
        In simulation mode: uses deterministic plan templates.
        """
        if self.use_llm:
            return self._llm_generate_plan(case_id, client_instruction)
        return self._simulate_plan(case_id, client_instruction)

    def _simulate_plan(self, case_id: str, instruction: str) -> list[IntentObject]:
        """
        Simulation mode: deterministic plans for demo scenarios.
        Maps natural language instructions to known ethical/unethical action sequences.
        """
        instruction_lower = instruction.lower()

        # Scenario 1: Legitimate landlord dispute
        if any(k in instruction_lower for k in ["landlord", "apartment", "illegal entry", "eviction"]):
            return [
                IntentObject(
                    action="summarize_case",
                    initiated_by=self.ROLE,
                    target="case_summary",
                    content="Summarize the landlord illegal entry case",
                    case_id=case_id,
                ),
                IntentObject(
                    action="search_case_law",
                    initiated_by=self.ROLE,
                    target="legal_precedents",
                    content="Search for precedents on illegal landlord entry, tenant rights",
                    case_id=case_id,
                ),
                IntentObject(
                    action="draft_document",
                    initiated_by=self.ROLE,
                    target=f"output/legal_notice_{case_id}.txt",
                    content="Draft a legal notice to the landlord for illegal entry under Rent Control Act",
                    case_id=case_id,
                ),
                IntentObject(
                    action="advise_client",
                    initiated_by=self.ROLE,
                    target="client",
                    content="Advise client to document all instances of illegal entry with timestamps and witnesses",
                    case_id=case_id,
                ),
            ]

        # Scenario 2: Client wants to lie (triggers perjury block)
        if any(k in instruction_lower for k in ["never received", "say we didn't", "tell them we never", "deny receiving"]):
            return [
                IntentObject(
                    action="suborning_perjury",
                    initiated_by=self.ROLE,
                    target="opposing_counsel",
                    content=f"Client instruction: {instruction}",
                    case_id=case_id,
                ),
            ]

        # Scenario 3: Client wants direct contact with opposing party
        if any(k in instruction_lower for k in ["contact them", "call them", "message opposing", "reach out to landlord directly"]):
            return [
                IntentObject(
                    action="contact_opposing_party_directly",
                    initiated_by=self.ROLE,
                    target="opposing_party@email.com",
                    content=f"Client instruction: {instruction}",
                    case_id=case_id,
                ),
            ]

        # Scenario 4: Evidence destruction
        if any(k in instruction_lower for k in ["delete", "destroy evidence", "get rid of", "shred"]):
            return [
                IntentObject(
                    action="advise_evidence_destruction",
                    initiated_by=self.ROLE,
                    target="client",
                    content=f"Client instruction: {instruction}",
                    case_id=case_id,
                ),
            ]

        # Default: general strategy + advice
        return [
            IntentObject(
                action="summarize_case",
                initiated_by=self.ROLE,
                target="case_summary",
                content="Summarize the client's situation",
                case_id=case_id,
            ),
            IntentObject(
                action="advise_client",
                initiated_by=self.ROLE,
                target="client",
                content=f"Provide legal advice based on: {instruction}",
                case_id=case_id,
            ),
        ]

    def _llm_generate_plan(self, case_id: str, instruction: str) -> list[IntentObject]:
        """
        LLM-powered plan generation. Calls OpenAI or Gemini.
        The LLM outputs a structured JSON list of proposed actions.
        We parse this into IntentObjects.
        """
        # This would call OpenAI/Gemini in production
        # Falls back to simulation for the hackathon
        return self._simulate_plan(case_id, instruction)
