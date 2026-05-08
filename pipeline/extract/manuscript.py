"""Manuscript-transcription extractor.

Reads human-typed transcriptions from ``pipeline/sources/manuscript/*.txt`` —
each file representing one article transcribed directly from the calligraphic
1950 manuscript — and emits structured JSON records into
``pipeline/intermediate/scraped/manuscript/`` in the same shape as the CLPR
and IK extractors. The render step downstream consumes them uniformly.

File format (see ``pipeline/sources/manuscript/README.md`` for the full spec):

    # Title: Interpretation
    # Page: 87

    Where a High Court exercises jurisdiction...
    (a) references in this Chapter ...
    (b) the reference to the approval...

The filename ``article-NNN.txt`` (or ``article-NNNX.txt`` for letter suffixes)
provides the canonical article number.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCES_DIR = REPO_ROOT / "pipeline" / "sources" / "manuscript"
OUT_DIR = REPO_ROOT / "pipeline" / "intermediate" / "scraped" / "manuscript"
MANUSCRIPT_PDF_SHA256 = (
    "e5cb50a2df24f4fbf65fbb1e125cbaa81124e0f518ba52d005344de10c742ec4"
)
MANUSCRIPT_PROVENANCE_URL = (
    "https://www.constitutionofindia.net/read/original-manuscript/"
)

_FILENAME_RE = re.compile(r"^article-(\d+[A-Za-z]*)\.txt$")
_HEADER_RE = re.compile(r"^#\s*([A-Za-z][A-Za-z _-]*?)\s*:\s*(.*?)\s*$")


@dataclass(frozen=True)
class ManuscriptArticle:
    """One article transcribed from the calligraphic 1950 manuscript."""

    number: str  # zero-padded canonical, e.g. "232" or "031A"
    raw_id: str  # as parsed from the filename, e.g. "232" or "31A"
    title: str  # from `# Title:` header (or empty)
    page: str | None  # from `# Page:` header
    notes: str | None  # from `# Notes:` header
    body_text: str  # the verbatim body (clauses preserved)
    transcription_sha256: str  # sha256 of the body_text for change detection
    source_file: str  # relative path of the .txt
    source_pdf_sha256: str  # sha256 of the manuscript PDF
    source_url: str  # canonical URL of the manuscript
    extracted_at: str  # ISO-8601 UTC


def _normalize_number(raw: str) -> str:
    m = re.match(r"^([0-9]+)([A-Za-z]*)$", raw)
    if not m:
        return raw
    num, suffix = m.groups()
    return f"{int(num):03d}{suffix.upper()}"


def parse_file(path: Path) -> ManuscriptArticle | None:
    """Parse a single transcription file. Returns None if filename is malformed."""
    fn_m = _FILENAME_RE.match(path.name)
    if not fn_m:
        return None
    raw_id = fn_m.group(1)
    text = path.read_text(encoding="utf-8")

    headers: dict[str, str] = {}
    body_lines: list[str] = []
    in_body = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not in_body:
            if line.startswith("#"):
                hm = _HEADER_RE.match(line)
                if hm:
                    headers[hm.group(1).strip().lower()] = hm.group(2)
                continue
            if line.strip() == "":
                # The first blank line after headers (or first blank line
                # period) ends the header section and begins the body.
                in_body = True
                continue
            # First non-header non-blank line: body has begun.
            in_body = True
            body_lines.append(line)
            continue
        body_lines.append(line)

    body_text = "\n".join(body_lines).strip()
    return ManuscriptArticle(
        number=_normalize_number(raw_id),
        raw_id=raw_id,
        title=headers.get("title", ""),
        page=headers.get("page") or None,
        notes=headers.get("notes") or None,
        body_text=body_text,
        transcription_sha256=hashlib.sha256(body_text.encode("utf-8")).hexdigest(),
        source_file=str(path.relative_to(REPO_ROOT)),
        source_pdf_sha256=MANUSCRIPT_PDF_SHA256,
        source_url=MANUSCRIPT_PROVENANCE_URL,
        extracted_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def iter_transcriptions() -> Iterator[ManuscriptArticle]:
    if not SOURCES_DIR.exists():
        return
    for path in sorted(SOURCES_DIR.glob("article-*.txt")):
        art = parse_file(path)
        if art is not None:
            yield art


def write_record(article: ManuscriptArticle) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"article-{article.number}.json"
    out.write_text(json.dumps(asdict(article), indent=2, ensure_ascii=False))
    return out


def extract_all() -> int:
    """Parse every transcription in pipeline/sources/manuscript and write JSONs."""
    n = 0
    for art in iter_transcriptions():
        write_record(art)
        n += 1
    return n



# ──────────────────────────── schedules ────────────────────────────

SCHEDULES_OUT = REPO_ROOT / "pipeline" / "intermediate" / "scraped" / "manuscript-schedules"

# Filename forms accepted for schedule transcriptions:
#   schedule-NN.txt        — single-section schedule (e.g. schedule-08.txt)
#   schedule-NN-X.txt      — sub-part X (e.g. schedule-02-b.txt, schedule-07-iii.txt)
_SCHEDULE_FILENAME_RE = re.compile(r"^schedule-(\d{2})(?:-([a-z0-9]+))?\.txt$")


@dataclass(frozen=True)
class ManuscriptSchedule:
    """One schedule (or sub-part of a multi-part schedule) transcribed from
    the calligraphic 1950 manuscript.
    """

    schedule_number: int          # 1..8 for the 1950 baseline
    sub_part: str | None          # e.g. "B", "III", or None for single-section
    sub_part_order: int           # ordering within the schedule (matches CLPR)
    title: str                    # from `# Title:` header
    page: str | None              # from `# Page:` header
    notes: str | None             # from `# Notes:` header
    body_text: str                # the verbatim body (entries / paragraphs preserved)
    transcription_sha256: str
    source_file: str
    source_pdf_sha256: str
    source_url: str
    extracted_at: str


_SCHEDULE_SUBPART_ORDER = {
    None: 0,
    "i": 1, "ii": 2, "iii": 3, "iv": 4,
    "a": 1, "b": 2, "c": 3, "d": 4, "e": 5,
}


def _schedule_subpart_order(sub: str | None) -> int:
    if sub is None:
        return 0
    return _SCHEDULE_SUBPART_ORDER.get(sub.lower(), 99)


def parse_schedule_file(path: Path) -> ManuscriptSchedule | None:
    """Parse a single schedule-NN[-X].txt transcription file."""
    fn_m = _SCHEDULE_FILENAME_RE.match(path.name)
    if not fn_m:
        return None
    schedule_no = int(fn_m.group(1))
    sub_part_raw = fn_m.group(2)
    sub_part = sub_part_raw.upper() if sub_part_raw else None

    text = path.read_text(encoding="utf-8")
    headers: dict[str, str] = {}
    body_lines: list[str] = []
    in_body = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not in_body:
            if line.startswith("#"):
                hm = _HEADER_RE.match(line)
                if hm:
                    headers[hm.group(1).strip().lower()] = hm.group(2)
                continue
            if line.strip() == "":
                in_body = True
                continue
            in_body = True
            body_lines.append(line)
            continue
        body_lines.append(line)

    body_text = "\n".join(body_lines).strip()
    if not body_text:
        return None
    return ManuscriptSchedule(
        schedule_number=schedule_no,
        sub_part=sub_part,
        sub_part_order=_schedule_subpart_order(sub_part_raw),
        title=headers.get("title", ""),
        page=headers.get("page") or None,
        notes=headers.get("notes") or None,
        body_text=body_text,
        transcription_sha256=hashlib.sha256(body_text.encode("utf-8")).hexdigest(),
        source_file=str(path.relative_to(REPO_ROOT)),
        source_pdf_sha256=MANUSCRIPT_PDF_SHA256,
        source_url=MANUSCRIPT_PROVENANCE_URL,
        extracted_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def iter_schedule_transcriptions() -> Iterator[ManuscriptSchedule]:
    if not SOURCES_DIR.exists():
        return
    for path in sorted(SOURCES_DIR.glob("schedule-*.txt")):
        seg = parse_schedule_file(path)
        if seg is not None:
            yield seg


def write_schedule_record(seg: ManuscriptSchedule) -> Path:
    SCHEDULES_OUT.mkdir(parents=True, exist_ok=True)
    if seg.sub_part is None:
        name = f"schedule-{seg.schedule_number:02d}.json"
    else:
        name = f"schedule-{seg.schedule_number:02d}-{seg.sub_part.lower()}.json"
    out = SCHEDULES_OUT / name
    out.write_text(json.dumps(asdict(seg), indent=2, ensure_ascii=False))
    return out


def extract_all_schedules() -> int:
    n = 0
    for seg in iter_schedule_transcriptions():
        write_schedule_record(seg)
        n += 1
    return n
