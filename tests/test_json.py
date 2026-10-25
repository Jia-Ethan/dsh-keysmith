"""JSON contract: preview/execute/error paths for deploy, status, uninstall, recover."""

from __future__ import annotations

import json

from conftest import run_cli


def load_json(result):
    assert result.stdout.strip().startswith("{"), result.stdout
    payload = json.loads(result.stdout)
    assert payload["schema"] == "dsh-keysmith/v1"
    return payload


def test_json_status_not_installed(dsh_home):
    result = run_cli(["--dsh-dir", str(dsh_home), "--status", "--json"])
    payload = load_json(result)
    assert result.returncode == 0
    assert payload["operation"] == "status"
    assert payload["mode"] == "preview"
    assert payload["ok"] is True
    assert payload["ready"] is True
    assert payload["manifest"] is None
    assert payload["adapter_patch"]["state"] == "absent"
    assert payload["error"] is None
    assert payload["state"] == "not-installed"


def test_json_deploy_preview_does_not_write(dsh_home):
    result = run_cli(["--dsh-dir", str(dsh_home), "--json", "--lang", "en"])
    payload = load_json(result)
    assert result.returncode == 0
    assert payload["operation"] == "deploy"
    assert payload["mode"] == "preview"
    assert payload["ok"] is True
    assert payload["actions"]
    assert (dsh_home / ".dsh-keysmith-manifest.json").exists() is False
    assert (dsh_home / "profiles" / "web" / "node_modules" / "dsh-keysmith").exists() is False
    assert any(item.get("detail") == "profile_plugin" for item in payload["actions"])


def test_json_deploy_execute_and_status(dsh_home):
    preview = load_json(run_cli(["--dsh-dir", str(dsh_home), "--json"]))
    result = run_cli(["--dsh-dir", str(dsh_home), "--yes", "--json"])
    payload = load_json(result)
    assert result.returncode == 0
    assert payload["mode"] == "execute"
    assert payload["ok"] is True
    assert payload["deployment_id"]
    assert (dsh_home / "profiles" / "web" / "node_modules" / "dsh-keysmith").is_dir()
    status = load_json(run_cli(["--dsh-dir", str(dsh_home), "--status", "--json"]))
    assert status["ready"] is True
    assert status["state"] == "active"
    assert status["manifest"]["deployment_id"] == payload["deployment_id"]
    assert preview["mode"] == "preview"


def test_json_uninstall_preview_and_execute(dsh_home):
    assert run_cli(["--dsh-dir", str(dsh_home), "--yes"]).returncode == 0
    preview = load_json(run_cli(["--dsh-dir", str(dsh_home), "--uninstall", "--json"]))
    assert preview["mode"] == "preview"
    assert preview["ok"] is True
    assert (dsh_home / ".dsh-keysmith-manifest.json").exists()
    executed = load_json(run_cli(["--dsh-dir", str(dsh_home), "--uninstall", "--yes", "--json"]))
    assert executed["mode"] == "execute"
    assert executed["ok"] is True
    assert not (dsh_home / ".dsh-keysmith-manifest.json").exists()
    assert not (dsh_home / "profiles" / "web" / "node_modules" / "dsh-keysmith").exists()


def test_json_recover_preview_no_residue(dsh_home):
    result = run_cli(["--dsh-dir", str(dsh_home), "--recover", "--json"])
    payload = load_json(result)
    assert result.returncode == 0
    assert payload["operation"] == "recover"
    assert payload["ok"] is True
    assert payload["residue"] == []


def test_json_missing_file_error(dsh_home):
    result = run_cli(
        ["--dsh-dir", str(dsh_home), "--file", str(dsh_home / "nope.md"), "--json"]
    )
    payload = load_json(result)
    assert result.returncode == 2
    assert payload["ok"] is False
    assert payload["error"]
    assert "nope.md" in payload["error"]


def test_json_missing_dir_error(tmp_path):
    result = run_cli(["--dsh-dir", str(tmp_path / "absent"), "--yes", "--json"])
    payload = load_json(result)
    assert result.returncode == 2
    assert payload["ok"] is False
    assert payload["operation"] == "deploy"


def test_json_status_yes_rejected(tmp_path):
    result = run_cli(["--status", "--yes", "--json", "--dsh-dir", str(tmp_path / ".dsh")])
    payload = load_json(result)
    assert result.returncode == 2
    assert payload["ok"] is False
    assert payload["operation"] == "status"
    assert "--yes" in payload["error"]


def test_json_usage_error_not_bare_text(tmp_path):
    result = run_cli(["--status", "--uninstall", "--json", "--dsh-dir", str(tmp_path)])
    payload = load_json(result)
    assert result.returncode == 2
    assert payload["ok"] is False
    assert payload["schema"] == "dsh-keysmith/v1"
    assert "usage:" not in result.stdout.lower()


def test_json_keys_are_language_neutral(dsh_home):
    result = run_cli(["--dsh-dir", str(dsh_home), "--status", "--json", "--lang", "zh-CN"])
    payload = load_json(result)
    assert payload["adapter_patch"]["state"] == "absent"
    joined = json.dumps(payload, ensure_ascii=False)
    assert "未修补" not in joined
    assert "就绪判定" not in joined


def test_text_path_unchanged_without_json(dsh_home):
    result = run_cli(["--dsh-dir", str(dsh_home), "--lang", "en"])
    assert result.returncode == 0
    assert result.stdout.strip().startswith("{") is False
    assert "Dry-run" in result.stdout


def test_json_payload_carries_version(dsh_home):
    payload = load_json(run_cli(["--dsh-dir", str(dsh_home), "--status", "--json"]))
    assert payload["version"] == "0.4.0"


def test_json_status_reports_missing_dir_distinctly(tmp_path):
    missing = tmp_path / "absent"
    payload = load_json(run_cli(["--dsh-dir", str(missing), "--status", "--json"]))
    assert payload["dsh_dir_exists"] is False
    assert payload["state"] == "not-installed"

    (tmp_path / "present").mkdir()
    payload = load_json(run_cli(["--dsh-dir", str(tmp_path / "present"), "--status", "--json"]))
    assert payload["dsh_dir_exists"] is True


def test_json_status_not_installed_state(dsh_home):
    payload = load_json(run_cli(["--dsh-dir", str(dsh_home), "--status", "--json"]))
    assert payload["state"] == "not-installed"
    assert payload["drift"] == []


def test_json_status_active_after_deploy(dsh_home):
    run_cli(["--dsh-dir", str(dsh_home), "--json", "--yes"])
    payload = load_json(run_cli(["--dsh-dir", str(dsh_home), "--status", "--json"]))
    assert payload["state"] == "active"
    assert payload["ok"] is True
    assert payload["drift"] == []


def test_json_status_reports_drift_after_bundle_edit(dsh_home):
    run_cli(["--dsh-dir", str(dsh_home), "--json", "--yes"])
    pkg_path = dsh_home / "profiles" / "web" / "package.json"
    pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
    pkg["dsh"]["profile"]["bundles"] = [
        item for item in pkg["dsh"]["profile"]["bundles"] if item != "dsh-keysmith"
    ]
    pkg_path.write_text(json.dumps(pkg, indent=2) + "\n", encoding="utf-8")
    payload = load_json(run_cli(["--dsh-dir", str(dsh_home), "--status", "--json"]))
    assert payload["state"] == "drift"
    assert payload["ok"] is True
    assert any("profile_bundles" in note for note in payload["drift"])
