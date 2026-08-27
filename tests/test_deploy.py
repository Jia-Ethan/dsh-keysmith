"""Deploy / uninstall / layered redeploy behavior."""

from __future__ import annotations

import json

from conftest import run_cli

MANIFEST = ".dsh-keysmith-manifest.json"


def test_deploy_creates_files_and_manifest(dsh_home):
    result = run_cli(["--dsh-dir", str(dsh_home), "--yes", "--lang", "en"])
    assert result.returncode == 0
    agents = dsh_home / "AGENTS.md"
    patch = dsh_home / "cordis.patch.yml"
    manifest = dsh_home / MANIFEST
    assert agents.is_file()
    assert patch.is_file()
    assert manifest.is_file()
    assert agents.read_text(encoding="utf-8").startswith("You are a senior engineer")
    assert "includeHarnessIdentity: false" in patch.read_text(encoding="utf-8")

    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["tool_version"] == "0.1.0"
    assert data["agents_md"]["before"] is None
    assert data["agents_md"]["backup"] is None
    assert data["agents_md"]["after"]["sha256"]
    assert data["cordis_patch"]["before"] is None
    assert set(data.keys()) == {
        "schema_version",
        "tool_version",
        "deployment_id",
        "created_at",
        "agents_md",
        "cordis_patch",
        "previous_manifest",
    }


def test_status_after_deploy_is_ready(dsh_home):
    assert run_cli(["--dsh-dir", str(dsh_home), "--yes", "--lang", "en"]).returncode == 0
    result = run_cli(["--dsh-dir", str(dsh_home), "--status", "--lang", "en"])
    assert result.returncode == 0
    assert "ready" in result.stdout


def test_deploy_backs_up_existing_files(dsh_home):
    (dsh_home / "AGENTS.md").write_text("original agents\n", encoding="utf-8")
    (dsh_home / "cordis.patch.yml").write_text("[]\n", encoding="utf-8")
    result = run_cli(["--dsh-dir", str(dsh_home), "--yes", "--lang", "en"])
    assert result.returncode == 0
    backups = sorted(p.name for p in dsh_home.glob("*.bak_*"))
    assert len(backups) == 2
    assert any(b.startswith("AGENTS.md.bak_") for b in backups)
    assert any(b.startswith("cordis.patch.yml.bak_") for b in backups)
    manifest = json.loads((dsh_home / MANIFEST).read_text(encoding="utf-8"))
    assert manifest["agents_md"]["before"]["sha256"]
    assert manifest["agents_md"]["backup"].startswith("AGENTS.md.bak_")


def test_uninstall_restores_backups(dsh_home):
    (dsh_home / "AGENTS.md").write_text("original agents\n", encoding="utf-8")
    (dsh_home / "cordis.patch.yml").write_text("[]\n", encoding="utf-8")
    assert run_cli(["--dsh-dir", str(dsh_home), "--yes", "--lang", "en"]).returncode == 0
    result = run_cli(["--dsh-dir", str(dsh_home), "--uninstall", "--yes", "--lang", "en"])
    assert result.returncode == 0
    assert (dsh_home / "AGENTS.md").read_text(encoding="utf-8") == "original agents\n"
    assert (dsh_home / "cordis.patch.yml").read_text(encoding="utf-8") == "[]\n"
    assert not (dsh_home / MANIFEST).exists()
    assert list(dsh_home.glob(f"{MANIFEST}.uninstalled_*"))


def test_uninstall_deletes_created_files(dsh_home):
    assert run_cli(["--dsh-dir", str(dsh_home), "--yes", "--lang", "en"]).returncode == 0
    assert run_cli(
        ["--dsh-dir", str(dsh_home), "--uninstall", "--yes", "--lang", "en"]
    ).returncode == 0
    assert not (dsh_home / "AGENTS.md").exists()
    assert not (dsh_home / "cordis.patch.yml").exists()
    assert not (dsh_home / MANIFEST).exists()


def test_uninstall_without_manifest_fails(dsh_home):
    result = run_cli(["--dsh-dir", str(dsh_home), "--uninstall", "--yes", "--lang", "en"])
    assert result.returncode == 1


def test_layered_redeploy_records_previous(dsh_home):
    assert run_cli(["--dsh-dir", str(dsh_home), "--yes", "--lang", "en"]).returncode == 0
    first = json.loads((dsh_home / MANIFEST).read_text(encoding="utf-8"))
    assert first["previous_manifest"]["fingerprint"] is None

    # Second deploy over the first.
    assert run_cli(["--dsh-dir", str(dsh_home), "--yes", "--lang", "en"]).returncode == 0
    second = json.loads((dsh_home / MANIFEST).read_text(encoding="utf-8"))
    assert second["previous_manifest"]["fingerprint"] is not None
    assert second["deployment_id"] != first["deployment_id"]


def test_custom_file_deploy(dsh_home, tmp_path):
    custom = tmp_path / "custom.md"
    custom.write_text("Custom persona text.\n", encoding="utf-8")
    result = run_cli(
        ["--dsh-dir", str(dsh_home), "--file", str(custom), "--yes", "--lang", "en"]
    )
    assert result.returncode == 0
    assert (dsh_home / "AGENTS.md").read_text(encoding="utf-8") == "Custom persona text.\n"


def test_uninstall_drift_refused(dsh_home):
    assert run_cli(["--dsh-dir", str(dsh_home), "--yes", "--lang", "en"]).returncode == 0
    (dsh_home / "AGENTS.md").write_text("tampered\n", encoding="utf-8")
    result = run_cli(["--dsh-dir", str(dsh_home), "--uninstall", "--yes", "--lang", "en"])
    assert result.returncode == 1
    assert (dsh_home / "AGENTS.md").read_text(encoding="utf-8") == "tampered\n"
