# ⚖️ Submission Document — ARMORIQ x OPENCLAW Hackathon

**Project:** AI Lawyer — Intent-Aware Legal Agent
**Repo:** <https://github.com/404Avinash/rusty_claw>

---

## Intent Model

The system uses a structured `IntentObject` dataclass as the atomic unit of agent intent. Agents never call tools directly — they build IntentObjects which are submitted to the gated executor.

```python
IntentObject(
    action: str,           # proposed action identifier
    initiated_by: str,     # agent role ("lead_lawyer" | "research_agent")
    delegated_by: str,     # None for principal agent; parent role for sub-agents
    target: str,           # target resource or recipient
    content: str,          # human-readable description of the action
    case_id: str,          # case context
    timestamp: str,        # ISO 8601 auto-generated
)
```

**Why this matters:** Any text string could be ambiguous. A typed, structured IntentObject forces agents to explicitly declare *what* they want to do, *to whom*, and *in what context* — making enforcement deterministic.

---

## Policy Model

Rules are defined in `policies/legal_rules.json` — a structured JSON file loaded at runtime. The enforcement engine never uses hardcoded `if/else` checks.

### Constraints Implemented

| Type | Examples |
|------|---------|
| **Allowed actions** | `draft_document`, `search_case_law`, `advise_client` |
| **Hard-blocked actions** | `contact_opposing_party_directly` (Rule 4.2), `suborning_perjury` (IPC 191), `fabricate_evidence` (IPC 192), `advise_evidence_destruction` (IPC 201) |
| **Delegation scope** | `research_agent`: only `search_case_law`, `read_case_files` |
| **Ethical constraints** | `attorney_client_privilege`, `no_direct_opposing_contact`, `no_perjury`, `no_evidence_tampering` |

---

## Enforcement Mechanism

The `PolicyEngine` class implements a 5-step validation pipeline:

1. **Load rules** — reads `legal_rules.json` at runtime (hot-reloadable)
2. **Delegation check** — if `delegated_by` is set, validates against `delegation_rules` scope first
3. **Hard block check** — checks `blocked_actions` list → returns `HARD_BLOCK` immediately
4. **Allow check** — checks `allowed_actions` list → returns `ALLOWED`
5. **Fail-closed** — actions not in either list are denied by default
6. **ArmorIQ IAP** (optional) — if `ARMORIQ_API_KEY` is set, calls the Intent Access Proxy for cryptographic token verification before execution

Every decision produces a `PolicyDecision(allowed, reason, rule_violated, enforcement_type)` and is logged to `logs/audit_log.jsonl`.

### Enforcement Types

| Type | Meaning |
|------|---------|
| `ALLOWED` | Action proceeded |
| `HARD_BLOCK` | Explicitly in blocked list with legal rule reference |
| `DELEGATION_EXCEEDED` | Sub-agent attempted action outside its delegated scope |

---

## OpenClaw Integration

- **OpenClaw** serves as the agent gateway framework
- **ArmorIQ plugin** (`@openclaw/armoriq`) installed for intent verification layer
- **ArmorIQ IAP** called for cryptographic intent token when API key is configured
- Local `PolicyEngine` provides identical enforcement in simulation mode

---

## Delegation

The `LeadLawyer` agent can spawn a `ResearchAgent` sub-agent via `spawn_research_agent()`. The sub-agent's policy scope is read from `delegation_rules.research_agent` in the policy file — it does **not** inherit the lead lawyer's permissions. Any action outside the delegated scope triggers a `DELEGATION_EXCEEDED` block.
