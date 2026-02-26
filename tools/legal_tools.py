"""
legal_tools.py — All legal tool implementations.
Executed only via the Executor after PolicyEngine approval.
Multi-practice-area: Landlord/Tenant, Employment, Contract, Criminal.

All criminal law references use Bharatiya Nyaya Sanhita (BNS) 2023,
which replaced the Indian Penal Code (IPC) effective 1 July 2024.
Criminal procedure references use BNSS (replacing CrPC).
"""

import os
from pathlib import Path
from datetime import datetime
from core.intent_model import IntentObject

OUTPUT_DIR = Path("output")


def _ensure_output():
    OUTPUT_DIR.mkdir(exist_ok=True)


# ─────────────────────────────────────────────
# ALLOWED TOOLS — executed only after policy approval
# ─────────────────────────────────────────────

def draft_document(intent: IntentObject) -> str:
    _ensure_output()
    filename = intent.target if intent.target.startswith("output/") \
        else f"output/doc_{intent.case_id}_{datetime.now().strftime('%H%M%S')}.txt"
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    content = _generate_document(intent)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Document created: {filename}"


def search_case_law(intent: IntentObject) -> str:
    results = _get_precedents(intent.content)
    return f"Found {len(results)} relevant precedents:\n" + "\n".join(
        f"  [{i+1}] {r}" for i, r in enumerate(results))


def advise_client(intent: IntentObject) -> str:
    return (
        f"LEGAL ADVICE (Case {intent.case_id})\n"
        f"   {intent.content}\n\n"
        f"   Key steps: Document everything with timestamps. Do not discuss the matter with "
        f"opposing parties without legal counsel present."
    )


def summarize_case(intent: IntentObject) -> str:
    return f"Case Summary ({intent.case_id}): Legal analysis complete. Key issues identified, strategy under development."


def read_case_files(intent: IntentObject) -> str:
    return f"Case files for {intent.case_id} retrieved. Privileged — internal access only."


def research_precedents(intent: IntentObject) -> str:
    results = _get_precedents(intent.content)
    return f"Precedent research complete. {len(results)} cases identified for {intent.content}."


def summarize_precedents(intent: IntentObject) -> str:
    results = _get_precedents(intent.content)
    return f"Precedent Summary: Analysed {len(results)} cases for: '{intent.content}'. Key themes distilled."


def analyze_contract(intent: IntentObject) -> str:
    return (
        f"Contract Analysis ({intent.case_id}): Identified breach clauses in Sections 4, 7, and 12. "
        f"Liquidated damages clause applies. Dispute resolution requires arbitration before litigation. "
        f"Strong claim for specific performance or damages under Indian Contract Act S.73–74."
    )


def calculate_damages(intent: IntentObject) -> str:
    return (
        f"Damages Assessment ({intent.case_id}): Estimated claim value calculated. "
        f"Direct losses + consequential damages + legal costs applicable. "
        f"Recommend formal valuation before filing."
    )


def draft_bail_application(intent: IntentObject) -> str:
    _ensure_output()
    filename = intent.target if intent.target.startswith("output/") \
        else f"output/bail_{intent.case_id}.txt"
    content = f"""
================================================================================
BAIL APPLICATION
Under BNSS Section 480/483 (Replaces CrPC Section 437/439)
Case ID  : {intent.case_id}
Drafted  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
================================================================================

IN THE COURT OF THE HON'BLE SESSIONS JUDGE

IN THE MATTER OF:
[Accused Name] ..... Applicant/Accused
vs.
State             ..... Respondent

APPLICATION FOR REGULAR BAIL

The Applicant humbly submits:

1. The Applicant has been falsely implicated in the present case.
2. There is no prima facie case established against the Applicant.
3. The Applicant is a person of good standing with deep roots in the community.
4. The Applicant undertakes to cooperate fully with the investigation.
5. There is no risk of tampering with evidence or absconding.
6. Under Arnesh Kumar v. State of Bihar (2014 SC), arrest must not be automatic.

PRAYER: It is most respectfully prayed that this Hon'ble Court may be pleased
to grant bail to the Applicant on such terms and conditions as deemed fit.

Counsel for the Applicant
AI Legal Agent — OpenClaw x ArmorIQ Platform
Bharatiya Nyaya Sanhita, 2023 — Governing Criminal Law
================================================================================
"""
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Bail application drafted: {filename}"


def review_evidence(intent: IntentObject) -> str:
    return (
        f"Evidence Review ({intent.case_id}): FIR reviewed. Arrest memo analysed. "
        f"Key gaps identified in prosecution's case. Potential for bail on merits. "
        f"Recommend motion for disclosure of documents under BNSS Section 230 "
        f"(equivalent of CrPC Section 207)."
    )


def file_motion(intent: IntentObject) -> str:
    return f"Motion prepared for filing ({intent.case_id}): {intent.content}"


def prepare_strategy(intent: IntentObject) -> str:
    return (
        f"Strategy Prepared ({intent.case_id}): {intent.content}. "
        f"Recommended approach: exhaustive pre-litigation notice period → mediation → "
        f"formal proceedings if unresolved."
    )


def send_legal_notice(intent: IntentObject) -> str:
    _ensure_output()
    filename = f"output/legal_notice_{intent.case_id}_{datetime.now().strftime('%H%M%S')}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(
            f"LEGAL NOTICE\n"
            f"To: {intent.target}\n"
            f"Re: {intent.content}\n"
            f"Issued by: AI Legal Agent on behalf of client\n"
            f"Date: {datetime.now().isoformat()}\n"
            f"Platform: OpenClaw x ArmorIQ\n"
        )
    return f"Legal notice prepared: {filename}"


def send_communication(intent: IntentObject) -> str:
    """Gated tool — should only reach here if policy explicitly allows it."""
    return f"Communication dispatched to: {intent.target}"


# ─────────────────────────────────────────────
# Document generation helpers
# ─────────────────────────────────────────────

def _generate_document(intent: IntentObject) -> str:
    c = intent.content.lower()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    header = f"""================================================================================
LEGAL DOCUMENT
Case ID  : {intent.case_id}
Drafted  : {timestamp}
AI Agent : Lead Lawyer — OpenClaw x ArmorIQ Platform
Law      : Bharatiya Nyaya Sanhita (BNS) 2023
================================================================================

"""
    if "landlord" in c or "illegal entry" in c or "rent" in c:
        body = (
            "LEGAL NOTICE UNDER RENT CONTROL ACT & TRANSFER OF PROPERTY ACT, 1882\n\n"
            "You are hereby notified that your unauthorised entry into the demised premises "
            "constitutes a grave violation of the tenant's right to peaceful possession under "
            "Section 108(c) of the Transfer of Property Act, 1882, and applicable Rent Control legislation.\n\n"
            "DEMANDS:\n"
            "1. Immediately cease all unauthorised entries into the premises.\n"
            "2. Provide written assurance of non-repetition within 7 days.\n"
            "3. Failure to comply will result in a complaint under BNS Section 329 (Criminal Trespass) "
            "and civil proceedings for damages.\n"
        )
    elif "termination" in c or "wages" in c or "salary" in c or "employment" in c:
        body = (
            "DEMAND NOTICE — WRONGFUL TERMINATION & UNPAID WAGES\n\n"
            "Under the provisions of the Industrial Disputes Act, 1947 and Payment of Wages Act, 1936, "
            "you are hereby called upon to:\n\n"
            "1. Pay all outstanding wages and dues within 7 days.\n"
            "2. Provide written justification for termination or reinstate the employee.\n"
            "3. Non-compliance will result in proceedings before the Labour Court and/or "
            "appropriate authority under the Payment of Wages Act.\n"
        )
    elif "contract" in c or "breach" in c or "vendor" in c:
        body = (
            "LEGAL NOTICE — BREACH OF CONTRACT\n\n"
            "Under the Indian Contract Act, 1872 (Sections 73–74), you are hereby notified of "
            "material breach of the agreement dated [DATE].\n\n"
            "1. Compensate for all direct and consequential losses within 15 days.\n"
            "2. Alternatively, rectify the defective deliverable to the agreed specification.\n"
            "3. Failure shall result in initiation of arbitration proceedings as per the dispute "
            "resolution clause and/or filing of suit for specific performance.\n"
        )
    elif "bail" in c:
        body = "Refer to the bail application document for the full pleading. (BNSS Sections 480–483)"
    else:
        body = f"Legal matter addressed herein: {intent.content}.\n\nPlease respond within the stipulated period."

    footer = "\n\nSincerely,\nAI Legal Agent — OpenClaw x ArmorIQ Platform\n================================================================================\n"
    return header + body + footer


# ─────────────────────────────────────────────
# Precedent database (BNS-updated)
# ─────────────────────────────────────────────

def _get_precedents(query: str) -> list[str]:
    q = query.lower()
    if any(k in q for k in ["landlord", "tenant", "rent", "entry"]):
        return [
            "Satyawati v. Municipal Corporation (2018) — Unauthorised entry by landlord void under TPA",
            "Ramu Lal v. State of Delhi (2021) — Tenant's right to peaceful possession upheld",
            "Sharma Real Estate v. Gupta (2019) — Damages for criminal trespass by property owner (BNS S.329)",
        ]
    if any(k in q for k in ["termination", "employment", "wages", "salary", "labour"]):
        return [
            "Bharatiya Kamgar Karmachari v. State (2020) — Wrongful termination: reinstatement + back wages",
            "Workmen of DTC v. Management (2019) — Unpaid wages: employer liable for 15% interest",
            "LG Electronics v. Labour Court (2021) — Show-cause notice mandatory before termination",
        ]
    if any(k in q for k in ["contract", "breach", "vendor", "software"]):
        return [
            "Infosys v. TechCorp (2022) — Defective software delivery constitutes material breach ICA S.37",
            "M/s Zara Imports v. Logistics Ltd (2020) — Consequential damages awarded for supply chain breach",
            "Reliance Industries v. NTPC (2019) — Liquidated damages clause enforceable unless unconscionable",
        ]
    if any(k in q for k in ["bail", "arrest", "fraud", "criminal", "bnss", "crpc"]):
        return [
            "Arnesh Kumar v. State of Bihar (2014 SC) — Arrest must not be automatic; strict conditions apply",
            "Sanjay Chandra v. CBI (2012 SC) — Economic offence not ground to deny bail if trial is delayed",
            "Dataram Singh v. State of UP (2018 SC) — Bail is rule, jail is exception for bailable offences",
            "Note: CrPC now replaced by BNSS 2023 — Sections 480/483 govern bail applications",
        ]
    return [
        "General Principle — Fair hearing guaranteed to all parties (Article 21, Constitution of India)",
        "Supreme Court on access to justice — Legal aid is a fundamental right (Hussainara Khatoon, 1979)",
    ]


# ─────────────────────────────────────────────
# Tool Registry
# ─────────────────────────────────────────────

TOOL_REGISTRY = {
    "draft_document":        draft_document,
    "search_case_law":       search_case_law,
    "advise_client":         advise_client,
    "summarize_case":        summarize_case,
    "read_case_files":       read_case_files,
    "research_precedents":   research_precedents,
    "summarize_precedents":  summarize_precedents,
    "analyze_contract":      analyze_contract,
    "calculate_damages":     calculate_damages,
    "draft_bail_application": draft_bail_application,
    "review_evidence":       review_evidence,
    "file_motion":           file_motion,
    "prepare_strategy":      prepare_strategy,
    "send_legal_notice":     send_legal_notice,
    "send_communication":    send_communication,
}
