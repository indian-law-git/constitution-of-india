"""Render baseline JSON records to ``articles/article-NNN.md``.

Reads from two source directories with manuscript taking precedence on overlap:

  - ``pipeline/intermediate/scraped/manuscript/`` — human-typed transcriptions
    from the calligraphic 1950 manuscript (most authoritative).
  - ``pipeline/intermediate/scraped/articles/``  — CLPR-curated digital text
    (broad coverage, validated against the manuscript on the spot-check).

For each baseline article 1..395 we emit ``articles/article-NNN.md`` with
YAML frontmatter (PRD §5.2) and a Markdown body. The body comes from
``body_text`` (manuscript) or from the HTML in ``body_html`` (CLPR), which
is converted with a small set of rules:

  - <p> → paragraph (blank-line separated)
  - <div class="wst-hanging-indent"> → its own paragraph (sub-clause text
    already carries (a)/(b) notation; the visual indent in the source is
    typographic, not semantic)
  - <em>/<i>          → *italic*
  - <b>/<strong>      → **bold**
  - <span class="wst-gap"> → dropped entirely (CLPR typography spacer)
  - U+2060 (word joiner) → dropped
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from bs4 import BeautifulSoup, NavigableString, Tag

REPO_ROOT = Path(__file__).resolve().parents[2]
CLPR_DIR = REPO_ROOT / "pipeline" / "intermediate" / "scraped" / "articles"
MANU_DIR = REPO_ROOT / "pipeline" / "intermediate" / "scraped" / "manuscript"
OUT_DIR = REPO_ROOT / "articles"

WORD_JOINER = "⁠"
NBSP = " "

# Part structure of the 26 January 1950 Constitution (as enacted).
# Each entry: (roman numeral, part title, inclusive article range start, inclusive end).
PART_RANGES: list[tuple[str, str, int, int]] = [
    ("I",     "The Union and its territory",                                              1,   4),
    ("II",    "Citizenship",                                                              5,  11),
    ("III",   "Fundamental Rights",                                                      12,  35),
    ("IV",    "Directive Principles of State Policy",                                    36,  51),
    ("V",     "The Union",                                                               52, 151),
    ("VI",    "The States in Part A of the First Schedule",                             152, 237),
    ("VII",   "The States in Part B of the First Schedule",                             238, 238),
    ("VIII",  "The States in Part C of the First Schedule",                             239, 242),
    ("IX",    "The territories in Part D of the First Schedule and other territories not specified in that Schedule", 243, 243),
    ("X",     "Scheduled Areas and Tribal Areas",                                       244, 244),
    ("XI",    "Relations between the Union and the States",                             245, 263),
    ("XII",   "Finance, Property, Contracts and Suits",                                 264, 300),
    ("XIII",  "Trade, Commerce and Intercourse within the Territory of India",          301, 307),
    ("XIV",   "Services under the Union and the States",                                308, 323),
    ("XV",    "Elections",                                                              324, 329),
    ("XVI",   "Special Provisions relating to certain Classes",                         330, 342),
    ("XVII",  "Official Language",                                                      343, 351),
    ("XVIII", "Emergency Provisions",                                                   352, 360),
    ("XIX",   "Miscellaneous",                                                          361, 367),
    ("XX",    "Amendment of the Constitution",                                          368, 368),
    ("XXI",   "Temporary and Transitional Provisions",                                  369, 392),
    ("XXII",  "Short title, commencement and repeals",                                  393, 395),
]


@dataclass(frozen=True)
class BaselineArticle:
    number: int            # bare integer, 1..395
    title: str
    body_md: str           # the rendered Markdown body (no frontmatter)
    source: str            # "manuscript" or "clpr"
    source_url: str | None
    source_pdf_sha256: str | None  # set for manuscript records
    page: str | None       # manuscript page reference, when supplied


def part_for(num: int) -> tuple[str, str] | None:
    for roman, title, lo, hi in PART_RANGES:
        if lo <= num <= hi:
            return roman, title
    return None


def _capitalize_title(slug_title: str) -> str:
    """Capitalise the first letter of a slug-derived title; leave the rest alone.

    CLPR slugs lowercase everything (e.g., "establishment of a common high
    court for two or more states"). Pure title-case mangles the legal vocabulary
    (it would mis-capitalise prepositions and articles), so we only fix the
    first letter and preserve the case of subsequent words.
    """
    s = slug_title.strip()
    if not s:
        return s
    return s[0].upper() + s[1:]


# ──────────────────────────── HTML → Markdown ────────────────────────────


def _strip_typography(text: str) -> str:
    return text.replace(WORD_JOINER, "").replace(NBSP, " ")


def _inline_md(node: Tag | NavigableString) -> str:
    if isinstance(node, NavigableString):
        return _strip_typography(str(node))
    name = node.name
    inner = "".join(_inline_md(c) for c in node.children)
    if name in {"em", "i"}:
        return f"*{inner}*"
    if name in {"strong", "b"}:
        return f"**{inner}**"
    if name == "span":
        # Drop CLPR's typographic gap spans entirely.
        cls = " ".join(node.get("class") or [])
        if "wst-gap" in cls:
            return ""
        return inner
    if name == "br":
        return "\n"
    if name == "a":
        href = node.get("href", "")
        return f"[{inner}]({href})" if href else inner
    return inner


def _block_to_paragraph(node: Tag) -> str:
    text = _inline_md(node)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def html_body_to_markdown(body_html: str) -> str:
    """Convert a CLPR-style article body fragment to Markdown paragraphs."""
    soup = BeautifulSoup(body_html, "lxml")
    # CLPR sometimes wraps in <html><body> via lxml; iterate top-level blocks.
    root = soup.body if soup.body is not None else soup
    paragraphs: list[str] = []
    for child in root.children:
        if isinstance(child, NavigableString):
            text = _strip_typography(str(child)).strip()
            if text:
                paragraphs.append(text)
            continue
        if not hasattr(child, "name") or child.name is None:
            continue
        if child.name in {"p", "div"}:
            para = _block_to_paragraph(child)
            if para:
                paragraphs.append(para)
        else:
            # Unknown top-level — best effort
            para = _inline_md(child).strip()
            if para:
                paragraphs.append(para)
    return "\n\n".join(paragraphs).strip()


_CLAUSE_START_RE = re.compile(
    # A new paragraph begins at a line that opens with:
    #   - a parenthesised clause marker like (1), (2), (a), (b), (i)
    #   - the word "Provided" (provisos)
    #   - the word "Explanation" or "Illustration" (legalese constructs)
    r"^(?:\([0-9a-zA-Z]+\)|Provided\b|Explanation\b|Illustration\b)",
)


def manuscript_body_to_markdown(body_text: str) -> str:
    """Manuscript transcriptions are plain text with clause notation.

    A new Markdown paragraph begins on each blank line OR on a line whose first
    non-whitespace token is a clause marker like ``(1)``, ``(a)``, ``Provided``,
    ``Explanation``. Continuation lines within a clause (indented or not) are
    joined with single spaces.
    """
    s = _strip_typography(body_text)
    paragraphs: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if current:
            paragraphs.append(" ".join(current))
            current.clear()

    for line in s.splitlines():
        stripped = line.strip()
        if not stripped:
            flush()
            continue
        if _CLAUSE_START_RE.match(stripped):
            flush()
        current.append(stripped)
    flush()
    return "\n\n".join(p for p in paragraphs if p)


# ────────────────────────── source loading + dispatch ──────────────────────────


def _load_manuscript_sources() -> dict[int, BaselineArticle]:
    """Return {bare-integer: BaselineArticle} for every manuscript transcription."""
    out: dict[int, BaselineArticle] = {}
    for path in sorted(MANU_DIR.glob("article-*.json")):
        d = json.loads(path.read_text())
        # Only bare-numeric (i.e. 1950 baseline) — skip any letter-suffixed
        # transcriptions (none today, but defensive).
        if not d["raw_id"].isdigit():
            continue
        n = int(d["raw_id"])
        if not (1 <= n <= 395):
            continue
        out[n] = BaselineArticle(
            number=n,
            title=d.get("title") or "",
            body_md=manuscript_body_to_markdown(d["body_text"]),
            source="manuscript",
            source_url=d.get("source_url"),
            source_pdf_sha256=d.get("source_pdf_sha256"),
            page=d.get("page"),
        )
    return out


def _load_clpr_sources() -> dict[int, BaselineArticle]:
    """Return {bare-integer: BaselineArticle} for every CLPR record."""
    out: dict[int, BaselineArticle] = {}
    for path in sorted(CLPR_DIR.glob("article-*.json")):
        d = json.loads(path.read_text())
        slug = d.get("slug_number", "")
        if not slug.isdigit():
            continue
        n = int(slug)
        if not (1 <= n <= 395):
            continue
        out[n] = BaselineArticle(
            number=n,
            title=_capitalize_title(d.get("title", "")),
            body_md=html_body_to_markdown(d["body_html"]),
            source="clpr",
            source_url=d.get("source_url"),
            source_pdf_sha256=None,
            page=None,
        )
    return out


def collect_baseline() -> dict[int, BaselineArticle]:
    """Manuscript precedence over CLPR on overlap. Returns at most 395 articles."""
    clpr = _load_clpr_sources()
    manu = _load_manuscript_sources()
    merged = dict(clpr)
    merged.update(manu)
    return merged


# ────────────────────────── frontmatter + file emission ──────────────────────────


def _yaml_quote(s: str) -> str:
    """Quote a string for YAML frontmatter using double quotes; escape backslash and quote."""
    if s is None:
        return "null"
    s = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{s}"'


def render_frontmatter(art: BaselineArticle) -> str:
    p = part_for(art.number)
    if p is None:
        raise ValueError(f"Article {art.number} is outside the 1950 part structure")
    roman, _part_title = p
    lines = [
        "---",
        f"article: {art.number}",
        f"part: {roman}",
        f"title: {_yaml_quote(art.title)}",
        "status: active",
        "inserted_by: original",
        "repealed_by: null",
        "amended_by: []",
        'current_as_of: "1950-01-26"',
        f"source: {art.source}",
    ]
    if art.source_url:
        lines.append(f"source_url: {_yaml_quote(art.source_url)}")
    if art.source_pdf_sha256:
        lines.append(f"source_pdf_sha256: {_yaml_quote(art.source_pdf_sha256)}")
    if art.page:
        lines.append(f"manuscript_page: {_yaml_quote(art.page)}")
    lines.append("---")
    return "\n".join(lines)


def render_article(art: BaselineArticle) -> str:
    fm = render_frontmatter(art)
    title = art.title or f"Article {art.number}"
    heading = f"# Article {art.number}. {title}"
    return f"{fm}\n\n{heading}\n\n{art.body_md}\n"


def render_all() -> tuple[int, int]:
    """Render every available baseline article to articles/article-NNN.md.

    Returns (written, missing) where ``missing`` is the count of 1..395 that
    had no source record (should be 0 for v1)."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    baseline = collect_baseline()
    written = 0
    for n in range(1, 396):
        art = baseline.get(n)
        if art is None:
            continue
        out = OUT_DIR / f"article-{n:03d}.md"
        out.write_text(render_article(art))
        written += 1
    missing = 395 - written
    return written, missing
