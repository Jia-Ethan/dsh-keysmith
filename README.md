# dsh-keysmith

DeepSeek Harness Cordis plugin: assemble-time identity strip, system-level
delivery contract, lookup route, dock badge. MIT.

The runtime is `plugin/`. The Python CLI is a preview-first installer that
copies that package into one DSH profile. It does not dump `AGENTS.md` and
does not patch `@deepseek-ai` node_modules.

## Which profile

| Host | Profile it boots |
| --- | --- |
| DSH Desktop (Electron app) | `profiles/desktop` only |
| `dsh web` / `dsh --profile web` | `profiles/web` |

Without `--profile` the CLI picks `desktop` when `profiles/desktop` exists
(DSH Desktop creates it on first launch), else `web`. A deployment made with
an explicit `--profile NAME` keeps that profile on later runs. An older
automatic `web` deployment shows `drift` once `profiles/desktop` appears, and
a redeploy moves it: the plugin, bundles entry and insert leave `web`; the
rest of `web` stays. Use `--profile web` to target `dsh web` on a machine that
also has DSH Desktop.

```sh
python3 dsh-keysmith.py --dsh-dir /tmp/dsh-home/.dsh --dry-run --lang en
python3 dsh-keysmith.py --dsh-dir /tmp/dsh-home/.dsh --yes            # auto
python3 dsh-keysmith.py --dsh-dir /tmp/dsh-home/.dsh --yes --profile web
python3 -m pytest -q tests
node tests/plugin/test_identity.mjs
node tests/plugin/test_assemble_guard.mjs
```

Equivalent official channel for `web` (same package; the `dsh` CLI refuses
plugin management for `desktop`, which the Electron app owns):

```sh
dsh plugin --profile web add /path/to/dsh-keysmith/plugin
```

Fully quit and reopen that host after install. Closing the DSH Desktop window
only hides it; quit from the tray (Windows) or the app menu (macOS). New sessions pick up the
assemble guard. Live `~/.dsh/AGENTS.md` (Switch pack) is left alone.

v1 does not write host `node_modules` and does not restart DSH.

## Docs

- [CHANGELOG.md](CHANGELOG.md) — 0.4.1
- [docs/hooks-transactions.md](docs/hooks-transactions.md) — install resources
- [docs/refusal-reduction.md](docs/refusal-reduction.md) — why assemble beats personaPrefix
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [SECURITY.md](SECURITY.md)
