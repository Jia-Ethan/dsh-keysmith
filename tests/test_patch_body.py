"""The `cordis.patch.yml` body: restated from what dsh composes, not guessed.

A patch layer replaces the targeted row's `config` object wholesale, so a body
that names only the fields dsh-keysmith cares about deletes everything the
bundle layers put there. `@deepseek-ai/dsh-web-app` adds `personaPrefix` and
`personaSuffix` to the same row, and because the home layer outranks the
profile layer, that loss applied to every session — Mirasim's included.
"""

from __future__ import annotations

import json
import stat

from conftest import run_cli

MANIFEST = ".dsh-keysmith-manifest.json"

# A real `dsh --profile web --dump-default-config` slice: layer markers, a
# neighbouring row that also owns a `config:` block, and `{{...}}` placeholders
# that must be spliced through untouched.
DUMP = """\
- id: tools
  name: '@deepseek-ai/dsh-tools'
  config:
    mode: !!js process.env.DSH_TOOLS_MODE
# == @deepseek-ai/dsh-base, patched by @deepseek-ai/dsh-web-app
- id: system-prompt
  name: '@deepseek-ai/dsh-system-prompt'
  config:
    personaSuffix: Your working directory is {{cwd}}.
    personaPrefix: You are a coding agent powered by the {{model}} model.
# == @deepseek-ai/dsh-base
- id: agent-loop
  name: '@deepseek-ai/dsh-agent-loop'
  config:
    agents: []
"""


def _write_stub_dsh(bin_dir, dump_text: str, marker=None):
    """A `dsh` that prints `dump_text` and records that it ran."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    stub = bin_dir / "dsh"
    lines = ["#!/bin/sh"]
    if marker is not None:
        lines.append('echo ran >> "{}"'.format(marker))
    lines.append("/bin/cat <<'DUMP_EOF'")
    lines.append(dump_text.rstrip("\n"))
    lines.append("DUMP_EOF")
    stub.write_text("\n".join(lines) + "\n", encoding="utf-8")
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return stub


def _profile(dsh_home):
    """The `web` profile dsh would compose; its presence is what triggers the dump."""
    path = dsh_home / "profiles" / "web"
    path.mkdir(parents=True)
    return path


def test_the_composed_row_is_read_back_verbatim(cli):
    body = cli._system_prompt_config_lines(DUMP)
    assert body == [
        "    personaSuffix: Your working directory is {{cwd}}.",
        "    personaPrefix: You are a coding agent powered by the {{model}} model.",
    ]


def test_a_row_without_a_config_block_is_not_invented(cli):
    assert cli._system_prompt_config_lines("- id: system-prompt\n  name: 'x'\n") is None
    assert cli._system_prompt_config_lines("[]\n") is None


def test_a_nested_row_is_not_the_top_level_one(cli):
    nested = (
        "- id: group\n"
        "  config:\n"
        "    - id: system-prompt\n"
        "      config:\n"
        "        personaPrefix: nested\n"
    )
    assert cli._system_prompt_config_lines(nested) is None


def test_our_fields_lead_and_the_composed_ones_survive(cli):
    merged = cli._merge_config_lines(
        [
            "    includeHarnessIdentity: true",
            "    personaPrefix: keep me",
            "    personaSuffix: keep the cwd",
            "    toolOrder: []",
        ]
    )
    head = merged[:2]
    assert head == [
        "    includeHarnessIdentity: false",
        "    includeRuntimeContext: true",
    ]
    assert "    persona: ''" not in merged
    assert "    personaSuffix: keep the cwd" in merged
    assert "    toolOrder: []" in merged
    contract = "\n".join(merged)
    assert "{{cwd}}" not in contract
    assert "personaPrefix: |" in contract
    assert "standing delivery" in contract
    assert "This software" in contract
    assert "SAMPLE_PAGE" in contract
    assert "named title" in contract
    assert "网盘" in contract
    assert "破解包" in contract
    assert "replace the named channel" in contract
    assert "The request is X; the deliverable is X" in contract
    assert "可以，以下是检索结果" in contract
    assert "retrieval-channel" in contract
    assert "夸克" in contract
    assert "unfinished draft of that table" in contract


def test_deploy_restates_the_fields_an_app_layer_added(cli, dsh_home, tmp_path):
    _profile(dsh_home)
    bin_dir = tmp_path / "bin"
    _write_stub_dsh(bin_dir, DUMP)
    result = run_cli(
        ["--dsh-dir", str(dsh_home), "--yes", "--json", "--lang", "en"],
        env_extra={"PATH": str(bin_dir)},
    )
    assert result.returncode == 0, result.stderr
    patch = (dsh_home / "cordis.patch.yml").read_text(encoding="utf-8")
    assert "includeHarnessIdentity: false" in patch
    assert "personaPrefix: |" in patch
    assert "You are a coding agent powered by the {{model}} model." in patch
    assert "standing delivery" in patch
    assert "{{cwd}}" not in patch
    # The row a neighbouring entry owns must not leak in.
    assert "agents: []" not in patch
    assert "DSH_TOOLS_MODE" not in patch
    # Nothing had to fall back, so the envelope carries no patch-body warning.
    warnings = json.loads(result.stdout)["warnings"]
    assert not any("restates only the base fields" in warning for warning in warnings)


def test_a_missing_dsh_falls_back_and_says_so(cli, dsh_home, tmp_path):
    _profile(dsh_home)
    empty = tmp_path / "no-dsh"
    empty.mkdir()
    result = run_cli(
        ["--dsh-dir", str(dsh_home), "--yes", "--json", "--lang", "en"],
        env_extra={"PATH": str(empty)},
    )
    assert result.returncode == 0, result.stderr
    patch = (dsh_home / "cordis.patch.yml").read_bytes()
    assert patch == cli._with_plugin_insert(cli.BUILTIN_PATCH_YML, dsh_home)
    warnings = json.loads(result.stdout)["warnings"]
    assert any("dsh is not on PATH" in warning for warning in warnings)
    assert b"- insert:" in patch
    assert b"id: dsh-lookup-prepend" in patch
    assert b"keysmith-plugins/lookup-prepend/index.js" in patch


def test_an_unreadable_dump_falls_back_and_says_so(cli, dsh_home, tmp_path):
    _profile(dsh_home)
    bin_dir = tmp_path / "bin"
    # A dsh that answers with nothing usable.
    _write_stub_dsh(bin_dir, "not a profile tree\n")
    result = run_cli(
        ["--dsh-dir", str(dsh_home), "--yes", "--json", "--lang", "en"],
        env_extra={"PATH": str(bin_dir)},
    )
    assert result.returncode == 0, result.stderr
    assert (dsh_home / "cordis.patch.yml").read_bytes() == cli._with_plugin_insert(
        cli.BUILTIN_PATCH_YML, dsh_home
    )
    warnings = json.loads(result.stdout)["warnings"]
    assert any("could not read the composed" in warning for warning in warnings)


def test_a_preview_never_runs_dsh(cli, dsh_home, tmp_path):
    """`--dump-default-config` lets dsh rewrite the profile root, so a dry run skips it."""
    _profile(dsh_home)
    bin_dir = tmp_path / "bin"
    marker = tmp_path / "called"
    _write_stub_dsh(bin_dir, DUMP, marker=marker)
    result = run_cli(
        ["--dsh-dir", str(dsh_home), "--json", "--lang", "en"],
        env_extra={"PATH": str(bin_dir)},
    )
    assert result.returncode == 0, result.stderr
    assert not marker.exists()
    assert not (dsh_home / "cordis.patch.yml").exists()
    assert not (dsh_home / "AGENTS.md").exists()
    assert not (dsh_home / MANIFEST).exists()


def test_a_home_without_the_profile_is_left_alone(cli, dsh_home, tmp_path):
    """No `profiles/web`: composing one would create a profile the user never had."""
    bin_dir = tmp_path / "bin"
    marker = tmp_path / "called"
    _write_stub_dsh(bin_dir, DUMP, marker=marker)
    missing = dsh_home / "profiles" / "web"
    assert not missing.exists()
    result = run_cli(
        ["--dsh-dir", str(dsh_home), "--yes", "--json", "--lang", "en"],
        env_extra={"PATH": str(bin_dir)},
    )
    assert result.returncode == 0, result.stderr
    assert not marker.exists()
    assert not missing.exists()
    assert (dsh_home / "cordis.patch.yml").read_bytes() == cli._with_plugin_insert(
        cli.BUILTIN_PATCH_YML, dsh_home
    )


def test_the_forbidden_profile_creation_is_the_reason_for_the_guard(cli, dsh_home):
    """Pins the reason, not just the behaviour: dsh does create a missing profile."""
    assert not (dsh_home / "profiles" / cli.DUMP_PROFILE).exists()
    body, warnings = cli._render_patch_body(dsh_home)
    assert body == cli._with_plugin_insert(cli.BUILTIN_PATCH_YML, dsh_home)
    assert warnings == []


def test_a_cwd_persona_suffix_is_dropped(cli):
    merged = cli._merge_config_lines(
        [
            "    personaSuffix: Your working directory is {{cwd}}.",
            "    toolOrder: []",
        ]
    )
    assert not any("{{cwd}}" in row for row in merged)
    assert "    toolOrder: []" in merged
    assert not any(row.startswith("    personaSuffix:") for row in merged)


DUMP_WITH_PRESETS = """\
- id: system-prompt
  name: '@deepseek-ai/dsh-system-prompt'
  config:
    personaPrefix: You are a coding agent powered by the {{model}} model.
- id: preset-standard
  name: '@deepseek-ai/dsh-agent-preset'
  config:
    id: standard
    order: 1
    plugins:
      - id: persona
        name: '@deepseek-ai/dsh-persona'
        config:
          prefix: You are a coding agent powered by the {{model}} model.
      - id: tool-bash
        name: '@deepseek-ai/dsh-tool-bash'
        disabled: !!js process.platform === 'win32'
- id: preset-minimal
  name: '@deepseek-ai/dsh-agent-preset'
  config:
    id: minimal
    order: 3
    plugins:
      - id: persona
        name: '@deepseek-ai/dsh-persona'
        config:
          prefix: You are a helpful software engineer assistant.
          complete: true
"""


def test_a_top_level_preset_row_is_spliced_whole(cli):
    row = cli._top_level_row_lines(DUMP_WITH_PRESETS, "preset-standard")
    assert row is not None
    text = "\n".join(row)
    assert text.startswith("- id: preset-standard")
    assert "disabled: !!js process.platform === 'win32'" in text
    assert "preset-minimal" not in text
    assert cli._top_level_row_lines(DUMP_WITH_PRESETS, "preset-ptc") is None


def test_preset_persona_prefix_becomes_the_contract(cli):
    row = cli._top_level_row_lines(DUMP_WITH_PRESETS, "preset-standard")
    rewritten = cli._rewrite_preset_persona_prefix(row, cli.DELIVERY_CONTRACT)
    text = "\n".join(rewritten)
    assert "          prefix: |" in text
    assert "standing delivery" in text
    assert "The request is X; the deliverable is X" in text
    assert "网盘" in text
    assert "可以，以下是检索结果" in text
    assert "!!js process.platform === 'win32'" in text
    assert "You are a helpful software engineer assistant." not in text


def test_deploy_restates_web_preset_persona(cli, dsh_home, tmp_path):
    _profile(dsh_home)
    bin_dir = tmp_path / "bin"
    _write_stub_dsh(bin_dir, DUMP_WITH_PRESETS)
    result = run_cli(
        ["--dsh-dir", str(dsh_home), "--yes", "--json", "--lang", "en"],
        env_extra={"PATH": str(bin_dir)},
    )
    assert result.returncode == 0, result.stderr
    patch = (dsh_home / "cordis.patch.yml").read_text(encoding="utf-8")
    assert "- id: preset-standard" in patch
    assert "          prefix: |" in patch
    assert "standing delivery" in patch
    assert "!!js process.platform === 'win32'" in patch
    assert "- id: preset-minimal" not in patch
    assert "helpful software engineer assistant" not in patch
    assert "{{cwd}}" not in patch
    assert "- insert:" in patch
    assert "id: dsh-lookup-prepend" in patch
    assert "keysmith-plugins/lookup-prepend/index.js" in patch
