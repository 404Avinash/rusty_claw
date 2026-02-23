# -*- coding: utf-8 -*-
"""
server.py - FastAPI backend for the AI Lawyer Web UI
Wraps the existing core engine (PolicyEngine, Executor, Agents) as REST API + SSE stream.

Run with: uvicorn server:app --reload --port 8000
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import asyncio
import json
import time
import uuid
from pathlib import Path

from core.policy_engine import PolicyEngine
from core.executor import Executor, PolicyViolationError
from core.intent_model import IntentObject
from core.audit_logger import clear_logs, get_all_logs
from agents.lead_lawyer import LeadLawyer
from agents.research_agent import ResearchAgent
from memory.case_store import CaseStore
from tools.legal_tools import TOOL_REGISTRY

app = FastAPI(title="AI Lawyer - ArmorIQ x OpenClaw")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
static_dir = Path("web/static")
static_dir.mkdir(parents=True, exist_ok=True)


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
# Engine factory (fresh state per session is fine for demo)
# ──────────────────────────────────────────────

def make_engine():
    policy_engine = PolicyEngine()
    executor = Executor(policy_engine=policy_engine, tools=TOOL_REGISTRY)
    case_store = CaseStore()
    lawyer = LeadLawyer(executor=executor, case_store=case_store)
    return policy_engine, executor, case_store, lawyer

_policy_engine, _executor, _case_store, _lawyer = make_engine()


# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    html_path = Path("web/index.html")
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>UI not found. Place web/index.html</h1>")


@app.post("/api/intake")
async def intake_case(req: CaseRequest):
    """Register a new client case."""
    global _policy_engine, _executor, _case_store, _lawyer
    _policy_engine, _executor, _case_store, _lawyer = make_engine()
    clear_logs()
    _lawyer.intake_case(req.client_statement, req.case_id)
    return {"status": "ok", "case_id": req.case_id, "message": "Case registered successfully."}


@app.post("/api/act")
async def agent_act(req: InstructionRequest):
    """Agent analyzes instruction, proposes and executes actions."""
    results = _lawyer.analyze_and_act(req.case_id, req.instruction)
    output = []
    for r in results:
        intent = r["intent"]
        output.append({
            "action": intent.action,
            "agent": intent.initiated_by,
            "delegated_by": intent.delegated_by,
            "target": intent.target,
            "content": intent.content,
            "case_id": intent.case_id,
            "decision": r["decision"],
            "enforcement_type": r.get("enforcement_type", ""),
            "reason": r.get("reason", ""),
            "rule_violated": r.get("rule_violated"),
            "result": r.get("result", ""),
        })
    return {"status": "ok", "results": output}


@app.post("/api/delegate")
async def delegate_action(req: DelegationRequest):
    """Spawn research sub-agent and attempt an action (for delegation demo)."""
    research_agent = _lawyer.spawn_research_agent(req.case_id)
    result = research_agent.attempt_unauthorized_action(
        req.case_id, req.action, req.target, req.content
    )
    intent = result["intent"]
    return {
        "action": intent.action,
        "agent": intent.initiated_by,
        "delegated_by": intent.delegated_by,
        "target": intent.target,
        "content": intent.content,
        "case_id": intent.case_id,
        "decision": result["decision"],
        "enforcement_type": result.get("enforcement_type", ""),
        "reason": result.get("reason", ""),
        "rule_violated": result.get("rule_violated"),
        "result": result.get("result", ""),
    }


@app.get("/api/logs")
async def get_logs():
    """Return all audit log entries."""
    return {"logs": get_all_logs()}


@app.get("/api/policy")
async def get_policy():
    """Return the current policy rulebook."""
    import json
    from pathlib import Path
    policy = json.loads(Path("policies/legal_rules.json").read_text(encoding="utf-8"))
    return policy


@app.get("/api/demo/stream")
async def demo_stream():
    """
    Server-Sent Events stream that replays the full 3-minute demo sequence.
    Frontend subscribes to this and animates each event as it arrives.
    """
    async def event_generator():
        global _policy_engine, _executor, _case_store, _lawyer
        _policy_engine, _executor, _case_store, _lawyer = make_engine()
        clear_logs()

        async def send(event_type: str, data: dict, delay: float = 0.8):
            yield f"data: {json.dumps({'type': event_type, **data})}\n\n"
            await asyncio.sleep(delay)

        # Scene 1
        async for chunk in send("scene", {"scene": 1, "title": "Client Case Intake"}): yield chunk
        _lawyer.intake_case("My landlord has been illegally entering my apartment without notice.", "CASE-2026-001")
        async for chunk in send("intake", {
            "case_id": "CASE-2026-001",
            "statement": "My landlord has been illegally entering my apartment without notice, multiple times in the past month. I want to take legal action."
        }, delay=1.5): yield chunk

        # Scene 2
        async for chunk in send("scene", {"scene": 2, "title": "Agent Builds Strategy"}): yield chunk
        results = _lawyer.analyze_and_act("CASE-2026-001", "landlord apartment illegal entry")
        for r in results:
            intent = r["intent"]
            async for chunk in send("thinking", {"text": f"Validating: {intent.action}..."}, delay=0.5): yield chunk
            async for chunk in send("decision", {
                "action": intent.action,
                "agent": intent.initiated_by,
                "target": intent.target,
                "content": intent.content,
                "decision": r["decision"],
                "enforcement_type": r.get("enforcement_type", ""),
                "reason": r.get("reason", ""),
                "rule_violated": r.get("rule_violated"),
                "result": r.get("result", ""),
            }, delay=1.0): yield chunk

        # Scene 3
        async for chunk in send("scene", {"scene": 3, "title": "Perjury Attempt - BLOCKED"}): yield chunk
        async for chunk in send("client_says", {
            "text": "\"Just tell them we never received that notice. Say we didn't get it.\""
        }, delay=1.5): yield chunk
        results3 = _lawyer.analyze_and_act("CASE-2026-001", "tell them we never received that email, say we didn't get it")
        for r in results3:
            intent = r["intent"]
            async for chunk in send("thinking", {"text": "PolicyEngine checking against legal_rules.json..."}, delay=1.0): yield chunk
            async for chunk in send("decision", {
                "action": intent.action,
                "agent": intent.initiated_by,
                "target": intent.target,
                "content": intent.content,
                "decision": r["decision"],
                "enforcement_type": r.get("enforcement_type", ""),
                "reason": r.get("reason", ""),
                "rule_violated": r.get("rule_violated"),
                "result": r.get("result", ""),
            }, delay=1.2): yield chunk

        # Scene 4
        async for chunk in send("scene", {"scene": 4, "title": "Rule 4.2 Violation - BLOCKED"}): yield chunk
        async for chunk in send("client_says", {
            "text": "\"Can you just reach out to the landlord directly and sort this out?\""
        }, delay=1.5): yield chunk
        results4 = _lawyer.analyze_and_act("CASE-2026-001", "contact them directly, message opposing party landlord")
        for r in results4:
            intent = r["intent"]
            async for chunk in send("thinking", {"text": "PolicyEngine checking Rule 4.2..."}, delay=1.0): yield chunk
            async for chunk in send("decision", {
                "action": intent.action,
                "agent": intent.initiated_by,
                "target": intent.target,
                "content": intent.content,
                "decision": r["decision"],
                "enforcement_type": r.get("enforcement_type", ""),
                "reason": r.get("reason", ""),
                "rule_violated": r.get("rule_violated"),
                "result": r.get("result", ""),
            }, delay=1.2): yield chunk

        # Scene 5 - Delegation
        async for chunk in send("scene", {"scene": 5, "title": "Delegation Enforcement (Bonus)"}): yield chunk
        research_agent = _lawyer.spawn_research_agent("CASE-2026-001")

        async for chunk in send("thinking", {"text": "Lead Lawyer spawns Research Agent with scoped permissions..."}, delay=1.5): yield chunk

        r_allowed = research_agent.attempt_unauthorized_action(
            "CASE-2026-001", "search_case_law", "legal_database", "Tenant rights illegal landlord entry India"
        )
        intent_a = r_allowed["intent"]
        async for chunk in send("decision", {
            "action": intent_a.action,
            "agent": intent_a.initiated_by,
            "delegated_by": intent_a.delegated_by,
            "target": intent_a.target,
            "content": intent_a.content,
            "decision": r_allowed["decision"],
            "enforcement_type": r_allowed.get("enforcement_type", ""),
            "reason": r_allowed.get("reason", ""),
            "rule_violated": r_allowed.get("rule_violated"),
            "result": r_allowed.get("result", ""),
        }, delay=1.2): yield chunk

        async for chunk in send("thinking", {"text": "Research Agent tries to send an email..."}, delay=1.0): yield chunk

        r_blocked = research_agent.attempt_unauthorized_action(
            "CASE-2026-001", "send_communication", "landlord@property.com",
            "We know about the situation and are taking action."
        )
        intent_b = r_blocked["intent"]
        async for chunk in send("decision", {
            "action": intent_b.action,
            "agent": intent_b.initiated_by,
            "delegated_by": intent_b.delegated_by,
            "target": intent_b.target,
            "content": intent_b.content,
            "decision": r_blocked["decision"],
            "enforcement_type": r_blocked.get("enforcement_type", ""),
            "reason": r_blocked.get("reason", ""),
            "rule_violated": r_blocked.get("rule_violated"),
            "result": r_blocked.get("result", ""),
        }, delay=1.2): yield chunk

        # Done
        logs = get_all_logs()
        allowed = sum(1 for l in logs if l["status"] == "ALLOWED")
        blocked = sum(1 for l in logs if l["status"] == "BLOCKED")
        async for chunk in send("done", {"allowed": allowed, "blocked": blocked}, delay=0): yield chunk

    return StreamingResponse(event_generator(), media_type="text/event-stream")
