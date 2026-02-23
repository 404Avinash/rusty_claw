"""
case_store.py — Simple local case file memory.
Stores case data as JSON files in memory/cases/.
"""

import json
from pathlib import Path

CASES_DIR = Path("memory/cases")


class CaseStore:
    """Simple persistent key-value store for case data."""

    def __init__(self):
        CASES_DIR.mkdir(parents=True, exist_ok=True)

    def save(self, case_id: str, data: dict):
        path = CASES_DIR / f"{case_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load(self, case_id: str) -> dict | None:
        path = CASES_DIR / f"{case_id}.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def all_cases(self) -> list[str]:
        return [p.stem for p in CASES_DIR.glob("*.json")]
