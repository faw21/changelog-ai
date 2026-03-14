# changelog-ai

> Generate professional CHANGELOG entries from git history — in seconds.

```bash
changelog-ai                           # unreleased since last tag
changelog-ai --release-version v1.2.0  # label the release
changelog-ai --format github           # GitHub Releases format
changelog-ai --prepend CHANGELOG.md   # write to file
```

[![PyPI version](https://img.shields.io/pypi/v/changelog-ai.svg)](https://pypi.org/project/changelog-ai/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-49%20passing-brightgreen.svg)](https://github.com/faw21/changelog-ai)

---

## The problem

Writing a CHANGELOG is one of the most tedious tasks in software development:
> "Okay, I have 43 commits since v1.0.0... let me read each one and figure out what to say."

You already *wrote* the commits. Why are you also *writing* about them?

**`changelog-ai` reads your git history and writes the CHANGELOG for you.**

Even with messy commit messages. Even without conventional commits.

---

## Why changelog-ai?

[git-cliff](https://github.com/orhun/git-cliff) (3.2k stars) and conventional-changelog are great — if you write perfect conventional commits.

`changelog-ai` goes further:

| Feature | changelog-ai | git-cliff | conv-changelog |
|---------|--------------|-----------|----------------|
| Works with messy commits | ✅ | ❌ | ❌ |
| AI-summarized descriptions | ✅ | ❌ | ❌ |
| Groups related commits | ✅ | limited | limited |
| Keep a Changelog format | ✅ | ✅ | ✅ |
| GitHub Releases format | ✅ | ✅ | ✅ |
| Local LLM support (Ollama) | ✅ | ❌ | ❌ |
| Breaking change detection | ✅ | ✅ | ✅ |

---

## Install

```bash
pip install changelog-ai
```

Or with [pipx](https://pipx.pypa.io/) (recommended):
```bash
pipx install changelog-ai
```

---

## Quick Start

```bash
# Auto-detects provider from env (ANTHROPIC_API_KEY or OPENAI_API_KEY)
changelog-ai

# Label the release version
changelog-ai --release-version v1.2.0

# Generate for a specific range
changelog-ai --from v1.0.0 --to v1.1.0

# GitHub Releases format
changelog-ai --format github

# Write to CHANGELOG.md
changelog-ai --release-version v1.2.0 --prepend CHANGELOG.md

# Preview without writing
changelog-ai --prepend CHANGELOG.md --dry-run

# List available tags
changelog-ai --list-tags

# No API key needed
changelog-ai --provider ollama --model llama3.2
```

---

## Formats

### `--format keepachangelog` (default)
Follows [Keep a Changelog](https://keepachangelog.com) spec with Added, Changed, Fixed, Security, Breaking Changes sections.

### `--format github`
GitHub Release Notes style with "What's Changed" summary.

### `--format minimal`
Simple bullet list — great for internal changelogs.

---

## Providers

| Provider | Flag | Requires |
|----------|------|---------|
| Claude (default if key exists) | `--provider claude` | `ANTHROPIC_API_KEY` |
| OpenAI | `--provider openai` | `OPENAI_API_KEY` |
| Ollama (local, free) | `--provider ollama` | [Ollama](https://ollama.ai) running |

---

## Options

```
changelog-ai [PATH] [OPTIONS]

Ref range:
  --from REF            Start ref (tag, SHA, branch). Defaults to latest tag.
  --to REF              End ref [default: HEAD]

Release info:
  --release-version VER Version label (e.g. v1.2.0) [default: Unreleased]
  --date DATE           Release date YYYY-MM-DD [default: today]

Format:
  --format              keepachangelog | github | minimal [default: keepachangelog]

Output:
  --prepend FILE        Prepend entry to this file
  --dry-run             Preview without writing
  --raw                 Plain text output (no formatting)

Utilities:
  --list-tags           List recent tags and exit
  --show-commits        Show commits found before generating
  -V, --version         Show version
  -h, --help            Show help
```

---

## Tips

```bash
# Release workflow
changelog-ai --list-tags                                          # see last release
changelog-ai --release-version v1.3.0 --dry-run                  # preview
changelog-ai --release-version v1.3.0 --prepend CHANGELOG.md     # commit it

# GitHub Release automation
changelog-ai --format github --raw > release-notes.txt
gh release create v1.3.0 --notes-file release-notes.txt
```

---

## Related Tools

**[gitbrief](https://github.com/faw21/gitbrief)** — Pack the right files from any repo into LLM-ready context.

**[gpr](https://github.com/faw21/gpr)** — AI-powered PR descriptions and commit messages.

**[standup-ai](https://github.com/faw21/standup-ai)** — Generate daily standups from git commits.

**[critiq](https://github.com/faw21/critiq)** — AI code reviewer that runs locally before you push.

**[git-chronicle](https://github.com/faw21/chronicle)** — AI-powered git history narrator. Turns your git log into engaging stories (narrative, timeline, or detective mode).

**[prcat](https://github.com/faw21/prcat)** — AI reviewer for teammates' pull requests. Summarizes, flags risks, and suggests review comments.

```bash
# The complete AI-powered git workflow:
standup-ai --yesterday                                    # 1. morning standup
critiq                                                    # 2. AI review before committing
gpr --commit-run                                          # 3. commit with AI message
gitbrief . --changed-only --clipboard                    # 4. pack context for PR review
gpr                                                       # 5. generate PR description
prcat 42                                                  # 6. AI review of teammate's PR
changelog-ai --release-version v1.x.0 --prepend CHANGELOG.md  # 7. update changelog
```

---

## Development

```bash
git clone https://github.com/faw21/changelog-ai
cd changelog-ai
python -m venv .venv && source .venv/bin/activate
.venv/bin/pip install -e ".[dev]"
pytest tests/   # 49 tests, 87% coverage
```

---

- [difftests](https://github.com/faw21/difftests) — AI test generator from git diffs

- [critiq-action](https://github.com/faw21/critiq-action) — critiq as a GitHub Action for CI

## License

MIT
