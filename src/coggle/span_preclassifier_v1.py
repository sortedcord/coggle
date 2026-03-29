from __future__ import annotations
from enum import Enum
from dataclasses import dataclass
from typing import Optional
import re


class SpanRole(str, Enum):
    TARGET = "target"
    DESTINATION = "destination"
    CONSTRAINT = "constraint"
    ATTRIBUTE = "attribute"


# ---------------------------------------------------------------------------
# Signal vocabularies
# ---------------------------------------------------------------------------

# Prepositions that strongly indicate a destination span
_DESTINATION_PREPS = {"to", "into", "as", "toward", "towards"}

# Prepositions that strongly indicate a constraint span
_CONSTRAINT_PREPS = {"before", "after", "since", "until", "from", "within"}

# Comparative prepositions / phrases that signal size/value constraints
_CONSTRAINT_COMPARATIVES = {"larger", "smaller", "bigger", "greater", "less", "older", "newer", "over", "under", "above", "below"}

# Filter verbs — past-participle or base form verbs that act as selectors
_FILTER_VERBS = {"modified", "created", "accessed", "named", "called", "tagged", "dated", "starting", "ending", "matching", "containing", "starts", "ends", "matches", "contains", "beginning"}

# Known unit suffixes that signal an attribute value
_UNIT_PATTERN = re.compile(
    r"""
    ^\d+(\.\d+)?            # leading number (integer or decimal)
    \s*                     # optional space
    (
        kbps | mbps | bps   # bitrate
      | fps                 # framerate
      | kb | mb | gb | tb   # file size
      | kib | mib | gib     # file size (binary)
      | px                  # pixels
      | ms | s | m | h      # time
      | %                   # percentage
      | x                   # scale factor (2x, 4x)
      | p                   # resolution shorthand (720p, 1080p)
    )$
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Keywords that signal codec / quality attributes even without a numeric value
_ATTRIBUTE_KEYWORDS = {
    "lossless", "lossy", "compressed", "encoded", "codec",
    "quality", "bitrate", "framerate", "resolution", "format",
    "h264", "h265", "hevc", "avc", "vp9", "av1",
    "mp3", "aac", "flac", "opus",
    "webp", "jpeg", "png", "gif",
}

# File extension pattern — signals a filepath token (target or destination)
_EXTENSION_PATTERN = re.compile(r"\.\w{1,5}$")

# Path separator pattern — signals a filepath token
_PATH_PATTERN = re.compile(r"[/\\]")


# ---------------------------------------------------------------------------
# Per-token signal helpers
# ---------------------------------------------------------------------------

def _is_path_like(token) -> bool:
    """True if the token looks like a file path or filename."""
    text = token.text
    return bool(_PATH_PATTERN.search(text) or _EXTENSION_PATTERN.search(text))


def _is_unit_value(token) -> bool:
    """True if the token is a number+unit pair like 192kbps or 720p."""
    return bool(_UNIT_PATTERN.match(token.text))


def _is_numeric(token) -> bool:
    return token.pos_ == "NUM" or token.text.isdigit()


def _is_noun(token) -> bool:
    return token.pos_ in {"NOUN", "PROPN"}


def _is_prep(token) -> bool:
    return token.pos_ == "ADP" or token.dep_ == "prep"


# ---------------------------------------------------------------------------
# Span-level classifiers (evaluated in priority order)
# ---------------------------------------------------------------------------

def _classify_destination(span: list) -> bool:
    """
    A span is a destination if:
    - It leads with a destination preposition (to, into, as, ...), AND
      the next meaningful token is a noun or path-like token.
    - OR any token in the span is path-like AND no constraint prep is present.
    """
    if not span:
        return False

    first = span[0]

    # Leading destination preposition
    if first.lower_ in _DESTINATION_PREPS:
        # Confirm the rest of the span has a noun or path-like token
        rest = span[1:]
        if any(_is_noun(t) or _is_path_like(t) for t in rest):
            return True

    # Path-like token anywhere in span (but not led by a constraint prep)
    leading_word = first.lower_
    if leading_word not in _CONSTRAINT_PREPS and leading_word not in _CONSTRAINT_COMPARATIVES:
        if any(_is_path_like(t) for t in span):
            return True

    return False


def _classify_constraint(span: list) -> bool:
    """
    A span is a constraint if:
    - It contains a constraint preposition (before, after, since, ...)
    - Or it contains a filter verb (modified, starts, ends, matches, ...)
    - Or it contains a comparative keyword (larger than, smaller than, ...)
    """
    if not span:
        return False

    tokens_lower = [t.lower_ for t in span]

    # Constraint preposition anywhere in the span
    if any(t in _CONSTRAINT_PREPS for t in tokens_lower):
        return True

    # Filter verb anywhere in the span
    if any(t in _FILTER_VERBS for t in tokens_lower):
        return True

    # Comparative keyword (larger, smaller, older, newer, ...)
    if any(t in _CONSTRAINT_COMPARATIVES for t in tokens_lower):
        return True

    return False


def _classify_attribute(span: list) -> bool:
    """
    A span is an attribute if:
    - Any token matches the number+unit pattern (192kbps, 720p, 50%)
    - Or a numeric token is adjacent to a unit-like token
    - Or it contains an attribute keyword (lossless, codec, quality, ...)
    """
    if not span:
        return False

    tokens_lower = [t.lower_ for t in span]

    # Explicit unit value token
    if any(_is_unit_value(t) for t in span):
        return True

    # Attribute keyword
    if any(t in _ATTRIBUTE_KEYWORDS for t in tokens_lower):
        return True

    # Numeric token adjacent to a known unit word
    for i, token in enumerate(span):
        if _is_numeric(token):
            neighbours = []
            if i > 0:
                neighbours.append(span[i - 1].lower_)
            if i < len(span) - 1:
                neighbours.append(span[i + 1].lower_)
            unit_words = {"percent", "pixels", "seconds", "minutes", "hours", "frames", "kilobytes", "megabytes"}
            if any(n in unit_words for n in neighbours):
                return True

    return False


# ---------------------------------------------------------------------------
# Main classifier
# ---------------------------------------------------------------------------

@dataclass
class ClassifiedSpan:
    tokens: list          # original spaCy token objects
    role: SpanRole
    text: str             # human-readable reconstruction

    def __repr__(self) -> str:
        return f"ClassifiedSpan(role={self.role.value!r}, text={self.text!r})"


def classify_span(span: list) -> ClassifiedSpan:
    """
    Classify a single span (list of spaCy tokens) into one of four roles.
    Evaluation order: destination → constraint → attribute → target (default).
    """
    text = " ".join(t.text for t in span)

    if _classify_destination(span):
        role = SpanRole.DESTINATION
    elif _classify_constraint(span):
        role = SpanRole.CONSTRAINT
    elif _classify_attribute(span):
        role = SpanRole.ATTRIBUTE
    else:
        role = SpanRole.TARGET

    return ClassifiedSpan(tokens=span, role=role, text=text)


def classify_spans(spans: list[list]) -> list[ClassifiedSpan]:
    """
    Classify a list of spans as produced by the span splitter.
    Returns a list of ClassifiedSpan objects in the same order.
    """
    return [classify_span(span) for span in spans]


# ---------------------------------------------------------------------------
# Debug / pretty print
# ---------------------------------------------------------------------------

def explain_span(span: list) -> dict:
    """
    Returns a breakdown of which signals fired for a span.
    Useful for debugging and testing.
    """
    tokens_lower = [t.lower_ for t in span]
    return {
        "text": " ".join(t.text for t in span),
        "signals": {
            "destination_prep": [t for t in tokens_lower if t in _DESTINATION_PREPS],
            "constraint_prep": [t for t in tokens_lower if t in _CONSTRAINT_PREPS],
            "filter_verb": [t for t in tokens_lower if t in _FILTER_VERBS],
            "comparative": [t for t in tokens_lower if t in _CONSTRAINT_COMPARATIVES],
            "path_like": [t.text for t in span if _is_path_like(t)],
            "unit_value": [t.text for t in span if _is_unit_value(t)],
            "attribute_keyword": [t for t in tokens_lower if t in _ATTRIBUTE_KEYWORDS],
        },
        "role": classify_span(span).role.value,
    }