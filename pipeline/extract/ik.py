"""Indian Kanoon (offline) Constitution-of-India extractor.

Parses the manually-saved IK HTML at ``docs/ConstitutionofIndia_IK.html`` —
which uses Akoma Ntoso semantic markup (akn-section / akn-content / akn-p
/ akn-remark) — and emits one structured JSON record per article into
``pipeline/intermediate/scraped/ik/``.

IK serves the *current* consolidated Constitution, so this is NOT a 1950
baseline source. It is useful for:
  - cross-checking CLPR-derived 1950 articles for unchanged-since-1950 ones
  - filling gaps where the article is unchanged since 1950 (e.g., Article 40)
  - harvesting per-article amendment citations from the inline editorial
    annotations (a leg-up on Phase 2 amendment metadata)
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from bs4 import BeautifulSoup, Tag

REPO_ROOT = Path(__file__).resolve().parents[2]
IK_HTML_PATH = REPO_ROOT / "docs" / "ConstitutionofIndia_IK.html"
OUT_DIR = REPO_ROOT / "pipeline" / "intermediate" / "scraped" / "ik"

log = logging.getLogger("ik")

# Top-level article id is "section_N" or "section_NA" (numeric + optional letter
# suffix). Sub-clause ids contain a dot (section_N.M / section_N.M.a) — those
# are nested and must be excluded from the article-level pass.
_ARTICLE_ID_RE = re.compile(r"^section_([0-9]+[A-Z]*)$")
# CLPR/IK use ordinal English for amendment numbers in the citation form
# "Constitution (Forty-Second Amendment) Act, 1976".
_AMENDMENT_RE = re.compile(
    r"Constitution\s*\(\s*[A-Za-z\-\s]+?\s*Amendment\s*\)\s*Act,?\s*\d{4}"
)


@dataclass(frozen=True)
class IkArticle:
    """A single article from the IK current consolidated Constitution."""

    number: str  # zero-padded canonical, e.g. "040" or "031B"
    raw_id: str  # IK id stripped of the "section_" prefix, e.g. "40", "31B"
    title: str  # the heading text after "N."
    body_html: str  # akn-content inner HTML, with editorial annotations preserved
    body_text: str  # plain-text rendering for quick diffing
    has_amendment_remarks: bool
    amendment_citations: list[str]  # de-duped list of amendment-act citations found
    source_file: str  # relative path to the source HTML
    source_file_sha256: str
    extracted_at: str


def _normalize_number(raw: str) -> str:
    m = re.match(r"^([0-9]+)([A-Z]*)$", raw)
    if not m:
        return raw
    num, suffix = m.groups()
    return f"{int(num):03d}{suffix}"


def _heading_title(h3: Tag | None) -> str:
    if h3 is None:
        return ""
    text = h3.get_text(" ", strip=True)
    return re.sub(r"^\d+[A-Z]*\.\s*", "", text)


def _amendment_citations(scope: Tag) -> list[str]:
    """Return de-duped amendment-act citations from any akn-remark within scope."""
    seen: list[str] = []
    for remark in scope.find_all(class_="akn-remark"):
        for m in _AMENDMENT_RE.finditer(remark.get_text(" ", strip=True)):
            cite = re.sub(r"\s+", " ", m.group(0)).strip()
            if cite not in seen:
                seen.append(cite)
    return seen


def parse_ik_html(html: str, source_file: str) -> Iterator[IkArticle]:
    """Yield one ``IkArticle`` for each top-level akn-section in the IK page."""
    soup = BeautifulSoup(html, "lxml")
    file_sha = hashlib.sha256(html.encode("utf-8")).hexdigest()
    extracted_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for sec in soup.find_all("section", class_="akn-section"):
        sid = sec.get("id", "")
        m = _ARTICLE_ID_RE.match(sid)
        if not m:
            continue
        raw_id = m.group(1)
        body_el = sec.find(class_="akn-content")
        body_html = str(body_el) if body_el is not None else ""
        body_text = (
            body_el.get_text(" ", strip=True) if body_el is not None else ""
        )
        citations = _amendment_citations(sec)
        yield IkArticle(
            number=_normalize_number(raw_id),
            raw_id=raw_id,
            title=_heading_title(sec.find("h3")),
            body_html=body_html,
            body_text=body_text,
            has_amendment_remarks=bool(citations) or sec.find(class_="akn-remark") is not None,
            amendment_citations=citations,
            source_file=source_file,
            source_file_sha256=file_sha,
            extracted_at=extracted_at,
        )


def write_record(article: IkArticle) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"article-{article.number}.json"
    out.write_text(json.dumps(asdict(article), indent=2, ensure_ascii=False))
    return out


def extract_all(path: Path = IK_HTML_PATH) -> tuple[int, int]:
    """Parse the IK HTML on disk; return (article_count, with_amendments_count)."""
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found — drop the manually-saved IK Constitution HTML there."
        )
    html = path.read_text(encoding="utf-8")
    rel = str(path.relative_to(REPO_ROOT))
    n = 0
    n_with_amend = 0
    for art in parse_ik_html(html, rel):
        write_record(art)
        n += 1
        if art.amendment_citations:
            n_with_amend += 1
    return n, n_with_amend
