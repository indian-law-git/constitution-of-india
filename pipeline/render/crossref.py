"""Generate ``metadata/cross-references.json``.

Walks every ``articles/article-NNN.md`` and ``schedules/schedule-NN.md`` body,
extracts citations to other articles and schedules, and emits an inbound /
outbound index keyed by canonical id (``article-019``, ``schedule-07``).

Detection rules (per PRD §5.10):
  - ``Article 19``, ``article 19``, ``Article 31A`` — single article references
  - ``Articles 14 to 35`` / ``articles 14 to 35`` — ranges, expanded
  - ``First Schedule`` / ``Second Schedule`` ... ``Eighth Schedule`` — ordinal form
  - ``the First Schedule``, ``the Second Schedule`` — same with the article
  - ``Schedule II`` — Roman-numeral form (rare)
  - YAML frontmatter is excluded (we only read the body after the closing ``---``)
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTICLES_DIR = REPO_ROOT / "articles"
SCHEDULES_DIR = REPO_ROOT / "schedules"
OUT_PATH = REPO_ROOT / "metadata" / "cross-references.json"

_ORDINAL_TO_NUM = {
    "first": 1, "second": 2, "third": 3, "fourth": 4,
    "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8,
    "ninth": 9, "tenth": 10, "eleventh": 11, "twelfth": 12,
}
_ROMAN_TO_NUM = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
    "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10,
    "XI": 11, "XII": 12,
}

# Citations we actively detect.
_ARTICLE_REF_RE = re.compile(r"\barticles?\s+([0-9]+[A-Za-z]*)\b", re.I)
_ARTICLE_RANGE_RE = re.compile(
    r"\barticles?\s+([0-9]+)\s+to\s+([0-9]+)\b", re.I
)
_SCHEDULE_ORDINAL_RE = re.compile(
    r"\b(?:the\s+)?(First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth)\s+Schedule\b"
)
_SCHEDULE_ROMAN_RE = re.compile(r"\bSchedule\s+([IVX]+)\b")

_FRONTMATTER_RE = re.compile(r"^---\s*\n.*?\n---\s*\n", re.S)


def _normalize_article_id(raw: str) -> str | None:
    m = re.match(r"^([0-9]+)([A-Za-z]*)$", raw)
    if not m:
        return None
    n = int(m.group(1))
    if not (1 <= n <= 395):
        return None
    suffix = m.group(2).upper()
    return f"article-{n:03d}{suffix}" if suffix else f"article-{n:03d}"


def _normalize_schedule_id(num: int) -> str | None:
    if 1 <= num <= 12:
        return f"schedule-{num:02d}"
    return None


def _strip_frontmatter(text: str) -> str:
    return _FRONTMATTER_RE.sub("", text, count=1)


def extract_refs(body: str) -> set[str]:
    """Return the set of canonical ids cited anywhere in ``body``."""
    refs: set[str] = set()
    # Single-article references
    for m in _ARTICLE_REF_RE.finditer(body):
        rid = _normalize_article_id(m.group(1))
        if rid:
            refs.add(rid)
    # Ranges
    for m in _ARTICLE_RANGE_RE.finditer(body):
        try:
            lo, hi = int(m.group(1)), int(m.group(2))
        except ValueError:
            continue
        if lo > hi or hi - lo > 100:
            continue  # implausible / nonsense
        for n in range(lo, hi + 1):
            rid = _normalize_article_id(str(n))
            if rid:
                refs.add(rid)
    # Schedules — ordinal form
    for m in _SCHEDULE_ORDINAL_RE.finditer(body):
        n = _ORDINAL_TO_NUM.get(m.group(1).lower())
        if n is not None:
            sid = _normalize_schedule_id(n)
            if sid:
                refs.add(sid)
    # Schedules — Roman form
    for m in _SCHEDULE_ROMAN_RE.finditer(body):
        n = _ROMAN_TO_NUM.get(m.group(1).upper())
        if n is not None:
            sid = _normalize_schedule_id(n)
            if sid:
                refs.add(sid)
    return refs


def _id_for_article_path(path: Path) -> str | None:
    m = re.match(r"^article-(\d{3}[A-Z]*)\.md$", path.name)
    return f"article-{m.group(1)}" if m else None


def _id_for_schedule_path(path: Path) -> str | None:
    m = re.match(r"^schedule-(\d{2})\.md$", path.name)
    return f"schedule-{m.group(1)}" if m else None


def build() -> int:
    """Write ``metadata/cross-references.json``. Returns the number of nodes."""
    outbound: dict[str, set[str]] = defaultdict(set)
    inbound: dict[str, set[str]] = defaultdict(set)
    all_ids: set[str] = set()

    for path in sorted(ARTICLES_DIR.glob("article-*.md")):
        self_id = _id_for_article_path(path)
        if self_id is None:
            continue
        all_ids.add(self_id)
        body = _strip_frontmatter(path.read_text(encoding="utf-8"))
        for ref in extract_refs(body):
            if ref == self_id:
                continue
            outbound[self_id].add(ref)
            inbound[ref].add(self_id)

    for path in sorted(SCHEDULES_DIR.glob("schedule-*.md")):
        self_id = _id_for_schedule_path(path)
        if self_id is None:
            continue
        all_ids.add(self_id)
        body = _strip_frontmatter(path.read_text(encoding="utf-8"))
        for ref in extract_refs(body):
            if ref == self_id:
                continue
            outbound[self_id].add(ref)
            inbound[ref].add(self_id)

    every_id = sorted(all_ids | set(outbound) | set(inbound))
    result: dict[str, dict[str, list[str]]] = {}
    for id_ in every_id:
        result[id_] = {
            "outbound": sorted(outbound.get(id_, set())),
            "inbound": sorted(inbound.get(id_, set())),
        }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return len(every_id)
