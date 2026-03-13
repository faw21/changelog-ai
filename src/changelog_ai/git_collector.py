"""Collect git commits between two refs (tags, SHAs, or branch names)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import git


@dataclass(frozen=True)
class CommitInfo:
    sha: str
    short_sha: str
    message: str
    author: str
    title: str           # first line of message
    body: str            # rest of message
    commit_type: str     # feat, fix, perf, chore, etc. (parsed from conventional commits)
    breaking: bool       # whether this is a breaking change
    scope: str           # conventional commit scope (optional)
    files_changed: list[str]


_CONVENTIONAL_RE = re.compile(
    r"^(?P<type>feat|fix|perf|refactor|docs|test|chore|style|ci|build|revert)"
    r"(?:\((?P<scope>[^)]+)\))?"
    r"(?P<breaking>!)?:\s*(?P<desc>.+)$",
    re.IGNORECASE,
)

_BREAKING_FOOTER_RE = re.compile(r"^BREAKING[- ]CHANGE:", re.MULTILINE)


def _parse_commit_type(message: str) -> tuple[str, str, bool]:
    """Parse conventional commit type, scope, and breaking flag from message title."""
    title = message.splitlines()[0].strip()
    m = _CONVENTIONAL_RE.match(title)
    if m:
        ctype = m.group("type").lower()
        scope = m.group("scope") or ""
        breaking = bool(m.group("breaking")) or bool(_BREAKING_FOOTER_RE.search(message))
        return ctype, scope, breaking
    # heuristic fallback
    lower = title.lower()
    if lower.startswith(("add ", "added ", "new ", "feature")):
        return "feat", "", False
    if lower.startswith(("fix", "bug", "patch", "resolved", "closes")):
        return "fix", "", False
    if lower.startswith(("perf", "optim", "speed", "faster")):
        return "perf", "", False
    if lower.startswith(("doc", "readme", "comment")):
        return "docs", "", False
    if lower.startswith(("refactor", "restructur", "clean", "rename", "move")):
        return "refactor", "", False
    if lower.startswith(("test", "spec")):
        return "test", "", False
    return "other", "", False


def get_latest_tag(repo: git.Repo) -> str | None:
    """Return the most recent tag in the repo, or None if no tags exist."""
    try:
        tags = sorted(repo.tags, key=lambda t: t.commit.committed_date, reverse=True)
        return tags[0].name if tags else None
    except Exception:
        return None


def get_commits_between(
    repo_path: str,
    from_ref: str | None = None,
    to_ref: str = "HEAD",
) -> list[CommitInfo]:
    """Collect commits between from_ref and to_ref.

    Args:
        repo_path: Path to the git repository.
        from_ref: Start ref (exclusive). If None, uses the latest tag; if still None, uses all commits.
        to_ref: End ref (inclusive). Defaults to HEAD.

    Returns:
        List of CommitInfo, newest first.
    """
    repo = git.Repo(repo_path)

    # resolve from_ref
    effective_from = from_ref
    if effective_from is None:
        effective_from = get_latest_tag(repo)

    try:
        if effective_from:
            rev_range = f"{effective_from}..{to_ref}"
        else:
            rev_range = to_ref

        raw_commits = list(repo.iter_commits(rev_range))
    except (git.GitCommandError, git.BadName, ValueError):
        return []

    result: list[CommitInfo] = []
    for commit in raw_commits:
        msg = commit.message.strip()
        title = msg.splitlines()[0].strip() if msg else ""
        body_lines = msg.splitlines()[1:] if "\n" in msg else []
        body = "\n".join(body_lines).strip()

        ctype, scope, breaking = _parse_commit_type(msg)

        # get changed files
        files_changed: list[str] = []
        try:
            if commit.parents:
                diff = commit.diff(commit.parents[0])
                files_changed = [d.a_path or d.b_path for d in diff]
            else:
                files_changed = list(commit.stats.files.keys())
        except Exception:
            files_changed = list(commit.stats.files.keys())

        result.append(CommitInfo(
            sha=commit.hexsha,
            short_sha=commit.hexsha[:8],
            message=msg,
            author=commit.author.name,
            title=title,
            body=body,
            commit_type=ctype,
            breaking=breaking,
            scope=scope,
            files_changed=files_changed,
        ))

    return result


def get_tags(repo_path: str) -> list[tuple[str, str]]:
    """Return list of (tag_name, sha) sorted newest first."""
    try:
        repo = git.Repo(repo_path)
        tags = sorted(repo.tags, key=lambda t: t.commit.committed_date, reverse=True)
        return [(t.name, t.commit.hexsha[:8]) for t in tags]
    except Exception:
        return []
