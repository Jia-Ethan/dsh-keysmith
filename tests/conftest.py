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
PLUGIN_SRC = REPO_ROOT / "plugin"


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


def profile_dir(home: Path, name: str = "web") -> Path:
    return home / "profiles" / name


def desktop_profile(home: Path) -> Path:
    """What DSH Desktop leaves after its first launch: the web template under
    `profiles/desktop` (apps/desktop `createPluginProfile`)."""
    import json

    profile = home / "profiles" / "desktop"
    profile.mkdir(parents=True, exist_ok=True)
    (profile / "package.json").write_text(
        json.dumps(
            {
                "name": "dsh-profile-desktop",
                "private": True,
                "dependencies": {},
                "dsh": {"profile": {"bundles": ["@deepseek-ai/dsh-base", "@deepseek-ai/dsh-web-app"]}},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (profile / "cordis.patch.yml").write_text(
        "# Your patch layer for this dsh profile, applied after every bundle layer:\n[]\n",
        encoding="utf-8",
    )
    (profile / "pnpm-workspace.yaml").write_text("packages:\n  - .\n", encoding="utf-8")
    return profile
