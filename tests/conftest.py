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


ADAPTER_REL = "profiles/node_modules/@deepseek-ai/dsh-llm-deepseek/lib/index.js"


def write_adapter(home, body: str) -> Path:
    """Create a fake dsh-llm-deepseek adapter under a test DSH home."""
    path = home / ADAPTER_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def adapter_original_body() -> str:
    """A minimal adapter source containing the ORIGINAL (buggy) snippet."""
    return (
        "function translate(payloads) {\n"
        "\t\t\t\tif (call.id !== void 0) block.callId = call.id;\n"
        "\t\t\t\tif (call.function?.name !== void 0) block.name = call.function.name;\n"
        "}\n"
    )


def adapter_patched_body() -> str:
    """The same minimal source with the patched (truthy-guard) snippet."""
    return (
        "function translate(payloads) {\n"
        "\t\t\t\tif (call.id) block.callId = call.id;\n"
        "\t\t\t\tif (call.function?.name) block.name = call.function.name;\n"
        "}\n"
    )


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
