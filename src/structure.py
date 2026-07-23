import re
import statistics
from typing import TypedDict

_HEADING_RE = re.compile(r"^\s*(chapter|scene|part)\s+\w+.*$", re.IGNORECASE | re.MULTILINE)
_SCENE_BREAK_RE = re.compile(r"^\s*(\*\s*\*\s*\*|-{3,}|#{3,})\s*$", re.MULTILINE)

DEFAULT_TOLERANCE_PCT = 10.0
DEFAULT_STDDEV_THRESHOLD = 1.5
DEFAULT_Z_THRESHOLD = 1.5


class SceneInfo(TypedDict):
    index: int
    heading: str | None
    start_word: int
    word_count: int
    pct_start: float
    pct_end: float


class BeatDefinition(TypedDict):
    name: str
    expected_pct: float
    description: str


class BeatMatch(TypedDict):
    beat_name: str
    expected_pct: float
    matched_scene_index: int | None
    matched_scene_pct: float | None
    delta_pct: float | None


class PacingFlag(TypedDict):
    scene_index: int
    word_count: int
    expected_weight: float
    actual_weight: float
    deviation: float
    flag: str


class ChapterLengthFlag(TypedDict):
    scene_index: int
    word_count: int
    mean_word_count: float
    pct_deviation: float
    z_score: float
    flag: str


STRUCTURE_TEMPLATES: dict[str, list[BeatDefinition]] = {
    "None / General": [],
    "Three-Act Structure": [
        {"name": "Inciting Incident", "expected_pct": 10.0, "description": "The event that sets the story in motion."},
        {"name": "Plot Point 1 (Act break)", "expected_pct": 25.0, "description": "Protagonist commits to the journey."},
        {"name": "Midpoint", "expected_pct": 50.0, "description": "A major shift raises the stakes."},
        {"name": "Plot Point 2 (Act break)", "expected_pct": 75.0, "description": "The lowest point before the final push."},
        {"name": "Climax", "expected_pct": 90.0, "description": "The central conflict comes to a head."},
        {"name": "Resolution", "expected_pct": 97.0, "description": "Aftermath and new equilibrium."},
    ],
    "Save the Cat": [
        {"name": "Opening Image", "expected_pct": 1.0, "description": "A snapshot of the world before change."},
        {"name": "Catalyst", "expected_pct": 10.0, "description": "The inciting event."},
        {"name": "Break into Two", "expected_pct": 20.0, "description": "Protagonist enters the new world."},
        {"name": "Midpoint", "expected_pct": 50.0, "description": "False victory or false defeat."},
        {"name": "All Is Lost", "expected_pct": 75.0, "description": "The lowest point."},
        {"name": "Break into Three", "expected_pct": 80.0, "description": "The solution is found."},
        {"name": "Finale", "expected_pct": 90.0, "description": "The final confrontation."},
    ],
    "Hero's Journey": [
        {"name": "Call to Adventure", "expected_pct": 10.0, "description": "The hero is presented with a challenge."},
        {"name": "Crossing the Threshold", "expected_pct": 25.0, "description": "The hero commits to the journey."},
        {"name": "Tests, Allies, Enemies", "expected_pct": 40.0, "description": "The hero navigates the new world."},
        {"name": "Ordeal", "expected_pct": 55.0, "description": "The hero's greatest challenge yet."},
        {"name": "Reward", "expected_pct": 65.0, "description": "The hero claims what they sought."},
        {"name": "The Road Back", "expected_pct": 80.0, "description": "The hero commits to finishing the journey."},
        {"name": "Resurrection/Climax", "expected_pct": 90.0, "description": "The final, most dangerous test."},
        {"name": "Return with the Elixir", "expected_pct": 98.0, "description": "The hero returns transformed."},
    ],
}


def _scenes_from_spans(text: str, spans: list[tuple[int, str | None]]) -> list[SceneInfo]:
    """Build SceneInfo list from a sorted list of (char_offset, heading) split points."""
    boundaries = [span[0] for span in spans]
    segments: list[tuple[str, str | None]] = []
    for i, (offset, heading) in enumerate(spans):
        end = boundaries[i + 1] if i + 1 < len(boundaries) else len(text)
        segments.append((text[offset:end], heading))

    total_words = sum(len(seg.split()) for seg, _ in segments)
    if total_words == 0:
        return []

    scenes: list[SceneInfo] = []
    cursor = 0
    for i, (seg, heading) in enumerate(segments):
        word_count = len(seg.split())
        pct_start = cursor / total_words * 100
        pct_end = (cursor + word_count) / total_words * 100
        scenes.append({
            "index": i,
            "heading": heading,
            "start_word": cursor,
            "word_count": word_count,
            "pct_start": pct_start,
            "pct_end": pct_end,
        })
        cursor += word_count
    return scenes


def detect_scenes(raw_text: str, chunks: list[str] | None = None) -> list[SceneInfo]:
    """Split a manuscript into scenes/chapters by heading, then scene-break marker,
    falling back to the existing token-budget chunks as pseudo-scenes."""
    if not raw_text.strip():
        return []

    heading_matches = list(_HEADING_RE.finditer(raw_text))
    if heading_matches:
        spans = [(m.start(), m.group(0).strip()) for m in heading_matches]
        if spans[0][0] != 0:
            spans.insert(0, (0, None))
        return _scenes_from_spans(raw_text, spans)

    break_matches = list(_SCENE_BREAK_RE.finditer(raw_text))
    if break_matches:
        spans: list[tuple[int, str | None]] = [(0, None)]
        for m in break_matches:
            spans.append((m.end(), None))
        return _scenes_from_spans(raw_text, spans)

    if chunks:
        total_words = sum(len(c.split()) for c in chunks)
        if total_words == 0:
            return []
        scenes: list[SceneInfo] = []
        cursor = 0
        for i, chunk in enumerate(chunks):
            word_count = len(chunk.split())
            pct_start = cursor / total_words * 100
            pct_end = (cursor + word_count) / total_words * 100
            scenes.append({
                "index": i,
                "heading": None,
                "start_word": cursor,
                "word_count": word_count,
                "pct_start": pct_start,
                "pct_end": pct_end,
            })
            cursor += word_count
        return scenes

    return []


def map_beats_to_scenes(
    scenes: list[SceneInfo],
    template_name: str,
    tolerance_pct: float = DEFAULT_TOLERANCE_PCT,
) -> list[BeatMatch]:
    """Map each beat in a structure template to the nearest scene, flagging missing beats."""
    template = STRUCTURE_TEMPLATES.get(template_name, [])
    if not template or not scenes:
        return []

    matches: list[BeatMatch] = []
    for beat in template:
        best_index: int | None = None
        best_pct: float | None = None
        best_delta: float | None = None
        for scene in scenes:
            midpoint = (scene["pct_start"] + scene["pct_end"]) / 2
            delta = abs(midpoint - beat["expected_pct"])
            if best_delta is None or delta < best_delta:
                best_delta = delta
                best_pct = midpoint
                best_index = scene["index"]

        matched = best_delta is not None and best_delta <= tolerance_pct
        matches.append({
            "beat_name": beat["name"],
            "expected_pct": beat["expected_pct"],
            "matched_scene_index": best_index if matched else None,
            "matched_scene_pct": best_pct if matched else None,
            "delta_pct": best_delta if matched else None,
        })
    return matches


def analyze_pacing_weight(
    scenes: list[SceneInfo],
    template_name: str | None = None,
    stddev_threshold: float = DEFAULT_STDDEV_THRESHOLD,
) -> list[PacingFlag]:
    """Flag scenes disproportionately long/short relative to their expected narrative weight."""
    if len(scenes) < 2:
        return []

    total_words = sum(s["word_count"] for s in scenes)
    if total_words == 0:
        return []

    template = STRUCTURE_TEMPLATES.get(template_name, []) if template_name else []

    flags: list[PacingFlag] = []
    if template:
        boundaries = [0.0] + [b["expected_pct"] for b in template] + [100.0]
        for scene in scenes:
            midpoint = (scene["pct_start"] + scene["pct_end"]) / 2
            lower = max((b for b in boundaries if b <= midpoint), default=0.0)
            upper = min((b for b in boundaries if b >= midpoint), default=100.0)
            expected_weight = (upper - lower) / 100.0 if upper > lower else 1.0 / len(scenes)
            actual_weight = scene["word_count"] / total_words
            deviation = actual_weight - expected_weight
            if actual_weight > expected_weight * 1.5:
                flag = "too_long"
            elif actual_weight < expected_weight * 0.5:
                flag = "too_short"
            else:
                flag = "ok"
            flags.append({
                "scene_index": scene["index"],
                "word_count": scene["word_count"],
                "expected_weight": expected_weight,
                "actual_weight": actual_weight,
                "deviation": deviation,
                "flag": flag,
            })
    else:
        word_counts = [s["word_count"] for s in scenes]
        mean = statistics.mean(word_counts)
        stdev = statistics.pstdev(word_counts)
        for scene in scenes:
            actual_weight = scene["word_count"] / total_words
            expected_weight = 1.0 / len(scenes)
            z = (scene["word_count"] - mean) / stdev if stdev else 0.0
            if z > stddev_threshold:
                flag = "too_long"
            elif z < -stddev_threshold:
                flag = "too_short"
            else:
                flag = "ok"
            flags.append({
                "scene_index": scene["index"],
                "word_count": scene["word_count"],
                "expected_weight": expected_weight,
                "actual_weight": actual_weight,
                "deviation": actual_weight - expected_weight,
                "flag": flag,
            })
    return flags


def analyze_chapter_length_consistency(
    scenes: list[SceneInfo],
    z_threshold: float = DEFAULT_Z_THRESHOLD,
) -> list[ChapterLengthFlag]:
    """Flag scenes/chapters wildly outside the manuscript's own average length."""
    if len(scenes) < 2:
        return []

    word_counts = [s["word_count"] for s in scenes]
    mean = statistics.mean(word_counts)
    stdev = statistics.pstdev(word_counts)

    flags: list[ChapterLengthFlag] = []
    for scene in scenes:
        pct_deviation = ((scene["word_count"] - mean) / mean * 100) if mean else 0.0
        z_score = (scene["word_count"] - mean) / stdev if stdev else 0.0
        if z_score > z_threshold:
            flag = "outlier_long"
        elif z_score < -z_threshold:
            flag = "outlier_short"
        else:
            flag = "ok"
        flags.append({
            "scene_index": scene["index"],
            "word_count": scene["word_count"],
            "mean_word_count": mean,
            "pct_deviation": pct_deviation,
            "z_score": z_score,
            "flag": flag,
        })
    return flags
