# dsh-keysmith

DeepSeek Harness Cordis plugin: assemble-time identity strip, system-level
delivery contract, lookup route, dock badge. MIT.

The runtime is `plugin/`. The Python CLI is a preview-first installer that
copies that package into one DSH profile (default `web`). It does not dump
`AGENTS.md` and does not patch `@deepseek-ai` node_modules.

```sh
python3 dsh-keysmith.py --dsh-dir /tmp/dsh-home/.dsh --dry-run --lang en
python3 dsh-keysmith.py --dsh-dir /tmp/dsh-home/.dsh --yes --profile web
python3 -m pytest -q tests
node tests/plugin/test_identity.mjs
node tests/plugin/test_assemble_guard.mjs
```

Equivalent official channel (same package):

```sh
dsh plugin --profile web add /path/to/dsh-keysmith/plugin
```

Fully quit and reopen that host after install. New sessions pick up the
assemble guard. Live `~/.dsh/AGENTS.md` (Switch pack) is left alone.

v1 does not write host `node_modules` and does not restart DSH.

## Docs

- [CHANGELOG.md](CHANGELOG.md) — 0.4.0
- [docs/refusal-reduction.md](docs/refusal-reduction.md) — why assemble beats personaPrefix
- [CONTRIBUTING.md](CONTRIBUTING.md)
