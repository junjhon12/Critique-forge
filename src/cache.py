import hashlib
import json
import os

from src.ai_client import CritiqueResult

CACHE_DIR = ".cache"
CACHE_PATH = os.path.join(CACHE_DIR, "critique_forge_cache.json")


def _cache_key(chunk: str, persona: str, genre: str = "None / General") -> str:
    return hashlib.sha256(f"{persona}::{genre}::{chunk}".encode()).hexdigest()


def load_cache() -> dict[str, CritiqueResult]:
    if not os.path.exists(CACHE_PATH):
        return {}
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_cache(cache: dict[str, CritiqueResult]) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f)
