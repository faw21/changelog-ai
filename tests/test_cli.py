"""Tests for CLI entry point."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from changelog_ai.cli import main
from changelog_ai.git_collector import CommitInfo


def make_commit(title: str = "feat: add feature") -> CommitInfo:
    return CommitInfo(
        sha="abc12345abcd1234",
        short_sha="abc12345",
        message=title,
        author="Dev",
        title=title,
        body="",
        commit_type="feat",
        breaking=False,
        scope="",
        files_changed=["src/app.py"],
    )


FAKE_CHANGELOG = "## [Unreleased] - 2026-03-13\n\n### Added\n- New feature\n"


class TestCLIVersion:
    def test_version_flag(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_help_flag(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "changelog" in result.output.lower()


class TestCLIListTags:
    @patch("changelog_ai.cli.get_tags", return_value=[("v1.0.0", "abc123"), ("v0.9.0", "def456")])
    @patch("changelog_ai.cli._resolve_repo", return_value="/fake/repo")
    def test_list_tags_shows_tags(self, mock_repo, mock_tags):
        runner = CliRunner()
        result = runner.invoke(main, ["--list-tags"])
        assert result.exit_code == 0
        assert "v1.0.0" in result.output
        assert "v0.9.0" in result.output

    @patch("changelog_ai.cli.get_tags", return_value=[])
    @patch("changelog_ai.cli._resolve_repo", return_value="/fake/repo")
    def test_list_tags_empty(self, mock_repo, mock_tags):
        runner = CliRunner()
        result = runner.invoke(main, ["--list-tags"])
        assert result.exit_code == 0
        assert "No tags" in result.output


class TestCLINoCommits:
    @patch("changelog_ai.cli.get_commits_between", return_value=[])
    @patch("changelog_ai.cli._resolve_repo", return_value="/fake/repo")
    def test_no_commits_shows_message(self, mock_repo, mock_commits):
        runner = CliRunner()
        result = runner.invoke(main, [])
        assert result.exit_code == 0
        assert "No commits" in result.output


class TestCLIWithCommits:
    @patch("changelog_ai.cli.create_provider")
    @patch("changelog_ai.cli.get_commits_between")
    @patch("changelog_ai.cli._resolve_repo", return_value="/fake/repo")
    def test_generates_changelog(self, mock_repo, mock_commits, mock_factory):
        mock_commits.return_value = [make_commit()]
        mock_provider = MagicMock()
        mock_provider.complete.return_value = FAKE_CHANGELOG
        mock_factory.return_value = mock_provider

        runner = CliRunner()
        result = runner.invoke(main, ["--provider", "claude"])
        assert result.exit_code == 0
        assert "Added" in result.output or "Changelog" in result.output

    @patch("changelog_ai.cli.create_provider")
    @patch("changelog_ai.cli.get_commits_between")
    @patch("changelog_ai.cli._resolve_repo", return_value="/fake/repo")
    def test_raw_flag_plain_output(self, mock_repo, mock_commits, mock_factory):
        mock_commits.return_value = [make_commit()]
        mock_provider = MagicMock()
        mock_provider.complete.return_value = FAKE_CHANGELOG
        mock_factory.return_value = mock_provider

        runner = CliRunner()
        result = runner.invoke(main, ["--provider", "claude", "--raw"])
        assert result.exit_code == 0
        assert result.output.strip() == FAKE_CHANGELOG.strip()

    @patch("changelog_ai.cli.create_provider")
    @patch("changelog_ai.cli.get_commits_between")
    @patch("changelog_ai.cli._resolve_repo", return_value="/fake/repo")
    def test_show_commits_flag(self, mock_repo, mock_commits, mock_factory):
        mock_commits.return_value = [make_commit("feat: my cool feature")]
        mock_provider = MagicMock()
        mock_provider.complete.return_value = FAKE_CHANGELOG
        mock_factory.return_value = mock_provider

        runner = CliRunner()
        result = runner.invoke(main, ["--provider", "claude", "--show-commits"])
        assert result.exit_code == 0
        assert "my cool feature" in result.output

    @patch("changelog_ai.cli.create_provider")
    @patch("changelog_ai.cli.get_commits_between")
    @patch("changelog_ai.cli._resolve_repo", return_value="/fake/repo")
    def test_dry_run_does_not_write_file(self, mock_repo, mock_commits, mock_factory, tmp_path):
        mock_commits.return_value = [make_commit()]
        mock_provider = MagicMock()
        mock_provider.complete.return_value = FAKE_CHANGELOG
        mock_factory.return_value = mock_provider

        changelog_file = tmp_path / "CHANGELOG.md"
        runner = CliRunner()
        result = runner.invoke(main, [
            "--provider", "claude",
            "--prepend", str(changelog_file),
            "--dry-run",
        ])
        assert result.exit_code == 0
        assert not changelog_file.exists()

    @patch("changelog_ai.cli.create_provider")
    @patch("changelog_ai.cli.get_commits_between")
    @patch("changelog_ai.cli._resolve_repo", return_value="/fake/repo")
    def test_prepend_writes_to_file(self, mock_repo, mock_commits, mock_factory, tmp_path):
        mock_commits.return_value = [make_commit()]
        mock_provider = MagicMock()
        mock_provider.complete.return_value = FAKE_CHANGELOG
        mock_factory.return_value = mock_provider

        changelog_file = tmp_path / "CHANGELOG.md"
        changelog_file.write_text("# Old Content\n")

        runner = CliRunner()
        result = runner.invoke(main, [
            "--provider", "claude",
            "--prepend", str(changelog_file),
        ])
        assert result.exit_code == 0
        content = changelog_file.read_text()
        assert FAKE_CHANGELOG.strip() in content
        assert "Old Content" in content
        # new content should come before old
        assert content.index("Added") < content.index("Old Content")

    @patch("changelog_ai.cli.create_provider")
    @patch("changelog_ai.cli.get_commits_between")
    @patch("changelog_ai.cli._resolve_repo", return_value="/fake/repo")
    def test_version_and_date_passed(self, mock_repo, mock_commits, mock_factory):
        mock_commits.return_value = [make_commit()]
        mock_provider = MagicMock()
        mock_provider.complete.return_value = FAKE_CHANGELOG
        mock_factory.return_value = mock_provider

        runner = CliRunner()
        result = runner.invoke(main, [
            "--provider", "claude",
            "--release-version", "v2.0.0",
            "--date", "2026-03-13",
        ])
        assert result.exit_code == 0

    @patch("changelog_ai.cli.create_provider")
    @patch("changelog_ai.cli.get_commits_between")
    @patch("changelog_ai.cli._resolve_repo", return_value="/fake/repo")
    def test_github_format(self, mock_repo, mock_commits, mock_factory):
        mock_commits.return_value = [make_commit()]
        mock_provider = MagicMock()
        mock_provider.complete.return_value = "## What's Changed\n- New feature\n"
        mock_factory.return_value = mock_provider

        runner = CliRunner()
        result = runner.invoke(main, ["--provider", "claude", "--format", "github"])
        assert result.exit_code == 0


class TestCLIProviderErrors:
    @patch("changelog_ai.cli.create_provider", side_effect=KeyError("ANTHROPIC_API_KEY"))
    @patch("changelog_ai.cli.get_commits_between")
    @patch("changelog_ai.cli._resolve_repo", return_value="/fake/repo")
    def test_missing_key_exits_1(self, mock_repo, mock_commits, mock_factory):
        mock_commits.return_value = [make_commit()]
        runner = CliRunner()
        result = runner.invoke(main, ["--provider", "claude"])
        assert result.exit_code == 1
