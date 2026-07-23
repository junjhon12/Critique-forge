import json
import os
import re
from typing import TypedDict


HISTORY_DIR = os.path.join(".cache", "history")


class HistoryEntry(TypedDict):
    timestamp: str
    persona: str
    avg_scores: dict[str, int]
    num_sections: int


def manuscript_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "untitled"


def history_path(manuscript_id: str) -> str:
    return os.path.join(HISTORY_DIR, f"{manuscript_id}.json")


def load_history(manuscript_id: str) -> list[HistoryEntry]:
    path = history_path(manuscript_id)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def append_history(manuscript_id: str, entry: HistoryEntry) -> None:
    entries = load_history(manuscript_id)
    entries.append(entry)
    os.makedirs(HISTORY_DIR, exist_ok=True)
    with open(history_path(manuscript_id), "w", encoding="utf-8") as f:
        json.dump(entries, f)
