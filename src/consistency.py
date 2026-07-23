from typing import TypedDict

from src.ai_client import BibleEntity


class AttributeSighting(TypedDict):
    value: str
    chunk_index: int


class StoryBibleEntry(TypedDict):
    canonical_name: str
    entity_type: str
    aliases: set[str]
    attributes: dict[str, list[AttributeSighting]]
    first_seen_chunk: int


class ConsistencyFlag(TypedDict):
    entity_name: str
    attribute: str
    chunk_index: int
    previous_value: str
    new_value: str
    previous_chunk_index: int


def _resolve_key(bible: dict[str, StoryBibleEntry], entity: BibleEntity) -> str | None:
    candidates = {entity["name"].strip().lower()} | {a.strip().lower() for a in entity.get("aliases", [])}
    for key, entry in bible.items():
        known_names = {entry["canonical_name"].lower()} | {a.lower() for a in entry["aliases"]}
        if candidates & known_names:
            return key
    return None


def merge_entity(bible: dict[str, StoryBibleEntry], entity: BibleEntity, chunk_index: int) -> list[ConsistencyFlag]:
    """Merges a single extracted entity into the running story bible, returning any newly detected contradictions."""
    name = entity.get("name", "").strip()
    if not name:
        return []

    key = _resolve_key(bible, entity)
    if key is None:
        key = name.lower()
        bible[key] = {
            "canonical_name": name,
            "entity_type": entity.get("entity_type", "character"),
            "aliases": set(),
            "attributes": {},
            "first_seen_chunk": chunk_index,
        }

    entry = bible[key]
    entry["aliases"].update(a.strip() for a in entity.get("aliases", []) if a.strip())
    if name.lower() != entry["canonical_name"].lower():
        entry["aliases"].add(name)

    flags: list[ConsistencyFlag] = []
    for attr_name, new_value in entity.get("attributes", {}).items():
        new_value = str(new_value).strip()
        if not new_value:
            continue
        sightings = entry["attributes"].setdefault(attr_name, [])
        if sightings:
            last = sightings[-1]
            if last["value"].strip().lower() != new_value.lower():
                flags.append({
                    "entity_name": entry["canonical_name"],
                    "attribute": attr_name,
                    "chunk_index": chunk_index,
                    "previous_value": last["value"],
                    "new_value": new_value,
                    "previous_chunk_index": last["chunk_index"],
                })
        sightings.append({"value": new_value, "chunk_index": chunk_index})

    return flags
