"""AI-powered CHANGELOG entry generator."""

from __future__ import annotations

from .git_collector import CommitInfo
from .providers import LLMProvider


_TYPE_LABELS = {
    "feat": "Added",
    "fix": "Fixed",
    "perf": "Performance",
    "refactor": "Changed",
    "docs": "Documentation",
    "test": "Tests",
    "chore": "Chores",
    "style": "Style",
    "ci": "CI/CD",
    "build": "Build",
    "revert": "Reverted",
    "other": "Other",
}

_FORMAT_INSTRUCTIONS = {
    "keepachangelog": """Format the output as a Keep a Changelog (keepachangelog.com) section.
Use these section headers (only include sections with changes):
## [VERSION] - DATE

### Breaking Changes
- ...

### Added
- ...

### Changed
- ...

### Deprecated
- ...

### Removed
- ...

### Fixed
- ...

### Security
- ...

Rules:
- Each bullet point should be a clear, user-facing description (not just the commit message)
- Group related commits into single bullets where it makes sense
- Omit chore/test/docs commits unless they're significant
- For breaking changes, explain what users need to change
- VERSION and DATE will be substituted by the tool""",

    "github": """Format the output as GitHub Release Notes.
Start with a brief 1-2 sentence summary of the release.
Then use these sections (only include sections with changes):

## What's Changed
- ...

## Bug Fixes
- ...

## Performance Improvements
- ...

## Breaking Changes
- ...

Rules:
- Lead with user impact, not technical detail
- Group related changes
- Link to commit SHAs where helpful (use the short SHA provided)
- Keep it concise""",

    "minimal": """Format the output as a simple bullet list.
No headers. Just a plain list of what changed:
- ...
- ...

Rules:
- One bullet per meaningful change (group related commits)
- User-facing language
- No implementation details
- Breaking changes should start with 'BREAKING:'""",
}


def _build_prompt(
    commits: list[CommitInfo],
    version: str,
    release_date: str,
    fmt: str,
) -> str:
    format_instruction = _FORMAT_INSTRUCTIONS.get(fmt, _FORMAT_INSTRUCTIONS["keepachangelog"])

    # build commit list grouped by type
    lines: list[str] = []
    breaking = [c for c in commits if c.breaking]
    by_type: dict[str, list[CommitInfo]] = {}
    for c in commits:
        by_type.setdefault(c.commit_type, []).append(c)

    lines.append(f"Generate a CHANGELOG entry for version {version} (released {release_date}).")
    lines.append("")
    lines.append(f"You have {len(commits)} commit(s) to summarize:")
    lines.append("")

    if breaking:
        lines.append("⚠️  BREAKING CHANGES:")
        for c in breaking:
            lines.append(f"  [{c.short_sha}] {c.title}")
        lines.append("")

    for ctype in ["feat", "fix", "perf", "refactor", "docs", "chore", "other"]:
        type_commits = by_type.get(ctype, [])
        if not type_commits:
            continue
        label = _TYPE_LABELS.get(ctype, ctype.title())
        lines.append(f"{label} ({len(type_commits)} commit(s)):")
        for c in type_commits:
            scope_str = f"[{c.scope}] " if c.scope else ""
            files_hint = f" (files: {', '.join(c.files_changed[:3])})" if c.files_changed else ""
            lines.append(f"  [{c.short_sha}] {scope_str}{c.title}{files_hint}")
            if c.body:
                for body_line in c.body.splitlines()[:2]:
                    body_line = body_line.strip()
                    if body_line:
                        lines.append(f"    > {body_line}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(format_instruction)
    lines.append("")
    lines.append(f"Use VERSION={version} and DATE={release_date} in the output.")
    lines.append("Output ONLY the changelog entry, no explanation.")

    return "\n".join(lines)


def generate_changelog(
    commits: list[CommitInfo],
    llm: LLMProvider,
    version: str = "Unreleased",
    release_date: str = "TBD",
    fmt: str = "keepachangelog",
) -> str:
    """Generate a CHANGELOG entry from a list of commits."""
    if not commits:
        return f"## [{version}] - {release_date}\n\nNo changes.\n"

    prompt = _build_prompt(commits, version, release_date, fmt)
    return llm.complete(prompt)
