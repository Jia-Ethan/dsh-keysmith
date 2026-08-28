# dsh-keysmith GUI

Tauri 2 + React 19 + Tailwind 4 客户端，视觉与结构对齐 Codex Keysmith（浅色 clay / 深色 tech blue）。

- CLI：`dsh-keysmith.py`（flag 式）。所有调用带 `--json`，契约 `dsh-keysmith/v1`。
- 视图：Dashboard = `--status --json`（含 adapter patch 状态）；Deploy = 预览（无 `--yes`）/ 执行（`--yes`）；Manage = `--uninstall` / `--recover`。无 Scenarios。
- Sidecar：`scripts/build-sidecar.mjs` 产出 `dsh-keysmith-cli-<triple>`，烟雾测试 `--version` 与 `--status --json`。
- identifier：`com.jia-ethan.dsh-keysmith-gui`
- 版本：`0.1.0-beta.1`
