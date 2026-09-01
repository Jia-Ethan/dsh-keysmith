# Security Policy

## Reporting a vulnerability

Use GitHub **private vulnerability reporting** on this repository. Include:

- the `--version` output and the commit you run,
- platform and Python version,
- a minimal reproduction (commands plus the `--dry-run` output),
- the impact you see.

Do not open a public issue for security reports.

## Scope

`dsh-keysmith` modifies exactly two files inside the DeepSeek Harness home
(`~/.dsh/AGENTS.md` and `~/.dsh/cordis.patch.yml`) plus its own ownership
manifest, transaction journals, backups, and cleanup markers — all inside that
same home directory. It does not patch binaries, intercept network traffic,
store credentials, or touch the DSH installation under the npm cache.

Changing `~/.dsh/AGENTS.md` and the home patch layer changes **global behavior
for every future DSH session** under that home — it is not a per-project
switch. The deployed prompt governs the agent the same way any
user-authored `AGENTS.md` would.

## Supported versions

Only the latest tagged Release is supported. Build candidates and the
floating `main` branch are development states.
