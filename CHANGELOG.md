# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — Unreleased

### Added

- Single-file stdlib-only CLI `dsh-keysmith.py` deploying a Markdown
  instruction as the DeepSeek Harness user-global `~/.dsh/AGENTS.md`
  (`dsh-agent-instructions` auto-loads it for every new session).
- Home-level `~/.dsh/cordis.patch.yml` deployment that patches the
  `system-prompt` entry: suppresses the fixed harness identity and sets the
  deployment persona, leaving the base bundle untouched.
- Preview-first workflow: `--dry-run` (default), explicit `--yes` gate,
  `--status`, `--uninstall`, and `--recover` operations.
- Durable transaction journals (deploy and uninstall) with immutable intent,
  write-ahead pending journals, before-state snapshots, and cleanup markers so
  an interruption such as SIGKILL can be inspected and restored through
  explicit `--recover`.
- Layered ownership manifest `.dsh-keysmith-manifest.json` enabling layered
  uninstall across successive deployments.
- Bundled `dsh-unrestricted` prompt (byte-identical to
  `examples/dsh-unrestricted.md`).
- Bilingual CLI output (`zh-CN` default, `en`), `--lang auto|zh-CN|en`.
- pytest suite (CLI surface, deploy/uninstall, recovery, release build) and
  offline prompt-bank contract cases.
- Deterministic release builder `scripts/build_release.py` producing
  zip/tar.gz/standalone `.py` plus `SHA256SUMS`.

### Known limitations

- DeepSeek Harness is in developer preview with announced compatibility
  breaks; the patch targets the `system-prompt` entry id of
  `@deepseek-ai/dsh-base` as of `@deepseek-ai/dsh` `0.1.1-rc.2`.
- A user patch replaces the targeted row's whole config (no deep merge); a
  future `dsh-base` config addition to that row will not be restated by the
  deployed patch and requires a keysmith upgrade.

[Unreleased]: https://github.com/Jia-Ethan/dsh-keysmith/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Jia-Ethan/dsh-keysmith/releases/tag/v0.1.0
