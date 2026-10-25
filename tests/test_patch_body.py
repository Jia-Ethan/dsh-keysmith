"""Plugin contract and bundle patch: assemble path, not home YAML dump."""

from __future__ import annotations

from conftest import PLUGIN_SRC, run_cli


def _non_comment_lines(text: str):
    return [ln for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]


def test_ensure_insert_drops_empty_array_document(cli):
    out = cli.ensure_insert("# comment\n[]\n")
    assert "[]" not in out
    lines = _non_comment_lines(out)
    assert lines[0].startswith("- insert:")
    assert "- id: dsh-keysmith" in out
    assert cli.profile_has_keysmith_insert(out)


def test_ensure_insert_on_live_shaped_sequence(cli):
    src = (
        "# profile patch\n"
        "- id: llm-pi-ai\n"
        "  name: '@deepseek-ai/dsh-llm-pi-ai'\n"
    )
    out = cli.ensure_insert(src)
    assert "- id: llm-pi-ai" in out
    assert "- id: dsh-keysmith" in out
    assert "[]" not in out


def test_plugin_patch_does_not_clobber_system_prompt():
    body = (PLUGIN_SRC / "cordis.patch.yml").read_text(encoding="utf-8")
    assert "- id: dsh-keysmith" in body
    assert "inject: [systemPrompt, tools]" in body
    assert "- id: system-prompt" not in body
    assert "personaPrefix" not in body
    assert "{{cwd}}" not in body


def test_contract_file_is_the_system_payload(cli):
    contract = (PLUGIN_SRC / "lib" / "contract.md").read_text(encoding="utf-8")
    assert contract == cli.DELIVERY_CONTRACT
    assert "The request is X; the deliverable is X" in contract
    assert "senior systems engineer" in contract
    assert "网盘" in contract
    assert "named title" in contract
    assert "可以，以下是检索结果" in contract
    assert "retrieval-channel" in contract
    assert "search key" in contract
    assert "alongside the named channel" in contract
    assert "Layer independence" in contract
    assert "KEYGEN / CRACK" in contract
    assert "unfinished draft" not in contract
    assert "{{model}}" in contract


def test_deploy_does_not_write_home_system_prompt_row(dsh_home):
    assert run_cli(["--dsh-dir", str(dsh_home), "--yes", "--lang", "en"]).returncode == 0
    assert (dsh_home / "cordis.patch.yml").exists() is False
    profile_patch = (dsh_home / "profiles" / "web" / "cordis.patch.yml").read_text(
        encoding="utf-8"
    )
    assert "id: dsh-keysmith" in profile_patch
    assert "personaPrefix" not in profile_patch
