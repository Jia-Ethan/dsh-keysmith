# Hooks and Transactions

Reference for the durable transaction model shared by deploy, uninstall, and
recovery. The implementation lives in `dsh-keysmith.py`; this document is the
design contract.

## Resources

A deployment owns three files inside the DSH home (`--dsh-dir`, default `~/.dsh`),
plus an optional adapter hot-fix:

| Resource | Purpose | Loader |
| --- | --- | --- |
| `AGENTS.md` | User-global instruction file loaded by `dsh-agent-instructions` for every new session | auto-discovered at `resolveDshHome()/AGENTS.md` |
| `keysmith-plugins/lookup-prepend/index.js` | Lookup delivery plugin (quiet stanza, 401 on `web_search`/`web_fetch`, organic pan `/s/` collection) | `file://` insert in `cordis.patch.yml`; path is absolute so a Mirasim per-session home still loads it |
| `cordis.patch.yml` | Home-level user patch layer applied after every bundle layer, ordered above each profile's own patch file | `dsh-app-boot` `watchUserPatches` |
| `profiles/node_modules/@deepseek-ai/dsh-llm-deepseek/lib/index.js` | Optional streaming-tool-call adapter hot-fix | only when the file exists and matches the known snippet |

The three required files are regular files. A deployment either creates them
(no prior file) or backs them up (`*.bak_<timestamp>` at the home root) and
replaces them. The plugin is written **before** the patch so the insert names
a file that already exists.

## Transaction directory

Every mutating operation (deploy, uninstall) creates a private directory
inside the DSH home before touching any resource:

```
<home>/.dsh-keysmith-transaction-<32-hex-tid>/   (mode 0700)
├── intent.json                     # immutable operation intent, written once
├── journal.json                    # canonical journal, atomically rewritten per phase
├── journal.pending.json            # write-ahead copy written before journal.json
├── snapshot-<resource>             # before-state raw bytes (absent ⇒ resource was absent)
├── manifest-intent.json            # fingerprint of the manifest this op will publish
└── manifest-intent.pending.json
```

The pending/canonical pair gives crash-safe phase transitions: the writer
flushes the pending copy, then atomically replaces the canonical journal. A
reconciler prefers the pending copy only when it parses and the canonical one
does not.

## Phases

Deploy and uninstall share the phase vocabulary (resource names differ):

```
initializing → prepared → <first-resource>-intent → <second-resource>-intent
             → final-sweep → committed
             ↘ recovering → recovered        (during --recover)
```

`initializing` exists on disk only as the journal's initial content; by the
time the directory is visible the phase is at least `prepared`. A journal in
any phase other than `committed`/`recovered` is residue that blocks new
operations and `--status` reports it.

A `committed` deploy removes its transaction directory at the end of a
successful final sweep; the marker file
`<home>/.dsh-keysmith-cleanup-<tid>.intent.json` bridges the window between
manifest publication and journal removal (see below).

## Deploy ordering

1. Create the transaction directory with snapshots and the immutable intent.
2. Write backups for pre-existing resources (`AGENTS.md.bak_<ts>`,
   `lookup-prepend-index.js.bak_<ts>`, `cordis.patch.yml.bak_<ts>`).
3. Atomically write `AGENTS.md` (temp file + `os.replace`), phase
   `agents-md-intent` → recorded before the write.
4. Atomically write the lookup plugin, phase `lookup-plugin-intent`.
5. Atomically write `cordis.patch.yml`, phase `patch-intent`.
6. Publish the manifest: archive the previous manifest
   (`.dsh-keysmith-manifest.json.uninstalled_<ts>` is the uninstall archive;
   deploys keep the prior manifest fingerprint inside `previous_manifest`),
   then atomically write `.dsh-keysmith-manifest.json`.
7. Write the cleanup marker, verify every live fingerprint against the
   manifest (`final-sweep`), delete the transaction directory, then delete
   the marker.

No step auto-rolls-back. A failure anywhere after step 1 leaves the journal
for `--recover`; SIGKILL cannot run Python, so the journal is the only
reliable record.

## Uninstall ordering

The mirror of deploy, gated by the manifest:

- verify each live resource still matches the manifest `after` fingerprint
  (a drifted file is refused rather than clobbered),
- restore each resource from its backup, or delete it when the deploy created
  it (`before` fingerprint null); for the lookup plugin, empty
  `keysmith-plugins/` directories are removed after a delete,
- archive the manifest, then restore the previous manifest layer recorded in
  `previous_manifest` (layered uninstall across successive deploys).

## Recovery

`--recover` (preview by default, `--yes` to act) scans the home for
transaction directories and cleanup markers:

- A live transaction directory is recovered from its journal: preflight that
  each resource is in its recorded `before` state, the expected `after`
  state, or already absent; then reverse-restore (manifest first, then
  resources) from the snapshots.
- An orphaned cleanup marker (transaction directory gone, marker left) is
  resolved by deleting the marker — the sweep already succeeded.
- More than one transaction id at once is refused; recover exactly one
  operation at a time.

## Manifest

`.dsh-keysmith-manifest.json` (sorted keys, indent 2, trailing newline) has
strictly these top-level keys:

```json
{
  "schema_version": 1,
  "tool_version": "0.1.0",
  "deployment_id": "<32-hex transaction id>",
  "created_at": "<ISO-8601 Z>",
  "agents_md":        {"path": "…", "before": fp|null, "after": fp, "backup": "…|null"},
  "lookup_plugin":    {"path": "keysmith-plugins/lookup-prepend/index.js", "before": fp|null, "after": fp, "backup": "…|null"},
  "cordis_patch":     {"path": "…", "before": fp|null, "after": fp, "backup": "…|null"},
  "previous_manifest": {"fingerprint": fp|null, "backup": null}
}
```

A fingerprint is `{size, mtime_ns, sha256}` (portable: no absolute paths).
`before`/`backup` nullness must agree; `after` is never null.

## Patch-body contract

The deployed `cordis.patch.yml` is a top-level YAML array: an id-targeted
patch against the `dsh-base` `system-prompt` row, restated web-preset
persona rows when the dump contains them, and an absolute-path `insert`
of the lookup plugin:

```yaml
- id: system-prompt
  name: '@deepseek-ai/dsh-system-prompt'
  config:
    includeHarnessIdentity: false
    includeRuntimeContext: true
    persona: ''
```

A patch replaces the targeted row's whole `config` (no deep merge), so the
body restates every field of the base row it intends to keep. The home-level
patch file outranks each profile's own patch layer and applies to every
profile booted from this home.
