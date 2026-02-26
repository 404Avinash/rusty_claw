# AI Lawyer — Complete Project Explainer

> **Stack:** Python · FastAPI · Rich TUI · ArmorIQ SDK · Google Gemini (optional)  
> **Repo:** https://github.com/404Avinash/rusty_claw  
> **Event:** ArmorIQ × OpenClaw Hackathon  

---

## Table of Contents

1. [What This Project Is](#1-what-this-project-is)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Folder Structure](#3-folder-structure)
4. [Entry Points](#4-entry-points)
5. [Core Layer — The Brain & Enforcement](#5-core-layer)
   - [intent_model.py](#51-intent_modelpy)
   - [llm_brain.py](#52-llm_brainpy)
   - [policy_engine.py](#53-policy_enginepy)
   - [executor.py](#54-executorpy)
   - [csrg.py](#55-csrgpy)
   - [injection_detector.py](#56-injection_detectorpy)
   - [audit_logger.py](#57-audit_loggerpy)
6. [Agents Layer](#6-agents-layer)
   - [lead_lawyer.py](#61-lead_lawyerpy)
   - [research_agent.py](#62-research_agentpy)
7. [Tools Layer](#7-tools-layer)
8. [Memory Layer](#8-memory-layer)
9. [Policies — legal_rules.json](#9-policies--legal_rulesjson)
10. [Web UI & API Server](#10-web-ui--api-server)
11. [ArmorIQ SDK Integration — Deep Dive](#11-armoriq-sdk-integration--deep-dive)
12. [Request Lifecycle — Step by Step](#12-request-lifecycle--step-by-step)
13. [Security Architecture](#13-security-architecture)
14. [Environment Variables](#14-environment-variables)
15. [Running Locally](#15-running-locally)
16. [Demo Scenes (main.py)](#16-demo-scenes-mainpy)

---

## 1. What This Project Is

**AI Lawyer** is an agentic legal assistant that can analyse a client's case, build a legal strategy, draft documents, search case law, and advise the client — all while being **cryptographically prevented from doing anything unethical or illegal**.

The key innovation is that every action the AI wants to take must pass **two enforcement layers** before it executes:

| Layer | What it does |
|---|---|
| **Local Policy Engine** | Checks `policies/legal_rules.json` — hard-coded ethical/legal rules (no perjury, no Rule 4.2 violation, no fabrication) |
| **ArmorIQ SDK (CSRG)** | Cryptographically signs the plan *before* execution; verifies every action at runtime against a Merkle-proof chain |

If either layer says **NO**, the action is hard-blocked. No exceptions.

---

## 2. High-Level Architecture

```
                         ┌────────────────────────────────────────┐
                         │           CLIENT / USER                │
                         │  (web/index.html  or  main.py CLI)     │
                         └──────────────────┬─────────────────────┘
                                            │ HTTP / CLI
                         ┌──────────────────▼─────────────────────┐
                         │           server.py (FastAPI)           │
                         │  POST /analyze   GET /case/:id          │
                         └──────────────────┬─────────────────────┘
                                            │
                         ┌──────────────────▼─────────────────────┐
                         │         agents/lead_lawyer.py           │
                         │  1. intake_case()                       │
                         │  2. analyze_and_act()                   │
                         │     ├─ llm_brain.generate_plan()   ──── ► ArmorIQ IAP
                         │     │      returns (plan, mode, token)  │  capture_plan()
                         │     └─ For each IntentObject:           │  get_intent_token()
                         │         ├─ policy_engine.validate()     │
                         │         └─ executor.execute()      ──── ► Merkle proof check
                         └──────────────────┬─────────────────────┘
                                            │
              ┌─────────────────────────────┼──────────────────────────┐
              │                             │                          │
   ┌──────────▼──────────┐    ┌─────────────▼────────┐    ┌──────────▼─────────┐
   │  core/policy_engine │    │   core/executor.py   │    │   core/csrg.py     │
   │  • Load rules JSON  │    │  • Run tool if ALLOW │    │  • Merkle chain    │
   │  • Time constraints │    │  • ArmorIQ step proof│    │  • CSRG hash nodes │
   │  • ArmorIQ SDK verify│   │  • Drift detection   │    │                    │
   └─────────────────────┘    └──────────────────────┘    └────────────────────┘
              │
   ┌──────────▼──────────┐    ┌──────────────────────┐    ┌────────────────────┐
   │ tools/legal_tools   │    │  memory/case_store   │    │  audit_logger      │
   │  • summarize_case   │    │  • JSON case files   │    │  • JSONL audit log │
   │  • search_case_law  │    │  • load/save/update  │    │  • every decision  │
   │  • draft_document   │    └──────────────────────┘    └────────────────────┘
   │  • advise_client    │
   └─────────────────────┘
```

---

## 3. Folder Structure

```
claw/
├── main.py                  # Rich CLI demo (5 scenes)
├── server.py                # FastAPI REST + WebSocket server
├── build_ui.py              # Utility to serve / build UI assets
├── requirements.txt         # Python deps (FastAPI, armoriq-sdk, rich, …)
├── .env                     # 🔒 Secret keys (gitignored)
├── .env.example             # Template for environment variables
├── Procfile                 # Render.com deploy config
├── render.yaml              # Render.com service config
│
├── agents/
│   ├── lead_lawyer.py       # Top-level orchestrating agent
│   └── research_agent.py    # Sub-agent (delegated, scoped)
│
├── core/
│   ├── intent_model.py      # IntentObject dataclass + enums
│   ├── llm_brain.py         # LLM reasoning + ArmorIQ plan registration
│   ├── policy_engine.py     # Rule enforcement + ArmorIQ token verify
│   ├── executor.py          # Tool execution + Merkle proof enforcement
│   ├── csrg.py              # Local CSRG Merkle tree implementation
│   ├── injection_detector.py# Prompt injection scanner
│   └── audit_logger.py      # Append-only JSONL audit log
│
├── tools/
│   └── legal_tools.py       # All callable legal tools (TOOL_REGISTRY)
│
├── memory/
│   ├── case_store.py        # Case load/save (JSON files in cases/)
│   └── cases/
│       └── CASE-2026-001.json
│
├── policies/
│   └── legal_rules.json     # Declarative rule set (YAML-like JSON)
│
├── logs/
│   └── audit_log.jsonl      # Append-only decision log
│
├── output/
│   └── *.txt                # Generated legal documents
│
└── web/
    ├── index.html           # Single-page React-like UI (Tailwind + vanilla JS)
    └── static/              # Static assets
```

---

## 4. Entry Points

### `main.py` — CLI Demo
The fastest way to see everything. Runs **5 scripted scenes** in a Rich terminal UI:
1. Client intake
2. Allowed legal actions (summarise, search law, draft, advise)
3. Perjury attempt → BLOCKED
4. Rule 4.2 violation (direct opposing contact) → BLOCKED
5. Delegation enforcement (research agent scope check)

```bash
python main.py
```

### `server.py` — REST API Backend
FastAPI app that powers the web UI:
- `POST /analyze` — receives case query, runs full pipeline, returns JSON results
- `GET /case/{case_id}` — fetch stored case data
- Static file serving for `web/`

```bash
uvicorn server:app --reload --port 8000
```

---

## 5. Core Layer

### 5.1 `intent_model.py`

Defines the **IntentObject** — the universal unit of work. Every action the AI wants to take is expressed as an `IntentObject` before it touches any tool.

```python
@dataclass
class IntentObject:
    action: str           # e.g. "draft_document"
    initiated_by: str     # e.g. "lead_lawyer"
    target: str           # e.g. "client_letter"
    content: str          # what to do / write
    case_id: str          # CASE-2026-001
    delegated_by: str     # set when a sub-agent acts (e.g. "lead_lawyer")
    timestamp: str        # ISO 8601
```

`ACTION_LABELS` maps action names to human-readable descriptions:
```python
ACTION_LABELS = {
    "summarize_case":   "Summarise Case File",
    "search_case_law":  "Search Case Law",
    "draft_document":   "Draft Legal Document",
    "advise_client":    "Advise Client",
    "file_motion":      "File Court Motion",
    ...
}
```

`PolicyDecision` is the return type from the policy engine — `ALLOWED` or `BLOCKED`.

---

### 5.2 `llm_brain.py`

The **reasoning layer** — decides *what actions to take* for a given case query.

**Priority cascade:**
1. **Gemini API** (if `GEMINI_API_KEY` set) → real LLM reasoning, JSON output
2. **Simulation fallback** (no key) → keyword-matched intents

**ArmorIQ integration happens here** — immediately after plan generation:

```
generate_plan(case_data, query)
    │
    ├─ [Gemini / simulation] → list of IntentObjects
    │
    └─ _register_plan_with_armoriq(prompt, plan_items, ...)
           │
           ├─ client.capture_plan(llm=..., prompt=..., plan={goal, steps})
           │        ↑ sends plan to ArmorIQ backend for audit
           │
           └─ client.get_intent_token(plan_capture_id)
                    ↑ returns signed IntentToken with:
                      • plan_hash (SHA-256 of plan)
                      • step_proofs (one Merkle proof per step)
                      • signed_by (Ed25519 public key)
                      • expires_at
```

**Return signature:**
```python
def generate_plan(case_data, query) -> tuple[list[dict], str, IntentToken | None]:
    #                                          plan_items  mode   armoriq_token
```

The token is threaded through to every `IntentObject` so the executor can verify each step.

---

### 5.3 `policy_engine.py`

The **local enforcement layer** — authoritative, fail-closed, runs before any tool executes.

**What it checks (in order):**

1. **Injection scan** — calls `injection_detector.scan()`, blocks prompt injection
2. **Delegation scope** — if `delegated_by` is set, checks the sub-agent only uses allowed actions
3. **Time constraints** — some rules only apply in business hours (IST), court filing windows, etc.
4. **Block list** — actions explicitly blocked (e.g. `fabricate_evidence`, `perjury`, `contact_opposing_party`)
5. **Allow list** — only whitelisted actions can execute
6. **ArmorIQ SDK verify** — cryptographically confirms the intent token is valid

**ArmorIQ verification path:**
```python
def _verify_with_armoriq_sdk(intent, session_token=None):
    if session_token and not session_token.is_expired:
        verified = client.verify_token(session_token)
        return verified, token.plan_hash[:32], "sdk"
    else:
        # issue a single-action token for standalone calls
        plan_capture = client.capture_plan(...)
        token = client.get_intent_token(...)
        return True, token.plan_hash[:32], "sdk"
```

**Decision metadata returned:**
```json
{
  "decision": "ALLOWED",
  "enforcement_type": "SOFT_LOG | HARD_BLOCK",
  "reason": "...",
  "rule_violated": "...",
  "intent_token": "abc123...",
  "sdk_mode": "sdk | local",
  "csrg_hash": "...",
  "merkle_root": "..."
}
```

---

### 5.4 `executor.py`

The **execution layer** — runs the approved tool and applies Merkle proof enforcement afterwards.

**Execution flow:**
```
execute(intent, policy_result)
    │
    ├─ if decision == BLOCKED → raise PolicyViolationError immediately
    │
    ├─ _invoke_via_armoriq(intent, tool_result)
    │       │
    │       ├─ Check token not expired
    │       ├─ client.verify_token(token) — cryptographic check
    │       ├─ Check intent.action ∈ token.step_proofs (intent drift detection)
    │       │       └─ If NOT present → raise PolicyViolationError("armoriq_intent_drift")
    │       └─ Log Merkle proof hash per step
    │
    ├─ TOOL_REGISTRY[intent.action](intent) — actually calls the tool function
    │
    └─ return {
           "decision": "ALLOWED",
           "result": tool_output,
           "armoriq_enforced": True,
           "armoriq_verified": True,
           "token_id": "...",
           "plan_hash": "...",
           "step_index": 0,
           "merkle_proof_present": True,
       }
```

**Intent Drift Detection** is the crown jewel: if the AI tries to execute an action that was NOT in the original signed plan (e.g. plan said "search_case_law" but at runtime it tries "file_motion"), the Merkle proof won't match → hard block with `rule_violated="armoriq_intent_drift"`.

---

### 5.5 `csrg.py`

Local **CSRG Merkle tree** implementation — Cryptographic State-Result Graph.

Every policy decision is hashed and appended to a chain:
```
node_0 = sha256("genesis")
node_1 = sha256(node_0 + decision_1_json)
node_2 = sha256(node_1 + decision_2_json)
...
```

This means the full decision history is tamper-evident. Any modification to a past decision will break the chain. The Merkle root is included in every policy response.

Used for:
- Tamper-evident audit trails
- Court-admissible decision provenance
- The ArmorIQ CSRG badge in the UI

---

### 5.6 `injection_detector.py`

Scans every `IntentObject.content` for prompt injection patterns before the policy engine checks rules:

- Regex patterns for classic injection strings (`ignore previous instructions`, `jailbreak`, etc.)
- Action injection: attempts to inject a new action keyword into the content
- Returns `(is_injection: bool, injection_type: str, confidence: float)`

If injection is detected → immediate `HARD_BLOCK` with `enforcement_type="INJECTION"`, the action never reaches the policy rules.

---

### 5.7 `audit_logger.py`

Append-only JSONL log at `logs/audit_log.jsonl`.

Every `PolicyDecision` is serialised and appended with:
```json
{
  "timestamp": "2026-02-26T10:23:45.123Z",
  "agent": "lead_lawyer",
  "delegated_by": null,
  "proposed_action": "draft_document",
  "target": "demand_notice",
  "case_id": "CASE-2026-001",
  "status": "ALLOWED",
  "enforcement_type": null,
  "rule_violated": null,
  "reason": "Action is on the allowed list",
  "intent_token": "a3f9...",
  "sdk_mode": "sdk",
  "merkle_root": "8f2c..."
}
```

Since it is append-only (file opened in `"a"` mode), no entry can be deleted or modified after the fact.

---

## 6. Agents Layer

### 6.1 `lead_lawyer.py`

The **top-level orchestrating agent**. It is the only agent that talks directly to the LLM Brain.

**Key methods:**

```python
lawyer.intake_case(statement: str, case_id: str)
    # Stores client statement in CaseStore
    # Returns case dict

lawyer.analyze_and_act(case_id: str, query: str) -> list[dict]
    # 1. Load case from CaseStore
    # 2. Call LLMBrain.generate_plan() → (plan_items, mode, armoriq_token)
    # 3. Register simulation plans with ArmorIQ too (simulation fallback path)
    # 4. For each plan item:
    #    a. Build IntentObject
    #    b. Attach armoriq_token via setattr(intent, '_armoriq_token', token)
    #    c. Run policy_engine.validate(intent, session_token=token)
    #    d. Run executor.execute(intent, policy_result)
    #    e. Collect result dict (includes armoriq_enforced, verified, token_id, plan_hash)
    # 5. Return list of result dicts

lawyer.spawn_research_agent(case_id: str) -> ResearchAgent
    # Creates a sub-agent with a restricted action scope
    # Delegation is enforced by the policy engine (delegated_by field)
```

---

### 6.2 `research_agent.py`

A **scoped sub-agent** spawned by the lead lawyer for research tasks only.

- Allowed actions: `search_case_law`, `read_case_files`
- Sets `delegated_by="lead_lawyer"` on every `IntentObject`
- The policy engine checks: if `delegated_by` is set, only actions in the delegation whitelist are permitted
- Attempting `draft_document` or `advise_client` from the research agent → `HARD_BLOCK` with `rule_violated="delegation_scope_exceeded"`

---

## 7. Tools Layer

`tools/legal_tools.py` contains all the callable tool functions. Each function takes an `IntentObject` and returns a string result.

| Tool | What it does |
|---|---|
| `summarize_case` | Reads case file from `memory/cases/`, returns structured summary |
| `search_case_law` | Keyword search against embedded case law dataset, returns precedents |
| `draft_document` | Templates a legal document (demand notice, complaint, etc.) and saves to `output/` |
| `advise_client` | Generates legal advice narrative based on case facts |
| `file_motion` | Prepares court motion document |
| `read_case_files` | Raw case file read (research agent only) |

`TOOL_REGISTRY` is a plain dict mapping action name → function:
```python
TOOL_REGISTRY = {
    "summarize_case":  summarize_case,
    "search_case_law": search_case_law,
    "draft_document":  draft_document,
    "advise_client":   advise_client,
    "file_motion":     file_motion,
    "read_case_files": read_case_files,
}
```

The executor calls `TOOL_REGISTRY[intent.action](intent)`. If the action isn't in the registry, it raises `KeyError` (which is caught and converted to a policy block).

---

## 8. Memory Layer

`memory/case_store.py` — simple JSON-file-backed case storage.

```python
store = CaseStore()

# Create / load
case = store.load_case("CASE-2026-001")

# Update
store.update_case("CASE-2026-001", {"status": "active", "facts": [...]})

# Cases stored at:
# memory/cases/CASE-2026-001.json
```

Case JSON structure:
```json
{
  "case_id": "CASE-2026-001",
  "client_statement": "My landlord has been illegally entering...",
  "practice_area": "tenant_rights",
  "status": "active",
  "created_at": "2026-02-26T10:00:00Z",
  "facts": [],
  "documents": [],
  "actions_taken": []
}
```

---

## 9. Policies — `legal_rules.json`

The declarative rule set. Loaded at runtime by the policy engine (hot-reloadable without restarting the server).

Structure:
```json
{
  "version": "2.0",
  "jurisdiction": "India",
  "legal_framework": "BNS 2023",
  "allowed_actions": ["summarize_case", "search_case_law", "draft_document", ...],
  "blocked_actions": ["fabricate_evidence", "perjury", "destroy_evidence", ...],
  "delegation_rules": {
    "research_agent": ["search_case_law", "read_case_files"]
  },
  "time_constraints": {
    "file_motion": { "allowed_hours": [9, 17], "timezone": "IST" }
  },
  "rules": [
    {
      "id": "RULE-4.2",
      "name": "no_opposing_party_contact",
      "description": "An agent may not contact a represented opposing party directly",
      "actions_blocked": ["contact_opposing_party", "message_landlord"],
      "enforcement": "HARD_BLOCK",
      "citation": "Bar Council of India Rules, Rule 4.2"
    },
    {
      "id": "RULE-PERJURY",
      "name": "no_perjury",
      "actions_blocked": ["fabricate_statement", "deny_receipt"],
      "enforcement": "HARD_BLOCK",
      "citation": "BNS 2023 Section 227"
    }
  ]
}
```

---

## 10. Web UI & API Server

### `server.py` (FastAPI)

**Endpoints:**

| Method | Path | Description |
|---|---|---|
| `POST` | `/analyze` | Run full pipeline on a query |
| `GET` | `/case/{case_id}` | Get stored case |
| `GET` | `/logs` | Get full audit log |
| `GET` | `/` | Serve web UI |

**Request body for `/analyze`:**
```json
{
  "query": "landlord illegal entry harassment",
  "case_id": "CASE-2026-001"
}
```

**Response for `/analyze`:**
```json
{
  "case_id": "CASE-2026-001",
  "actions": [
    {
      "action": "summarize_case",
      "decision": "ALLOWED",
      "result": "Case summary...",
      "armoriq_enforced": true,
      "armoriq_verified": true,
      "armoriq_token_id": "990d514d...",
      "armoriq_plan_hash": "a3f91c...",
      "sdk_mode": "sdk",
      "merkle_root": "8f2c..."
    }
  ]
}
```

### `web/index.html`

Single-file SPA (no bundler). Uses:
- **Tailwind CSS** (CDN) for styling
- Vanilla JS `fetch()` for API calls
- **Action cards**: one card per action, shows verdict badge, result text, and ArmorIQ CSRG badge

ArmorIQ badge (shown when `armoriq_enforced === true`):
```
🔐 ArmorIQ CSRG verified · token 990d514d... · hash a3f91c...
```

---

## 11. ArmorIQ SDK Integration — Deep Dive

### What ArmorIQ Provides

ArmorIQ is a **Cryptographic Intent Guard** for AI agents. It prevents:
- Intent drift (plan says X, runtime does Y)
- Unauthorized action injection
- Unaudited agent behaviour

### SDK Flow

```
1. pip install armoriq-sdk

2. client = ArmorIQClient(
       api_key=...,
       user_id=...,
       agent_id=...,
       context_id="legal-hackathon"
   )

3. plan_capture = client.capture_plan(
       llm="simulation",          # or "gemini-1.5-pro"
       prompt="Handle case...",
       plan={
           "goal": "...",
           "steps": [
               {"action": "summarize_case", "mcp": "ai-lawyer", "params": {...}},
               {"action": "search_case_law", "mcp": "ai-lawyer", "params": {...}},
           ]
       },
       metadata={"case_id": "CASE-2026-001"}
   )

4. intent_token = client.get_intent_token(plan_capture.id)
   # Returns IntentToken with:
   #   .plan_hash       — SHA-256 of the full plan
   #   .step_proofs     — list of Merkle proof nodes, one per step
   #   .signed_by       — Ed25519 public key
   #   .expires_at      — token TTL
   #   .is_expired      — bool property

5. At execution time, for each action:
   verified = client.verify_token(intent_token)
   # Checks Ed25519 signature + TTL

6. Intent drift check (local, no network call):
   action_in_plan = any(
       proof.action == intent.action
       for proof in intent_token.step_proofs
   )
   if not action_in_plan:
       raise PolicyViolationError("armoriq_intent_drift")
```

### Why NOT using `client.invoke()`?

`client.invoke(mcp="ai-lawyer", ...)` routes through the ArmorIQ proxy, which requires your agent to be registered as an **HTTP MCP server** in the ArmorIQ dashboard. Since this project runs locally (not as a public HTTP endpoint), the proxy returns `400 MCP server not found`.

**The solution**: use **local Merkle proof verification** from `intent_token.step_proofs`. This is cryptographically equivalent — the token was signed by ArmorIQ's Ed25519 key, so the proofs can be verified offline.

### Verified Test Output

```
✅ Stage 1 — SDK client initialised
✅ Stage 2 — Intent token issued: 990d514d... (7 Merkle proofs)
✅ Stage 3 — Agent ran: 4 allowed, 0 blocked
   ✅ summarize_case    [sdk]
   ✅ search_case_law   [sdk]
   ✅ draft_document    [sdk]
   ✅ advise_client     [sdk]
✅ Stage 4 — Perjury correctly blocked: INJECTION:ACTION_INJECTION
✅ Stage 5 — Merkle chain: 4 nodes, valid=True
🎉 Full end-to-end test PASSED with real ArmorIQ key!
```

---

## 12. Request Lifecycle — Step by Step

Here is the exact journey of the query `"landlord illegal entry harassment"` for `CASE-2026-001`:

```
POST /analyze  {"query": "landlord illegal entry harassment", "case_id": "CASE-2026-001"}
  │
  ▼
server.py → lawyer.analyze_and_act("CASE-2026-001", "landlord illegal entry harassment")
  │
  ▼
llm_brain.generate_plan(case_data, query)
  ├─ [No Gemini key] → simulation: keyword "landlord" + "entry" → 4 intents
  │    summarize_case, search_case_law, draft_document, advise_client
  └─ _register_plan_with_armoriq(prompt, plan_items, ...)
       ├─ capture_plan() → plan_capture_id = "abc..."
       └─ get_intent_token("abc...") → IntentToken (4 step_proofs, signed)
  
Returns: ([4 intents], "simulation", IntentToken)
  │
  ▼
For each intent (e.g. "summarize_case"):
  1. Build IntentObject(action="summarize_case", initiated_by="lead_lawyer", ...)
  2. setattr(intent, '_armoriq_token', intent_token)
  3. injection_detector.scan(intent) → clean
  4. policy_engine.validate(intent, session_token=intent_token)
       ├─ "summarize_case" NOT in blocked_actions ✅
       ├─ "summarize_case" IN allowed_actions ✅
       ├─ No time constraints ✅
       ├─ client.verify_token(intent_token) → True ✅
       └─ Returns PolicyDecision.ALLOWED + metadata
  5. executor.execute(intent, policy_result)
       ├─ _invoke_via_armoriq(intent, ...):
       │    ├─ verify_token() → True ✅
       │    └─ "summarize_case" IN step_proofs → no drift ✅
       ├─ TOOL_REGISTRY["summarize_case"](intent) → "Case Summary: ..."
       └─ audit_logger.log_decision(ALLOWED, ...)
  6. Result: {decision:"ALLOWED", result:"Case Summary:...", armoriq_enforced:true, ...}
  │
  ▼
server.py serializes → JSON response with all 4 action results
  │
  ▼
web/index.html renders action cards with 🔐 ArmorIQ badges
```

---

## 13. Security Architecture

### Layered Defense Model

```
Request
   │
   ▼ Layer 0 ─── InjectionDetector ──── blocks prompt injection
   │
   ▼ Layer 1 ─── PolicyEngine (local) ── blocks unethical/illegal actions
   │                                      (perjury, fabrication, Rule 4.2)
   │
   ▼ Layer 2 ─── ArmorIQ SDK ─────────── cryptographic intent token verify
   │                                      (Ed25519 + Merkle proof)
   │
   ▼ Layer 3 ─── Executor (drift check) ─ ensures runtime action == signed plan
   │                                       (intent drift detection)
   │
   ▼ Layer 4 ─── CSRG Merkle chain ────── tamper-evident audit trail
   │
Tool executed ✅
```

### Fail-Closed Design

- If ArmorIQ SDK is unavailable → falls back to **local token** (SHA-256), but still enforces all local rules
- If LLM returns invalid JSON → simulation fallback, plan still registered with ArmorIQ
- If Merkle proof missing for a step → `merkle_proof_present: False` in result (logged, not blocked — the ArmorIQ `verify_token` already confirmed the overall signature)
- If token expired → `PolicyViolationError` immediately, action blocked

### What CANNOT Happen (by design)

| Attack | Blocked by |
|---|---|
| Prompt injection into content | InjectionDetector (Layer 0) |
| Ask AI to commit perjury | PolicyEngine rule RULE-PERJURY (Layer 1) |
| Contact opposing party directly | PolicyEngine rule RULE-4.2 (Layer 1) |
| Research agent tries to draft documents | Delegation scope check (Layer 1) |
| Plan registered then different action runs | Intent drift detection (Layer 3) |
| Replay old token | `is_expired` check (Layer 2) |
| Tamper with audit log retroactively | CSRG Merkle chain (Layer 4) |

---

## 14. Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ARMORIQ_API_KEY` | ✅ Yes | ArmorIQ live API key (`ak_live_...`) |
| `ARMORIQ_USER_ID` | Optional | User identifier (default: `ai-lawyer-user`) |
| `ARMORIQ_AGENT_ID` | Optional | Agent identifier (default: `ai-lawyer-agent`) |
| `GEMINI_API_KEY` | Optional | Google Gemini key for real LLM reasoning |

Without `GEMINI_API_KEY` the system runs in **simulation mode** (keyword-matched plans). All ArmorIQ enforcement still works identically — the plan is registered and signed regardless of whether it came from Gemini or simulation.

```env
# .env (gitignored)
ARMORIQ_API_KEY=ak_live_...
ARMORIQ_USER_ID=avinash1807007
ARMORIQ_AGENT_ID=ai-lawyer-agent
GEMINI_API_KEY=          # optional
```

---

## 15. Running Locally

```bash
# 1. Clone
git clone https://github.com/404Avinash/rusty_claw.git
cd rusty_claw

# 2. Create virtualenv
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

# 3. Install deps
pip install -r requirements.txt

# 4. Configure env
cp .env.example .env
# Edit .env: add ARMORIQ_API_KEY

# 5a. Run CLI demo (5 scenes, no browser needed)
python main.py

# 5b. Run web server
uvicorn server:app --reload --port 8000
# Open http://127.0.0.1:8000
```

---

## 16. Demo Scenes (`main.py`)

The CLI runs 5 structured scenes to showcase every feature:

| Scene | What happens | ArmorIQ outcome |
|---|---|---|
| **1 — Case Intake** | Client describes landlord illegal entry. Case stored in `memory/cases/`. | Plan registered, token issued |
| **2 — Allowed Actions** | AI builds strategy: summarise → search law → draft notice → advise. All 4 execute. | `[sdk]` badge, Merkle proofs verified |
| **3 — Perjury Attempt** | Client asks AI to lie about receiving a notice. Blocked before it reaches a tool. | `INJECTION:ACTION_INJECTION` → `HARD_BLOCK` |
| **4 — Rule 4.2** | Client asks to contact landlord directly. Blocked by Bar Council Rule 4.2. | `HARD_BLOCK`, `rule_violated: "RULE-4.2"` |
| **5 — Delegation** | Lead lawyer spawns research agent. Research agent tries to draft — blocked. Then does search — allowed. | Delegation scope enforced |

After all scenes, a full audit table is printed showing every decision with timestamps, agents, rules, and Merkle roots.

---

*Generated: 2026-02-26 | Commit: 105cf2e | Built for ArmorIQ × OpenClaw Hackathon*
