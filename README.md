# ⚖️ CLAW — AI Legal Assistant

> *"We built an AI lawyer. But unlike a human lawyer, this one literally cannot cut corners."*

An autonomous legal AI agent demonstrating **intent-aware execution** with **deterministic policy enforcement**, powered by **ArmorIQ CSRG Merkle-proof verification** and the **Bharatiya Nyaya Sanhita (BNS) 2023**.

---

## 🌐 Live Demo

**[![Live on Render](https://img.shields.io/badge/Live%20Demo-ai--lawyer--armoriq.onrender.com-brightgreen?style=for-the-badge&logo=render)](https://ai-lawyer-armoriq.onrender.com/)**

> 🔗 **[https://ai-lawyer-armoriq.onrender.com/](https://ai-lawyer-armoriq.onrender.com/)**

Click **"▶ Run Full Demo"** to watch the ArmorIQ policy engine enforce ethical boundaries in real time across **7 scenes** — including prompt injection blocking.

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| **Chat-first Interface** | Conversational UX with real-time agent responses |
| **4 Practice Areas** | Landlord/Tenant · Employment · Contract · Criminal |
| **BNS 2023 Knowledge Base** | 21 sections of Bharatiya Nyaya Sanhita embedded |
| **Indian Constitution KB** | 20+ Articles + 7 landmark Supreme Court cases |
| **General Q&A Mode** | Ask any legal question — no case registration needed |
| **ArmorIQ CSRG** | Cryptographic Merkle-proof intent chain for every decision |
| **Prompt Injection Shield** | 4-layer defense: harmful query, system override, action injection, privilege escalation |
| **Live Agent Feed** | Real-time SSE decision cards with verdict, rule, and ArmorIQ signature |
| **Audit Trail** | Filterable audit table with JSON export |
| **Collapsible Panels** | Sidebar + drawer toggle for focused workflows |
| **Tamper Detection** | Live Merkle chain visualization with tamper-test button |

---

## 🚀 Quick Start

### Web UI (recommended)
```bash
pip install -r requirements.txt
uvicorn server:app --reload --port 8000
# Open http://localhost:8000
```

### CLI Demo
```bash
pip install rich
python main.py
```

---

## 📁 Project Structure

```
claw/
├── server.py               # 🌐 FastAPI backend (all API endpoints)
├── main.py                 # 🎬 CLI demo entry point
├── web/
│   └── index.html          # 💎 Chat-first responsive UI
├── policies/
│   ├── legal_rules.json    # 📜 Policy rulebook (enforcement source of truth)
│   ├── bns_2023.json       # ⚖️  BNS 2023 sections (replaces IPC)
│   └── constitution_india.json # 🏛️ Constitution articles + landmark cases
├── core/
│   ├── intent_model.py     # 📋 IntentObject + PolicyDecision schemas
│   ├── policy_engine.py    # 🛡️ Enforcement layer (ArmorIQ SDK integration)
│   ├── executor.py         # ⚙️  Only gateway to tool execution
│   ├── injection_detector.py # 🔒 4-layer prompt injection + harmful query blocker
│   ├── csrg.py             # 🌳 CSRG Merkle tree implementation
│   ├── llm_brain.py        # 🧠 LLM reasoning (Gemini / simulation)
│   └── audit_logger.py     # 📝 JSONL decision trace
├── agents/
│   ├── lead_lawyer.py      # 🧠 Main reasoning agent (4 practice areas)
│   └── research_agent.py   # 🔍 Delegated sub-agent (bounded scope)
├── tools/
│   └── legal_tools.py      # 🔧 16 tools + BNS/Constitution search
├── memory/
│   └── case_store.py       # 💾 Case file storage
├── output/                 # Generated legal documents
└── logs/
    └── audit_log.jsonl     # Full decision trace
```

---

## 🏗️ Architecture

```
Client Input
     ↓
[Injection Detector] ← Layer 0: harmful queries + prompt injection
     ↓ (clean)
[Lead Lawyer Agent] ← reason, propose IntentObjects
     ↓ IntentObject
[Policy Engine] ← legal_rules.json + ArmorIQ CSRG token verification
     ↓              ↓
 ALLOWED         BLOCKED (rule + reason + BNS section)
     ↓              ↓
[Executor]     PolicyViolationError
  runs tool      logged + shown
     ↓
[CSRG Merkle Tree] ← every decision → Merkle node
     ↓
[Audit Logger] ← full trace → audit_log.jsonl
```

**Core principle:** Agents never execute tools directly. Every action flows through a structured `IntentObject` → `PolicyEngine` → `Executor` pipeline. No shortcuts possible.

---

## 🛡️ Safety Layers

| Layer | Component | What it catches |
|-------|-----------|----------------|
| **0** | Harmful Query Blocker | Explosives, drugs, violence, hacking, trafficking, fraud |
| **1** | Prompt Injection Detector | System override, jailbreak, role-play attacks |
| **2** | Action Injection Scanner | Hidden bribery, evidence destruction, witness threats |
| **3** | Privilege Escalation Guard | Unauthorized commands, admin-mode attempts |
| **4** | Policy Engine | BNS-aware blocked actions, delegation scope enforcement |
| **5** | ArmorIQ CSRG | Cryptographic Merkle-proof: intent drift = hard block |

---

## 🎬 Demo Scenes (7 Scenes)

| Scene | What Happens | Verdict |
|-------|-------------|---------|
| 1 | Client describes landlord case | ✅ Case registered |
| 2 | Agent builds legal strategy | ✅ ALLOWED — documents drafted |
| 3 | Client: "say we never got that email" | 🚫 Perjury — BLOCKED (BNS S.227) |
| 4 | Agent tries to contact landlord directly | 🚫 Rule 4.2 — BLOCKED |
| 5 | Research agent tries unauthorized email | 🚫 Delegation Exceeded — BLOCKED |
| 6 | Prompt injection embedded in text | 🚫 Injection Severed — BLOCKED |
| 7 | Legal Action Plan + Merkle root displayed | 📋 Summary |

---

## ⚙️ API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serve the web UI |
| `/health` | GET | Health check |
| `/api/intake` | POST | Register a new case |
| `/api/act` | POST | Execute case instruction |
| `/api/ask` | POST | General legal Q&A (no case needed) |
| `/api/delegate` | POST | Test delegation enforcement |
| `/api/demo/stream` | GET | SSE streaming demo (7 scenes) |
| `/api/merkle` | GET | CSRG Merkle intent chain |
| `/api/merkle/tamper` | POST | Simulate tamper for demo |
| `/api/injection/test` | POST | Test prompt injection detection |
| `/api/audit/export` | GET | Export audit log as JSON |
| `/api/policy` | GET | View loaded policy rules |
| `/api/summary/{id}` | GET | Case summary with findings |

---

## ⚙️ Environment Variables (Optional)

```bash
ARMORIQ_API_KEY=ak_live_xxx    # Enables cryptographic CSRG token verification
GEMINI_API_KEY=xxx             # Enables real Gemini LLM reasoning
```

Without keys: simulation mode (identical demo, mock LLM + local policy enforcement).

---

## 📬 Repository

GitHub: <https://github.com/404Avinash/rusty_claw>
