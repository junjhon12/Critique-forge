import re
from collections import Counter
from typing import TypedDict

FILTER_WORDS: list[str] = [
    "suddenly", "just", "very", "really", "somehow", "almost",
    "basically", "literally", "began to", "started to", "it was",
    "seemed to", "felt like", "sort of", "kind of",
]

SAID_BOOKISMS: list[str] = [
    "exclaimed", "interjected", "declared", "pontificated", "retorted",
    "ejaculated", "bellowed", "chortled", "hissed", "growled",
    "snapped", "asserted", "articulated",
]

_FIRST_PERSON = {"i", "me", "my", "mine", "we", "us", "our", "ours"}
_SECOND_PERSON = {"you", "your", "yours"}
_THIRD_PERSON = {"he", "him", "his", "she", "her", "hers", "they", "them", "their", "theirs"}

_PAST_IRREGULAR = {"was", "were", "had", "said", "went", "saw", "came", "took", "knew", "thought"}
_PRESENT_IRREGULAR = {"is", "are", "am", "has", "says", "goes", "sees", "comes", "takes", "knows", "thinks"}

_WORD_RE = re.compile(r"[a-zA-Z']+")


def audit_filter_words(text: str) -> dict[str, int]:
    """Case-insensitive count of crutch words/phrases and said-bookisms, non-zero only, sorted descending."""
    counts: dict[str, int] = {}
    for term in FILTER_WORDS + SAID_BOOKISMS:
        pattern = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
        n = len(pattern.findall(text))
        if n:
            counts[term] = n
    return dict(sorted(counts.items(), key=lambda kv: kv[1], reverse=True))


class PovTenseFlag(TypedDict):
    chunk_index: int
    dominant_pov: str
    dominant_tense: str
    shifted_pov: bool
    shifted_tense: bool


def _dominant_pov(words: list[str]) -> str:
    counts = Counter()
    for w in words:
        if w in _FIRST_PERSON:
            counts["first"] += 1
        elif w in _SECOND_PERSON:
            counts["second"] += 1
        elif w in _THIRD_PERSON:
            counts["third"] += 1
    if not counts:
        return "unknown"
    return counts.most_common(1)[0][0]


def _dominant_tense(words: list[str]) -> str:
    past = sum(1 for w in words if w in _PAST_IRREGULAR or (w.endswith("ed") and len(w) > 3))
    present = sum(1 for w in words if w in _PRESENT_IRREGULAR)
    if past == 0 and present == 0:
        return "unknown"
    return "past" if past >= present else "present"


def detect_pov_tense(chunks: list[str]) -> list[PovTenseFlag]:
    """Flag chunks whose dominant POV/tense differs from the previous chunk's. Heuristic, not a parser."""
    flags: list[PovTenseFlag] = []
    prev_pov: str | None = None
    prev_tense: str | None = None

    for i, chunk in enumerate(chunks):
        words = [w.lower() for w in _WORD_RE.findall(chunk)]
        pov = _dominant_pov(words)
        tense = _dominant_tense(words)

        shifted_pov = bool(
            prev_pov is not None and pov != "unknown" and prev_pov != "unknown" and pov != prev_pov
        )
        shifted_tense = bool(
            prev_tense is not None and tense != "unknown" and prev_tense != "unknown" and tense != prev_tense
        )

        flags.append({
            "chunk_index": i,
            "dominant_pov": pov,
            "dominant_tense": tense,
            "shifted_pov": shifted_pov,
            "shifted_tense": shifted_tense,
        })

        if pov != "unknown":
            prev_pov = pov
        if tense != "unknown":
            prev_tense = tense

    return flags
