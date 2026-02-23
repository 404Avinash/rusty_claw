# -*- coding: utf-8 -*-
"""
main.py - AI Lawyer | ARMORIQ x OPENCLAW Hackathon Demo
The 3-minute demo entry point.

Run with: python main.py
"""
import sys
import io
# Force UTF-8 output on Windows terminals
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


import time
import json
from pathlib import Path

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.rule import Rule
    from rich import box
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.prompt import Prompt
    from rich.align import Align
    from rich.columns import Columns
    from rich.live import Live
    from rich.layout import Layout
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from core.policy_engine import PolicyEngine
from core.executor import Executor, PolicyViolationError
from core.intent_model import IntentObject
from core.audit_logger import clear_logs, get_all_logs
from agents.lead_lawyer import LeadLawyer
from agents.research_agent import ResearchAgent
from memory.case_store import CaseStore
from tools.legal_tools import TOOL_REGISTRY

console = Console() if RICH_AVAILABLE else None

CASE_ID = "CASE-2026-001"

# ─────────────────────────────────────────────
# UI Helpers
# ─────────────────────────────────────────────

def print_banner():
    console.print()
    console.print(Panel.fit(
        "[bold cyan]== AI LEGAL AGENT ==[/bold cyan]\n"
        "[dim]Powered by OpenClaw + ArmorIQ Intent Enforcement[/dim]\n\n"
        "[yellow]\"We built an AI lawyer.\n"
        " But unlike a human lawyer, this one literally cannot cut corners.\"[/yellow]",
        border_style="cyan",
        padding=(1, 4),
    ))
    console.print()


def print_separator(title: str = ""):
    if title:
        console.print(Rule(f"[bold white]{title}[/bold white]", style="dim white"))
    else:
        console.print(Rule(style="dim white"))
    console.print()


def thinking(text: str, duration: float = 1.5):
    """Shows an animated thinking indicator."""
    with Progress(
        SpinnerColumn(spinner_name="dots"),
        TextColumn(f"[dim cyan]{text}[/dim cyan]"),
        transient=True,
        console=console,
    ) as progress:
        progress.add_task("", total=None)
        time.sleep(duration)


def show_intent(intent: IntentObject):
    """Displays a proposed intent in a formatted box."""
    table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
    table.add_column("Key", style="dim")
    table.add_column("Value")
    table.add_row("Action", f"[bold]{intent.action}[/bold]")
    table.add_row("Agent", intent.initiated_by)
    if intent.delegated_by:
        table.add_row("Delegated by", f"[yellow]{intent.delegated_by}[/yellow]")
    table.add_row("Target", intent.target)
    table.add_row("Content", intent.content[:80] + ("..." if len(intent.content) > 80 else ""))
    table.add_row("Case ID", intent.case_id)

    console.print(Panel(
        table,
        title="[bold blue]Agent Proposes Intent[/bold blue]",
        border_style="blue",
    ))


def show_decision(result: dict):
    """Displays the PolicyEngine decision with color coding."""
    decision = result.get("decision", "")
    enforcement = result.get("enforcement_type", "")
    reason = result.get("reason", "")
    rule = result.get("rule_violated", "")

    if decision == "ALLOWED":
        icon = "[OK]"
        color = "green"
        title = "[bold green]ALLOWED -- Action Executed[/bold green]"
        extra = result.get("result", "")
        body = f"[green]{reason}[/green]\n\n[dim]{extra}[/dim]"
    else:
        icon = "[X]"
        color = "red"
        title = f"[bold red]BLOCKED: {enforcement} -- Action Denied[/bold red]"
        rule_str = f"\n[yellow]Rule Violated: {rule}[/yellow]" if rule else ""
        body = f"[red]{reason}[/red]{rule_str}"

    console.print(Panel(
        body,
        title=title,
        border_style=color,
        padding=(0, 1),
    ))
    console.print()


def show_audit_log():
    """Displays the full audit log as a formatted table."""
    logs = get_all_logs()
    if not logs:
        console.print("[dim]No audit log entries yet.[/dim]")
        return

    table = Table(
        title="AUDIT LOG - Full Decision Trace",
        box=box.ROUNDED,
        border_style="cyan",
        show_lines=True,
    )
    table.add_column("Time", style="dim", width=10)
    table.add_column("Agent", style="cyan", width=16)
    table.add_column("Action", width=30)
    table.add_column("Status", width=10)
    table.add_column("Rule / Reason", width=40)

    for entry in logs:
        ts = entry.get("timestamp", "")[11:16]  # HH:MM from ISO string
        agent = entry.get("agent", "")
        del_by = entry.get("delegated_by")
        if del_by:
            agent += f" (via {del_by})"
        action = entry.get("proposed_action", "")
        status = entry.get("status", "")
        enforcement = entry.get("enforcement_type", "")
        reason = entry.get("reason", "")[:60] + ("..." if len(entry.get("reason","")) > 60 else "")
        rule = entry.get("rule_violated") or ""

        status_styled = f"[green]{status}[/green]" if status == "ALLOWED" else f"[red]{status}[/red]"
        reason_short = reason[:55] + ("..." if len(reason) > 55 else "")
        rule_reason = f"[yellow]{rule}[/yellow] | [dim]{reason_short}[/dim]" if rule else f"[dim]{reason_short}[/dim]"

        table.add_row(ts, agent, action, status_styled, rule_reason)

    console.print(table)


# ─────────────────────────────────────────────
# Demo Scenes
# ─────────────────────────────────────────────

def scene_1_case_intake(lawyer: LeadLawyer):
    """Scene 1: Client describes their case."""
    print_separator("SCENE 1 — CLIENT CASE INTAKE")

    console.print(Panel(
        "[bold white]Client Statement:[/bold white]\n\n"
        "[italic]\"My landlord has been illegally entering my apartment without notice, "
        "multiple times in the past month. I want to take legal action.\"[/italic]",
        title="[bold yellow]CLIENT[/bold yellow]",
        border_style="yellow",
    ))
    console.print()

    thinking("Lead Lawyer Agent analyzing case...", 2.0)
    lawyer.intake_case(
        "My landlord has been illegally entering my apartment without notice.",
        CASE_ID
    )
    console.print("[green]>>> Case registered.[/green] Case ID: [bold cyan]CASE-2026-001[/bold cyan]\n")


def scene_2_allowed_actions(lawyer: LeadLawyer):
    """Scene 2: Agent proposes and executes allowed legal actions."""
    print_separator("SCENE 2 — ALLOWED ACTIONS (Strategy Execution)")

    console.print("[dim italic]Lawyer is building a legal strategy...[/dim italic]\n")

    results = lawyer.analyze_and_act(CASE_ID, "landlord apartment illegal entry")

    for r in results:
        show_intent(r["intent"])
        thinking("PolicyEngine validating intent...", 1.0)
        show_decision(r)
        time.sleep(0.3)


def scene_3_perjury_block(lawyer: LeadLawyer):
    """Scene 3: Client asks agent to help lie — BLOCKED."""
    print_separator("SCENE 3 - ETHICAL VIOLATION ATTEMPT (Perjury)")

    console.print(Panel(
        "[bold white]Client says:[/bold white]\n\n"
        "[italic red]\"Just tell them we never received that notice. "
        "Say we didn't get it.\"[/italic red]",
        title="[bold yellow]CLIENT[/bold yellow]",
        border_style="red",
    ))
    console.print()

    thinking("Lead Lawyer Agent processing request...", 1.5)
    results = lawyer.analyze_and_act(CASE_ID, "tell them we never received that email, say we didn't get it")

    for r in results:
        show_intent(r["intent"])
        thinking("PolicyEngine validating intent against legal_rules.json...", 1.5)
        show_decision(r)

    console.print(Panel(
        "[dim]The agent has logged this violation and will suggest a legal alternative.[/dim]\n\n"
        "[green]>>> Legal Alternative:[/green] Assert that the notice was not properly served under "
        "applicable procedural rules, and request the opposing party to provide proof of service.",
        title="[green]Agent Suggests Legal Alternative[/green]",
        border_style="green",
    ))
    console.print()


def scene_4_direct_contact_block(lawyer: LeadLawyer):
    """Scene 4: Agent tries to contact opposing party — BLOCKED by Rule 4.2."""
    print_separator("SCENE 4 - RULE 4.2 VIOLATION (Direct Opposition Contact)")

    console.print(Panel(
        "[bold white]Client says:[/bold white]\n\n"
        "[italic red]\"Can you just reach out to the landlord directly and sort this out?\"[/italic red]",
        title="[bold yellow]CLIENT[/bold yellow]",
        border_style="red",
    ))
    console.print()

    thinking("Lead Lawyer Agent processing...", 1.5)
    results = lawyer.analyze_and_act(CASE_ID, "contact them directly, message opposing party landlord")

    for r in results:
        show_intent(r["intent"])
        thinking("PolicyEngine checking Rule 4.2...", 1.5)
        show_decision(r)


def scene_5_delegation(lawyer: LeadLawyer):
    """Scene 5: Delegation bonus — research agent tries to exceed scope."""
    print_separator("SCENE 5 — DELEGATION ENFORCEMENT (Bonus)")

    console.print(Panel(
        "[bold white]Lead Lawyer spawns a Research Agent...[/bold white]\n"
        "[dim]Delegated scope: [green]search_case_law[/green], [green]read_case_files[/green] only[/dim]",
        title="[bold cyan]DELEGATION[/bold cyan]",
        border_style="cyan",
    ))
    console.print()

    research_agent = lawyer.spawn_research_agent(CASE_ID)

    # Step 5a: Allowed research
    thinking("Research Agent searching case law...", 1.5)
    allowed_intent = IntentObject(
        action="search_case_law",
        initiated_by="research_agent",
        delegated_by="lead_lawyer",
        target="legal_database",
        content="Tenant rights illegal landlord entry India",
        case_id=CASE_ID,
    )
    console.print("[dim]Research Agent proposes intent:[/dim]")
    show_intent(allowed_intent)

    from core.policy_engine import PolicyEngine as PE
    result_allowed = research_agent.attempt_unauthorized_action(
        CASE_ID, "search_case_law", "legal_database", "Tenant rights illegal landlord entry India"
    )
    thinking("PolicyEngine checking delegated scope...", 1.0)
    show_decision(result_allowed)

    # Step 5b: Blocked — exceeds delegation
    console.print("[dim]Research Agent now tries to send an email...[/dim]\n")
    time.sleep(0.5)

    blocked_intent = IntentObject(
        action="send_communication",
        initiated_by="research_agent",
        delegated_by="lead_lawyer",
        target="landlord@property.com",
        content="We are aware of the tenant's situation and are taking action.",
        case_id=CASE_ID,
    )
    show_intent(blocked_intent)
    thinking("PolicyEngine checking delegation boundaries...", 1.5)

    result_blocked = research_agent.attempt_unauthorized_action(
        CASE_ID, "send_communication", "landlord@property.com",
        "We are aware of the tenant's situation and are taking action."
    )
    show_decision(result_blocked)

    console.print(Panel(
        "[green]>>> Delegation boundaries enforced.[/green]\n"
        "The research agent was hard-blocked from communicating externally.\n"
        "Its delegated authority is strictly limited to read-only research tasks.",
        title="[green]Delegation Enforcement Confirmed[/green]",
        border_style="green",
    ))
    console.print()


def scene_6_audit_log():
    """Scene 6: Show the full audit trail."""
    print_separator("SCENE 6 — AUDIT LOG (Full Decision Trace)")
    console.print("[dim italic]Every decision has been logged automatically...[/dim italic]\n")
    time.sleep(0.5)
    show_audit_log()


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    if not RICH_AVAILABLE:
        print("ERROR: 'rich' library not installed. Run: pip install rich")
        sys.exit(1)

    # Clean logs for fresh demo run
    clear_logs()

    # Initialize the system
    policy_engine = PolicyEngine()
    executor = Executor(policy_engine=policy_engine, tools=TOOL_REGISTRY)
    case_store = CaseStore()
    lawyer = LeadLawyer(executor=executor, case_store=case_store)

    # Print banner
    print_banner()

    console.print(
        "[bold]ArmorIQ x OpenClaw -- Intent Enforcement Demo[/bold]\n"
        "[dim]Policy: policies/legal_rules.json | Mode: Simulation[/dim]\n",
        justify="center",
    )

    input_val = console.input("[cyan]Press [bold]ENTER[/bold] to begin the demo...[/cyan] ")
    console.print()

    # Run all scenes
    scene_1_case_intake(lawyer)
    input("[dim press Enter to continue...][/dim]") if False else None
    time.sleep(0.5)

    scene_2_allowed_actions(lawyer)
    time.sleep(0.5)

    scene_3_perjury_block(lawyer)
    time.sleep(0.5)

    scene_4_direct_contact_block(lawyer)
    time.sleep(0.5)

    scene_5_delegation(lawyer)
    time.sleep(0.5)

    scene_6_audit_log()

    # Final summary
    logs = get_all_logs()
    allowed_count = sum(1 for l in logs if l["status"] == "ALLOWED")
    blocked_count = sum(1 for l in logs if l["status"] == "BLOCKED")

    console.print(Panel(
        f"[bold green]ALLOWED Actions : {allowed_count}[/bold green]\n"
        f"[bold red]BLOCKED Actions : {blocked_count}[/bold red]\n\n"
        f"[dim]Full trace saved to: logs/audit_log.jsonl[/dim]\n"
        f"[dim]Documents created in: output/[/dim]",
        title="[bold cyan]DEMO COMPLETE -- ArmorIQ x OpenClaw[/bold cyan]",
        border_style="cyan",
        padding=(1, 4),
    ))
    console.print()


if __name__ == "__main__":
    main()
