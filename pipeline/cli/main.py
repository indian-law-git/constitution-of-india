"""CLI entry point for the indian-law-git pipeline."""
from __future__ import annotations

import logging

import httpx
import typer

app = typer.Typer(help="indian-law-git pipeline CLI", no_args_is_help=True)


@app.command()
def version() -> None:
    """Print the pipeline version."""
    from importlib.metadata import version as _v

    typer.echo(_v("indian-law-git-pipeline"))


@app.command()
def info() -> None:
    """Print pipeline status (stubs)."""
    typer.echo("indian-law-git pipeline — Phase 0 (scaffolded). Modules are stubs.")


@app.command("render-articles")
def render_articles(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """Render the merged baseline JSONs into articles/article-NNN.md."""
    from pipeline.render import markdown as md

    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    written, missing = md.render_all()
    typer.echo(f"done: written={written} missing={missing} -> {md.OUT_DIR}")


@app.command("render-parts")
def render_parts(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """Render Part manifests to parts/part-X.md (one per Part of the 1950 Constitution)."""
    from pipeline.render import markdown as md

    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    written = md.render_all_parts()
    typer.echo(f"done: written={written} -> {md.PARTS_OUT}")

@app.command("build-provenance")
def build_provenance(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """Generate metadata/provenance.json — list every source the v1 baseline draws on."""
    from pipeline.render import provenance

    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    n = provenance.build()
    typer.echo(f"done: sources={n} -> {provenance.OUT_PATH}")


@app.command("build-crossrefs")
def build_crossrefs(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """Generate metadata/cross-references.json — inbound/outbound citation index."""
    from pipeline.render import crossref

    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    n = crossref.build()
    typer.echo(f"done: nodes={n} -> {crossref.OUT_PATH}")

@app.command("build-amendments")
def build_amendments(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """Generate metadata/amendments.json — unified index across legislative.gov.in + pykih + IK."""
    from pipeline.render import amendments

    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    out, summary = amendments.build()
    typer.echo(f"done: {summary} -> {out}")

@app.command("render-schedules")
def render_schedules(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """Render schedules/schedule-NN.md from scraped CLPR schedule segments."""
    from pipeline.render import markdown as md

    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    written, missing = md.render_all_schedules()
    suffix = f" missing_schedules={missing}" if missing else ""
    typer.echo(f"done: written={written}{suffix} -> {md.SCHEDULES_OUT}")


@app.command("extract-manuscript")
def extract_manuscript(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """Parse human transcriptions in pipeline/sources/manuscript and emit JSON.

    Handles both article-NNN.txt files (1950 baseline articles and gap fills)
    and schedule-NN[-X].txt files (schedule fills like Schedule 2 Part B).
    """
    from pipeline.extract import manuscript

    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    n_articles = manuscript.extract_all()
    n_schedules = manuscript.extract_all_schedules()
    typer.echo(
        f"done: articles={n_articles} schedules={n_schedules} -> {manuscript.OUT_DIR.parent}"
    )


@app.command("extract-ik")
def extract_ik(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """Parse the offline Indian Kanoon Constitution HTML and emit per-article JSON."""
    from pipeline.extract import ik

    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    n, n_with_amend = ik.extract_all()
    typer.echo(
        f"done: articles={n} with_amendment_citations={n_with_amend} -> {ik.OUT_DIR}"
    )


@app.command("scrape-clpr")
def scrape_clpr(
    limit: int = typer.Option(0, "--limit", "-n", help="Stop after this many URLs (0 = all)."),
    throttle: float = typer.Option(1.5, "--throttle", help="Seconds between requests on cache miss."),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Scrape constitutionofindia.net for the 1950-enacted article texts."""
    from pipeline.extract import clpr

    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    headers = {"User-Agent": clpr.USER_AGENT}
    n_seen = 0
    n_baseline = 0
    n_skipped_no_1950 = 0
    with httpx.Client(headers=headers) as client:
        urls = clpr.discover_article_urls(client)
        typer.echo(f"sitemap: {len(urls)} article URLs")
        for url in urls:
            if limit and n_seen >= limit:
                break
            n_seen += 1
            try:
                article = clpr.scrape_article(url, client)
            except httpx.HTTPError as e:
                typer.echo(f"  [error] {url}: {e}", err=True)
                continue
            if article is None:
                n_skipped_no_1950 += 1
                continue
            out = clpr.write_record(article)
            n_baseline += 1
            if verbose:
                typer.echo(f"  [{article.number}] {article.title[:60]}  -> {out.name}")
    typer.echo(
        f"done: scanned={n_seen} baseline={n_baseline} skipped_no_1950={n_skipped_no_1950}"
    )

@app.command("scrape-clpr-schedules")
def scrape_clpr_schedules(
    throttle: float = typer.Option(1.5, "--throttle", help="Seconds between requests on cache miss."),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Scrape constitutionofindia.net for the 1950-enacted schedule texts."""
    from pipeline.extract import clpr_schedules

    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    n_scanned, n_emitted, n_skipped = clpr_schedules.scrape_all(throttle_s=throttle)
    typer.echo(
        f"done: scanned={n_scanned} emitted={n_emitted} skipped_post_1950={n_skipped}"
    )

@app.command("extract-legislative")
def extract_legislative(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """Parse docs/legislative-amendments.html for amendment PDF URLs + metadata."""
    from pipeline.extract import legislative

    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    records = legislative.parse_html()
    out = legislative.write_records(records)
    parsed_n = sum(1 for r in records if r.amendment_number is not None)
    typer.echo(
        f"done: rows={len(records)} parsed_numbers={parsed_n} -> {out}"
    )


@app.command("download-amendments")
def download_amendments(
    throttle: float = typer.Option(1.0, "--throttle", help="Seconds between PDF downloads."),
    force: bool = typer.Option(False, "--force", help="Re-download even if file exists."),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Download every amendment PDF to docs/amendments/{NN}.pdf."""
    from pipeline.extract import legislative

    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    records = legislative.parse_html()
    n_dl, n_skip, n_fail = legislative.download_pdfs(
        records, throttle_s=throttle, force=force
    )
    typer.echo(
        f"done: downloaded={n_dl} skipped_existing={n_skip} failed={n_fail} -> {legislative.DOWNLOAD_DIR}"
    )


if __name__ == "__main__":
    app()
