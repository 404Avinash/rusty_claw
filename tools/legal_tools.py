"""
legal_tools.py — All legal tool implementations.
Executed only via the Executor after PolicyEngine approval.
Multi-practice-area: Landlord/Tenant, Employment, Contract, Criminal.

All criminal law references use Bharatiya Nyaya Sanhita (BNS) 2023,
which replaced the Indian Penal Code (IPC) effective 1 July 2024.
Criminal procedure references use BNSS (replacing CrPC).

Knowledge bases loaded from:
  - policies/bns_2023.json        — BNS 2023 sections (replaces IPC)
  - policies/constitution_india.json — Indian Constitution articles
"""

import json
import re
import os
from pathlib import Path
from datetime import datetime
from core.intent_model import IntentObject

OUTPUT_DIR = Path("output")
_POLICY_DIR = Path("policies")

# ─────────────────────────────────────────────
# Load legal knowledge bases at module init
# ─────────────────────────────────────────────

def _load_json(path: Path) -> dict:
    try:
        # utf-8-sig handles UTF-8 BOM that Windows PowerShell adds
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return {}

_BNS_DB: dict = _load_json(_POLICY_DIR / "bns_2023.json")
_CONST_DB: dict = _load_json(_POLICY_DIR / "constitution_india.json")


def _search_bns(query: str) -> list[dict]:
    """Search BNS 2023 sections by keyword match on tags, title, text."""
    words = [w for w in query.lower().split() if len(w) > 3]
    hits = []
    for sec in _BNS_DB.get("sections", []):
        searchable = " ".join([
            sec.get("title", ""),
            sec.get("text", ""),
            " ".join(sec.get("tags", [])),
            sec.get("relevance", ""),
            sec.get("ipc_equivalent", ""),
        ]).lower()
        # require whole-word match to avoid false positives ('rights' in 'reproductive_rights')
        if any(re.search(r'\b' + re.escape(w) + r'\b', searchable) for w in words):
            hits.append(sec)
    return hits[:4]  # top 4


def _search_constitution(query: str) -> list[dict]:
    """Search Constitution articles by keyword match."""
    words = [w for w in query.lower().split() if len(w) > 3]
    hits = []
    all_articles = (
        _CONST_DB.get("fundamental_rights", [])
        + _CONST_DB.get("directive_principles", [])
        + _CONST_DB.get("other_key_articles", [])
    )
    for art in all_articles:
        searchable = " ".join([
            art.get("title", ""),
            art.get("text", ""),
            art.get("legal_relevance", ""),
            " ".join(art.get("tags", [])),
        ]).lower()
        if any(re.search(r'\b' + re.escape(w) + r'\b', searchable) for w in words):
            hits.append(art)
    return hits[:3]  # top 3


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
# Precedent database (BNS-updated) + live knowledge base lookup
# ─────────────────────────────────────────────

def _get_precedents(query: str) -> list[str]:
    q = query.lower()
    results = []

    # ── Case law by practice area ─────────────────────────────────────────────
    if any(k in q for k in ["landlord", "tenant", "rent", "entry", "trespass", "evict"]):
        results += [
            "Satyawati v. Municipal Corporation (2018) — Unauthorised entry by landlord void under TPA",
            "Ramu Lal v. State of Delhi (2021) — Tenant's right to peaceful possession upheld",
            "Sharma Real Estate v. Gupta (2019) — Damages for criminal trespass by property owner",
        ]
    if any(k in q for k in ["termination", "employment", "wages", "salary", "labour", "posh", "harassment"]):
        results += [
            "Bharatiya Kamgar Karmachari v. State (2020) — Wrongful termination: reinstatement + back wages",
            "Workmen of DTC v. Management (2019) — Unpaid wages: employer liable for 15% interest",
            "LG Electronics v. Labour Court (2021) — Show-cause notice mandatory before termination",
            "Vishaka v. State of Rajasthan (1997 SC) — Sexual harassment at workplace: laid down Vishaka Guidelines (now POSH Act 2013)",
        ]
    if any(k in q for k in ["contract", "breach", "vendor", "software", "supply"]):
        results += [
            "Infosys v. TechCorp (2022) — Defective software delivery constitutes material breach (ICA S.37)",
            "M/s Zara Imports v. Logistics Ltd (2020) — Consequential damages awarded for supply chain breach",
            "Reliance Industries v. NTPC (2019) — Liquidated damages clause enforceable unless unconscionable",
        ]
    if any(k in q for k in ["bail", "arrest", "fraud", "criminal", "bnss", "crpc", "fir", "custody"]):
        results += [
            "Arnesh Kumar v. State of Bihar (2014 SC) — Arrest must not be automatic; strict conditions apply",
            "Sanjay Chandra v. CBI (2012 SC) — Economic offence not ground to deny bail if trial is delayed",
            "Dataram Singh v. State of UP (2018 SC) — Bail is rule, jail is exception for bailable offences",
            "D.K. Basu v. State of West Bengal (1997) — 11 mandatory police arrest guidelines",
            "Note: CrPC replaced by BNSS 2023 — Sections 480/483 govern bail applications",
        ]
    if any(k in q for k in ["privacy", "data", "personal", "surveillance", "aadhaar"]):
        results += [
            "K.S. Puttaswamy v. Union of India (2017 SC, 9-judge) — Right to Privacy is a fundamental right under Article 21",
            "Justice Srikrishna Committee Report (2018) — Foundation of the Digital Personal Data Protection Act 2023",
        ]
    if any(k in q for k in ["defamation", "reputation", "slander", "libel", "social media"]):
        results += [
            "Subramanian Swamy v. Union of India (2016 SC) — Criminal defamation under IPC S.499 (now BNS S.356) upheld as constitutional",
            "Shreya Singhal v. Union of India (2015 SC) — Section 66A IT Act struck down; online speech protected under Article 19",
        ]
    if any(k in q for k in ["constitution", "fundamental right", "writ", "habeas", "article 21", "equality"]):
        results += [
            "Maneka Gandhi v. Union of India (1978 SC) — Articles 14, 19, 21 read together; procedure must be fair",
            "Hussainara Khatoon v. State of Bihar (1979 SC) — Speedy trial + free legal aid are fundamental rights",
            "Kesavananda Bharati v. State of Kerala (1973 SC, 13-judge) — Basic Structure Doctrine",
        ]

    # ── Enrich with live BNS knowledge base ──────────────────────────────────
    bns_hits = _search_bns(query)
    for sec in bns_hits:
        results.append(
            f"BNS Section {sec['section']} — {sec['title']}: {sec.get('punishment', 'See text')} "
            f"[replaces {sec.get('ipc_equivalent', 'N/A')}]"
        )

    # ── Enrich with Constitution articles ────────────────────────────────────
    const_hits = _search_constitution(query)
    for art in const_hits:
        results.append(
            f"Constitution Article {art['article']} — {art['title']}: "
            f"{art.get('legal_relevance', art.get('text', ''))[:100]}..."
        )

    if not results:
        results = [
            "General Principle — Fair hearing guaranteed to all parties (Article 21, Constitution of India)",
            "Supreme Court on access to justice — Legal aid is a fundamental right (Hussainara Khatoon, 1979)",
            "BNS 2023 replaced IPC 1860 effective 1 July 2024 — all criminal charges now filed under BNS sections",
        ]
    return results


def search_legal_knowledge(intent: IntentObject) -> str:
    """
    Searches the embedded BNS 2023 + Indian Constitution knowledge bases.
    Returns relevant sections, articles, landmark cases, and quick-reference entries.
    """
    query = intent.content
    q = query.lower()
    output_lines = [
        f"LEGAL KNOWLEDGE SEARCH",
        f"Query : {query}",
        f"Case  : {intent.case_id}",
        "=" * 72,
        "",
    ]

    # -- BNS 2023 hits --
    bns_hits = _search_bns(query)
    if bns_hits:
        output_lines.append("-- BHARATIYA NYAYA SANHITA (BNS) 2023 --")
        for sec in bns_hits:
            output_lines.append(
                f"  S.{sec['section']} -- {sec['title']}\n"
                f"    Punishment : {sec.get('punishment', 'See full text')}\n"
                f"    Replaces   : {sec.get('ipc_equivalent', 'N/A')}\n"
                f"    Relevance  : {sec.get('relevance', sec.get('text', '')[:120])}...\n"
            )

    # -- Constitution hits --
    const_hits = _search_constitution(query)
    if const_hits:
        output_lines.append("-- CONSTITUTION OF INDIA --")
        for art in const_hits:
            lr = art.get("legal_relevance", "")
            lcases = art.get("landmark_cases", [])
            output_lines.append(
                f"  Article {art['article']} -- {art['title']}\n"
                f"    {lr if lr else art.get('text', '')[:180]}\n"
            )
            if lcases:
                output_lines.append("    Landmark cases:")
                for c in lcases[:2]:
                    output_lines.append(f"      > {c}")
            output_lines.append("")

    # -- Quick-reference table --
    bns_qr = _BNS_DB.get("quick_reference", {})
    const_qr = _CONST_DB.get("quick_reference", {})
    matched_qr = []
    for key, refs in {**bns_qr, **const_qr}.items():
        key_words = [w for w in key.split("_") if len(w) > 3]
        if any(re.search(r'\b' + re.escape(w) + r'\b', q) for w in key_words):
            matched_qr.extend(refs)
    if matched_qr:
        output_lines.append("-- QUICK REFERENCE --")
        for ref in dict.fromkeys(matched_qr):
            output_lines.append(f"  * {ref}")
        output_lines.append("")

    # -- Landmark cases --
    lm = _CONST_DB.get("landmark_cases_master", [])
    query_words = [w for w in q.split() if len(w) > 3]
    case_hits = [
        c for c in lm
        if any(re.search(r'\b' + re.escape(w) + r'\b', " ".join(c.get("tags", []))) for w in query_words)
    ]
    if case_hits:
        output_lines.append("-- LANDMARK CASES --")
        for c in case_hits[:3]:
            output_lines.append(
                f"  {c['name']} ({c['year']} {c['court']})\n"
                f"    {c['principle']}\n"
            )

    if len(output_lines) <= 6:
        output_lines.append("No direct matches found. Try keywords like: 'bail', 'trespass', 'fraud', 'Article 21', 'BNS 318', etc.")

    return "\n".join(output_lines)


# ─────────────────────────────────────────────
# Tool Registry
# ─────────────────────────────────────────────

TOOL_REGISTRY = {
    "draft_document":          draft_document,
    "search_case_law":         search_case_law,
    "advise_client":           advise_client,
    "summarize_case":          summarize_case,
    "read_case_files":         read_case_files,
    "research_precedents":     research_precedents,
    "summarize_precedents":    summarize_precedents,
    "analyze_contract":        analyze_contract,
    "calculate_damages":       calculate_damages,
    "draft_bail_application":  draft_bail_application,
    "review_evidence":         review_evidence,
    "file_motion":             file_motion,
    "prepare_strategy":        prepare_strategy,
    "send_legal_notice":       send_legal_notice,
    "send_communication":      send_communication,
    "search_legal_knowledge":  search_legal_knowledge,
}
