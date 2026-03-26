from dataclasses import dataclass
from enum import Enum
from typing import Optional
import re


class Intent(str, Enum):
    LIST = "list"
    MOVE = "move"
    COPY = "copy"
    DELETE = "delete"
    RENAME = "rename"
    CREATE = "create"
    TRUNCATE = "truncate"
    SYMLINK = "symlink"
    HARDLINK = "hardlink"


class Domain(str, Enum):
    FILESYSTEM = "filesystem"


@dataclass
class IntentDefinition:
    keywords: list[str]
    # this intent takes priority over when both are matched in the same query.
    # e.g. symlink overrides create so "make a symlink" resolves to symlink, not a compound query.
    overrides: list[Intent] | None = None

    def __post_init__(self):
        if self.overrides is None:
            self.overrides = []


INTENT_DEFINITIONS: dict[Intent, IntentDefinition] = {
    Intent.LIST: IntentDefinition(
        keywords=[
            "list",
            "find",
            "search",
            "show",
            "get",
            "look",
            "locate",
            "display",
            "fetch",
            "where",
        ]
    ),
    Intent.MOVE: IntentDefinition(
        keywords=["move", "transfer", "relocate", "shift", "put"]
    ),
    Intent.COPY: IntentDefinition(keywords=["copy", "duplicate", "clone", "replicate"]),
    Intent.DELETE: IntentDefinition(
        keywords=[
            "delete",
            "remove",
            "erase",
            "wipe",
            "trash",
            "destroy",
            "unlink",
            "purge",
        ]
    ),
    Intent.RENAME: IntentDefinition(keywords=["rename", "relabel"]),
    Intent.CREATE: IntentDefinition(
        keywords=["create", "make", "touch", "new", "add", "generate", "init"]
    ),
    Intent.TRUNCATE: IntentDefinition(keywords=["truncate", "clear", "empty", "zero"]),
    Intent.SYMLINK: IntentDefinition(
        keywords=["symlink", "symbolic", "softlink", "soft link", "sym link"],
        overrides=[Intent.CREATE],
    ),
    Intent.HARDLINK: IntentDefinition(
        keywords=["hardlink", "hard link", "hard-link"], overrides=[Intent.CREATE]
    ),
}


@dataclass
class ClassifierResult:
    success: bool
    intent: Optional[Intent] = None
    domain: Optional[Domain] = None
    error: Optional[str] = None
    matched_intents: Optional[list[Intent]] = None


def _tokenize(query: str) -> str:
    """Lowercase and normalize whitespace."""
    return re.sub(r"\s+", " ", query.lower().strip())


def classify(query: str) -> ClassifierResult:
    normalized = _tokenize(query)
    matched: list[Intent] = []

    for intent, defn in INTENT_DEFINITIONS.items():
        for keyword in defn.keywords:
            # word-boundary matching to avoid partial matches (e.g. "finder" matching "find")
            pattern = rf"\b{re.escape(keyword)}\b"
            if re.search(pattern, normalized):
                matched.append(intent)
                break  # one keyword match per intent is enough

    if len(matched) == 0:
        return ClassifierResult(
            success=False, error="No recognizable intent found in query."
        )

    if len(matched) > 1:
        resolved = list(matched)
        for intent in matched:
            for overridden in INTENT_DEFINITIONS[intent].overrides:
                if overridden in resolved:
                    resolved.remove(overridden)

        if len(resolved) == 1:
            return ClassifierResult(
                success=True, intent=resolved[0], domain=Domain.FILESYSTEM
            )

        return ClassifierResult(
            success=False,
            error=f"Compound query detected. Coggle currently supports single operations only. "
            f"Detected intents: {[i.value for i in resolved]}",
            matched_intents=resolved,
        )

    return ClassifierResult(success=True, intent=matched[0], domain=Domain.FILESYSTEM)
