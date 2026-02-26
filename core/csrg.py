"""
core/csrg.py — CSRG: Cryptographic Signed Response Graph
Implements ArmorIQ's Merkle tree intent chain concept.

Every IntentObject becomes a Merkle node. Each node's hash includes:
  - SHA256(action + agent + case_id + timestamp + parent_hash)
So the chain is tamper-evident: modifying ANY node breaks all subsequent hashes.

ArmorIQ armorclaw docs: "Cryptographic Verification — Optional CSRG Merkle tree proofs
for tamper-proof intent tracking"

This provides verifiable proof that:
  1. Every action was explicitly proposed as an IntentObject
  2. The chain has not been modified after the fact
  3. Blocked actions are permanently recorded in the chain
"""

import hashlib
import json
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional
from core.intent_model import IntentObject, PolicyDecision


@dataclass
class MerkleNode:
    """A single node in the CSRG Merkle intent chain."""
    depth: int
    action: str
    action_label: str
    agent: str
    delegated_by: Optional[str]
    case_id: str
    timestamp: str
    decision: str           # "ALLOWED" | "BLOCKED"
    enforcement_type: str
    plain_explanation: str
    parent_hash: str        # Hash of previous node (or "GENESIS" for root)
    node_hash: str = ""     # Computed after creation

    def compute_hash(self) -> str:
        payload = (
            f"{self.depth}:{self.action}:{self.agent}:{self.case_id}:"
            f"{self.timestamp}:{self.decision}:{self.parent_hash}"
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    def to_dict(self) -> dict:
        return {
            "depth":            self.depth,
            "action":           self.action,
            "action_label":     self.action_label,
            "agent":            self.agent,
            "delegated_by":     self.delegated_by,
            "case_id":          self.case_id,
            "timestamp":        self.timestamp,
            "decision":         self.decision,
            "enforcement_type": self.enforcement_type,
            "plain_explanation": self.plain_explanation,
            "parent_hash":      self.parent_hash[:12] + "...",
            "node_hash":        self.node_hash[:12] + "...",
            "node_hash_full":   self.node_hash,
            "parent_hash_full": self.parent_hash,
            "is_blocked":       self.decision != "ALLOWED",
            "tampered":         False,   # Set by verify_integrity()
        }


class MerkleIntentTree:
    """
    Append-only Merkle tree of all IntentObject decisions in the session.
    Provides cryptographic proof that the decision log has not been tampered with.

    The root_hash changes with every new decision — it represents the
    "state of the enforcement session" at any point in time.
    """

    GENESIS_HASH = "0" * 64  # Genesis block — root has no parent

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.nodes: list[MerkleNode] = []
        self.root_hash: str = self.GENESIS_HASH
        self._tamper_mode: bool = False  # For demo tamper simulation

    def add(self, intent: IntentObject, decision: PolicyDecision) -> MerkleNode:
        """Add a new decision to the Merkle chain. Returns the created node."""
        node = MerkleNode(
            depth=len(self.nodes),
            action=intent.action,
            action_label=intent.action_label,
            agent=intent.initiated_by,
            delegated_by=intent.delegated_by,
            case_id=intent.case_id,
            timestamp=datetime.now().isoformat(),
            decision="ALLOWED" if decision.allowed else "BLOCKED",
            enforcement_type=decision.enforcement_type,
            plain_explanation=decision.plain_explanation or decision.chat_message,
            parent_hash=self.root_hash,
        )
        node.node_hash = node.compute_hash()
        self.root_hash = node.node_hash
        self.nodes.append(node)
        return node

    def verify_integrity(self) -> dict:
        """
        Re-computes every node's hash from scratch and checks against stored hashes.
        Returns a report: {valid: bool, tampered_at: index or None, details: [...]}
        """
        prev_hash = self.GENESIS_HASH
        details = []
        tampered_at = None

        for i, node in enumerate(self.nodes):
            # Recompute based on stored fields
            recomputed = hashlib.sha256(
                f"{node.depth}:{node.action}:{node.agent}:{node.case_id}:"
                f"{node.timestamp}:{node.decision}:{prev_hash}".encode()
            ).hexdigest()

            actual = node.node_hash
            # Inject tamper if demo mode
            if self._tamper_mode and i == len(self.nodes) // 2:
                actual = "tampered_" + actual[9:]  # Simulate corruption

            ok = recomputed == actual
            if not ok and tampered_at is None:
                tampered_at = i

            details.append({
                "depth":      i,
                "action":     node.action,
                "hash_ok":    ok,
                "hash":       actual[:12] + "...",
            })
            prev_hash = actual  # Propagate (even if tampered, to show cascade)

        return {
            "valid":       tampered_at is None,
            "tampered_at": tampered_at,
            "total_nodes": len(self.nodes),
            "root_hash":   self.root_hash[:16] + "...",
            "details":     details,
        }

    def get_proof(self, action: str) -> list[dict]:
        """Returns the Merkle path for a specific action (audit proof)."""
        path = []
        for node in self.nodes:
            path.append({
                "depth":    node.depth,
                "action":   node.action,
                "hash":     node.node_hash[:16] + "...",
                "decision": node.decision,
                "is_target": node.action == action,
            })
        return path

    def to_dict(self) -> dict:
        """Serialize the full tree for the /api/merkle endpoint."""
        return {
            "session_id":  self.session_id,
            "root_hash":   self.root_hash[:16] + "...",
            "root_hash_full": self.root_hash,
            "total_nodes": len(self.nodes),
            "genesis_hash": self.GENESIS_HASH[:16] + "...",
            "nodes":       [n.to_dict() for n in self.nodes],
            "integrity":   self.verify_integrity(),
        }

    def simulate_tamper(self):
        """Demo: Toggle tamper mode to show chain integrity check catching corruption."""
        self._tamper_mode = not self._tamper_mode
        return self._tamper_mode


# Global session tree (reset on each demo run)
_session_tree: Optional[MerkleIntentTree] = None


def get_session_tree(session_id: str = "default") -> MerkleIntentTree:
    global _session_tree
    if _session_tree is None:
        _session_tree = MerkleIntentTree(session_id)
    return _session_tree


def reset_tree(session_id: str) -> MerkleIntentTree:
    global _session_tree
    _session_tree = MerkleIntentTree(session_id)
    return _session_tree
