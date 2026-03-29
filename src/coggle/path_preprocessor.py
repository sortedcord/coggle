"""
Docstring for coggle.path_preprocessor

preprocess_paths -> _extract_candidiates: finds all path like tokens in the query and returns their positions
preprocess_paths -> (for each candidate) -> _resolve_path: converts token to absolute path
    if path DNE: _regex_fallback: use pattern matching to guess if it's a file or dir
    if path exists: _filesystem_check: check if it's file or dir and get MIME type
preprocess_paths -> (for each candidate) -> _make_placeholder: create a placeholder name based on file/dir type and index
"""
import re
import os
import mimetypes
from dataclasses import dataclass 

# --- Patterns ---

# for matching absolute paths like /foo/bar, /foo/bar.jpg, ~/foo/bar/
# ~ must be followed by / to avoid matching bare ~
# TODO: Map ~ to home dir
_ABS_PATH_RE = re.compile(r'(?:~/[\w.\-/]*|(?:/[\w.\-]+)+/?)')

# match relative paths with at least one separator: foo/bar, ./foo, ../foo/bar.jpg
_REL_PATH_RE = re.compile(r'(?:\.{1,2}/|[\w.\-]+/+)[\w./\-]*')

# match bare words: a single alphanumeric/underscore/hyphen/dot token
# match contain at least one letter (filters out pure numbers)
_BARE_WORD_RE = re.compile(r'\b([A-Za-z][\w.\-]*)\b')


@dataclass
class PathContext:
    original: str
    placeholder: str
    is_file: bool | None
    mime: str | None = None
    existed: bool = False


def _resolve_path(token: str, cwd: str) -> str:
    """raw token -> absolute path."""
    if token.startswith('~/'):
        return os.path.expanduser(token)
    if token.startswith('/'):
        return token
    # relative or bare word resolve against cwd
    return os.path.join(cwd, token)


def _filesystem_check(resolved: str) -> tuple[bool | None, str | None, bool]:
    """
    returns (is_file, mime, existed).
    is_file is true if file; false if dir; None if unknown
    mime: MIME type string or None
    existed: if the path existed at all
    """
    if os.path.isfile(resolved):
        mime, _ = mimetypes.guess_type(resolved)
        return True, mime, True
    if os.path.isdir(resolved):
        return False, None, True
    return None, None, False


def _regex_fallback(token: str) -> bool | None:
    """
    differentiate file vs directory from token syntax alone.
    returns True=file, False=dir, None=ambiguous.
    """
    if token.endswith('/'):
        return False  # directory
    if '.' in os.path.basename(token):
        return True  # has a dot in the final component treat as file
    # TODO: more heuristics? File directories may also have a dot, but we have already enforced that directories should end with /
    return None  # ambiguous


def _make_placeholder(is_file: bool | None, index: int) -> str:
    if is_file is True:
        return f'myfilepath{index}'
    return f'mydirpath{index}'  # dir or ambiguous both default to dir


def _extract_candidates(query: str) -> list[tuple[int, int, str]]:
    """
    extract (start, end, token) tuples for all path candidates in the query.
    sorted right-to-left so substitution doesn't shift earlier indices.
    """

    # collect all structured matches, then deduplicate by keeping only the
    # longest match at any overlapping region.
    raw: list[tuple[int, int, str]] = []
    for pattern in (_ABS_PATH_RE, _REL_PATH_RE):
        for m in pattern.finditer(query):
            raw.append((m.start(), m.end(), m.group()))

    # sort by length descending so longer (more specific) matches win
    raw.sort(key=lambda x: x[1] - x[0], reverse=True)

    # greedily accept matches that don't overlap with already-accepted ones
    covered: set[int] = set()
    accepted: list[tuple[int, int, str]] = []
    for start, end, tok in raw:
        span_chars = set(range(start, end))
        if not span_chars & covered:
            accepted.append((start, end, tok))
            covered |= span_chars

    # bare words only where not covered by any structured match
    for m in _BARE_WORD_RE.finditer(query):
        if m.start() not in covered:
            accepted.append((m.start(), m.end(), m.group()))
            covered.update(range(m.start(), m.end()))

    # RTL so string substitution doesn't invalidate earlier indices
    return sorted(accepted, key=lambda x: x[0], reverse=True)


def preprocess_paths(query: str, cwd: str | None = None) -> tuple[str, dict[str, PathContext]]:
    """
    Replace path like tokens in `query` with stable placeholders.

    Returns:
        rewritten_query: query string with placeholders substituted in
        context: mapping of placeholder -> PathContext
    """
    if cwd is None:
        cwd = os.getcwd()

    candidates = _extract_candidates(query)
    context: dict[str, PathContext] = {}
    rewritten = query
    index = 0

    for start, end, token in candidates:
        resolved = _resolve_path(token, cwd)
        is_file, mime, existed = _filesystem_check(resolved)

        if not existed:
            # bare words that fail filesystem check are skipped
            is_bare = '/' not in token and not token.startswith('~')
            if is_bare:
                continue
            # structured paths that don't exist: regex fallback
            is_file = _regex_fallback(token)
            # ambiguous non existent structured paths default to dir

        placeholder = _make_placeholder(is_file, index)
        ctx = PathContext(
            original=token,
            placeholder=placeholder,
            is_file=is_file,
            mime=mime,
            existed=existed,
        )
        context[placeholder] = ctx
        rewritten = rewritten[:start] + placeholder + rewritten[end:]
        index += 1

    return rewritten, context


def restore_paths(rewritten: str, context: dict[str, PathContext]) -> str:
    """Substitute placeholders back to original path strings."""
    result = rewritten
    for placeholder, ctx in context.items():
        result = result.replace(placeholder, ctx.original)
    return result