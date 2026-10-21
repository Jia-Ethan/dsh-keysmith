# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] — 2026-10-21

### Changed

- The delivery contract now deploys into the `system-prompt` row's
  `personaPrefix`, not only into `AGENTS.md`. DSH injects the user-global
  `AGENTS.md` as a user-role block *after* the request and introduces it as
  guidance that "does not override system, developer, or direct user
  instructions"; the same text in `personaPrefix` is part of the system prompt
  and precedes the request. This is the structural fix for the refusal-rate
  gap between DSH Keysmith and the Codex/OpenCode packs.
- The contract itself is now procedural: newest request is the sole task,
  first line is the deliverable, named elements are required fields, boundary
  words map to placeholders and routing rather than to scope reduction, and a
  final delivery check closes the system prompt. The stale `persona` key is
  removed — dsh's schema reads `personaPrefix`/`personaSuffix`, so the old key
  was a no-op.
- `_merge_config_lines` restates the composed row's `personaSuffix` (the
  working-directory line) while replacing `personaPrefix` with the contract.

## [0.2.2] — 2026-10-20

### Fixed

- The generated `cordis.patch.yml` no longer deletes fields another layer adds
  to the same row. A patch replaces the targeted entry's `config` object
  wholesale — the include loader assigns `target[key] = value`, there is no deep
  merge — so restating only the three fields this tool decides on silently
  dropped everything else. `@deepseek-ai/dsh-web-app` adds `personaPrefix` and
  `personaSuffix` to the `system-prompt` row, and the home layer outranks the
  profile layer, so the loss hit every session: the "powered by the {{model}}
  model" line and the working-directory line disappeared under a stock dsh web
  boot, and under Mirasim, which mounts this home into each of its own session
  homes, it hit every Mirasim session too.

  The body is now read back from `dsh --profile web --dump-default-config` and
  restated verbatim, with the three fields forced on top. `--dump-default-config`
  is deliberate: it stops at the bundle layers, so it never reads a patch this
  tool wrote earlier and cannot fold its own output back in. Only the
  `system-prompt` block's text is spliced, not parsed as YAML, so nesting,
  quoting and `!!js` expressions survive.

  When that read is impossible the deploy still happens, on the previous body,
  and says so: `dsh` off `PATH`, an unusable dump, or no `profiles/web` on disk.
  The last one is not laziness — composing a missing profile makes dsh create
  it, and a deploy is not a reason to conjure a profile the user never had. A
  preview never runs the dump at all: `--dump-default-config` rewrites the
  profile root on its way through, and a dry run that writes nothing stays that
  way.

## [0.2.1] — 2026-10-20

### Fixed

- Redeploy no longer adopts its own output as the user's original. A second
  deploy recorded the prompt it had written as the backup, so `--uninstall`
  restored that prompt instead of the `AGENTS.md` it had replaced; when there
  was no pre-existing file, uninstall left the prompt behind as though the user
  had authored it. Redeploying over a file that is still byte-identical to what
  was written now keeps the previous manifest's answer — its backup if it had
  one, no backup if it did not. Content the user edited in between is adopted as
  their original, which is what they would expect. Both the text and `--json`
  deploy paths had the bug and share the fix.

## [0.2.0] — 2026-10-20

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
- `--json` machine-readable contract (`dsh-keysmith/v1`) for deploy,
  `--status`, `--uninstall`, and `--recover`. JSON payloads are
  language-neutral. Argument errors also emit JSON when `--json` is set.
- Every JSON payload now carries `version`, so a consumer can reject an
  adapter that is older than the contract it expects without parsing
  `--version` text.
- `--status --json` reports `dsh_dir_exists`, separating "dsh has never run
  here" from "dsh home exists but nothing is deployed".
- `--status --json` reports `state` — `not-installed` / `active` / `drift` /
  `recovery-required` — plus a `drift` list naming each managed file that
  changed or vanished since deploy. Previously status said `ok: true` for a
  hand-edited `AGENTS.md` while `--uninstall` refused it; both now share one
  comparison (`_drifted_resources`), so they cannot disagree.

### Fixed

- The recover journal now records absolute resource paths. It stored only the
  file name, so an interrupted deploy would have restored the adapter patch
  into `$DSH_HOME/index.js` instead of
  `profiles/node_modules/@deepseek-ai/dsh-llm-deepseek/lib/index.js`. Journals
  written by earlier builds still resolve relative to `$DSH_HOME`.

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
