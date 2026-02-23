# ⚖️ AI Lawyer — ARMORIQ x OPENCLAW Hackathon

> *"We built an AI lawyer. But unlike a human lawyer, this one literally cannot cut corners."*

An autonomous legal AI agent demonstrating **intent-aware execution** with **deterministic policy enforcement** using OpenClaw + ArmorIQ.

---

## 🚀 Quick Start

```bash
pip install rich
python main.py
```

---

## 📁 Project Structure

```
claw/
├── main.py                 # 🎬 Demo entry point (run this!)
├── policies/
│   └── legal_rules.json    # 📜 Policy rulebook (the enforcement source of truth)
├── core/
│   ├── intent_model.py     # 📋 IntentObject + PolicyDecision schemas
│   ├── policy_engine.py    # 🛡️ THE enforcement layer (ArmorIQ integration)
│   ├── executor.py         # ⚙️  Only gateway to tool execution
│   └── audit_logger.py     # 📝 JSONL decision trace
├── agents/
│   ├── lead_lawyer.py      # 🧠 Main reasoning agent
│   └── research_agent.py   # 🔍 Delegated sub-agent (bounded scope)
├── tools/
│   └── legal_tools.py      # 🔧 Tool implementations + registry
├── memory/
│   └── case_store.py       # 💾 Case file storage
├── output/                 # Generated legal documents
└── logs/
    └── audit_log.jsonl     # Full decision trace (auto-generated)
```

---

## 🏗️ Architecture

```
Client Input
     ↓
[Lead Lawyer Agent] ← reasons, proposes IntentObjects only
     ↓ IntentObject
[Policy Engine] ← reads legal_rules.json + optional ArmorIQ IAP
     ↓              ↓
 ALLOWED         BLOCKED (with rule + reason)
     ↓              ↓
[Executor]     PolicyViolationError
  runs tool      logged + shown
     ↓
[Audit Logger] ← every decision logged to audit_log.jsonl
```

**Core principle:** Agents never execute tools directly. Every action is expressed as a structured `IntentObject`, validated by the `PolicyEngine`, then either executed or blocked with a clear reason.

---

## 📜 Intent Model

Every proposed action is a typed `IntentObject`:

```python
IntentObject(
    action="draft_document",         # What to do
    initiated_by="lead_lawyer",      # Who wants it
    target="output/legal_notice.txt",# Target resource
    content="Draft legal notice...", # What it does
    case_id="CASE-2026-001",         # Case context
    delegated_by=None,               # None = lead agent
)
```

---

## 🛡️ Policy Model

Rules loaded at runtime from `policies/legal_rules.json`:

| Category | Examples |
|----------|---------|
| **Allowed** | `draft_document`, `search_case_law`, `advise_client` |
| **Blocked** | `contact_opposing_party_directly`, `suborning_perjury`, `fabricate_evidence` |
| **Delegation** | `research_agent` → only `search_case_law`, `read_case_files` |

**Not hardcoded if/else** — rules are loaded from JSON and evaluated dynamically.

---

## 🚫 Enforcement Mechanism

The `PolicyEngine`:

1. Loads `legal_rules.json` at runtime
2. Checks if action is in `blocked_actions` → **HARD_BLOCK** immediately
3. Checks if action is in `allowed_actions` → **ALLOWED**
4. For delegated agents: checks `delegation_rules` scope → **DELEGATION_EXCEEDED** if exceeded
5. If `ARMORIQ_API_KEY` is set: calls ArmorIQ IAP for cryptographic token verification
6. Logs every decision to `logs/audit_log.jsonl`
7. Fails **closed** by default (deny-by-default)

---

## 🎬 Demo Scenes

| Scene | What Happens | Verdict |
|-------|-------------|---------|
| 1 | Client describes landlord case | Case registered |
| 2 | Agent builds strategy, drafts legal notice | ✅ ALLOWED |
| 3 | Client: "say we never got that email" | 🚫 Suborning Perjury — BLOCKED |
| 4 | Agent tries to contact landlord directly | 🚫 Rule 4.2 — BLOCKED |
| 5 | Research sub-agent tries to send email | 🚫 Delegation Exceeded — BLOCKED |
| 6 | Live audit log displayed | Full trace shown |

---

## ⚙️ With API Keys (Optional)

```bash
# .env
ARMORIQ_API_KEY=ak_live_xxx       # Enables cryptographic IAP verification
OPENAI_API_KEY=sk-xxx             # Enables real LLM reasoning
```

Without keys: simulation mode (identical demo, mock LLM + local policy enforcement).

---

## 📬 Repository

GitHub: <https://github.com/404Avinash/rusty_claw>
