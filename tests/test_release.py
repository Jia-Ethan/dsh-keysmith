"""Prompt-bank validate-only run and release-build contract checks."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
import zipfile

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


def test_build_from_clean_tag_emits_verified_assets(tmp_path):
    repo = tmp_path / "source"
    repo.mkdir()
    (repo / "scripts").mkdir()
    shutil.copyfile(BUILD_SCRIPT, repo / "scripts" / BUILD_SCRIPT.name)
    for name in ("dsh-keysmith.py", "VERSION"):
        shutil.copyfile(REPO_ROOT / name, repo / name)
    version = (repo / "VERSION").read_text().strip()
    tag = f"v{version}"

    def git(*args):
        subprocess.run(
            ["git", "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false", *args],
            cwd=repo, check=True, capture_output=True,
        )

    git("init")
    git("config", "user.name", "Release test")
    git("config", "user.email", "release-test@example.invalid")
    git("add", ".")
    git("commit", "-m", "release fixture")
    git("tag", tag)
    out = tmp_path / "artifacts"
    result = subprocess.run(
        [sys.executable, "scripts/build_release.py", "--tag", tag, "--out", str(out)],
        cwd=repo, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    checksums = (out / "SHA256SUMS").read_text().splitlines()
    assert len(checksums) == 3
    for row in checksums:
        digest, name = row.split("  ", 1)
        assert hashlib.sha256((out / name).read_bytes()).hexdigest() == digest
    cli = (repo / "dsh-keysmith.py").read_bytes()
    assert (out / f"dsh-keysmith-{tag}.py").read_bytes() == cli
    prefix = f"dsh-keysmith-{tag}/"
    with zipfile.ZipFile(out / f"dsh-keysmith-{tag}.zip") as archive:
        assert archive.testzip() is None
        assert archive.read(prefix + "dsh-keysmith.py") == cli
        assert archive.read(prefix + "VERSION").decode().strip() == version
    with tarfile.open(out / f"dsh-keysmith-{tag}.tar.gz") as archive:
        assert archive.extractfile(prefix + "dsh-keysmith.py").read() == cli
        assert archive.extractfile(prefix + "VERSION").read().decode().strip() == version
