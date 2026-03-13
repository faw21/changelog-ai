"""Tests for generator module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from changelog_ai.generator import generate_changelog, _build_prompt
from changelog_ai.git_collector import CommitInfo


def make_commit(
    title: str = "feat: add feature",
    commit_type: str = "feat",
    breaking: bool = False,
    scope: str = "",
    short_sha: str = "abc12345",
) -> CommitInfo:
    return CommitInfo(
        sha="abc12345abcd1234",
        short_sha=short_sha,
        message=title,
        author="Dev",
        title=title,
        body="",
        commit_type=commit_type,
        breaking=breaking,
        scope=scope,
        files_changed=["src/app.py"],
    )


class TestBuildPrompt:
    def test_includes_version(self):
        commits = [make_commit()]
        prompt = _build_prompt(commits, "v1.2.0", "2026-03-13", "keepachangelog")
        assert "v1.2.0" in prompt

    def test_includes_commit_titles(self):
        commits = [make_commit("feat: cool thing")]
        prompt = _build_prompt(commits, "v1.0.0", "2026-01-01", "keepachangelog")
        assert "cool thing" in prompt

    def test_breaking_section_shown(self):
        commits = [make_commit("feat!: remove old API", breaking=True)]
        prompt = _build_prompt(commits, "v2.0.0", "2026-01-01", "keepachangelog")
        assert "BREAKING" in prompt

    def test_github_format_instruction(self):
        commits = [make_commit()]
        prompt = _build_prompt(commits, "v1.0.0", "2026-01-01", "github")
        assert "GitHub" in prompt or "What's Changed" in prompt

    def test_minimal_format_instruction(self):
        commits = [make_commit()]
        prompt = _build_prompt(commits, "v1.0.0", "2026-01-01", "minimal")
        assert "bullet" in prompt.lower() or "plain list" in prompt.lower()

    def test_scope_included(self):
        commits = [make_commit("feat(auth): add OAuth", scope="auth")]
        prompt = _build_prompt(commits, "v1.0.0", "2026-01-01", "keepachangelog")
        assert "auth" in prompt


class TestGenerateChangelog:
    def test_empty_commits_returns_no_changes(self):
        mock_llm = MagicMock()
        result = generate_changelog([], mock_llm, version="v1.0.0", release_date="2026-01-01")
        assert "No changes" in result
        mock_llm.complete.assert_not_called()

    def test_calls_llm_with_prompt(self):
        mock_llm = MagicMock()
        mock_llm.complete.return_value = "## [v1.0.0] - 2026-01-01\n\n### Added\n- Cool feature"
        commits = [make_commit()]
        result = generate_changelog(commits, mock_llm, version="v1.0.0", release_date="2026-01-01")
        assert mock_llm.complete.called
        assert result == "## [v1.0.0] - 2026-01-01\n\n### Added\n- Cool feature"

    def test_uses_keepachangelog_format_by_default(self):
        mock_llm = MagicMock()
        mock_llm.complete.return_value = "changelog"
        commits = [make_commit()]
        generate_changelog(commits, mock_llm)
        prompt = mock_llm.complete.call_args[0][0]
        assert "Keep a Changelog" in prompt or "keepachangelog" in prompt.lower()

    def test_github_format_uses_different_prompt(self):
        mock_llm = MagicMock()
        mock_llm.complete.return_value = "release notes"
        commits = [make_commit()]
        generate_changelog(commits, mock_llm, fmt="github")
        prompt_kac = _build_prompt(commits, "v1.0.0", "2026-01-01", "keepachangelog")
        prompt_gh = _build_prompt(commits, "v1.0.0", "2026-01-01", "github")
        assert prompt_kac != prompt_gh
