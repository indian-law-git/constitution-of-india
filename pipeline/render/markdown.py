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

CLPR_CONSOLIDATED_DIR = REPO_ROOT / "pipeline" / "intermediate" / "scraped" / "articles-consolidated"
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
        # CLPR's consolidated 1950 page italicises clause letters and digits
        # inside parens (e.g. "(<em>a</em>)" or "(<em>1</em>)"). These are
        # typography, not semantic emphasis — strip the italic. Keep italic on
        # longer tokens like "Explanation" / "Explanation I".
        bare = inner.strip()
        if len(bare) <= 2 and re.match(r"^[A-Za-z0-9]+$", bare):
            return inner
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
    """Convert a CLPR-style body fragment to Markdown paragraphs.

    Handles top-level <p>/<div>, ordered/unordered lists, and unknown elements
    via a best-effort inline pass. Sub-clause indentation is preserved by
    rendering each block as its own paragraph. The CLPR consolidated 1950
    page wraps groups of sub-clauses in a parent <div> with nested
    wst-hanging-indent <div> siblings; we flatten those so each sub-clause
    becomes its own paragraph instead of getting jammed onto one block.
    """
    soup = BeautifulSoup(body_html, "lxml")
    root = soup.body if soup.body is not None else soup
    paragraphs: list[str] = []
    for child in _flatten_blocks(root.children):
        if isinstance(child, NavigableString):
            text = _strip_typography(str(child)).strip()
            if text:
                paragraphs.append(text)
            continue
        if not hasattr(child, "name") or child.name is None:
            continue
        if child.name == "ol":
            items = [_inline_md(li).strip() for li in child.find_all("li", recursive=False)]
            paragraphs.append("\n".join(f"{i}. {item}" for i, item in enumerate(items, 1) if item))
            continue
        if child.name == "ul":
            items = [_inline_md(li).strip() for li in child.find_all("li", recursive=False)]
            paragraphs.append("\n".join(f"- {item}" for item in items if item))
            continue
        if child.name in {"p", "div"}:
            para = _block_to_paragraph(child)
            if para:
                paragraphs.append(para)
        else:
            para = _inline_md(child).strip()
            if para:
                paragraphs.append(para)
    return "\n\n".join(paragraphs).strip()


def _flatten_blocks(children):
    """Yield top-level blocks, expanding wrapper <div>s that only contain
    block-level <div>/<p> children (CLPR consolidated pattern for grouped
    sub-clauses). Wrapper <div>s with mixed content are left intact.
    """
    for child in children:
        if (
            hasattr(child, "name")
            and child.name == "div"
            and not (child.get("class") or [])
        ):
            inner_blocks = [
                c for c in child.children
                if hasattr(c, "name") and c.name in {"div", "p"}
            ]
            other = [
                c for c in child.children
                if isinstance(c, NavigableString) and str(c).strip()
            ]
            if inner_blocks and not other:
                yield from inner_blocks
                continue
        yield child


_CLAUSE_START_RE = re.compile(
    # A new paragraph begins at a line that opens with:
    #   - a parenthesised clause marker like (1), (2), (a), (b), (i)
    #   - a numbered-list entry like "1." or "47." (used for Schedule list items)
    #   - the word "Provided" (provisos)
    #   - the word "Explanation" or "Illustration" (legalese constructs)
    r"^(?:\([0-9a-zA-Z]+\)|[0-9]+\.\s|Provided\b|Explanation\b|Illustration\b)",
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


# 1950 marginal-note overrides for articles where neither the CLPR consolidated
# page (no <h4>) nor the per-article slug-derived title gives the right 1950
# title. Verified against the Aggarwala 1950 facsimile
# (docs/constitutionofin_1ed_fulltext.txt). All in the [1, 395] range.
_TITLE_OVERRIDES_1950: dict[int, str] = {
    17:  "Abolition of Untouchability",
    142: "Enforcement of decrees and orders of Supreme Court and orders as to discovery, etc.",
    199: "Definition of “Money Bills”",
    342: "Scheduled Tribes",
    375: "Courts, authorities and officers to continue to function subject to the provisions of the Constitution",
}

# Body-level typo fixes for CLPR's consolidated 1950 page. Pure typos
# verified against the Aggarwala 1950 facsimile (no semantic effect).
_BODY_TYPO_FIXES_1950: list[tuple[str, str]] = [
    # Article 31 clause (4): consolidated has "clause (2}" with a closing brace.
    ("clause (2}", "clause (2)"),
]

def _load_clpr_sources() -> dict[int, BaselineArticle]:
    """Return {bare-integer: BaselineArticle} preferring CLPR's consolidated
    /constitution-of-india-1950/ extraction over the per-article-page extraction.

    Why: CLPR's per-article pages drift to post-amendment text under the "1950"
    label in a non-trivial fraction of articles (Articles 3, 19, 31, 81, 305 had
    substantive drift; 269 and 286 had cosmetic drift; surfaced during the
    1st-6th-amendment validation cycles). The consolidated page consistently
    carries the true 1950 form.

    Strategy:
      - Body: prefer consolidated; fall back to per-article for the 5 articles
        genuinely missing from the consolidated page (142, 199, 300, 342, 375).
      - Title: prefer consolidated <h4> marginal note; for the one article with
        no title in consolidated (Article 17), fall back to per-article.
    """
    # First pass: per-article (carries every article + has slug-derived title we
    # can fall back on for body and title).
    per_article: dict[int, dict] = {}
    for path in sorted(CLPR_DIR.glob("article-*.json")):
        d = json.loads(path.read_text())
        slug = d.get("slug_number", "")
        if not slug.isdigit():
            continue
        n = int(slug)
        if not (1 <= n <= 395):
            continue
        per_article[n] = d

    # Second pass: consolidated (overrides per-article body; uses h4 title when
    # present).
    consolidated: dict[int, dict] = {}
    for path in sorted(CLPR_CONSOLIDATED_DIR.glob("article-*.json")):
        d = json.loads(path.read_text())
        slug = d.get("slug_number", "")
        if not slug.isdigit():
            continue
        n = int(slug)
        if not (1 <= n <= 395):
            continue
        consolidated[n] = d

    out: dict[int, BaselineArticle] = {}
    for n in sorted(set(per_article) | set(consolidated)):
        cons = consolidated.get(n)
        per = per_article.get(n)
        if cons is not None:
            # Title: consolidated h4 if non-empty, else per-article slug title.
            title = cons.get("title") or ""
            if not title and per is not None:
                title = _capitalize_title(per.get("title", ""))
            body_html = cons["body_html"]
            source_url = cons.get("source_url")
        elif per is not None:
            title = _capitalize_title(per.get("title", ""))
            body_html = per["body_html"]
            source_url = per.get("source_url")
        else:
            continue
        title = _TITLE_OVERRIDES_1950.get(n, title)
        body_md = html_body_to_markdown(body_html)
        for old, new in _BODY_TYPO_FIXES_1950:
            body_md = body_md.replace(old, new)
        out[n] = BaselineArticle(
            number=n,
            title=title,
            body_md=body_md,
            source="clpr",
            source_url=source_url,
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


# ──────────────────────────── parts manifests ────────────────────────────

PARTS_OUT = REPO_ROOT / "parts"


def render_part(roman: str, title: str, lo: int, hi: int) -> str:
    articles_list = list(range(lo, hi + 1))
    if lo == hi:
        body_sentence = f"This Part contains Article {lo} only."
    else:
        body_sentence = f"This Part contains Articles {lo} through {hi}."
    lines = [
        "---",
        f"part: {roman}",
        f"title: {_yaml_quote(title)}",
        f"articles: {articles_list}",
        "---",
        "",
        f"# Part {roman} — {title}",
        "",
        f"{body_sentence} See individual article files in `articles/`.",
        "",
    ]
    return "\n".join(lines)


def render_all_parts() -> int:
    PARTS_OUT.mkdir(parents=True, exist_ok=True)
    for roman, title, lo, hi in PART_RANGES:
        path = PARTS_OUT / f"part-{roman.lower()}.md"
        path.write_text(render_part(roman, title, lo, hi))
    return len(PART_RANGES)



# ──────────────────────────── schedules ────────────────────────────

SCHEDULES_OUT = REPO_ROOT / "schedules"
SCHEDULES_SCRAPED = REPO_ROOT / "pipeline" / "intermediate" / "scraped" / "clpr-schedules"

# Canonical title for each 1950 Schedule. Used because CLPR splits some
# Schedules across multiple URLs each with its own h1; we want a unified
# title at the top of the rendered Markdown file.
SCHEDULE_TITLES: dict[int, str] = {
    1: "First Schedule — The Territories",
    2: "Second Schedule — Provisions as to the President, Governors, Speakers, Judges, and the Comptroller and Auditor-General",
    3: "Third Schedule — Forms of Oaths or Affirmations",
    4: "Fourth Schedule — Allocation of Seats in the Council of States",
    5: "Fifth Schedule — Provisions as to the Administration and Control of Scheduled Areas and Scheduled Tribes",
    6: "Sixth Schedule — Provisions as to the Administration of Tribal Areas in Assam",
    7: "Seventh Schedule — Union, State and Concurrent Lists",
    8: "Eighth Schedule — Languages",
}

# Documented gaps: CLPR data is missing or insufficient for these segments;
# the rendered file includes a tombstone-like note pointing readers to the
# situation. Future fills (manuscript transcription, etc.) close the gaps.
SCHEDULE_GAPS: dict[tuple[int, str | None], str] = {
    (2, "B"): (
        "Part B of the Second Schedule (provisions as to the salaries of the Speaker "
        "and the Deputy Speaker of the House of the People and the Chairman and the "
        "Deputy Chairman of the Council of States, etc.) is not present on CLPR's "
        "schedules-sitemap and remains a documented gap pending manuscript transcription."
    ),
    (7, "III"): (
        "List III (Concurrent List) on CLPR does not carry a Version 2 (1950) "
        "section — only the current consolidated text is shown. Because the "
        "42nd Amendment, 1976, moved items between State List and Concurrent "
        "List, the current text is not a faithful 1950 baseline and this segment "
        "is a documented gap pending manuscript transcription."
    ),
}


SCHEDULES_MANU_SCRAPED = REPO_ROOT / "pipeline" / "intermediate" / "scraped" / "manuscript-schedules"


def _load_schedule_segments() -> dict[int, list[dict]]:
    """Group schedule segments by schedule_number, with manuscript precedence.

    For any (schedule_number, sub_part) pair present in
    ``pipeline/intermediate/scraped/manuscript-schedules/``, the manuscript
    record replaces the CLPR record (or fills the gap if CLPR has none).
    Manuscript records carry ``source = manuscript`` plus PDF SHA-256 +
    page provenance; CLPR segments stay ``source = clpr``.
    """
    by_schedule: dict[int, dict[tuple[int, str | None], dict]] = {}

    # Pass 1: CLPR
    if SCHEDULES_SCRAPED.exists():
        for path in sorted(SCHEDULES_SCRAPED.glob("*.json")):
            d = json.loads(path.read_text())
            d["source"] = "clpr"
            by_schedule.setdefault(d["schedule_number"], {})[(d["schedule_number"], d["sub_part"])] = d

    # Pass 2: manuscript schedule fills (override / fill gap)
    if SCHEDULES_MANU_SCRAPED.exists():
        for path in sorted(SCHEDULES_MANU_SCRAPED.glob("*.json")):
            d = json.loads(path.read_text())
            seg = {
                "schedule_number": d["schedule_number"],
                "sub_part": d["sub_part"],
                "sub_part_order": d["sub_part_order"],
                "schedule_title": "",  # not present in manuscript records; rendered from SCHEDULE_TITLES
                "section_title": d.get("title") or (
                    f"Part {d['sub_part']}" if d["sub_part"] else ""
                ),
                "body_text": d["body_text"],
                "body_html": "",
                "source": "manuscript",
                "source_url": d["source_url"],
                "source_pdf_sha256": d["source_pdf_sha256"],
                "page": d.get("page"),
            }
            by_schedule.setdefault(d["schedule_number"], {})[(d["schedule_number"], d["sub_part"])] = seg

    out: dict[int, list[dict]] = {}
    for n, parts_map in by_schedule.items():
        segs = list(parts_map.values())
        segs.sort(key=lambda x: x["sub_part_order"])
        out[n] = segs
    return out


def _render_schedule_segment(seg: dict) -> str:
    """Convert one segment to Markdown, prefixed by its sub-part heading.

    Dispatches on ``source``: CLPR records have body_html, manuscript records
    have body_text (plain text using the manuscript paragraph rules).
    """
    if seg.get("source") == "manuscript":
        body_md = manuscript_body_to_markdown(seg["body_text"])
    else:
        body_md = html_body_to_markdown(seg["body_html"])
    sub = seg["sub_part"]
    title = seg["section_title"] or ""
    if sub is None:
        return body_md
    return f"## {title}\n\n{body_md}"


def render_schedule(n: int, segments: list[dict]) -> str:
    """Build a single Markdown file for Schedule ``n`` from its segments.

    Frontmatter ``source`` reports ``clpr`` / ``manuscript`` / ``mixed`` based
    on which extractors contributed segments.
    """
    title = SCHEDULE_TITLES.get(n, f"Schedule {n}")
    sources = {seg.get("source", "clpr") for seg in segments}
    source_label = "mixed" if len(sources) > 1 else (sources.pop() if sources else "clpr")
    fm_lines = [
        "---",
        f"schedule: {n}",
        f"title: {_yaml_quote(title)}",
        "status: active",
        "inserted_by: original",
        "amended_by: []",
        'current_as_of: "1950-01-26"',
        f"source: {source_label}",
        "---",
    ]
    parts: list[str] = ["\n".join(fm_lines), "", f"# {title}", ""]
    rendered_subs: set[str | None] = set()
    for seg in segments:
        parts.append(_render_schedule_segment(seg))
        parts.append("")
        rendered_subs.add(seg["sub_part"])
    # Append gap notes for any expected sub-parts not yet covered by either
    # CLPR or a manuscript fill.
    for (sched_n, sub), note in SCHEDULE_GAPS.items():
        if sched_n != n:
            continue
        if sub in rendered_subs:
            continue
        heading = f"## Part {sub} — gap" if sub else "## (gap)"
        parts.append(heading)
        parts.append("")
        parts.append(f"> **Documented gap.** {note}")
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def render_all_schedules() -> tuple[int, list[int]]:
    """Render schedules/schedule-NN.md for each baseline schedule (1..8).

    Returns (written, missing_schedule_numbers)."""
    SCHEDULES_OUT.mkdir(parents=True, exist_ok=True)
    by_schedule = _load_schedule_segments()
    written = 0
    missing: list[int] = []
    for n in range(1, 9):
        segs = by_schedule.get(n)
        if not segs:
            missing.append(n)
            continue
        out = SCHEDULES_OUT / f"schedule-{n:02d}.md"
        out.write_text(render_schedule(n, segs))
        written += 1
    return written, missing
