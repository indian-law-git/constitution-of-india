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
    raw_number: str  # as it appeared in the heading, e.g. "19" or "31A"
    title: str  # heading text after the comma, e.g. "Protection of certain rights..."
    body_html: str  # raw inner HTML of the version block (preserves clauses, italics)
    source_url: str
    source_html_sha256: str
    fetched_at: str  # ISO-8601 UTC


_HEADING_RE = re.compile(
    r"^Article\s+([0-9]+[A-Z]*),\s*Constitution of India 1950\s*$",
    re.IGNORECASE,
)


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


def _sub_block_body_html(sub_block: Tag) -> str:
    """Inner HTML of a version sub-block, minus its h4 label."""
    parts: list[str] = []
    for child in sub_block.children:
        if getattr(child, "name", None) == "h4":
            continue
        if hasattr(child, "name") and child.name is not None:
            parts.append(str(child))
    return "".join(parts).strip()


def parse_1950_block(html: str) -> tuple[str | None, str] | None:
    """Return (raw_number, body_html) for the 1950 version block, or None.

    Strategy:
      1. Prefer an explicit ``<h4>Article N, Constitution of India 1950</h4>``
         inside an ``.article-detail__content__sub-block`` — return its number
         and content.
      2. Fall back to the last non-Draft version sub-block lacking such a label
         (CLPR sometimes omits the heading on the 1950 version, e.g., Article 145).
         In that case ``raw_number`` is None and the caller should use the slug.
      3. If every labeled version is a Draft or post-1950, return None — this
         article is a post-1950 insertion with no 1950 baseline.
    """
    soup = BeautifulSoup(html, "lxml")
    sub_blocks = soup.find_all(class_="article-detail__content__sub-block")

    h4_match: tuple[str, Tag] | None = None
    unlabeled_candidates: list[Tag] = []
    has_draft_version = False

    for sb in sub_blocks:
        # Skip the Summary sub-block (its parent main-block has an h3 'Summary').
        parent = sb.find_parent(class_="article-detail__content__main-block")
        if parent is not None:
            left_h3 = parent.find("h3")
            if left_h3 and "Summary" in left_h3.get_text(strip=True):
                continue

        h4 = sb.find("h4")
        label = h4.get_text(strip=True) if h4 else ""

        if not label:
            unlabeled_candidates.append(sb)
            continue
        if "Draft" in label:
            has_draft_version = True
            continue
        m = _HEADING_RE.match(label)
        if m:
            h4_match = (m.group(1), sb)
            break
        # Labeled but not 1950 and not Draft — assume post-1950 variant; ignore.

    if h4_match is not None:
        raw_number, sb = h4_match
        return raw_number, _sub_block_body_html(sb)
    # Unlabeled fallback only fires when the page also shows a Draft Article version.
    # That's the signal that the article existed at drafting time, so the unlabeled
    # block must be its 1950 enactment. Without a Draft version, an unlabeled block
    # is most likely a post-1950 insertion (e.g., Article 338A, 134A, 139A).
    if unlabeled_candidates and has_draft_version:
        return None, _sub_block_body_html(unlabeled_candidates[-1])
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
    """Extract the article number from a CLPR slug like ``article-145-rules-...``."""
    slug = urlparse(url).path.strip("/").split("/")[-1]
    m = re.match(r"^article-([0-9]+[a-z]*)-", slug)
    if not m:
        return None
    return m.group(1).upper()


def scrape_article(url: str, client: httpx.Client) -> Article1950 | None:
    """Fetch and parse one CLPR article page; return None if no 1950 block."""
    from datetime import datetime, timezone

    html = fetch(url, client)
    parsed = parse_1950_block(html)
    if parsed is None:
        return None
    raw_number, body_html = parsed
    if raw_number is None:
        # Unlabeled fallback — derive from slug.
        slug_num = slug_article_number(url)
        if slug_num is None:
            log.warning("no number derivable for %s", url)
            return None
        raw_number = slug_num
        log.warning("unlabeled 1950 block at %s; using slug number %s", url, raw_number)
    return Article1950(
        number=normalize_number(raw_number),
        raw_number=raw_number,
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
