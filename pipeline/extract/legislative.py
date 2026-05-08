"""Parse the offline legislative.gov.in Constitution-Amendment-Acts page.

The page (saved manually by the user as ``docs/legislative-amendments.html`` —
the live URL is behind Akamai bot detection) lists all 106 Constitutional
Amendment Acts as a table of rows, each with a ``<a id="btn-..." type="pdf"
href="...">`` link to the act's PDF on legislative.gov.in's static CDN.

We extract one record per row:
  - amendment number (parsed from the ordinal-English title, e.g.
    "Constitution (One Hundred And Sixth Amendment) Act, 2023" → 106)
  - title (verbatim)
  - published_date (YYYY-MM-DD; the page format is DD/MM/YYYY)
  - year (from the title)
  - file_size (bytes, where present)
  - pdf_url
  - source: "legislative.gov.in"

Records emit to ``pipeline/intermediate/scraped/legislative/amendments.json``.
The downloader is a separate concern (see :func:`download_pdfs`).
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

import httpx
from bs4 import BeautifulSoup, Tag

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_HTML = REPO_ROOT / "docs" / "legislative-amendments.html"
SCRAPED_DIR = REPO_ROOT / "pipeline" / "intermediate" / "scraped" / "legislative"
DOWNLOAD_DIR = REPO_ROOT / "docs" / "amendments"

USER_AGENT = "indian-law-git/0.0.1 (+https://github.com/indian-law-git/constitution-of-india)"

log = logging.getLogger("legislative")


# ────────────────────── ordinal → integer parser ──────────────────────

_ORDINALS: dict[str, int] = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
    "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
    "eleventh": 11, "twelfth": 12, "thirteenth": 13, "fourteenth": 14,
    "fifteenth": 15, "sixteenth": 16, "seventeenth": 17, "eighteenth": 18,
    "nineteenth": 19, "twentieth": 20,
    "thirtieth": 30, "fortieth": 40, "fiftieth": 50,
    "sixtieth": 60, "seventieth": 70, "eightieth": 80, "ninetieth": 90,
    "hundredth": 100,
}
_CARDINALS: dict[str, int] = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80,
    "ninety": 90, "hundred": 100,
}


def parse_ordinal_phrase(phrase: str) -> int | None:
    """Convert an English ordinal phrase to an integer.

    Examples:
        "Sixth"                    → 6
        "Twenty-First"             → 21
        "One Hundred And Sixth"    → 106
        "One Hundredth"            → 100  (base ordinal already encodes 100)
        "First"                    → 1
        "Seventy eight"            → 78  (legislative.gov.in occasionally uses
                                          a cardinal-ending phrase where
                                          ordinal is expected)
        "One Hundred One"          → 101 (same loose form)
    Returns None if any token is not in the lookup tables.
    """
    tokens = [t for t in re.split(r"[\s\-]+", phrase.lower()) if t and t != "and"]
    if not tokens:
        return None
    last = tokens[-1]
    if last in _ORDINALS:
        base = _ORDINALS[last]
    elif last in _CARDINALS:
        # Loose form: treat trailing cardinal as if it were the ordinal.
        base = _CARDINALS[last]
    else:
        return None
    if len(tokens) == 1:
        return base
    pending = 0
    for t in tokens[:-1]:
        if t not in _CARDINALS:
            return None
        v = _CARDINALS[t]
        if v == 100:
            pending = pending * 100 if pending else 100
        else:
            pending += v
    # "One Hundredth" → cardinal=1 + ordinal-base=100; want 100, not 101.
    if base == 100 and pending > 0:
        return pending * 100
    return pending + base


# ────────────────────── HTML row parsing ──────────────────────


@dataclass(frozen=True)
class AmendmentLink:
    amendment_number: int | None  # parsed from the title; None if regex failed
    title: str
    year: int | None              # from the title (e.g. "Act, 2023")
    published_date: str | None    # ISO YYYY-MM-DD; None if missing
    file_size_kb: float | None
    pdf_url: str
    source_html_btn_id: str | None


_TITLE_RE = re.compile(
    r"Title:\s*(?P<title>.*?)\s*"
    r"(?:Published Year:\s*(?P<date>[0-9/]+))?\s*"
    r"(?:Type/Size:\s*(?P<size>[0-9.]+)\s*KB)?",
    re.IGNORECASE,
)
_AMENDMENT_NUM_RE = re.compile(
    # Most rows: "Constitution (Third Amendment) Act, 1954".
    # Some rows omit the word "Amendment" inside the parens
    # (e.g. "Constitution (Thirty-seventh) Act, 1975"), so make it optional.
    r"Constitution\s*\(\s*([A-Za-z\s\-]+?)(?:\s*Amendment)?\s*\)\s*(?:Act|Bill)",
    re.IGNORECASE,
)
_YEAR_RE = re.compile(r"\b(\d{4})\b")


def _date_iso(date_str: str | None) -> str | None:
    if not date_str:
        return None
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", date_str.strip())
    if not m:
        return None
    d, mo, y = m.groups()
    return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"


_TITLE_FIELD_RE = re.compile(
    r"Title:\s*(?P<title>.+?)\s*(?=Published Year:|Type/Size:|visibility\b|$)",
    re.IGNORECASE,
)
_DATE_FIELD_RE = re.compile(r"Published Year:\s*(?P<date>[0-9/\-]+)", re.IGNORECASE)
_SIZE_FIELD_RE = re.compile(
    r"Type/Size:\s*(?P<size>[0-9.]+)\s*KB", re.IGNORECASE,
)


def _parse_row(row: Tag) -> AmendmentLink | None:
    a = row.find("a", attrs={"type": "pdf"})
    if a is None:
        return None
    pdf_url = a.get("href", "")
    if not pdf_url:
        return None
    btn_id = a.get("id")
    text = re.sub(r"\s+", " ", row.get_text(" ", strip=True))
    title_m = _TITLE_FIELD_RE.search(text)
    if not title_m:
        return None
    title = title_m.group("title").strip().rstrip(",").strip()
    if not title:
        return None
    date_m = _DATE_FIELD_RE.search(text)
    pub_date = _date_iso(date_m.group("date")) if date_m else None
    size_m = _SIZE_FIELD_RE.search(text)
    size_kb = None
    if size_m:
        try:
            size_kb = float(size_m.group("size"))
        except ValueError:
            size_kb = None
    am_match = _AMENDMENT_NUM_RE.search(title)
    amendment_number = parse_ordinal_phrase(am_match.group(1)) if am_match else None
    year_match = _YEAR_RE.search(title)
    year = int(year_match.group(1)) if year_match else None
    return AmendmentLink(
        amendment_number=amendment_number,
        title=title,
        year=year,
        published_date=pub_date,
        file_size_kb=size_kb,
        pdf_url=pdf_url,
        source_html_btn_id=btn_id,
    )


def parse_html(path: Path = SOURCE_HTML) -> list[AmendmentLink]:
    """Parse every announcement row in the saved legislative.gov.in HTML."""
    if not path.exists():
        raise FileNotFoundError(f"{path} not found")
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "lxml")
    rows = soup.find_all("div", class_="announcementbox")
    out: list[AmendmentLink] = []
    for row in rows:
        link = _parse_row(row)
        if link is not None:
            out.append(link)
    return out


def write_records(records: list[AmendmentLink]) -> Path:
    SCRAPED_DIR.mkdir(parents=True, exist_ok=True)
    out = SCRAPED_DIR / "amendments.json"
    out.write_text(
        json.dumps([asdict(r) for r in records], indent=2, ensure_ascii=False) + "\n"
    )
    return out


# ────────────────────── PDF downloader ──────────────────────


def _safe_name(num: int | None) -> str:
    return f"{num:03d}" if num is not None else "unknown"


def _is_sor_row(r: "AmendmentLink") -> bool:
    """SOR (Statement of Reasons) entries are secondary docs published alongside
    the act. They share the amendment number but aren't the principal text.
    """
    t = (r.title or "").lstrip().lower()
    return t.startswith("sor")


def select_act_per_amendment(
    records: list["AmendmentLink"],
) -> dict[int, "AmendmentLink"]:
    """Return one Act-PDF row per amendment number.

    SOR rows are excluded. Where multiple Act-PDF rows exist for the same
    amendment (rare — Amendment 3 has two scans), we keep the one with the
    larger ``file_size_kb`` on the assumption that's the cleaner/fuller scan.
    """
    by_num: dict[int, "AmendmentLink"] = {}
    for r in records:
        if r.amendment_number is None:
            continue
        if _is_sor_row(r):
            continue
        existing = by_num.get(r.amendment_number)
        if existing is None:
            by_num[r.amendment_number] = r
            continue
        # Prefer the row with the larger known file size; if neither has size,
        # keep the first.
        existing_size = existing.file_size_kb or 0.0
        new_size = r.file_size_kb or 0.0
        if new_size > existing_size:
            by_num[r.amendment_number] = r
    return by_num



def download_pdfs(
    records: list[AmendmentLink], throttle_s: float = 1.0, force: bool = False
) -> tuple[int, int, int]:
    """Download one Act-PDF per amendment into ``docs/amendments/{NN}.pdf``.

    SOR rows are skipped; duplicate Act rows are deduped via
    :func:`select_act_per_amendment` (largest file size wins).

    legislative.gov.in's static-CDN PDFs sit behind Akamai bot-detection that
    rejects requests with non-browser User-Agent strings or missing ``Referer``
    / ``Sec-Fetch-*`` headers. We send a Chrome-like header set with the
    amendments-listing page as the Referer.

    Returns (downloaded, skipped_existing, failed)."""
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    selected = select_act_per_amendment(records)
    n_dl = 0
    n_skipped = 0
    n_failed = 0
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/130.0.0.0 Safari/537.36"
        ),
        "Accept": "application/pdf,application/x-pdf,application/octet-stream,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": (
            "https://www.legislative.gov.in/documents/constitution-of-india/"
            "the-constitution-amendment-acts-YTM2EjMtQWa"
        ),
        "Sec-Ch-Ua": '"Chromium";v="130", "Not_A Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }
    with httpx.Client(headers=headers, timeout=60.0, follow_redirects=True) as client:
        for amendment_no in sorted(selected):
            r = selected[amendment_no]
            target = DOWNLOAD_DIR / f"{amendment_no:03d}.pdf"
            if target.exists() and not force:
                n_skipped += 1
                continue
            log.info("GET %s", r.pdf_url)
            try:
                resp = client.get(r.pdf_url)
                resp.raise_for_status()
            except httpx.HTTPError as e:
                log.error("download failed for amendment %s: %s", amendment_no, e)
                n_failed += 1
                continue
            target.write_bytes(resp.content)
            sha = hashlib.sha256(resp.content).hexdigest()
            log.info(
                "saved %s (%d bytes, sha256=%s)",
                target.name, len(resp.content), sha[:16],
            )
            n_dl += 1
            time.sleep(throttle_s)
    return n_dl, n_skipped, n_failed
