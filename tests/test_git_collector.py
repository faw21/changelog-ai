"""Tests for git_collector module."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from changelog_ai.git_collector import (
    CommitInfo,
    get_commits_between,
    get_tags,
    get_latest_tag,
    _parse_commit_type,
)


class TestParseCommitType:
    def test_conventional_feat(self):
        ctype, scope, breaking = _parse_commit_type("feat: add dark mode")
        assert ctype == "feat"
        assert scope == ""
        assert breaking is False

    def test_conventional_fix_with_scope(self):
        ctype, scope, breaking = _parse_commit_type("fix(auth): handle null token")
        assert ctype == "fix"
        assert scope == "auth"
        assert breaking is False

    def test_conventional_breaking_bang(self):
        ctype, scope, breaking = _parse_commit_type("feat!: remove deprecated API")
        assert ctype == "feat"
        assert breaking is True

    def test_conventional_breaking_footer(self):
        ctype, scope, breaking = _parse_commit_type(
            "feat: new auth\n\nBREAKING CHANGE: old tokens are invalid"
        )
        assert ctype == "feat"
        assert breaking is True

    def test_non_conventional_feat_heuristic(self):
        ctype, _, _ = _parse_commit_type("add user profile page")
        assert ctype == "feat"

    def test_non_conventional_fix_heuristic(self):
        ctype, _, _ = _parse_commit_type("fix null pointer in login")
        assert ctype == "fix"

    def test_non_conventional_fallback(self):
        ctype, _, _ = _parse_commit_type("update dependency versions")
        assert ctype == "other"

    def test_perf_heuristic(self):
        ctype, _, _ = _parse_commit_type("optimize database queries")
        assert ctype == "perf"

    def test_docs_heuristic(self):
        ctype, _, _ = _parse_commit_type("docs: update README")
        assert ctype == "docs"


class TestGetCommitsBetween:
    def _make_repo(self, tmp_path: Path) -> Path:
        subprocess.run(["git", "init", "-b", "main", str(tmp_path)], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Tester"], cwd=tmp_path, check=True, capture_output=True)
        return tmp_path

    def _commit(self, repo_path: Path, message: str, filename: str = "f.txt") -> None:
        (repo_path / filename).write_text(message)
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", message], cwd=repo_path, check=True, capture_output=True)

    def _tag(self, repo_path: Path, tag: str) -> None:
        subprocess.run(["git", "tag", tag], cwd=repo_path, check=True, capture_output=True)

    def test_empty_repo_returns_empty(self, tmp_path):
        self._make_repo(tmp_path)
        result = get_commits_between(str(tmp_path))
        assert result == []

    def test_all_commits_with_no_tags(self, tmp_path):
        self._make_repo(tmp_path)
        self._commit(tmp_path, "feat: first feature")
        self._commit(tmp_path, "fix: first fix")
        result = get_commits_between(str(tmp_path))
        assert len(result) == 2

    def test_only_unreleased_commits_returned(self, tmp_path):
        self._make_repo(tmp_path)
        self._commit(tmp_path, "feat: v1 feature", "a.txt")
        self._tag(tmp_path, "v1.0.0")
        self._commit(tmp_path, "fix: post-release fix", "b.txt")
        self._commit(tmp_path, "feat: new feature", "c.txt")
        result = get_commits_between(str(tmp_path))
        assert len(result) == 2
        titles = [c.title for c in result]
        assert "fix: post-release fix" in titles
        assert "feat: new feature" in titles

    def test_explicit_from_ref(self, tmp_path):
        self._make_repo(tmp_path)
        self._commit(tmp_path, "feat: v1 feature", "a.txt")
        self._tag(tmp_path, "v1.0.0")
        self._commit(tmp_path, "fix: post-release fix", "b.txt")
        result = get_commits_between(str(tmp_path), from_ref="v1.0.0")
        assert len(result) == 1
        assert result[0].title == "fix: post-release fix"

    def test_commit_type_parsed(self, tmp_path):
        self._make_repo(tmp_path)
        self._commit(tmp_path, "feat(ui): add dark mode")
        result = get_commits_between(str(tmp_path))
        assert result[0].commit_type == "feat"
        assert result[0].scope == "ui"

    def test_breaking_change_detected(self, tmp_path):
        self._make_repo(tmp_path)
        self._commit(tmp_path, "feat!: remove old API endpoint")
        result = get_commits_between(str(tmp_path))
        assert result[0].breaking is True

    def test_invalid_from_ref_returns_empty(self, tmp_path):
        self._make_repo(tmp_path)
        self._commit(tmp_path, "feat: something")
        result = get_commits_between(str(tmp_path), from_ref="nonexistent-tag")
        assert result == []

    def test_files_changed_populated(self, tmp_path):
        self._make_repo(tmp_path)
        self._commit(tmp_path, "feat: test", "myfile.txt")
        result = get_commits_between(str(tmp_path))
        assert "myfile.txt" in result[0].files_changed


class TestGetTags:
    def _make_repo_with_tags(self, tmp_path: Path) -> Path:
        subprocess.run(["git", "init", "-b", "main", str(tmp_path)], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "T"], cwd=tmp_path, check=True, capture_output=True)
        (tmp_path / "a.txt").write_text("v1")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "tag", "v1.0.0"], cwd=tmp_path, check=True, capture_output=True)
        return tmp_path

    def test_returns_tags(self, tmp_path):
        self._make_repo_with_tags(tmp_path)
        tags = get_tags(str(tmp_path))
        assert len(tags) == 1
        assert tags[0][0] == "v1.0.0"

    def test_empty_on_no_tags(self, tmp_path):
        subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
        tags = get_tags(str(tmp_path))
        assert tags == []
