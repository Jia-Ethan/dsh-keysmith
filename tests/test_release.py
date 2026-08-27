"""Prompt-bank validate-only run and release-build contract checks."""

from __future__ import annotations

import json
import subprocess
import sys

from conftest import REPO_ROOT

PROMPT_BANK = REPO_ROOT / "tests" / "prompt_bank" / "cases.json"
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build_release.py"
REGRESSION_SCRIPT = REPO_ROOT / "scripts" / "run_prompt_bank_regression.py"


def test_prompt_bank_json_is_wellformed():
    data = json.loads(PROMPT_BANK.read_text(encoding="utf-8"))
    assert data["version"] == "0.1.0"
    assert data["prompt_source"] == "builtin"
    assert isinstance(data["cases"], list) and len(data["cases"]) >= 4
    for case in data["cases"]:
        assert {"id", "contract", "input", "language", "category"} <= set(case.keys())


def test_prompt_bank_validate_only():
    result = subprocess.run(
        [sys.executable, str(REGRESSION_SCRIPT), "--validate-only"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(REPO_ROOT),
        env={"PYTHONUTF8": "1", "PATH": "/usr/bin:/bin"},
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_build_script_refuses_dirty_or_untagged(tmp_path):
    # The builder requires a tag pointing at HEAD; without one it must fail
    # loudly rather than emit an unversioned artifact.
    result = subprocess.run(
        [sys.executable, str(BUILD_SCRIPT), "--tag", "v9.9.9", "--out", str(tmp_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(REPO_ROOT),
        env={"PYTHONUTF8": "1", "PATH": "/usr/bin:/bin"},
    )
    assert result.returncode != 0


def test_bad_tag_format_rejected(tmp_path):
    result = subprocess.run(
        [sys.executable, str(BUILD_SCRIPT), "--tag", "not-a-version", "--out", str(tmp_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(REPO_ROOT),
        env={"PYTHONUTF8": "1", "PATH": "/usr/bin:/bin"},
    )
    assert result.returncode != 0
