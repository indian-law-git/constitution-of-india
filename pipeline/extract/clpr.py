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


def parse_1950_block(html: str) -> tuple[str, str, str] | None:
    """Return (raw_number, title, body_html) for the 1950 version block, or None.

    The block is identified by an <h4> matching ``_HEADING_RE`` inside a
    ``.article-detail__content__sub-block`` container.
    """
    soup = BeautifulSoup(html, "lxml")
    for h4 in soup.find_all("h4"):
        text = h4.get_text(strip=True)
        m = _HEADING_RE.match(text)
        if not m:
            continue
        raw_number = m.group(1)
        block: Tag | None = h4.find_parent(class_="article-detail__content__sub-block")
        if block is None:
            block = h4.parent
        # Title sits in the heading itself in CLPR's per-article pages — but the
        # human-readable title is the page <h1>; fall back to the slug. We surface
        # the slug-derived title in the caller; here we just keep a sentinel.
        body_parts: list[str] = []
        for sib in h4.find_next_siblings():
            body_parts.append(str(sib))
        return raw_number, "", "".join(body_parts).strip()
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


def scrape_article(url: str, client: httpx.Client) -> Article1950 | None:
    """Fetch and parse one CLPR article page; return None if no 1950 block."""
    from datetime import datetime, timezone

    html = fetch(url, client)
    parsed = parse_1950_block(html)
    if parsed is None:
        return None
    raw_number, _stub, body_html = parsed
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
