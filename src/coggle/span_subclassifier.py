import re
from dataclasses import dataclass
from typing import List, Literal, Dict, Any


@dataclass
class SpanResult:
    category: Literal["TARGET", "CONSTRAINT", "DESTINATION"]
    subtype: str
    value: dict
    raw_tokens: list
    confidence: float


@dataclass
class PathContext:
    original: str
    placeholder: str
    is_file: bool | None
    mime: str | None
    existed: bool


class SubclassifierError(Exception):
    def __init__(self, span_text, category, reason):
        super().__init__(f"[{category}] '{span_text}': {reason}")



MIME_CATEGORY_MAP = {
    "image":    ["photo", "image", "picture", "pics"],
    "video":    ["video", "movie", "clip", "footage"],
    "audio":    ["audio", "music", "sound", "recording", "track"],
    "document": ["document", "doc", "file", "pdf", "spreadsheet"],
} # maybe use MiniLM or similar to match cosine similarity

MIME_CATEGORY_EXTENSIONS = {
    "image":    [".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff", ".svg"],
    "video":    [".mp4", ".mkv", ".webm", ".mov", ".avi", ".flv"],
    "audio":    [".mp3", ".flac", ".wav", ".aac", ".ogg", ".m4a"],
    "document": [".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".txt", ".md"],
} # try using a MIME lookup table or something

SIZE_UNITS = {"kb": "KB", "mb": "MB", "gb": "GB", "b": "B"}

RESOLUTION_MAP = {
    "1080p": (1920, 1080),
    "720p": (1280, 720),
    "480p": (854, 480),
    "4k": (3840, 2160),
}

PLACEHOLDER_RE = re.compile(r"my(file|dir)path\d+")



def span_text(tokens):
    return " ".join(t.text for t in tokens)

def get_placeholder(tokens, path_ctx):
    for t in tokens:
        if PLACEHOLDER_RE.match(t.text):
            return path_ctx.get(t.text)
    return None

def normalize_extension(ext):
    ext = ext.lower().lstrip(".")
    return f".{ext}"



def classify_target(tokens, path_ctx):
    text = span_text(tokens)

    # 1. Placeholder
    pc = get_placeholder(tokens, path_ctx)
    if pc:
        return SpanResult(
            "TARGET",
            "filepath",
            {"pattern": pc.original},
            tokens,
            1.0 if pc.existed else 0.8
        )

    lemmas = [t.lemma_.lower() for t in tokens]

    # 2. extension / mime detection
    exts = []
    mime_hits = []
    extension_stopwords = {
        "all", "every", "file", "files", "folder", "folders",
        "the", "a", "an", "this", "that"
    }

    for t in tokens:
        txt = t.text.lower().lstrip(".")

        # collect everything that looks like a candidate
        if re.match(r"^[a-z0-9]{2,10}$", txt):
            if txt in extension_stopwords:
                continue

            # avoid pluralized stopwords, e.g. files/folders
            if txt.endswith("s") and txt[:-1] in extension_stopwords:
                continue

            exts.append(f".{txt}")

    # post-process
    valid_exts = []
    for ext in exts:
        raw = ext.lstrip(".")

        # check if it's actually a MIME category word
        for cat, words in MIME_CATEGORY_MAP.items():
            if raw in words:
                mime_hits.append(cat)
                break
        else:
            valid_exts.append(ext)

    # if we detected MIME category → prioritize it
    if mime_hits:
        cat = mime_hits[0]  # first match is enough
        return SpanResult(
            "TARGET",
            "mimecategory",
            {
                "category": cat,
                "extensions": MIME_CATEGORY_EXTENSIONS[cat]
            },
            tokens,
            0.8
        )

    # else if real extensions exist
    if valid_exts:
        return SpanResult(
            "TARGET",
            "extension_set",
            {"extensions": list(set(valid_exts))},
            tokens,
            1.0
        )

    # 4. filepath / glob
    if any(sym in text for sym in ["/", "~", "*", "?", "."]):
        return SpanResult("TARGET", "filepath", {"pattern": text}, tokens, 0.8)

    # 5. all (ONLY if nothing else matched)
    if any(l in ["all", "every"] for l in lemmas):
        return SpanResult("TARGET", "all", {}, tokens, 0.8)

    raise SubclassifierError(text, "TARGET", "No valid subtype match")



def classify_constraint(tokens):
    text = span_text(tokens)
    lemmas = [t.lemma_.lower() for t in tokens]

    # timestamp
    year_match = re.search(r"\b(20\d{2})\b", text)
    if year_match:
        year = year_match.group(1)
        comparator = "lt" if "before" in lemmas or "older" in lemmas else \
                     "gt" if "after" in lemmas or "newer" in lemmas else "eq"

        return SpanResult(
            "CONSTRAINT",
            "timestamp",
            {
                "field": "modified",
                "comparator": comparator,
                "value": f"{year}-01-01"
            },
            tokens,
            1.0
        )

    # quantity (size)
    m = re.search(r"(\d+)\s*(kb|mb|gb|b)", text.lower())
    if m:
        val = int(m.group(1))
        unit = SIZE_UNITS[m.group(2)]
        comparator = "gt" if any(w in lemmas for w in ["over", "larger", "bigger"]) else \
                     "lt" if any(w in lemmas for w in ["under", "smaller"]) else "eq"

        return SpanResult(
            "CONSTRAINT",
            "quantity",
            {"field": "size", "comparator": comparator, "value": val, "unit": unit},
            tokens,
            1.0
        )

    # count
    m = re.search(r"(first|last)\s+(\d+)", text.lower())
    if m:
        return SpanResult(
            "CONSTRAINT",
            "count",
            {"selector": m.group(1), "n": int(m.group(2))},
            tokens,
            1.0
        )

    # type
    if "file" in lemmas:
        return SpanResult("CONSTRAINT", "type", {"target": "file"}, tokens, 0.8)
    if "directory" in lemmas or "folder" in lemmas:
        return SpanResult("CONSTRAINT", "type", {"target": "directory"}, tokens, 0.8)

    raise SubclassifierError(text, "CONSTRAINT", "No valid subtype match")



def classify_destination(tokens, path_ctx):
    text = span_text(tokens)

    # 1. Placeholder
    pc = get_placeholder(tokens, path_ctx)
    if pc:
        return SpanResult(
            "DESTINATION",
            "filepath",
            {"resolved": pc.original, "is_file": pc.is_file},
            tokens,
            1.0
        )

    # 2. filepath_pattern (extension only)
    if re.match(r"^\.[a-z0-9]+$", text.strip()):
        ext = normalize_extension(text.strip())
        return SpanResult(
            "DESTINATION",
            "filepath_pattern",
            {"template": f"{{stem}}{ext}", "per_file": True},
            tokens,
            1.0
        )

    # 3. dimensions
    if text.lower() in RESOLUTION_MAP:
        w, h = RESOLUTION_MAP[text.lower()]
        return SpanResult(
            "DESTINATION",
            "dimensions",
            {"width": w, "height": h},
            tokens,
            1.0
        )

    # 4. quantity (compression target)
    m = re.search(r"(\d+)\s*(kb|mb|gb)", text.lower())
    if m:
        return SpanResult(
            "DESTINATION",
            "quantity",
            {"value": int(m.group(1)), "unit": SIZE_UNITS[m.group(2)]},
            tokens,
            1.0
        )

    # 5. enum (fallback, always allowed)
    if tokens:
        return SpanResult(
            "DESTINATION",
            "enum",
            {"raw": text.strip()},
            tokens,
            0.6
        )

    raise SubclassifierError(text, "DESTINATION", "No valid subtype match")



def subclassify(spans, path_ctx: Dict[str, PathContext]) -> List[SpanResult]:
    results = []

    for tokens, category in spans:
        if category == "TARGET":
            results.append(classify_target(tokens, path_ctx))
        elif category == "CONSTRAINT":
            results.append(classify_constraint(tokens))
        elif category == "DESTINATION":
            results.append(classify_destination(tokens, path_ctx))
        else:
            raise ValueError(f"Unknown category: {category}")

    return results