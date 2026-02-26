"""
intent_model.py — ArmorIQ x OpenClaw Hackathon
Structured intent model: agents PROPOSE, never execute directly.
Every action becomes a typed IntentObject before reaching the executor.
PolicyDecision carries both technical and plain-English explanations.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime
import json


# ─────────────────────────────────────────────
# Human-readable action labels (for UI display)
# ─────────────────────────────────────────────

ACTION_LABELS: dict[str, str] = {
    "draft_document":                  "Draft Legal Document",
    "search_case_law":                 "Search Case Law",
    "advise_client":                   "Advise Client",
    "summarize_case":                  "Summarize Case",
    "read_case_files":                 "Read Case Files",
    "file_motion":                     "File Court Motion",
    "prepare_strategy":                "Prepare Legal Strategy",
    "research_precedents":             "Research Precedents",
    "analyze_contract":                "Analyse Contract",
    "calculate_damages":               "Calculate Damages",
    "draft_bail_application":          "Draft Bail Application",
    "review_evidence":                 "Review Evidence",
    "send_legal_notice":               "Send Legal Notice",
    "send_communication":              "Send External Communication",
    "contact_opposing_party_directly": "Contact Opposing Party",
    "share_privileged_info_externally":"Share Privileged Information",
    "advise_evidence_destruction":     "Advise Evidence Destruction",
    "fabricate_evidence":              "Fabricate Evidence",
    "suborning_perjury":               "Coach Client to Lie (Perjury)",
    "act_outside_jurisdiction":        "Act Outside Jurisdiction",
    "file_frivolous_motion":           "File Frivolous Motion",
    "threaten_witness":                "Threaten a Witness",
    "bribe_court_official":            "Bribe Court Official",
    "conceal_relevant_facts":          "Conceal Relevant Facts",
    "misrepresent_law":                "Misrepresent the Law",
    "advise_illegal_activity":         "Advise Illegal Activity",
    "summarize_precedents":            "Summarise Legal Precedents",
    "search_legal_knowledge":          "Search BNS 2023 / Constitution",
}

# Plain English explanations for each action (shown in the chat panel)
ACTION_PLAIN_ENGLISH: dict[str, str] = {
    "draft_document":                  "Your lawyer is writing a formal legal document on your behalf.",
    "search_case_law":                 "Your lawyer is searching through court records and past cases to find arguments that support your position.",
    "advise_client":                   "Your lawyer is giving you personalised legal advice based on your situation.",
    "summarize_case":                  "Your lawyer is reviewing everything about your case and putting together a clear picture of the situation.",
    "read_case_files":                 "Your lawyer is reading all the documents related to your case.",
    "file_motion":                     "Your lawyer is preparing a formal request to submit to the court.",
    "prepare_strategy":                "Your lawyer is building a step-by-step plan to handle your case effectively.",
    "research_precedents":             "Your lawyer is looking at previous court rulings that could help your case.",
    "analyze_contract":                "Your lawyer is carefully reading through the contract to find where the other party broke the rules.",
    "calculate_damages":               "Your lawyer is working out how much money you may be entitled to claim.",
    "draft_bail_application":          "Your lawyer is writing an urgent application to get your client released on bail.",
    "review_evidence":                 "Your lawyer is examining all the evidence available to assess the strength of the case.",
    "send_legal_notice":               "Your lawyer is preparing a formal written warning to be sent to the other party.",
    "contact_opposing_party_directly": "⚠️ Your lawyer cannot contact the other party directly — that's not allowed when they have legal representation. All contact must go through their lawyer.",
    "share_privileged_info_externally":"⚠️ Everything you tell your lawyer is private and protected by law. Sharing it externally would be a serious breach of that trust.",
    "advise_evidence_destruction":     "⚠️ Your lawyer cannot advise you to destroy evidence. Doing so is a crime under Indian law.",
    "fabricate_evidence":              "⚠️ Your lawyer cannot help create fake evidence. This is a criminal offence.",
    "suborning_perjury":               "⚠️ Your lawyer cannot coach you or anyone else to lie in court. This is a serious criminal offence.",
    "act_outside_jurisdiction":        "⚠️ This case falls outside the area where your lawyer is authorised to practice.",
    "file_frivolous_motion":           "⚠️ Your lawyer cannot file a motion without proper legal grounds. Doing so could result in penalties.",
    "threaten_witness":                "⚠️ Threatening a witness is a criminal offence. Your lawyer absolutely cannot do this.",
    "bribe_court_official":            "⚠️ Bribing a judge or court official is a serious crime. Your lawyer refuses this request entirely.",
    "conceal_relevant_facts":          "⚠️ Your lawyer is required to be honest with the court. Hiding important facts is not allowed.",
    "misrepresent_law":                "⚠️ Your lawyer cannot misstate or misrepresent what the law says.",
    "advise_illegal_activity":         "⚠️ Your lawyer cannot advise you to do anything that breaks the law.",
    "send_communication":              "Your lawyer is sending a message on your behalf.",
    "summarize_precedents":            "Your lawyer is creating a summary of relevant past court decisions.",
}


@dataclass
class IntentObject:
    """
    The atomic unit of agent intent.
    Every proposed action must be expressed as an IntentObject.
    Agents never call tools directly — they build IntentObjects.
    The PolicyEngine validates these before execution is allowed.
    """
    action: str                          # e.g. "draft_document", "contact_opposing_party_directly"
    initiated_by: str                    # "lead_lawyer" | "research_agent"
    target: str                          # recipient, filename, resource
    content: str                         # summary of what will be done
    case_id: str                         # case context
    delegated_by: Optional[str] = None  # None for lead agent; "lead_lawyer" for sub-agents
    metadata: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def action_label(self) -> str:
        """Human-readable label for the action."""
        return ACTION_LABELS.get(self.action, self.action.replace("_", " ").title())

    @property
    def plain_english(self) -> str:
        """Plain English explanation of what this agent wants to do."""
        return ACTION_PLAIN_ENGLISH.get(self.action, f"Your lawyer wants to: {self.action_label}.")

    def to_dict(self) -> dict:
        d = asdict(self)
        d["action_label"] = self.action_label
        d["plain_english"] = self.plain_english
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def __str__(self) -> str:
        delegated_str = f" [delegated by: {self.delegated_by}]" if self.delegated_by else ""
        return (
            f"IntentObject(\n"
            f"  action      : {self.action} ({self.action_label})\n"
            f"  initiated_by: {self.initiated_by}{delegated_str}\n"
            f"  target      : {self.target}\n"
            f"  content     : {self.content[:80]}{'...' if len(self.content) > 80 else ''}\n"
            f"  case_id     : {self.case_id}\n"
            f"  timestamp   : {self.timestamp}\n"
            f")"
        )


@dataclass
class PolicyDecision:
    """
    The result of a PolicyEngine.validate() call.
    Contains the allow/block verdict + full reasoning + plain English.
    """
    allowed: bool
    reason: str
    rule_violated: Optional[str]         # e.g. "BNS Section 238", "attorney_client_privilege"
    enforcement_type: str                # "ALLOWED" | "HARD_BLOCK" | "DELEGATION_EXCEEDED"
    intent: Optional[IntentObject] = None
    plain_explanation: str = ""          # Simple one-liner for non-lawyers

    @property
    def chat_message(self) -> str:
        """The message to show in the Plain English chat panel."""
        if self.intent:
            if self.allowed:
                return self.intent.plain_english
            else:
                blocked_msg = ACTION_PLAIN_ENGLISH.get(
                    self.intent.action,
                    f"⚠️ Your lawyer refused this request — it violates professional rules."
                )
                return blocked_msg
        return self.plain_explanation

    def __str__(self) -> str:
        icon = "✅" if self.allowed else "🚫"
        return (
            f"{icon} PolicyDecision(\n"
            f"  allowed          : {self.allowed}\n"
            f"  enforcement_type : {self.enforcement_type}\n"
            f"  reason           : {self.reason}\n"
            f"  rule_violated    : {self.rule_violated or 'None'}\n"
            f"  plain            : {self.plain_explanation or self.chat_message}\n"
            f")"
        )
