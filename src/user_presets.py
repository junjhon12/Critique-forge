import json
import os
from typing import TypedDict

from src.structure import BeatDefinition

USER_PRESETS_PATH = os.path.join(".cache", "user_presets.json")


class UserPresets(TypedDict):
    genres: dict[str, str]
    structure_templates: dict[str, list[BeatDefinition]]


def _empty_presets() -> UserPresets:
    return {"genres": {}, "structure_templates": {}}


def load_user_presets() -> UserPresets:
    if not os.path.exists(USER_PRESETS_PATH):
        return _empty_presets()
    try:
        with open(USER_PRESETS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return _empty_presets()
    return {
        "genres": data.get("genres", {}),
        "structure_templates": data.get("structure_templates", {}),
    }


def _save_user_presets(presets: UserPresets) -> None:
    os.makedirs(os.path.dirname(USER_PRESETS_PATH), exist_ok=True)
    with open(USER_PRESETS_PATH, "w", encoding="utf-8") as f:
        json.dump(presets, f)


def save_genre_preset(name: str, guidance: str) -> None:
    presets = load_user_presets()
    presets["genres"][name] = guidance
    _save_user_presets(presets)


def save_structure_template(name: str, beats: list[BeatDefinition]) -> None:
    presets = load_user_presets()
    presets["structure_templates"][name] = beats
    _save_user_presets(presets)
