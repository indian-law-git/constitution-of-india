"""CLPR (constitutionofindia.net) scraper.

Discovers article URLs via the sitemap, fetches each page (disk-cached, throttled),
and extracts the "Constitution of India 1950" enacted-text block per article.

Output: one JSON record per article into ``pipeline/intermediate/scraped/articles/``.
The render-to-Markdown step lives elsewhere.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup, Tag

USER_AGENT = "indian-law-git/0.0.1 (+https://github.com/indian-law-git/constitution-of-india)"
SITEMAP_URL = "https://www.constitutionofindia.net/articles-sitemap.xml"
DEFAULT_THROTTLE_S = 1.5

REPO_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = REPO_ROOT / "pipeline" / "intermediate" / "cache" / "clpr"
SCRAPED_DIR = REPO_ROOT / "pipeline" / "intermediate" / "scraped" / "articles"

log = logging.getLogger("clpr")


@dataclass(frozen=True)
class Article1950:
    """A single article in the 1950-enacted Constitution as parsed from CLPR."""

    number: str  # canonical, zero-padded with optional letter suffix, e.g. "019" or "031A"
    slug_number: str  # number derived from the URL slug (the reliable source)
    heading_number: str | None  # number per the page's "Article N, Constitution of India 1950" label, when present
    title: str  # human title from the slug
    body_html: str  # raw inner HTML of the version block (preserves clauses, italics)
    source_url: str
    source_html_sha256: str
    fetched_at: str  # ISO-8601 UTC


_HEADING_RE = re.compile(
    # Accept "Article 19", "Article 81 (3)", "Article 31A", optionally with a
    # parenthesized clause specifier; comma separator; "Constitution of India"
    # with the year "1950" optional, and tolerating the spurious "Draft"
    # prefix CLPR sometimes mistakenly attaches (e.g., Articles 367, 373).
    r"^Article\s+([0-9]+[A-Z]*)\s*(?:\([^)]*\))?\s*,?\s*"
    r"(?:Draft\s+)?Constitution of India,?\s*(?:1950)?\s*$",
    re.IGNORECASE,
)
# A label is the Draft Constitution version only when it explicitly says 1948.
_DRAFT_RE = re.compile(r"\b1948\b")


def _cache_path(url: str) -> Path:
    h = hashlib.sha256(url.encode()).hexdigest()[:24]
    slug = urlparse(url).path.strip("/").split("/")[-1] or "root"
    return CACHE_DIR / f"{slug}.{h}.html"


def fetch(url: str, client: httpx.Client, throttle_s: float = DEFAULT_THROTTLE_S) -> str:
    """Fetch a URL with on-disk caching and polite throttling on miss."""
    cache_file = _cache_path(url)
    if cache_file.exists():
        return cache_file.read_text(encoding="utf-8")
    log.info("GET %s", url)
    time.sleep(throttle_s)
    resp = client.get(url, follow_redirects=True, timeout=30.0)
    resp.raise_for_status()
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(resp.text, encoding="utf-8")
    return resp.text


def discover_article_urls(client: httpx.Client) -> list[str]:
    """Return the article URLs listed in the CLPR sitemap."""
    xml = fetch(SITEMAP_URL, client, throttle_s=0.0)
    return re.findall(r"<loc>([^<]+)</loc>", xml)


def _label_of_sub_block(sub_block: Tag) -> tuple[str, Tag] | tuple[None, None]:
    """Return (label_text, label_element) for the version label, or (None, None).

    CLPR uses two label conventions:
      - ``<h4>Article N, Constitution of India 1950</h4>`` (e.g. Article 19)
      - ``<p><strong>Article N, Constitution of India 1950</strong></p>`` where
        the whole <p> is the bolded label (e.g. Article 17, 245)
    The first non-empty child element of the sub-block is inspected.
    """
    for child in sub_block.children:
        if not hasattr(child, "name") or child.name is None:
            continue
        if child.name == "h4":
            return child.get_text(strip=True), child
        if child.name == "p":
            strong = child.find("strong")
            if strong and strong.get_text(strip=True) == child.get_text(strip=True):
                return strong.get_text(strip=True), child
            return "", None
        return "", None
    return None, None


def _sub_block_body_html(sub_block: Tag, label_el: Tag | None) -> str:
    """Inner HTML of a version sub-block, with the label element removed."""
    parts: list[str] = []
    for child in sub_block.children:
        if child is label_el:
            continue
        if hasattr(child, "name") and child.name is not None:
            parts.append(str(child))
    return "".join(parts).strip()


def parse_1950_block(
    html: str, accept_lone_unlabeled: bool = False
) -> tuple[str | None, str] | None:
    """Return (raw_number, body_html) for the 1950 version block, or None.

    Strategy:
      1. Prefer an explicit ``Article N, Constitution of India 1950`` label
         (in either ``<h4>`` or ``<p><strong>`` form). Return its number.
      2. Fall back to an unlabeled non-Draft version block when the page also
         shows a labeled Draft — that's the signal that the article existed at
         drafting time, so the unlabeled block must be its 1950 enactment.
      3. If ``accept_lone_unlabeled`` is True (caller has determined the slug
         is a bare numeric one, i.e. a 1950 article), accept a single unlabeled
         non-Draft non-Summary block even without a Draft sibling. This covers
         pages like Article 380 where CLPR transcribed only the 1950 text
         without any labels.
      4. Otherwise return None — likely a post-1950 insertion.
    """
    soup = BeautifulSoup(html, "lxml")
    sub_blocks = soup.find_all(class_="article-detail__content__sub-block")

    labeled_match: tuple[str, Tag, Tag] | None = None  # (raw_number, sub_block, label_el)
    unlabeled_candidates: list[Tag] = []
    has_draft_version = False

    for sb in sub_blocks:
        # Skip the Summary sub-block (its parent main-block has an h3 'Summary').
        parent = sb.find_parent(class_="article-detail__content__main-block")
        if parent is not None:
            left_h3 = parent.find("h3")
            if left_h3 and "Summary" in left_h3.get_text(strip=True):
                continue

        label, label_el = _label_of_sub_block(sb)

        if label is None or label == "":
            unlabeled_candidates.append(sb)
            continue
        if _DRAFT_RE.search(label):
            has_draft_version = True
            continue
        m = _HEADING_RE.match(label)
        if m:
            labeled_match = (m.group(1), sb, label_el)
            break
        # Labeled but not 1950 and not Draft — assume post-1950 variant; ignore.

    if labeled_match is not None:
        raw_number, sb, label_el = labeled_match
        return raw_number, _sub_block_body_html(sb, label_el)
    # Unlabeled fallback fires when the page also shows a Draft Article version
    # (the article existed at drafting time, so the unlabeled successor block is
    # its 1950 enactment), OR when the caller has gated us with
    # ``accept_lone_unlabeled`` — meaning the slug is a bare 1950 article number.
    # Without either signal, an unlabeled block is most likely a post-1950
    # insertion (e.g., 338A, 134A, 139A).
    if unlabeled_candidates and (has_draft_version or accept_lone_unlabeled):
        return None, _sub_block_body_html(unlabeled_candidates[-1], None)
    return None


def title_from_url(url: str) -> str:
    """Derive a human title from the CLPR slug.

    Slug format: ``article-19-protection-of-certain-rights-regarding-freedom-of-speech-etc``
    Strips the leading ``article-N-`` and converts kebab to title-ish case while
    preserving common short words; the canonical title comes from the article body
    rendering step, this is a hint only.
    """
    slug = urlparse(url).path.strip("/").split("/")[-1]
    parts = slug.split("-", 2)
    if len(parts) < 3:
        return slug
    return parts[2].replace("-", " ")


def normalize_number(raw: str) -> str:
    """Zero-pad numeric portion to 3 digits, preserve letter suffix."""
    m = re.match(r"^([0-9]+)([A-Z]*)$", raw)
    if not m:
        return raw
    num, suffix = m.groups()
    return f"{int(num):03d}{suffix}"


def slug_article_number(url: str) -> str | None:
    """Extract the article number from a CLPR slug.

    Handles all observed CLPR slug formats:
      - ``article-145-rules-of-court-etc`` (typical)
      - ``article-4`` / ``article-319`` / ``article-362`` (bare, no descriptive title)
      - ``394a-authoritative-text-in-the-hindi-language`` (no ``article-`` prefix)
    """
    slug = urlparse(url).path.strip("/").split("/")[-1]
    m = re.match(r"^(?:article-)?([0-9]+[a-z]*)(?:[-/]|$)", slug)
    if not m:
        return None
    return m.group(1).upper()


def scrape_article(url: str, client: httpx.Client) -> Article1950 | None:
    """Fetch and parse one CLPR article page; return None if no 1950 block.

    The article's canonical number comes from the URL slug. CLPR's "Article N,
    Constitution of India 1950" heading is captured as ``heading_number`` for
    audit but is not authoritative — observed mismatches include Articles 39
    and 51 carrying copy-pasted headings ("Article 38" / "Article 50").
    """
    from datetime import datetime, timezone

    html = fetch(url, client)
    slug_num = slug_article_number(url)
    if slug_num is None:
        log.warning("no slug number derivable for %s", url)
        return None
    # A bare numeric slug (no letter suffix) signals a 1950 baseline article;
    # post-1950 insertions all use letter-suffixed numbers (21A, 31A-D, 134A...).
    # CLPR occasionally mislabels a letter-suffixed article's heading with
    # "Constitution of India 1950" (e.g. Article 257A, inserted by the 42nd
    # Amendment in 1976) — defensively reject those regardless of label.
    is_bare_numeric = slug_num.isdigit()
    if not is_bare_numeric:
        return None
    parsed = parse_1950_block(html, accept_lone_unlabeled=True)
    if parsed is None:
        return None
    heading_raw, body_html = parsed
    if heading_raw is None:
        log.warning("unlabeled 1950 block at %s; using slug number %s", url, slug_num)
    elif heading_raw.upper() != slug_num.upper():
        log.warning(
            "slug/heading number mismatch at %s: slug=%s heading=%s (using slug)",
            url, slug_num, heading_raw,
        )
    return Article1950(
        number=normalize_number(slug_num),
        slug_number=slug_num,
        heading_number=heading_raw,
        title=title_from_url(url),
        body_html=body_html,
        source_url=url,
        source_html_sha256=hashlib.sha256(html.encode("utf-8")).hexdigest(),
        fetched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def iter_article_urls(client: httpx.Client) -> Iterator[str]:
    """Yield article URLs in sitemap order."""
    yield from discover_article_urls(client)


def write_record(article: Article1950) -> Path:
    SCRAPED_DIR.mkdir(parents=True, exist_ok=True)
    out = SCRAPED_DIR / f"article-{article.number}.json"
    out.write_text(json.dumps(asdict(article), indent=2, ensure_ascii=False))
    return out
