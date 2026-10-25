"""Install / uninstall the Cordis plugin into a profile."""

from __future__ import annotations

import json

from conftest import PLUGIN_SRC, run_cli

MANIFEST = ".dsh-keysmith-manifest.json"


def _web(home):
    return home / "profiles" / "web"


def test_deploy_creates_plugin_and_manifest(dsh_home):
    result = run_cli(["--dsh-dir", str(dsh_home), "--yes", "--lang", "en"])
    assert result.returncode == 0, result.stdout + result.stderr
    dest = _web(dsh_home) / "node_modules" / "dsh-keysmith"
    pkg = json.loads((_web(dsh_home) / "package.json").read_text(encoding="utf-8"))
    patch = (_web(dsh_home) / "cordis.patch.yml").read_text(encoding="utf-8")
    manifest = json.loads((dsh_home / MANIFEST).read_text(encoding="utf-8"))
    assert dest.is_dir()
    assert (dest / "lib" / "index.js").is_file()
    assert (dest / "lib" / "contract.md").read_text(encoding="utf-8") == (
        PLUGIN_SRC / "lib" / "contract.md"
    ).read_text(encoding="utf-8")
    assert "dsh-keysmith" in pkg["dsh"]["profile"]["bundles"]
    assert "id: dsh-keysmith" in patch
    assert (dsh_home / "AGENTS.md").exists() is False
    assert (dsh_home / "cordis.patch.yml").exists() is False
    assert manifest["tool_version"] == "0.4.0"
    assert manifest["profile"] == "web"
    assert manifest["profile_plugin"]["after"]["sha256"]


def test_status_after_deploy_is_ready(dsh_home):
    assert run_cli(["--dsh-dir", str(dsh_home), "--yes", "--lang", "en"]).returncode == 0
    result = run_cli(["--dsh-dir", str(dsh_home), "--status", "--lang", "en"])
    assert result.returncode == 0
    assert "ready" in result.stdout.lower() or "就绪" in result.stdout


def test_uninstall_deletes_plugin(dsh_home):
    assert run_cli(["--dsh-dir", str(dsh_home), "--yes", "--lang", "en"]).returncode == 0
    result = run_cli(["--dsh-dir", str(dsh_home), "--uninstall", "--yes", "--lang", "en"])
    assert result.returncode == 0
    assert not (_web(dsh_home) / "node_modules" / "dsh-keysmith").exists()
    pkg = json.loads((_web(dsh_home) / "package.json").read_text(encoding="utf-8"))
    assert "dsh-keysmith" not in pkg["dsh"]["profile"]["bundles"]
    patch = (_web(dsh_home) / "cordis.patch.yml").read_text(encoding="utf-8")
    assert "id: dsh-keysmith" not in patch
    assert not (dsh_home / MANIFEST).exists()
    assert list(dsh_home.glob(f"{MANIFEST}.uninstalled_*"))


def test_uninstall_without_manifest_fails(dsh_home):
    result = run_cli(["--dsh-dir", str(dsh_home), "--uninstall", "--yes", "--lang", "en"])
    assert result.returncode == 1


def test_layered_redeploy_records_previous(dsh_home):
    assert run_cli(["--dsh-dir", str(dsh_home), "--yes", "--lang", "en"]).returncode == 0
    first = json.loads((dsh_home / MANIFEST).read_text(encoding="utf-8"))
    assert first["previous_manifest"]["fingerprint"] is None
    assert run_cli(["--dsh-dir", str(dsh_home), "--yes", "--lang", "en"]).returncode == 0
    second = json.loads((dsh_home / MANIFEST).read_text(encoding="utf-8"))
    assert second["previous_manifest"]["fingerprint"] is not None
    assert second["deployment_id"] != first["deployment_id"]


def test_custom_file_overlays_contract(dsh_home, tmp_path):
    custom = tmp_path / "custom.md"
    custom.write_text("Custom contract overlay.\n", encoding="utf-8")
    result = run_cli(
        ["--dsh-dir", str(dsh_home), "--file", str(custom), "--yes", "--lang", "en"]
    )
    assert result.returncode == 0
    dest = _web(dsh_home) / "node_modules" / "dsh-keysmith" / "lib" / "contract.md"
    assert dest.read_text(encoding="utf-8") == "Custom contract overlay.\n"


def test_deployed_profile_patch_is_a_single_sequence(dsh_home):
    assert run_cli(["--dsh-dir", str(dsh_home), "--yes", "--lang", "en"]).returncode == 0
    text = (_web(dsh_home) / "cordis.patch.yml").read_text(encoding="utf-8")
    assert not any(ln.strip() == "[]" for ln in text.splitlines())
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    assert lines[0].startswith("- ")
    assert any(ln.strip() == "- insert:" for ln in lines)


def test_does_not_touch_home_agents(dsh_home):
    (dsh_home / "AGENTS.md").write_text("switch pack\n", encoding="utf-8")
    (dsh_home / "cordis.patch.yml").write_text("# live\n", encoding="utf-8")
    assert run_cli(["--dsh-dir", str(dsh_home), "--yes", "--lang", "en"]).returncode == 0
    assert (dsh_home / "AGENTS.md").read_text(encoding="utf-8") == "switch pack\n"
    assert (dsh_home / "cordis.patch.yml").read_text(encoding="utf-8") == "# live\n"
    assert run_cli(
        ["--dsh-dir", str(dsh_home), "--uninstall", "--yes", "--lang", "en"]
    ).returncode == 0
    assert (dsh_home / "AGENTS.md").read_text(encoding="utf-8") == "switch pack\n"
