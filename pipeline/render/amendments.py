"""Generate ``metadata/amendments.json`` — the unified amendment index.

Triangulates four sources (one canonical for the act text, three for the
articles-touched index):

  - **legislative.gov.in** (canonical 1–106): title, year, published_date,
    PDF URL + local path, file size.
  - **pykih amendments.json** (1–99): one-paragraph summary per amendment.
  - **pykih data.json** (1–99): per-(amendment, article) status triples
    (modified / inserted / deleted).
  - **Indian Kanoon akn-remark citations** (95 amendments): inverted to
    a per-amendment list of articles whose body carries an editorial
    annotation citing that amendment.

Output schema:

    {
      "schema_version": "1",
      "summary": { ... counts ... },
      "amendments": [
        {
          "number": 1,
          "title": "The Constitution (First Amendment) Act, 1951",
          "year": 1951,
          "published_date": "1951-07-18",
          "pdf": {"url": "...", "local_path": "docs/amendments/001.pdf",
                  "size_kb": 319.77},
          "summary": "...",                               # from pykih
          "articles_touched": {
            "pykih":         [{"article": "19", "status": "modified"}, ...],
            "ik":            ["015", "019", ...],         # canonical IDs
          }
        },
        ...
      ]
    }
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = REPO_ROOT / "metadata" / "amendments.json"

LEGISLATIVE_PATH = REPO_ROOT / "pipeline" / "intermediate" / "scraped" / "legislative" / "amendments.json"
PYKIH_AMENDMENTS_PATH = REPO_ROOT / "pipeline" / "sources" / "pykih" / "amendments.json"
PYKIH_DATA_PATH = REPO_ROOT / "pipeline" / "sources" / "pykih" / "data.json"
IK_DIR = REPO_ROOT / "pipeline" / "intermediate" / "scraped" / "ik"

_CITATION_RE = re.compile(
    r"Constitution\s*\(\s*([A-Za-z\s\-]+?)\s*Amendment\s*\)\s*Act,?\s*\d{4}",
    re.IGNORECASE,
)


def _amendment_number_from_citation(citation: str) -> int | None:
    from pipeline.extract.legislative import parse_ordinal_phrase

    m = _CITATION_RE.search(citation)
    if not m:
        return None
    return parse_ordinal_phrase(m.group(1))


def _normalize_article_id(raw: str) -> str:
    """Convert pykih's loose article string ('15', '19', '21A') to the project
    canonical id format ('015', '019', '021A')."""
    s = str(raw).strip().upper()
    m = re.match(r"^([0-9]+)([A-Z]*)$", s)
    if not m:
        return s
    return f"{int(m.group(1)):03d}{m.group(2)}"


def _load_legislative() -> dict[int, dict]:
    """Return a {amendment_number: row} map from the legislative.gov.in extract."""
    if not LEGISLATIVE_PATH.exists():
        return {}
    rows = json.loads(LEGISLATIVE_PATH.read_text())
    out: dict[int, dict] = {}
    for r in rows:
        n = r.get("amendment_number")
        if n is None:
            continue
        # Skip SOR (Statement of Reasons) rows.
        title = (r.get("title") or "").lstrip().lower()
        if title.startswith("sor"):
            continue
        existing = out.get(n)
        if existing is None or (r.get("file_size_kb") or 0) > (existing.get("file_size_kb") or 0):
            out[n] = r
    return out


def _load_pykih_summaries() -> dict[int, str]:
    if not PYKIH_AMENDMENTS_PATH.exists():
        return {}
    rows = json.loads(PYKIH_AMENDMENTS_PATH.read_text())
    return {r["amendment"]: r.get("summary", "") for r in rows}


def _load_pykih_articles() -> dict[int, list[dict]]:
    """Return {amendment: [{article, status}, ...]} from pykih's data.json."""
    if not PYKIH_DATA_PATH.exists():
        return {}
    rows = json.loads(PYKIH_DATA_PATH.read_text())
    out: dict[int, list[dict]] = defaultdict(list)
    for r in rows:
        amendment = r.get("amendment")
        article = r.get("article")
        status = (r.get("status") or "").strip()
        if amendment is None or article is None:
            continue
        # Normalise "insertion" → "inserted" for consistency
        if status == "insertion":
            status = "inserted"
        out[amendment].append({
            "article": _normalize_article_id(article),
            "status": status or None,
        })
    # De-dupe per amendment, sort
    cleaned: dict[int, list[dict]] = {}
    for n, items in out.items():
        seen = set()
        deduped = []
        for it in items:
            key = (it["article"], it["status"])
            if key in seen:
                continue
            seen.add(key)
            deduped.append(it)
        deduped.sort(key=lambda x: (x["article"], x["status"] or ""))
        cleaned[n] = deduped
    return cleaned


def _load_ik_amendment_articles() -> dict[int, list[str]]:
    """Invert IK's per-article amendment citations to a per-amendment list of
    canonical article ids."""
    if not IK_DIR.exists():
        return {}
    out: dict[int, set[str]] = defaultdict(set)
    for path in IK_DIR.glob("*.json"):
        d = json.loads(path.read_text())
        article_id = d.get("number")  # already zero-padded canonical
        if not article_id:
            continue
        for cite in d.get("amendment_citations", []) or []:
            n = _amendment_number_from_citation(cite)
            if n is not None:
                out[n].add(article_id)
    return {k: sorted(v) for k, v in out.items()}


def build() -> tuple[Path, dict]:
    """Write metadata/amendments.json. Returns (path, summary dict)."""
    legislative = _load_legislative()
    pykih_summaries = _load_pykih_summaries()
    pykih_articles = _load_pykih_articles()
    ik_articles = _load_ik_amendment_articles()

    amendments: list[dict] = []
    for n in sorted(legislative.keys()):
        r = legislative[n]
        rec = {
            "number": n,
            "title": r.get("title"),
            "year": r.get("year"),
            "published_date": r.get("published_date"),
            "pdf": {
                "url": r.get("pdf_url"),
                "local_path": f"docs/amendments/{n:03d}.pdf",
                "size_kb": r.get("file_size_kb"),
            },
            "summary": pykih_summaries.get(n) or None,
            "articles_touched": {
                "pykih": pykih_articles.get(n, []),
                "ik": ik_articles.get(n, []),
            },
        }
        amendments.append(rec)

    summary = {
        "total": len(amendments),
        "with_pdf_url": sum(1 for a in amendments if a["pdf"]["url"]),
        "with_pykih_summary": sum(1 for a in amendments if a["summary"]),
        "with_pykih_articles": sum(1 for a in amendments if a["articles_touched"]["pykih"]),
        "with_ik_articles": sum(1 for a in amendments if a["articles_touched"]["ik"]),
    }

    out = {
        "schema_version": "1",
        "summary": summary,
        "amendments": amendments,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    return OUT_PATH, summary
