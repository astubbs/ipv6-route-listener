# Agent / Contributor Rules

Project-specific rules for contributors and AI coding agents. Synced (and customized) from the maintainer's global `~/.claude/CLAUDE.md` so anyone working on this repo benefits from the same conventions.

If a rule below conflicts with something in the user's own global config, the project rules win for work in this repo.

## Git Safety

- **Never commit or push without explicit user approval.** Wait for confirmation each time. This is the #1 rule.
- Branch protection on `main` and on PR branches enforces required status checks (verify, Dependency Vulnerabilities, Duplicate Code Check, File Similarity Check). Don't bypass.
- When opening a stacked PR, include `depends on #N` in the description so the dependency-gating action blocks merge until the parent merges.

## Commit Discipline

- **Never commit without tests and documentation in the same pass.**
  - New code = new tests. Don't ask "shall I add tests?" - write them.
  - Any feature change = update relevant docs (README, AGENTS.md, ARCHITECTURE.md, CHANGELOG.md) in the same commit.
  - Run the full CI suite (`make verify-check`) before committing. Fix failures, don't defer them.
- Group commits logically: one feature per commit, with the change + its tests + its docs together.
- **CHANGELOG.md discipline:** add only *significant* user- or operator-visible changes to `[Unreleased]`. In every PR, compact and clean the section: merge related entries, drop vanity items (badges, internal refactors, test count bumps, formatting passes), and rewrite for usefulness to a future reader scanning for what changed. The goal is a changelog people actually read, not a commit log.

## Development Discipline

- **Skateboard first.** Build the simplest end-to-end thing that works, then improve. Before starting any feature, ask: "Is this blocking the next public milestone?" If not, flag and move on.
- **Never paper over the real problem** - make the proper fix. Don't propose workarounds the software could derive itself.
- If you build state in memory that will eventually be saved, save it as soon as it's created - don't wait for "later".

## Code Quality

- **Be DRY.** Reuse existing functions and fixtures. Refactor when patterns repeat. The CI duplicate-detection check enforces this - see `pr-quality.yml`.
- Validate user/network input. Don't let bad input cause silent failures.
- Handle errors visibly - don't swallow exceptions.
- Never weaken test assertions to make them pass; classify exceptions instead.
- Give things meaningful names that describe what they do.

## Test Discipline

- **Run the full test suite before every commit** - `make verify-check`. Cross-module breakage is caught by tests in other files.
- Search for existing fixtures (`tests/conftest.py`) before creating new ones.
- Maintain high-level coverage. Get fine-grained only on complex functions.
- Unit tests live in `tests/`; end-to-end tests with real Scapy packets live in `tests/integration/`.

## CI and Automation

- Continuous integration, code coverage, dependency review, and duplicate-code scanning are all set up - keep them green.
- The `claude-code-review.yml` workflow auto-reviews every PR. Read its comments.
- Local quality matches CI: `make verify-check` runs the same five steps GitHub does.

## Documentation

- Keep `README.md` focused on the end user.
- Keep `ARCHITECTURE.md` focused on the developer / agent - internal flow, design decisions, extension points.
- Keep `AGENTS.md` (this file) in sync with the maintainer's global `~/.claude/CLAUDE.md` per the Rule Sync directive.
- Keep `CHANGELOG.md` updated in the same pass as the change.

## Communication

- Use precise terminology consistent with the codebase (PIO, RIO, ULA, RA, RS).
- Don't use em-dash or double-dash characters. Use a single dash (-) where you would otherwise reach for an em-dash or double dash.
