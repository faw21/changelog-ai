"""CLI entry point for changelog-ai."""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax

from . import __version__
from .git_collector import get_commits_between, get_latest_tag, get_tags
from .generator import generate_changelog
from .providers import create_provider
import git as gitlib

console = Console()
err_console = Console(stderr=True)


def _auto_detect_provider() -> str:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "claude"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    return "ollama"


def _resolve_repo(path: str) -> str:
    """Return the root of the git repo at or containing path."""
    p = Path(path).expanduser().resolve()
    try:
        repo = gitlib.Repo(p, search_parent_directories=True)
        return str(Path(repo.working_tree_dir))
    except (gitlib.InvalidGitRepositoryError, gitlib.NoSuchPathError):
        err_console.print(f"[red]Error:[/red] No git repository found at {path!r}")
        sys.exit(1)


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("path", default=".", metavar="[PATH]")
@click.option(
    "--from", "from_ref",
    default=None,
    help="Start ref (tag, SHA, branch). Defaults to the latest tag.",
)
@click.option(
    "--to", "to_ref",
    default="HEAD",
    show_default=True,
    help="End ref (tag, SHA, branch).",
)
@click.option(
    "--release-version", "release_version",
    default=None,
    help="Version label for this release (e.g. v1.2.0). Defaults to 'Unreleased'.",
)
@click.option(
    "--date", "release_date",
    default=None,
    help="Release date (YYYY-MM-DD). Defaults to today.",
)
@click.option(
    "--format", "fmt",
    type=click.Choice(["keepachangelog", "github", "minimal"], case_sensitive=False),
    default="keepachangelog",
    show_default=True,
    help="Output format.",
)
@click.option(
    "--provider",
    type=click.Choice(["claude", "openai", "ollama"], case_sensitive=False),
    default=None,
    help="LLM provider. Auto-detected from environment if not set.",
)
@click.option(
    "--model",
    default=None,
    help="LLM model name (overrides provider default).",
)
@click.option(
    "--prepend",
    default=None,
    metavar="FILE",
    help="Prepend generated entry to this file (e.g. CHANGELOG.md).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview the generated entry without writing to any file.",
)
@click.option(
    "--raw",
    is_flag=True,
    help="Print raw text only (no rich formatting).",
)
@click.option(
    "--list-tags",
    is_flag=True,
    help="List recent tags and exit (useful to find --from values).",
)
@click.option(
    "--show-commits",
    is_flag=True,
    help="Show commits found before generating.",
)
@click.version_option(__version__, "-V", "--version")
def main(
    path: str,
    from_ref: str | None,
    to_ref: str,
    release_version: str | None,
    release_date: str | None,
    fmt: str,
    provider: str | None,
    model: str | None,
    prepend: str | None,
    dry_run: bool,
    raw: bool,
    list_tags: bool,
    show_commits: bool,
) -> None:
    """Generate CHANGELOG entries from git history using AI.

    Reads commits between two refs (default: latest tag to HEAD) and generates
    a professional changelog entry you can paste into CHANGELOG.md or GitHub Releases.

    \b
    Examples:
      changelog-ai                              # unreleased since last tag
      changelog-ai --version v1.2.0            # label the release version
      changelog-ai --from v1.0.0 --to v1.1.0  # specific range
      changelog-ai --format github             # GitHub Releases format
      changelog-ai --prepend CHANGELOG.md      # write to file
      changelog-ai --list-tags                 # see available tags
    """
    repo_path = _resolve_repo(path)

    # --list-tags shortcut
    if list_tags:
        tags = get_tags(repo_path)
        if not tags:
            console.print("[yellow]No tags found in this repository.[/yellow]")
        else:
            console.print(f"\n[bold]Tags in {Path(repo_path).name}:[/bold]")
            for tag_name, sha in tags[:20]:
                console.print(f"  [cyan]{tag_name}[/cyan]  [dim]{sha}[/dim]")
        return

    # collect commits
    with console.status("[bold green]Scanning git history...[/bold green]"):
        commits = get_commits_between(repo_path, from_ref=from_ref, to_ref=to_ref)

    if show_commits:
        if commits:
            console.print(f"\n[dim]Found {len(commits)} commit(s):[/dim]")
            for c in commits:
                breaking_mark = " [red]BREAKING[/red]" if c.breaking else ""
                type_color = {"feat": "green", "fix": "yellow", "perf": "blue"}.get(c.commit_type, "dim")
                console.print(
                    f"  [{c.short_sha}] "
                    f"[{type_color}]{c.commit_type}[/{type_color}]{breaking_mark}: "
                    f"{c.title}"
                )
        else:
            console.print("[yellow]No commits found in range.[/yellow]")

    if not commits:
        # show which range was checked
        try:
            repo = gitlib.Repo(repo_path)
            latest_tag = from_ref or (lambda r: r.tags and sorted(r.tags, key=lambda t: t.commit.committed_date, reverse=True)[0].name or "the beginning")(repo)
        except Exception:
            latest_tag = from_ref or "the last tag"
        console.print(
            Panel(
                f"[yellow]No commits found between {latest_tag!r} and {to_ref!r}.[/yellow]\n\n"
                "Use [bold]--list-tags[/bold] to see available tags, or "
                "[bold]--from TAG[/bold] to specify a range.",
                title="changelog-ai",
                border_style="yellow",
            )
        )
        sys.exit(0)

    # resolve metadata
    effective_version = release_version or "Unreleased"
    effective_date = release_date or date.today().isoformat()
    chosen_provider = provider or _auto_detect_provider()

    # generate
    try:
        llm = create_provider(chosen_provider, model)
    except ValueError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except KeyError as e:
        err_console.print(f"[red]Missing API key:[/red] {e}")
        sys.exit(1)

    with console.status(f"[bold green]Generating changelog with {chosen_provider}...[/bold green]"):
        try:
            changelog_text = generate_changelog(
                commits,
                llm,
                version=effective_version,
                release_date=effective_date,
                fmt=fmt,
            )
        except Exception as e:
            err_console.print(f"[red]LLM error:[/red] {e}")
            sys.exit(1)

    # output
    if raw:
        click.echo(changelog_text)
    else:
        subtitle = f"{len(commits)} commit(s) · {Path(repo_path).name}"
        if not dry_run and prepend:
            subtitle += f" · will prepend to {prepend}"
        console.print()
        console.print(
            Panel(
                Markdown(changelog_text),
                title=f"[bold]Changelog[/bold] [dim]({effective_version} · {fmt})[/dim]",
                subtitle=f"[dim]{subtitle}[/dim]",
                border_style="cyan",
            )
        )

    # write to file
    if prepend and not dry_run:
        target = Path(prepend)
        existing = target.read_text() if target.exists() else ""
        new_content = changelog_text.rstrip() + "\n\n" + existing
        target.write_text(new_content)
        if not raw:
            console.print(f"[dim]✓ Prepended to {prepend}[/dim]")
    elif dry_run and prepend:
        if not raw:
            console.print(f"[dim][yellow]dry-run:[/yellow] would prepend to {prepend}[/dim]")
