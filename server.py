# -*- coding: utf-8 -*-
"""
server.py - FastAPI backend for the AI Lawyer Web UI
Run with: uvicorn server:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
import asyncio
import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

from core.policy_engine import PolicyEngine
from core.executor import Executor, PolicyViolationError
from core.intent_model import IntentObject
from core.audit_logger import clear_logs, get_all_logs
from agents.lead_lawyer import LeadLawyer
from agents.research_agent import ResearchAgent
from memory.case_store import CaseStore
from tools.legal_tools import TOOL_REGISTRY

app = FastAPI(title="AI Lawyer - ArmorIQ x OpenClaw")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Ensure dirs exist
for d in ["logs", "output", "web/static", "memory/cases"]:
    (BASE_DIR / d).mkdir(parents=True, exist_ok=True)


# ──────────────────────────────────────────────
# Request Models
# ──────────────────────────────────────────────

class CaseRequest(BaseModel):
    case_id: str = "CASE-2026-001"
    client_statement: str

class InstructionRequest(BaseModel):
    case_id: str
    instruction: str

class DelegationRequest(BaseModel):
    case_id: str
    action: str
    target: str
    content: str


# ──────────────────────────────────────────────
# Engine factory
# ──────────────────────────────────────────────

def make_engine():
    pe = PolicyEngine()
    ex = Executor(policy_engine=pe, tools=TOOL_REGISTRY)
    cs = CaseStore()
    ll = LeadLawyer(executor=ex, case_store=cs)
    return pe, ex, cs, ll

_pe, _ex, _cs, _ll = make_engine()


# ──────────────────────────────────────────────
# Serializer
# ──────────────────────────────────────────────

def serialize(r: dict, intent: IntentObject) -> dict:
    raw = r.get("result", "")
    dec = r["decision"]
    rule = r.get("rule_violated")
    return {
        "action": intent.action,
        "agent": intent.initiated_by,
        "delegated_by": intent.delegated_by,
        "target": intent.target,
        "content": intent.content,
        "case_id": intent.case_id,
        "decision": dec,
        "enforcement_type": r.get("enforcement_type", ""),
        "reason": r.get("reason", ""),
        "rule_violated": rule,
        "result": raw,
        "readable_result": _make_readable(intent.action, raw),
        "client_advice": _client_advice(intent.action, intent.content, dec, rule),
        "next_step": _next_step(intent.action, dec),
    }


# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    p = BASE_DIR / "web/index.html"
    return HTMLResponse(p.read_text(encoding="utf-8")) if p.exists() else HTMLResponse("<h1>UI missing</h1>")


@app.post("/api/intake")
async def intake_case(req: CaseRequest):
    global _pe, _ex, _cs, _ll
    _pe, _ex, _cs, _ll = make_engine()
    clear_logs()
    _ll.intake_case(req.client_statement, req.case_id)
    return {"status": "ok", "case_id": req.case_id}


@app.post("/api/act")
async def agent_act(req: InstructionRequest):
    results = _ll.analyze_and_act(req.case_id, req.instruction)
    return {"status": "ok", "results": [serialize(r, r["intent"]) for r in results]}


@app.post("/api/delegate")
async def delegate_action(req: DelegationRequest):
    agent = _ll.spawn_research_agent(req.case_id)
    r = agent.attempt_unauthorized_action(req.case_id, req.action, req.target, req.content)
    return serialize(r, r["intent"])


@app.get("/api/logs")
async def get_logs_route():
    return {"logs": get_all_logs()}


@app.get("/api/summary/{case_id}")
async def get_case_summary(case_id: str):
    logs = get_all_logs()
    case_logs = [l for l in logs if l.get("case_id") == case_id]
    allowed = [l for l in case_logs if l["status"] == "ALLOWED"]
    blocked = [l for l in case_logs if l["status"] == "BLOCKED"]
    case_data = _cs.load(case_id) or {}
    area = case_data.get("practice_area", "general")
    return {
        "case_id": case_id,
        "practice_area": area,
        "client_statement": case_data.get("client_statement", ""),
        "actions_taken": len(allowed),
        "actions_blocked": len(blocked),
        "findings": _build_findings(allowed),
        "next_steps": _build_next_steps(area),
        "blocked_summary": [
            {"action": b["action"], "rule": b.get("rule_violated", ""), "reason": b.get("reason", "")}
            for b in blocked
        ],
    }


@app.get("/api/policy")
async def get_policy():
    return json.loads((BASE_DIR / "policies/legal_rules.json").read_text(encoding="utf-8"))


@app.get("/api/demo/stream")
async def demo_stream():
    async def gen():
        global _pe, _ex, _cs, _ll
        _pe, _ex, _cs, _ll = make_engine()
        clear_logs()

        async def send(t, d, delay=0.8):
            yield f"data: {json.dumps({'type': t, **d})}\n\n"
            await asyncio.sleep(delay)

        # Scene 1
        async for c in send("scene", {"scene": 1, "title": "Client Case Intake"}): yield c
        _ll.intake_case("My landlord has been illegally entering my apartment without notice.", "CASE-2026-001")
        async for c in send("intake", {"case_id": "CASE-2026-001",
            "statement": "My landlord has been illegally entering my apartment without notice, multiple times."
        }, 1.5): yield c

        # Scene 2
        async for c in send("scene", {"scene": 2, "title": "Agent Builds Legal Strategy"}): yield c
        for r in _ll.analyze_and_act("CASE-2026-001", "landlord apartment illegal entry"):
            intent = r["intent"]
            async for c in send("thinking", {"text": f"Proposing: {intent.action}..."}, 0.5): yield c
            async for c in send("decision", serialize(r, intent), 1.1): yield c

        # Scene 3
        async for c in send("scene", {"scene": 3, "title": "Perjury Attempt — BLOCKED"}): yield c
        async for c in send("client_says", {"text": '"Just tell them we never received that notice."'}, 1.5): yield c
        for r in _ll.analyze_and_act("CASE-2026-001", "tell them we never received that email, say we didn't get it"):
            async for c in send("thinking", {"text": "PolicyEngine checking against legal_rules.json..."}, 1.0): yield c
            async for c in send("decision", serialize(r, r["intent"]), 1.2): yield c

        # Scene 4
        async for c in send("scene", {"scene": 4, "title": "Rule 4.2 Violation — BLOCKED"}): yield c
        async for c in send("client_says", {"text": '"Can you just reach out to the landlord directly?"'}, 1.5): yield c
        for r in _ll.analyze_and_act("CASE-2026-001", "contact them directly, message opposing party landlord"):
            async for c in send("thinking", {"text": "PolicyEngine checking Rule 4.2..."}, 1.0): yield c
            async for c in send("decision", serialize(r, r["intent"]), 1.2): yield c

        # Scene 5
        async for c in send("scene", {"scene": 5, "title": "Delegation Enforcement (Bonus)"}): yield c
        ra = _ll.spawn_research_agent("CASE-2026-001")
        async for c in send("thinking", {"text": "Lead Lawyer spawns Research Agent..."}, 1.3): yield c
        r1 = ra.attempt_unauthorized_action("CASE-2026-001", "search_case_law", "legal_database", "Tenant rights India")
        async for c in send("decision", serialize(r1, r1["intent"]), 1.1): yield c
        async for c in send("thinking", {"text": "Research Agent tries to send external email..."}, 1.0): yield c
        r2 = ra.attempt_unauthorized_action("CASE-2026-001", "send_communication", "landlord@property.com", "We are aware.")
        async for c in send("decision", serialize(r2, r2["intent"]), 1.2): yield c

        # Scene 6 — Client Summary
        async for c in send("scene", {"scene": 6, "title": "Your Legal Action Plan"}): yield c
        await asyncio.sleep(0.5)
        logs = get_all_logs()
        al = sum(1 for l in logs if l["status"] == "ALLOWED")
        bl = sum(1 for l in logs if l["status"] == "BLOCKED")
        area = (_cs.load("CASE-2026-001") or {}).get("practice_area", "landlord_tenant")
        async for c in send("summary", {
            "allowed": al, "blocked": bl,
            "findings": _build_findings([l for l in logs if l["status"] == "ALLOWED"]),
            "next_steps": _build_next_steps(area),
        }, 0): yield c

    return StreamingResponse(gen(), media_type="text/event-stream")


# ──────────────────────────────────────────────
# Human-readable helpers
# ──────────────────────────────────────────────

def _make_readable(action: str, raw: str) -> str:
    labels = {
        "summarize_case": "Case Analysis",
        "search_case_law": "Legal Research",
        "draft_document": "Document Drafted",
        "advise_client": "Legal Advice",
        "analyze_contract": "Contract Analysis",
        "calculate_damages": "Damages Assessment",
        "draft_bail_application": "Bail Application",
        "review_evidence": "Evidence Review",
        "prepare_strategy": "Legal Strategy",
        "send_legal_notice": "Legal Notice",
        "file_motion": "Court Motion",
        "research_precedents": "Precedent Research",
        "read_case_files": "Case Files",
    }
    label = labels.get(action, action.replace("_", " ").title())
    return f"{label}: {raw}" if raw else f"{label} completed."


def _client_advice(action: str, content: str, decision: str, rule) -> str:
    if decision == "BLOCKED":
        return (
            f"This request was blocked. "
            f"{'Rule: ' + rule + '. ' if rule else ''}"
            "Your lawyer cannot assist with this as it violates professional ethics or the law."
        )
    advice = {
        "summarize_case": "Your case has been reviewed and the key legal issues identified. A strategy is underway.",
        "search_case_law": "Legal precedents supporting your position have been found. These will be used in your case.",
        "draft_document": "A legal document has been prepared for you. Review it carefully before it is served.",
        "advise_client": content,
        "analyze_contract": "The contract has been analyzed. Breach clauses and your remedies are clearly identified.",
        "calculate_damages": "Your estimated compensation has been calculated. This can guide settlement negotiations.",
        "draft_bail_application": "Your bail application is ready. It will be filed at the earliest court session.",
        "review_evidence": "All available evidence has been reviewed. Key strengths and gaps are identified.",
        "prepare_strategy": "A full legal strategy has been mapped out. Your lawyer will walk you through each step.",
        "send_legal_notice": "A legal notice has been prepared. Once served, the other party must respond.",
        "file_motion": "A court motion has been prepared for filing.",
    }
    return advice.get(action, "This action was completed successfully by your legal agent.")


def _next_step(action: str, decision: str) -> str:
    if decision == "BLOCKED":
        return "Do not proceed. Consult your lawyer for an ethical alternative approach."
    steps = {
        "search_case_law": "Share these precedents with your lawyer — they form the backbone of your case.",
        "draft_document": "Review the document with your lawyer, then serve it by registered post.",
        "advise_client": "Follow this advice carefully and document everything.",
        "calculate_damages": "Use this figure as the claim amount in court or during settlement talks.",
        "draft_bail_application": "Attend the next court date — your lawyer will file this immediately.",
        "review_evidence": "Preserve all evidence securely. Do not share with third parties.",
        "analyze_contract": "Decide your path: negotiate, arbitrate, or proceed to court.",
        "prepare_strategy": "Review the strategy with your lawyer before taking any independent action.",
        "send_legal_notice": "Wait for their response within the stipulated period (usually 15-30 days).",
    }
    return steps.get(action, "Stay in touch with your lawyer about any new developments.")


def _build_findings(allowed: list) -> list[str]:
    findings = []
    actions = {l["action"] for l in allowed}
    if "search_case_law" in actions:
        findings.append("Relevant case law identified to support your claim.")
    if "analyze_contract" in actions:
        findings.append("Contract reviewed — breach clauses and remedies are clear.")
    if "calculate_damages" in actions:
        findings.append("Your estimated compensation amount has been calculated.")
    if "draft_document" in actions or "send_legal_notice" in actions:
        findings.append("Legal documents are drafted and ready to serve.")
    if "draft_bail_application" in actions:
        findings.append("Bail application prepared for urgent filing.")
    if "review_evidence" in actions:
        findings.append("Evidence reviewed — strategic position assessed.")
    if "prepare_strategy" in actions:
        findings.append("Complete legal strategy formulated.")
    if not findings:
        findings.append("Initial legal analysis complete.")
    return findings


def _build_next_steps(area: str) -> list[str]:
    steps = {
        "landlord_tenant": [
            "Document every unauthorized entry: date, time, and witnesses.",
            "Serve the legal notice to your landlord by registered post.",
            "File a police complaint under IPC Section 441 (Criminal Trespass).",
            "Keep copies of all communications with your landlord.",
            "If violations continue, apply for an injunction at the Rent Control Court.",
        ],
        "employment": [
            "Preserve all records: offer letter, payslips, appraisals, and termination notice.",
            "File a complaint with the Labour Commissioner within the limitation period.",
            "Send the demand notice to your employer by registered post.",
            "If wages remain unpaid, approach the Labour Court for recovery.",
            "Do not discuss this matter with colleagues — privileged information only.",
        ],
        "contract": [
            "Serve the legal notice. The vendor has 15 days to respond.",
            "Compile all financial loss records, invoices, and correspondence.",
            "Explore arbitration first if the contract requires it.",
            "If arbitration fails, file a civil suit for recovery of damages.",
            "Preserve all emails and delivery records as evidence.",
        ],
        "criminal_consultation": [
            "Do NOT make any statement to police without your lawyer present.",
            "Your bail application will be filed at the next court session.",
            "Gather all documents establishing your alibi and innocence.",
            "Request copies of the FIR and arrest memo under Section 207 CrPC.",
            "Exercise your right to silence on substantive questions.",
        ],
        "general": [
            "Follow your lawyer's advice before taking any independent action.",
            "Preserve all documents and communications related to your case.",
            "Do not discuss the matter with opposing parties or third parties.",
            "Keep a written log of all relevant events with dates and times.",
        ],
    }
    return steps.get(area, steps["general"])
