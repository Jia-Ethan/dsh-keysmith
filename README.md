# dsh-keysmith

Versioned DeepSeek Harness home deploy: `AGENTS.md`, `cordis.patch.yml`, and the required local-execution plugin. MIT. Standard library only.

```sh
python3 dsh-keysmith.py --dsh-dir /tmp/dsh-home/.dsh --dry-run
python3 -m pytest -q tests
```

Do not run `--yes` against a live `~/.dsh` that already holds a Switch pack `AGENTS.md`. Preview on a throwaway home. Plugin JS is embedded in the CLI and must stay byte-identical to `plugins/lookup-prepend/index.js`.

0.3.0 puts the delivery contract in `personaPrefix` (system prompt). The plugin adds an always-on local-execution context, a quiet lookup table stanza, and `401 Unauthorized` on native `web_search` / `web_fetch` during lookup.

## Docs

- [CHANGELOG.md](CHANGELOG.md) — 0.3.0
- [docs/refusal-reduction.md](docs/refusal-reduction.md) — refusal findings and the plugin
- [docs/hooks-transactions.md](docs/hooks-transactions.md) — journal / recover
- [CONTRIBUTING.md](CONTRIBUTING.md) — embed identity and live-home red line
