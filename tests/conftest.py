"""Shared fixtures: CLI module loader, fresh DSH home, subprocess runner."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CLI_PATH = REPO_ROOT / "dsh-keysmith.py"


def load_cli_module():
    spec = importlib.util.spec_from_file_location("dsh_keysmith_cli", CLI_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def cli():
    return load_cli_module()


@pytest.fixture()
def dsh_home(tmp_path):
    home = tmp_path / ".dsh"
    (home / "profiles").mkdir(parents=True)
    return home


def run_cli(args, cwd=None, env_extra=None):
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(CLI_PATH), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd,
        env=env,
    )
