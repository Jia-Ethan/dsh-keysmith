# Contributing

## Development invariants

- `dsh-keysmith.py` stays a single file with **zero runtime dependencies**
  (standard library only). Quality tooling (pytest, ruff, coverage) lives in
  `requirements-quality.txt` and is never imported by the CLI.
- The bundled `examples/dsh-unrestricted.md` stays the prompt-bank source;
  `tests/test_cli.py` enforces byte identity with the CLI constant.
- `plugin/lib/contract.md` is the system-level delivery contract. The CLI
  constant `DELIVERY_CONTRACT` must stay byte-identical to that file.
- `plugin/lib/lookup.js` is the lookup route. The CLI constant
  `LOOKUP_PLUGIN_JS` must stay byte-identical to that file.
- `VERSION` must equal `__version__` in the CLI and `plugin/package.json`.
- Deployment copies `plugin/` into
  `profiles/<name>/node_modules/dsh-keysmith`, appends `dsh-keysmith` to
  that profile's `dsh.profile.bundles`, and writes a body insert in the
  profile `cordis.patch.yml`. It does not write `AGENTS.md`, the home
  `cordis.patch.yml`, or `@deepseek-ai` packages.
- A live `~/.dsh` that already holds a Switch pack `AGENTS.md` is a valid
  install target for the **profile plugin** only. Never dump over that
  `AGENTS.md`. Isolated `web` first; live `profiles/web` only when the
  operator asks.
- Do not patch host `node_modules`. Do not auto-restart DSH.

## Workflow

```sh
python3 -m pytest -p no:cacheprovider -q tests
node tests/plugin/test_identity.mjs
node tests/plugin/test_assemble_guard.mjs
node tests/plugin/test_ensure_bundle.mjs
node --check plugin/lib/index.js plugin/lib/identity.js plugin/lib/lookup.js plugin/client.js
python3 -m ruff check dsh-keysmith.py scripts tests
python3 dsh-keysmith.py --dsh-dir <tmp>/.dsh --dry-run --lang en
```

- Preview-first: any write operation is exercised through its dry-run before
  `--yes` in both tests and manual verification.
- Releases are cut by tagging `vX.Y.Z` after the blocking tests pass.
- A PR changing `VERSION` must update `CHANGELOG.md` in the same commit.
