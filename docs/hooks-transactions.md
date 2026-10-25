# Hooks and Transactions

0.4.0 installs a Cordis plugin into one DSH profile. There is no home-level
`AGENTS.md` dump and no transaction journal. `--recover` is a documented
no-op.

## Resources

| Resource | Purpose | Writer |
| --- | --- | --- |
| `profiles/<name>/node_modules/dsh-keysmith/` | Cordis plugin (assemble guard, contract, lookup, dock) | CLI copy / `dsh plugin add` |
| `profiles/<name>/package.json` `dsh.profile.bundles` | Makes the host load the plugin | CLI / postinstall |
| `profiles/<name>/cordis.patch.yml` insert | Queues `id: dsh-keysmith` | CLI / postinstall |
| `.dsh-keysmith-manifest.json` | Ownership record for uninstall | CLI only |

The plugin copy is written **before** the insert so the queued id names a
directory that already exists. Live `$DSH_HOME/AGENTS.md` and the home
`cordis.patch.yml` are left alone. `@deepseek-ai` packages are not patched.

## Install ordering

1. Resolve `$DSH_HOME` and `profiles/<name>/` (default `web`). A never-booted
   home gets a stub `package.json` / `cordis.patch.yml` / `cordis.yml`.
2. Copy `plugin/` onto `profiles/<name>/node_modules/dsh-keysmith/`.
   `--file PATH` overlays `lib/contract.md` after the copy.
3. Append `dsh-keysmith` to `dsh.profile.bundles` if missing.
4. Append a body insert (`- insert: / - id: dsh-keysmith`) if missing.
5. Publish `.dsh-keysmith-manifest.json` with `profile_plugin`,
   `profile_bundles`, `profile_insert`, and the previous manifest fingerprint.

`dsh plugin --profile web add <plugin-dir>` is the same package via pnpm.
`plugin/scripts/ensure-profile-bundle.mjs` writes bundles + insert; Hub
already queues the plugin, so the plugin's own `cordis.patch.yml` does **not**
contain an insert (double-insert trips `already queued: dsh-keysmith`).

Preview (`--dry-run`, the default without `--yes`) prints the plan and
writes nothing, including no stub profile files.

## Uninstall ordering

Gated by the manifest:

1. `rmtree` the plugin copy.
2. Drop `dsh-keysmith` from that profile's bundles list.
3. Strip the keysmith insert from that profile's `cordis.patch.yml`.
4. Archive the manifest as `.dsh-keysmith-manifest.json.uninstalled_<ts>`.

Home `AGENTS.md` is not restored because it was never written.

## Recovery

`--recover` reports empty residue and returns 0. There is no journal
directory to reconcile.

## Manifest

`.dsh-keysmith-manifest.json` (sorted keys, indent 2, trailing newline):

```json
{
  "schema_version": 1,
  "tool_version": "0.4.0",
  "deployment_id": "<timestamp-pid>",
  "created_at": "<ISO-8601 Z>",
  "profile": "web",
  "profile_plugin":  {"path": "…/node_modules/dsh-keysmith", "before": fp|null, "after": fp, "backup": null},
  "profile_bundles": {"path": "…/package.json", "before": fp|null, "after": fp, "backup": null},
  "profile_insert":  {"path": "…/cordis.patch.yml", "before": fp|null, "after": fp, "backup": null},
  "previous_manifest": {"fingerprint": fp|null, "deployment_id": "…|null"}
}
```

A fingerprint is `{sha256}`. `after` on `profile_plugin` is the sha of
`lib/index.js`.

JSON CLI envelope `dsh-keysmith/v1` still reports `state`
(`not-installed` / `active` / `drift`), `dsh_dir_exists`, and
`adapter_patch` (always `absent` — 0.4.0 does not patch the llm adapter).

## Patch-body contract

The **plugin** `cordis.patch.yml` is a plugin row only:

```yaml
- id: dsh-keysmith
  inject: [systemPrompt, tools]
  config:
    enabled: true
```

It does not replace the `system-prompt` row. A wholesale config write
clobbers `dsh-web-app` fields; the unregistered cwd interpolator throws
on 0.2.1. Identity strip and contract pin happen in `systemPrompt.assemble`,
not in YAML.

The **profile** `cordis.patch.yml` receives the body insert that actually
loads the plugin. Home-level `cordis.patch.yml` is not a 0.4.0 resource.
