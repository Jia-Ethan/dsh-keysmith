"""Transaction residue blocking, recovery preview, and confirmed recovery."""

from __future__ import annotations

from conftest import run_cli

MANIFEST = ".dsh-keysmith-manifest.json"


def _simulate_interrupted_deploy(cli, dsh_home, phase="agents-md-intent"):
    """Create journals directly (as an interrupted deploy would leave them)."""
    tid = cli._new_transaction_id()
    agents_path = dsh_home / "AGENTS.md"
    patch_path = dsh_home / "cordis.patch.yml"
    agents_path.write_text("half-written agents\n", encoding="utf-8")
    resources = {
        cli.RESOURCE_AGENTS: {
            "path": agents_path,
            "before": None,
            "snapshot": None,
        },
        cli.RESOURCE_PATCH: {
            "path": patch_path,
            "before": None,
            "snapshot": None,
        },
    }
    txn = cli._create_deployment_journals(dsh_home, tid, cli.OPERATION_DEPLOY, resources)
    journal = cli._load_journal(txn)
    journal["phase"] = phase
    cli._write_journal(txn, journal)
    return tid, txn


def test_residue_blocks_status_and_deploy(cli, dsh_home):
    _simulate_interrupted_deploy(cli, dsh_home)
    status = run_cli(["--dsh-dir", str(dsh_home), "--status", "--lang", "en"])
    assert status.returncode == 1
    assert "residue" in status.stdout.lower() or "residue" in status.stdout

    deploy = run_cli(["--dsh-dir", str(dsh_home), "--yes", "--lang", "en"])
    assert deploy.returncode == 1


def test_recover_preview_is_read_only(cli, dsh_home):
    _simulate_interrupted_deploy(cli, dsh_home)
    result = run_cli(["--dsh-dir", str(dsh_home), "--recover", "--lang", "en"])
    assert result.returncode == 0
    assert (dsh_home / "AGENTS.md").read_text(encoding="utf-8") == "half-written agents\n"
    assert list(dsh_home.glob(".dsh-keysmith-transaction-*"))


def test_recover_yes_restores_before_state(cli, dsh_home):
    _simulate_interrupted_deploy(cli, dsh_home)
    result = run_cli(["--dsh-dir", str(dsh_home), "--recover", "--yes", "--lang", "en"])
    assert result.returncode == 0
    # before state was absent: resource removed, no residue left.
    assert not (dsh_home / "AGENTS.md").exists()
    assert not (dsh_home / "cordis.patch.yml").exists()
    assert not list(dsh_home.glob(".dsh-keysmith-transaction-*"))
    assert not list(dsh_home.glob(".dsh-keysmith-cleanup-*"))


def test_recover_with_existing_files_restores_snapshot(cli, dsh_home):
    agents_path = dsh_home / "AGENTS.md"
    agents_path.write_text("precious original\n", encoding="utf-8")
    tid = cli._new_transaction_id()
    resources = {
        cli.RESOURCE_AGENTS: {
            "path": agents_path,
            "before": cli._fingerprint(agents_path),
            "snapshot": agents_path.read_bytes(),
        },
        cli.RESOURCE_PATCH: {
            "path": dsh_home / "cordis.patch.yml",
            "before": None,
            "snapshot": None,
        },
    }
    cli._create_deployment_journals(dsh_home, tid, cli.OPERATION_DEPLOY, resources)
    # Simulate the deploy having half-written the file.
    agents_path.write_text("half-written\n", encoding="utf-8")
    result = run_cli(["--dsh-dir", str(dsh_home), "--recover", "--yes", "--lang", "en"])
    assert result.returncode == 0
    assert agents_path.read_text(encoding="utf-8") == "precious original\n"


def test_orphaned_cleanup_marker_recovery(cli, dsh_home):
    marker = dsh_home / f"{cli.CLEANUP_MARKER_PREFIX}deadbeef{cli.CLEANUP_MARKER_SUFFIX}"
    marker.write_text("{}", encoding="utf-8")
    result = run_cli(["--dsh-dir", str(dsh_home), "--recover", "--yes", "--lang", "en"])
    assert result.returncode == 0
    assert not marker.exists()


def test_no_residue_is_clean(dsh_home):
    result = run_cli(["--dsh-dir", str(dsh_home), "--recover", "--lang", "en"])
    assert result.returncode == 0
