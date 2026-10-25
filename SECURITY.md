# Security Policy

## Reporting a vulnerability

Use GitHub **private vulnerability reporting** on this repository. Include:

- the `--version` output and the commit you run,
- platform and Python version,
- a minimal reproduction (commands plus the `--dry-run` output),
- the impact you see.

Do not open a public issue for security reports.

## Scope

`dsh-keysmith` 0.4.0 installs a Cordis plugin into **one profile** under the
DeepSeek Harness home (`profiles/<name>/node_modules/dsh-keysmith`, that
profile's `package.json` bundles list, and that profile's `cordis.patch.yml`
insert), plus a home-level ownership manifest. It does not write `AGENTS.md`,
does not rewrite the home `cordis.patch.yml`, and does not patch
`@deepseek-ai` packages. It does not intercept network traffic or store
credentials.

Installing the plugin changes **behavior for new sessions of that profile**.
It is not a per-project switch. Fully quit and reopen the host after install.

## Supported versions

Only the latest tagged Release is supported. Build candidates and the
floating `main` branch are development states.
