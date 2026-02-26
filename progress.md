# AI Lawyer — Progress & Remaining Work

## Completed Upgrades

We have successfully implemented the core logic for all 4 upgrades:

1. **LLM Brain (`core/llm_brain.py`)**
   - Created the LLM router that tries Gemini first, then Ollama, and falls back to simulation.
   - Wired it into `agents/lead_lawyer.py` to generate dynamic legal plans instead of keyword matching.

2. **CSRG Merkle Intent Tree (`core/csrg.py`)**
   - Implemented real cryptographic tamper-proof intent chains.
   - Integrated into `core/policy_engine.py` to add every decision to the chain.
   - Integrated ArmorIQ's IAP verification using the real API key.
   - Added `/api/merkle` and `/api/merkle/tamper` endpoints to `server.py`.

3. **Time-Based Policy Constraints**
   - Added the business hours restriction (09:00 - 21:00 IST) to `policies/legal_rules.json`.
   - Added `_check_time_constraint` in `core/policy_engine.py`.

4. **Prompt Injection Protection (`core/injection_detector.py`)**
   - Built a regex-based scanner to catch malicious jailbreaks and hidden instructions.
   - Wired it into `core/executor.py` so it blocks threats BEFORE the policy engine even runs.
   - Added an explicit "Prompt Injection Demo" (Scene 6) to the SSE demo stream in `server.py` and a new `/api/injection/test` endpoint.

## What is Left (Next Steps)

1. **Wait for Dependencies to Install:**
   - Need to ensure `google-generativeai`, `httpx`, and `python-dotenv` are fully installed. (The PowerShell command `tail` error was just a display issue; the actual background `pip install` is likely completing).

2. **Update the Web UI (`web/index.html`):**
   - We need to add the visual representation of the **CSRG Merkle Chain** to the right-side panel so you can actually see the cryptographic hashes in the UI and click the "Tamper Test" button.
   - Adjust the SSE stream parser in JS to handle the new `merkle_root` and `reasoning_mode` fields sent in the summary.

3. **End-to-End Verification:**
   - Restart the FastAPI server.
   - Run the full browser demo to visualize the new Prompt Injection scene (Scene 6).
   - Ensure Gemini is correctly picking up the case and reasoning without throwing errors.
