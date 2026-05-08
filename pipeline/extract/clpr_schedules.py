"""CLPR (constitutionofindia.net) schedule scraper.

Fetches each /schedules/{slug}/ URL listed in CLPR's schedules-sitemap.xml,
parses the page's "Version 2 — Constitution of India 1950" block, and emits
one JSON record per URL.

The 1950 Constitution had eight schedules. CLPR splits some of them across
multiple per-Part URLs (Schedule 1 → 2 URLs, Schedule 2 → 4, Schedule 5 → 4,
Schedule 7 → 3). The render step consults ``SCHEDULE_URL_MAP`` to merge URL
records into one ``schedules/schedule-NN.md`` file per schedule.

Post-1950 schedules (Ninth, Tenth, Eleventh, Twelfth) are skipped — they
were inserted by later amendments and aren't part of the 1950 baseline.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup, NavigableString, Tag

USER_AGENT = "indian-law-git/0.0.1 (+https://github.com/indian-law-git/constitution-of-india)"
SITEMAP_URL = "https://www.constitutionofindia.net/schedules-sitemap.xml"
DEFAULT_THROTTLE_S = 1.5

REPO_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = REPO_ROOT / "pipeline" / "intermediate" / "cache" / "clpr-schedules"
SCRAPED_DIR = REPO_ROOT / "pipeline" / "intermediate" / "scraped" / "clpr-schedules"

log = logging.getLogger("clpr-schedules")

# ────────────────────── URL → (schedule_no, sub_part) mapping ──────────────────────
# Keys are CLPR slugs (last URL path segment). Values are (schedule_number, sub_part)
# where sub_part is None for single-section schedules. Schedules 9-12 are deliberately
# omitted — they were inserted post-1950.

SCHEDULE_URL_MAP: dict[str, tuple[int, str | None]] = {
    # First Schedule
    "i-the-states": (1, "I"),
    "ii-the-union-territories": (1, "II"),
    # Second Schedule (Part B is missing from CLPR's sitemap — known gap)
    "a-provisions-as-to-the-president-and-the-governors-of-states": (2, "A"),
    "c-provisions-as-to-the-speaker-and-the-deputy-speaker-of-the-house-of-the-people-and-the-chairman-and-the-deputy-chairman-of-the-council-of-states-and-the-speaker-and-the-deputy-speaker-of-the-legisl": (2, "C"),
    "d-provisions-as-to-the-judges-of-the-supreme-court-and-of-the-high-courts": (2, "D"),
    "e-provisions-as-to-the-comptroller-and-auditor-general-of-india": (2, "E"),
    # Third Schedule
    "forms-of-oaths-or-affirmations": (3, None),
    # Fourth Schedule
    "allocation-of-seats-in-the-council-of-states": (4, None),
    # Fifth Schedule
    "part-a-provisions-as-to-the-administration-and-control-of-scheduled-areas-and-scheduled-tribes": (5, "A"),
    "part-b-administration-and-control-of-scheduled-areas-and-scheduled-tribes": (5, "B"),
    "part-c-scheduled-areas": (5, "C"),
    "part-d-amendment-of-the-schedule": (5, "D"),
    # Sixth Schedule
    "provisions-as-to-the-administration-of-tribal-areas-in-the-states-of-assam-meghalaya-tripura-and-mizoram": (6, None),
    # Seventh Schedule
    "list-i-union-list": (7, "I"),
    "list-ii-state-list": (7, "II"),
    "list-iii-concurrent-list": (7, "III"),
    # Eighth Schedule
    "languages": (8, None),
}


# ────────────────────────────── data + http ──────────────────────────────


@dataclass(frozen=True)
class ScheduleSegment:
    """One schedule sub-part scraped from a single CLPR URL."""

    schedule_number: int
    sub_part: str | None  # 'I'/'II'/'A'/'B'/None
    sub_part_order: int   # ordering within the schedule (for merge)
    schedule_title: str   # h2 text, e.g. "First Schedule"
    section_title: str    # h1 text, e.g. "I: The States" or "Forms of Oaths or Affirmations"
    body_html: str        # the Version-2 (1950) content
    source_url: str
    source_html_sha256: str
    fetched_at: str


def _cache_path(url: str) -> Path:
    h = hashlib.sha256(url.encode()).hexdigest()[:24]
    slug = urlparse(url).path.strip("/").split("/")[-1] or "root"
    return CACHE_DIR / f"{slug}.{h}.html"


def fetch(url: str, client: httpx.Client, throttle_s: float = DEFAULT_THROTTLE_S) -> str:
    """Fetch with on-disk caching and polite throttling on miss."""
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


def discover_schedule_urls(client: httpx.Client) -> list[str]:
    xml = fetch(SITEMAP_URL, client, throttle_s=0.0)
    return re.findall(r"<loc>([^<]+)</loc>", xml)


# ────────────────────────────── parsing ──────────────────────────────


def _slug_of(url: str) -> str:
    return urlparse(url).path.strip("/").split("/")[-1]


def _find_version_block(soup: BeautifulSoup, want_year: str = "1950") -> Tag | None:
    """Return the col-span-9 content tag for the Version block whose label
    cites ``want_year``. Returns None if not found.

    On schedule pages the structure is:
        <div class="md:grid md:grid-cols-12 ...">
          <div class="md:col-span-3"><h3>VERSION N</h3></div>
          <div class="md:col-span-9">
            <h4>... Constitution of India 1950</h4>  (or similar)
            <p>...content...</p>
          </div>
        </div>

    We search every md:col-span-9 for one that mentions the target year
    in its label (h4 or first <strong>) and returns it.
    """
    for cs9 in soup.find_all(class_="md:col-span-9"):
        # Skip the page-title col-span-9 (it contains the h1, not version content)
        if cs9.find("h1") is not None:
            continue
        # Look at the leading label
        h4 = cs9.find("h4")
        label_text = h4.get_text(strip=True) if h4 else ""
        if not label_text:
            first_p = cs9.find("p")
            if first_p:
                strong = first_p.find("strong")
                if strong and strong.get_text(strip=True) == first_p.get_text(strip=True):
                    label_text = strong.get_text(strip=True)
        if not label_text:
            continue
        if "Draft" in label_text or "1948" in label_text:
            continue
        if want_year in label_text:
            return cs9
    return None


def _sub_block_body_html(content: Tag) -> str:
    """Extract everything inside the version content area except the leading
    label element (h4 or initial <p><strong>). Mirrors the article-level helper.
    """
    parts: list[str] = []
    seen_label = False
    for child in content.children:
        if not hasattr(child, "name") or child.name is None:
            continue
        if not seen_label:
            if child.name == "h4":
                seen_label = True
                continue
            if child.name == "p":
                strong = child.find("strong")
                if strong and strong.get_text(strip=True) == child.get_text(strip=True):
                    seen_label = True
                    continue
            seen_label = True  # nothing labelish — start capturing from this element
        parts.append(str(child))
    return "".join(parts).strip()


def parse_schedule_page(html: str, slug: str, url: str) -> ScheduleSegment | None:
    if slug not in SCHEDULE_URL_MAP:
        return None
    schedule_no, sub_part = SCHEDULE_URL_MAP[slug]
    soup = BeautifulSoup(html, "lxml")
    h2 = soup.find("h2")
    h1 = soup.find("h1")
    schedule_title = h2.get_text(strip=True) if h2 else ""
    section_title = h1.get_text(strip=True) if h1 else slug
    content = _find_version_block(soup, want_year="1950")
    if content is None:
        log.warning("no 1950 version block found at %s", url)
        return None
    body_html = _sub_block_body_html(content)
    if not body_html:
        return None
    return ScheduleSegment(
        schedule_number=schedule_no,
        sub_part=sub_part,
        sub_part_order=_sub_part_order(sub_part),
        schedule_title=schedule_title,
        section_title=section_title,
        body_html=body_html,
        source_url=url,
        source_html_sha256=hashlib.sha256(html.encode("utf-8")).hexdigest(),
        fetched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


_SUBPART_ORDER = {
    None: 0,
    "I": 1, "II": 2, "III": 3, "IV": 4,
    "A": 1, "B": 2, "C": 3, "D": 4, "E": 5,
}


def _sub_part_order(sub: str | None) -> int:
    return _SUBPART_ORDER.get(sub, 99)


# ────────────────────────────── orchestration ──────────────────────────────


def write_record(seg: ScheduleSegment, slug: str) -> Path:
    SCRAPED_DIR.mkdir(parents=True, exist_ok=True)
    out = SCRAPED_DIR / f"{slug}.json"
    out.write_text(json.dumps(asdict(seg), indent=2, ensure_ascii=False))
    return out


def scrape_all(throttle_s: float = DEFAULT_THROTTLE_S) -> tuple[int, int, int]:
    """Scrape every URL listed in the schedules-sitemap that maps to a 1950
    schedule (1..8). Returns (scanned, emitted, skipped_post_1950)."""
    headers = {"User-Agent": USER_AGENT}
    n_scanned = 0
    n_emitted = 0
    n_skipped = 0
    with httpx.Client(headers=headers) as client:
        urls = discover_schedule_urls(client)
        for url in urls:
            slug = _slug_of(url)
            if slug not in SCHEDULE_URL_MAP:
                n_skipped += 1
                continue
            n_scanned += 1
            try:
                html = fetch(url, client, throttle_s=throttle_s)
            except httpx.HTTPError as e:
                log.error("fetch failed for %s: %s", url, e)
                continue
            seg = parse_schedule_page(html, slug, url)
            if seg is None:
                continue
            write_record(seg, slug)
            n_emitted += 1
    return n_scanned, n_emitted, n_skipped


def iter_segments() -> Iterator[ScheduleSegment]:
    if not SCRAPED_DIR.exists():
        return
    for path in sorted(SCRAPED_DIR.glob("*.json")):
        d = json.loads(path.read_text())
        yield ScheduleSegment(**d)
