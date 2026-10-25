# dsh-keysmith — agent rules

Runtime is `plugin/`. The Python CLI is a profile installer. Next session
will go wrong if it dumps `AGENTS.md` or patches `@deepseek-ai`.

## Red lines

- Do not write `$DSH_HOME/AGENTS.md` or the home `cordis.patch.yml`.
- Do not `--yes` live `~/.dsh` unless the operator names that home.
- Do not patch `@deepseek-ai` `node_modules`. Do not auto-restart DSH.
- Do not replace the `system-prompt` row in `plugin/cordis.patch.yml`.
- Keep unregistered `{{cwd}}` out of YAML config. `{{model}}` in
  `plugin/lib/contract.md` is allowed.
- Default prompt is the engineering contract + lookup table + `[P]`,
  not 小码酱 / `[Y]`.
- Isolated `web` first. Live `profiles/web` only when asked.
- Fully quit and reopen the host after a live install.

## Layout

| Path | Role |
| --- | --- |
| `plugin/lib/identity.js` | assemble wrap, identity strip, contract pin |
| `plugin/lib/contract.md` | system payload (`DELIVERY_CONTRACT` must match) |
| `plugin/lib/lookup.js` | lookup route (`LOOKUP_PLUGIN_JS` must match) |
| `plugin/client.js` | web dock `Keysmith 已激活` |
| `plugin/scripts/ensure-profile-bundle.mjs` | bundles + body insert |
| `dsh-keysmith.py` | copies `plugin/` into one profile (default `web`) |

## Commands

```sh
python3 -m pytest -p no:cacheprovider -q tests
node tests/plugin/test_identity.mjs
node tests/plugin/test_assemble_guard.mjs
node tests/plugin/test_ensure_bundle.mjs
python3 dsh-keysmith.py --dsh-dir <tmp>/.dsh --dry-run --lang en
```

## Docs

- [README.md](README.md) — install / verify
- [docs/hooks-transactions.md](docs/hooks-transactions.md) — install resources
- [docs/refusal-reduction.md](docs/refusal-reduction.md) — why assemble
- [CONTRIBUTING.md](CONTRIBUTING.md) — invariants
