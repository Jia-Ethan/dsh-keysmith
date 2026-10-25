"""Recover is a documented no-op in 0.4.0 (no transaction journals)."""

from __future__ import annotations

import json

from conftest import run_cli


def test_recover_preview_is_ok(dsh_home):
    result = run_cli(["--dsh-dir", str(dsh_home), "--recover", "--lang", "en"])
    assert result.returncode == 0
    assert "residue" in result.stdout.lower() or "残留" in result.stdout


def test_recover_json_empty_residue(dsh_home):
    result = run_cli(["--dsh-dir", str(dsh_home), "--recover", "--json"])
    payload = json.loads(result.stdout)
    assert result.returncode == 0
    assert payload["residue"] == []
    assert payload["ok"] is True


def test_status_not_blocked_without_journals(dsh_home):
    result = run_cli(["--dsh-dir", str(dsh_home), "--status", "--lang", "en"])
    assert result.returncode == 0
