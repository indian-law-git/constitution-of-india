"""Extract per-article 1950 form from CLPR's consolidated page.

CLPR (Centre for Law and Policy Research) publishes two views of the 1950
Constitution:

1. Per-article pages at /articles/article-NNN-... — each carries Version 1
   (Draft 1948), Version 2 (1950), and Summary sections.
2. A single consolidated page at /constitution/constitution-of-india-1950/
   listing every article inline.

Across the 1st-6th-Amendment validation work in 2026-05, the per-article
pages were observed to drift to post-amendment text under the "1950" label
in at least 6 articles (19, 81, 31, 305, 3 with substantive drift; 269 and
286 with cosmetic drift). The consolidated page consistently carries the
true 1950 form on every comparison done so far. So this extractor parses
the consolidated page and emits per-article JSONs that the renderer can
prefer over the per-article-page extractor's output.

Caveats:
- The consolidated page only carries 391 of the 395 articles via COI.NN
  markers. CLPR's own bug: Article 131 is hidden under a second "COI.130"
  marker (130 appears twice, with the second instance actually being
  Article 131 by position and title).
- 5 articles are genuinely missing from the consolidated page (142, 199,
  300, 342, 375). For those the renderer falls back to the per-article
  page extractor.
- Schedules are NOT on the consolidated page; the schedule pipeline is
  unaffected.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
SOURCE_HTML = ROOT / "pipeline/intermediate/clpr-scout/constitution-1950.html"
OUT_DIR = ROOT / "pipeline/intermediate/scraped/articles-consolidated"
SOURCE_URL = "https://www.constitutionofindia.net/constitution/constitution-of-india-1950/"

_COI_MARKER_RE = re.compile(r"^COI\.\d+$")


def _grid_for(marker_node):
    node = marker_node.parent
    while node and not (
        node.get("class") and "md:grid" in node.get("class", [])
    ):
        node = node.parent
    return node


_CLAUSE_MARKER_RE = re.compile(r"^\s*[⁠]?\(\s*[a-zA-Z0-9]+\s*\)")


def _extract_article(grid_div, expected_number: int) -> dict | None:
    children = grid_div.find_all("div", recursive=False)
    if len(children) < 2:
        return None
    content_div = children[1]

    # Most articles: title in <h4>, body in following siblings.
    h4 = content_div.find("h4")
    if h4:
        title = h4.get_text(strip=True)
        h4.extract()
        body_html = "".join(str(c) for c in content_div.children).strip()
        return _record(expected_number, title, body_html)

    # A few articles (e.g. Article 169) render the title as the first <p>
    # with the body starting at the second <p>. Detect by checking whether
    # the second block looks like a clause ("(1)", "(a)", etc.).
    paras = content_div.find_all("p", recursive=False)
    if len(paras) >= 2:
        second_text = paras[1].get_text(strip=True)
        if _CLAUSE_MARKER_RE.match(second_text):
            title = paras[0].get_text(strip=True)
            paras[0].extract()
            body_html = "".join(str(c) for c in content_div.children).strip()
            return _record(expected_number, title, body_html)

    # No title in consolidated (e.g. Article 17). Body is everything; the
    # caller will fall back to the per-article extractor for the title.
    body_html = "".join(str(c) for c in content_div.children).strip()
    return _record(expected_number, "", body_html)


def _record(n: int, title: str, body_html: str) -> dict:
    return {
        "number": f"{n:03d}",
        "slug_number": str(n),
        "heading_number": str(n),
        "title": title,
        "body_html": body_html,
        "source_url": SOURCE_URL,
    }


def extract() -> dict[int, dict]:
    """Parse the consolidated HTML; return {article_number: record}."""
    html = SOURCE_HTML.read_text()
    soup = BeautifulSoup(html, "lxml")

    # Walk markers in document order.
    markers = soup.find_all(string=_COI_MARKER_RE)

    out: dict[int, dict] = {}
    last_number: int | None = None

    for marker in markers:
        marker_text = str(marker).strip()
        m = _COI_MARKER_RE.match(marker_text)
        if not m:
            continue
        n = int(marker_text.split(".")[1])

        # Handle CLPR's known bug: the second COI.130 is actually Article 131.
        if n == last_number == 130:
            n = 131

        grid = _grid_for(marker)
        if grid is None:
            continue
        record = _extract_article(grid, n)
        if record is None:
            continue
        out[n] = record
        last_number = n

    return out


def write_all() -> tuple[int, list[int]]:
    """Run the extractor and write per-article JSONs.

    Returns (count_written, sorted_missing_numbers_in_1..395).
    """
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    records = extract()

    source_sha = sha256(SOURCE_HTML.read_bytes()).hexdigest()
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")

    for n, rec in sorted(records.items()):
        if not (1 <= n <= 395):
            continue
        rec_with_provenance = {
            **rec,
            "source_html_sha256": source_sha,
            "fetched_at": fetched_at,
        }
        (OUT_DIR / f"article-{n:03d}.json").write_text(
            json.dumps(rec_with_provenance, ensure_ascii=False, indent=2) + "\n"
        )

    expected = set(range(1, 396))
    valid = {n for n in records.keys() if 1 <= n <= 395}
    missing = sorted(expected - valid)
    return len(valid), missing


if __name__ == "__main__":
    count, missing = write_all()
    print(f"wrote {count} articles to {OUT_DIR}")
    print(f"missing from consolidated (will need per-article fallback): {missing}")
