"""
lead_lawyer.py — Lead Lawyer Agent
Multi-practice-area AI legal agent. Proposes IntentObjects for PolicyEngine validation.
Covers: Landlord/Tenant, Employment, Contract Dispute, Criminal Consultation.

BNS references throughout (Bharatiya Nyaya Sanhita, 2023).
"""

from core.intent_model import IntentObject, PolicyDecision
from core.executor import Executor, PolicyViolationError
from core.llm_brain import get_brain, _register_plan_with_armoriq
from memory.case_store import CaseStore
import os

ARMORIQ_API_KEY = os.getenv("ARMORIQ_API_KEY")


class LeadLawyer:
    ROLE = "lead_lawyer"

    def __init__(self, executor: Executor, case_store: CaseStore):
        self.executor = executor
        self.case_store = case_store

    # ──────────────────────────────────────────────
    # Case Intake
    # ──────────────────────────────────────────────

    def intake_case(self, client_statement: str, case_id: str) -> dict:
        case_data = {
            "case_id": case_id,
            "client_statement": client_statement,
            "practice_area": self._detect_practice_area(client_statement),
            "status": "active",
        }
        self.case_store.save(case_id, case_data)
        return case_data

    def _detect_practice_area(self, text: str) -> str:
        text = text.lower()
        if any(kw in text for kw in ["landlord", "tenant", "rent", "evict", "apartment", "lease", "property"]):
            return "landlord_tenant"
        if any(kw in text for kw in ["employer", "employee", "fired", "termination", "salary", "wage", "job", "workplace", "hr"]):
            return "employment"
        if any(kw in text for kw in ["contract", "breach", "vendor", "agreement", "delivery", "payment terms", "supplier"]):
            return "contract"
        if any(kw in text for kw in ["bail", "arrest", "accused", "fir", "crime", "police", "prison", "charge", "fraud", "murder"]):
            return "criminal_consultation"
        return "general"

    # ──────────────────────────────────────────────
    # Main Agent Loop
    # ──────────────────────────────────────────────

    def analyze_and_act(self, case_id: str, client_instruction: str) -> list[dict]:
        results = []
        case_data = self.case_store.load(case_id) or {}
        practice_area = case_data.get("practice_area", self._detect_practice_area(client_instruction))
        client_statement = case_data.get("client_statement", client_instruction)

        # Try LLM brain first (Upgrade 1)
        # generate_plan now returns a 3-tuple: (plan_items, reasoning_mode, armoriq_token)
        brain = get_brain()
        llm_plan, reasoning_mode, armoriq_token = brain.generate_plan(
            client_statement, practice_area, case_id
        )

        if llm_plan:
            proposed_intents = []
            for item in llm_plan:
                intent = IntentObject(
                    action=item["action"],
                    initiated_by=self.ROLE,
                    target=item.get("target", "legal_resource"),
                    content=item.get("content", ""),
                    case_id=case_id,
                )
                # Attach the ArmorIQ IntentToken for Merkle-proof enforcement
                if armoriq_token is not None:
                    setattr(intent, '_armoriq_token', armoriq_token)
                proposed_intents.append(intent)
        else:
            # Simulation fallback: keyword-based plan
            reasoning_mode = "simulation"
            proposed_intents = self._generate_plan(case_id, client_instruction, practice_area)

            # Even for simulation plans, register with ArmorIQ if key is set
            # so the proxy Merkle-proof enforcement path is exercised
            sim_plan_items = [
                {"action": i.action, "target": i.target, "content": i.content}
                for i in proposed_intents
            ]
            armoriq_token = _register_plan_with_armoriq(
                client_statement or client_instruction,
                sim_plan_items,
                practice_area,
                case_id,
                "simulation",
            )
            if armoriq_token is not None:
                for intent in proposed_intents:
                    setattr(intent, '_armoriq_token', armoriq_token)

        for intent in proposed_intents:
            try:
                outcome = self.executor.execute(intent)
                results.append({
                    "intent": intent,
                    "decision": "ALLOWED",
                    "enforcement_type": "ALLOWED",
                    "reason": outcome.get("reason", ""),
                    "result": outcome.get("result", ""),
                    "rule_violated": None,
                    "plain_explanation": intent.plain_english,
                    "reasoning_mode": reasoning_mode,
                    "armoriq_enforced": outcome.get("armoriq_enforced", False),
                    "armoriq_verified": outcome.get("armoriq_verified", False),
                    "armoriq_token_id": outcome.get("token_id", ""),
                    "armoriq_plan_hash": outcome.get("plan_hash", ""),
                })
            except PolicyViolationError as e:
                results.append({
                    "intent": intent,
                    "decision": "BLOCKED",
                    "enforcement_type": e.decision.enforcement_type,
                    "reason": e.decision.reason,
                    "result": "",
                    "rule_violated": e.decision.rule_violated,
                    "plain_explanation": e.decision.plain_explanation or intent.plain_english,
                    "reasoning_mode": reasoning_mode,
                })
        return results

    # ──────────────────────────────────────────────
    # Plan Generator (Simulated Reasoning Layer)
    # ──────────────────────────────────────────────

    def _generate_plan(self, case_id: str, instruction: str, practice_area: str) -> list[IntentObject]:
        instr_lower = instruction.lower()

        # ── BLOCKED scenarios (detected universally across all practice areas) ──
        if any(k in instr_lower for k in ["never received", "didn't get it", "say we", "lie", "false statement", "deny receiving"]):
            return [self._intent("suborning_perjury", "court_record",
                "Coach client to deny receiving legal notice — fabrication of false statement", case_id)]

        if any(k in instr_lower for k in ["contact them directly", "message opposing", "reach out to landlord",
                                           "call the employer", "call opposing", "contact the other party"]):
            return [self._intent("contact_opposing_party_directly", "opposing_party",
                "Directly contacting represented opposing party", case_id)]

        if any(k in instr_lower for k in ["destroy", "delete document", "shred", "burn", "get rid of evidence"]):
            return [self._intent("advise_evidence_destruction", "evidence_file",
                "Client asked to destroy or delete evidence", case_id)]

        if any(k in instr_lower for k in ["bribe", "pay the judge", "pay off", "corrupt", "bribe the"]):
            return [self._intent("bribe_court_official", "court_official",
                "Client suggested bribing a judge or investigating officer — BNS Section 61", case_id)]

        if any(k in instr_lower for k in ["threaten witness", "scare witness", "silence them"]):
            return [self._intent("threaten_witness", "witness",
                "Client requested threatening a witness — BNS Section 353", case_id)]

        if any(k in instr_lower for k in ["fabricate", "make up evidence", "create fake", "forge"]):
            return [self._intent("fabricate_evidence", "case_record",
                "Client requested fabrication of evidence — BNS Section 228", case_id)]

        # ── Practice-area-aware ALLOWED plans ──
        if practice_area == "landlord_tenant":
            return self._plan_landlord(case_id, instr_lower)
        elif practice_area == "employment":
            return self._plan_employment(case_id, instr_lower)
        elif practice_area == "contract":
            return self._plan_contract(case_id, instr_lower)
        elif practice_area == "criminal_consultation":
            return self._plan_criminal(case_id, instr_lower)
        else:
            return self._plan_general(case_id, instr_lower)

    # ── Practice area plans ──

    def _plan_landlord(self, case_id: str, instr: str) -> list[IntentObject]:
        return [
            self._intent("summarize_case", "case_summary",
                "Summarise landlord illegal entry dispute", case_id),
            self._intent("search_case_law", "legal_precedents",
                "Search precedents: landlord unauthorised entry, tenant rights, Rent Control Act, BNS Section 329", case_id),
            self._intent("draft_document", f"output/legal_notice_{case_id}.txt",
                "Draft legal notice to landlord — illegal entry violation under TPA and Rent Control Act", case_id),
            self._intent("advise_client", "client",
                "Advise client to document all incidents with timestamps, photos, and witnesses. File complaint under BNS Section 329 (Criminal Trespass).", case_id),
        ]

    def _plan_employment(self, case_id: str, instr: str) -> list[IntentObject]:
        return [
            self._intent("summarize_case", "case_summary",
                "Summarise wrongful termination / unpaid wages dispute", case_id),
            self._intent("search_case_law", "labour_law_db",
                "Search: wrongful termination Industrial Disputes Act, unpaid wages claim, Labour Court jurisdiction", case_id),
            self._intent("calculate_damages", "damages_report",
                "Calculate claim: 3 months unpaid salary + severance + compensation under ID Act", case_id),
            self._intent("draft_document", f"output/demand_notice_{case_id}.txt",
                "Draft demand notice to employer for unpaid wages and reinstatement", case_id),
            self._intent("advise_client", "client",
                "Advise client to preserve all employment records, salary slips, and termination email.", case_id),
        ]

    def _plan_contract(self, case_id: str, instr: str) -> list[IntentObject]:
        return [
            self._intent("analyze_contract", "contract_docs",
                "Analyse contract terms for breach clauses, liability caps, and dispute resolution mechanism", case_id),
            self._intent("search_case_law", "contract_law_db",
                "Search: breach of contract Indian Contract Act 1872, specific performance, damages assessment", case_id),
            self._intent("calculate_damages", "damages_report",
                "Calculate financial losses from defective software delivery and contract breach", case_id),
            self._intent("draft_document", f"output/legal_notice_{case_id}.txt",
                "Draft legal notice invoking breach of contract, demanding compensation within 15 days", case_id),
            self._intent("prepare_strategy", "litigation_strategy",
                "Prepare litigation strategy: negotiation first, then Consumer Court / civil suit", case_id),
        ]

    def _plan_criminal(self, case_id: str, instr: str) -> list[IntentObject]:
        return [
            self._intent("review_evidence", "evidence_file",
                "Review all available evidence: FIR, arrest memo, alleged documents", case_id),
            self._intent("search_case_law", "criminal_law_db",
                "Search: bail jurisprudence BNSS Section 480/483, financial fraud BNS Section 318, wrongful arrest", case_id),
            self._intent("draft_bail_application", f"output/bail_application_{case_id}.txt",
                "Draft urgent bail application under BNSS Section 480 citing clean record and cooperation", case_id),
            self._intent("prepare_strategy", "defence_strategy",
                "Prepare defence strategy: challenge FIR validity, establish alibi, request document disclosure under BNSS Section 230", case_id),
            self._intent("advise_client", "client",
                "Advise client to exercise right to silence. Cooperate procedurally but do not answer questions without counsel present.", case_id),
        ]

    def _plan_general(self, case_id: str, instr: str) -> list[IntentObject]:
        return [
            self._intent("summarize_case", "case_summary", "Summarise the legal matter", case_id),
            self._intent("search_case_law", "legal_db", "Research applicable laws and precedents", case_id),
            self._intent("advise_client", "client", "Provide preliminary legal advisory", case_id),
        ]

    # ──────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────

    def _intent(self, action: str, target: str, content: str, case_id: str) -> IntentObject:
        return IntentObject(
            action=action,
            initiated_by=self.ROLE,
            target=target,
            content=content,
            case_id=case_id,
        )

    def spawn_research_agent(self, case_id: str):
        from agents.research_agent import ResearchAgent
        return ResearchAgent(
            executor=self.executor,
            case_store=self.case_store,
            delegated_by=self.ROLE,
            case_id=case_id,
        )
