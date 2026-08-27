# Contributing

## Development invariants

- `dsh-keysmith.py` stays a single file with **zero runtime dependencies**
  (standard library only). Quality tooling (pytest, ruff, coverage) lives in
  `requirements-quality.txt` and is never imported by the CLI.
- The embedded `BUILTIN_DSH_UNRESTRICTED_MD` must stay byte-identical to
  `examples/dsh-unrestricted.md`; `tests/test_cli.py` enforces it.
- `VERSION` (no trailing newline variance beyond a single `\n`) must equal
  `__version__` in the CLI; enforced by test.
- Deployment writes exactly two files under the DSH home (`AGENTS.md`,
  `cordis.patch.yml`) plus keysmith-owned manifest/journal/backup/marker
  files. Anything else is out of scope — see SECURITY.md.
- A patch entry restates the complete targeted row config; update the patch
  body whenever the upstream `dsh-base` row gains fields we want to keep.

## Workflow

```sh
python3 -m pytest -p no:cacheprovider -q tests   # unit + recovery + release tests
python3 -m ruff check dsh-keysmith.py scripts tests
python3 dsh-keysmith.py --dsh-dir <tmp>/.dsh --dry-run --lang en
```

- Preview-first: any write operation is exercised through its dry-run before
  `--yes` in both tests and manual verification.
- Releases are cut by tagging `vX.Y.Z` (strict semver) after the blocking
  tests pass; `scripts/build_release.py` refuses a dirty or shallow tree and
  verifies the tag points at HEAD.
- A PR changing `VERSION` must update `CHANGELOG.md` and
  `docs/releases/<tag>.md` in the same commit.
