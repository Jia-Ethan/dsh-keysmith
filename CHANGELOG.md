# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] — Unreleased

### Added

- Adapter hot-fix as a third deployment resource: `dsh-keysmith` now detects
  the `dsh-llm-deepseek` adapter under `profiles/node_modules` and patches the
  streaming-tool-call parse bug where OpenAI-compatible gateways (seen on
  lgw.gru.ai) echo `id`/`function.name` as empty strings on continuation
  chunks — the `!== void 0` guard admitted `""` and clobbered the real values,
  surfacing as `unknown tool ""` at dispatch. The patched guards are truthy
  checks that preserve the first chunk's name and id.
- Idempotent patch states: `pristine` (patch applied, backup created),
  `patched` (already fixed — manifest entry recorded, no write),
  `unknown`/`absent` (skipped with a warning; other resources deploy normally).
- Symlink-safe writes: the adapter file is resolved through the
  `profiles/node_modules` symlink to the real npx-cache file before writing,
  so `os.replace` never breaks the link.
- Uninstall restores the adapter from its backup when the patch was ours;
  a pre-existing patch (`already_patched: true`) is left untouched.
- `--status` reports the live adapter patch state.
- Bilingual messages for all adapter-related transitions, plus a restart
  hint (running dsh processes must restart to load the patched module).

### Changed

- Manifest validation now accepts the optional `adapter_patch` key (subset
  semantics instead of exact key equality); manifests without it remain valid.
- Version bumped to 0.2.0.

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
