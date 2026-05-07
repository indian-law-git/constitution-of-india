"""CLI entry point for the indian-law-git pipeline.

Stub: subcommands will be wired up as pipeline modules come online.
"""
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


if __name__ == "__main__":
    app()
