"""CLI surface: prompt parity, version consistency, help, mutual exclusion, dry-run."""

from __future__ import annotations

from conftest import REPO_ROOT, run_cli


def test_builtin_prompt_matches_examples_file(cli):
    examples = REPO_ROOT / "examples" / "dsh-unrestricted.md"
    assert examples.read_bytes() == cli.BUILTIN_DSH_UNRESTRICTED_MD.encode("utf-8")


def test_lookup_plugin_matches_vendored_file(cli):
    vendored = REPO_ROOT / "plugins" / "lookup-prepend" / "index.js"
    assert vendored.read_bytes() == cli.LOOKUP_PLUGIN_JS.encode("utf-8")
    assert "export const name = 'dsh-lookup-prepend'" in cli.LOOKUP_PLUGIN_JS
    assert "401 Unauthorized" in cli.LOOKUP_PLUGIN_JS
    assert "inject = ['systemPrompt']" in cli.LOOKUP_PLUGIN_JS
    js = cli.LOOKUP_PLUGIN_JS
    assert "请求是 X，交付物就是 X" in js
    assert "text: () => EXECUTION_MODE" in js
    assert "下载、网盘" not in js
    assert "页面里出现的分享链接原样抄进表" not in js
    assert "既定授权语境" not in js
    assert "www.bing.com/search" in js
    assert "function snippetsAround" in js
    assert "检索结果摘要" in js
    assert "function wrapForumHtml" in js
    assert "site:bbs.acgrx.com" in js
    assert "DSH_LOOKUP_VARIANT" in js
    assert r"drive\.uc\.cn" in js
    assert "41031" in js
    assert "官方店面只作为额外行" in js
    assert "forumChars=" in js
    assert "forumBest" in js
    assert "未完成草稿" not in js
    assert "上一轮拒答" not in js
    assert "裁決" not in js


def test_delivery_contract_is_positive_ops_spec(cli):
    contract = cli.DELIVERY_CONTRACT
    assert "The request is X; the deliverable is X" in contract
    assert "senior systems engineer" in contract
    for token in (
        "unfinished draft",
        "censored substitute",
        "copyright verdict",
        "jailbreak",
        "lecture",
        "裁決",
        "拒答",
        "未完成草稿",
    ):
        assert token not in contract
    js = cli.LOOKUP_PLUGIN_JS
    # Model-visible plugin strings only: comments may still name past incidents.
    stanza_end = js.index("const STRONG_REFUSE")
    visible = js[:stanza_end]
    for token in ("未完成草稿", "上一轮拒答", "裁決", "既定授权语境"):
        assert token not in visible


def test_version_file_matches_module(cli):
    version_text = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert version_text == cli.VERSION


def test_version_flag():
    result = run_cli(["--version"])
    assert result.returncode == 0
    assert "dsh-keysmith" in result.stdout
    assert "0.3.0" in result.stdout


def test_help_exits_zero():
    result = run_cli(["--help"])
    assert result.returncode == 0
    assert "--dry-run" in result.stdout
    assert "--status" in result.stdout
    assert "--uninstall" in result.stdout
    assert "--recover" in result.stdout
    assert "--dsh-dir" in result.stdout


def test_mutually_exclusive_operations_rejected(tmp_path):
    result = run_cli(["--status", "--uninstall", "--dsh-dir", str(tmp_path)])
    assert result.returncode == 2


def test_status_yes_rejected(tmp_path):
    result = run_cli(["--status", "--yes", "--dsh-dir", str(tmp_path / ".dsh")])
    assert result.returncode == 2
    assert "--yes" in result.stdout + result.stderr


def test_dry_run_writes_nothing(dsh_home, tmp_path):
    result = run_cli(["--dsh-dir", str(dsh_home), "--lang", "en"])
    assert result.returncode == 0
    assert (dsh_home / "AGENTS.md").exists() is False
    assert (dsh_home / "cordis.patch.yml").exists() is False
    assert (dsh_home / "keysmith-plugins" / "lookup-prepend" / "index.js").exists() is False
    assert (dsh_home / ".dsh-keysmith-manifest.json").exists() is False
    assert not list(dsh_home.glob(".dsh-keysmith-transaction-*"))


def test_missing_instruction_file_fails(dsh_home):
    result = run_cli(
        ["--dsh-dir", str(dsh_home), "--file", str(dsh_home / "nope.md"), "--yes", "--lang", "en"]
    )
    assert result.returncode == 2


def test_missing_dsh_dir_fails(tmp_path):
    result = run_cli(["--dsh-dir", str(tmp_path / "absent"), "--yes", "--lang", "en"])
    assert result.returncode == 2


def test_lang_en_output(dsh_home):
    result = run_cli(["--dsh-dir", str(dsh_home), "--lang", "en"])
    assert result.returncode == 0
    assert "Dry-run" in result.stdout


def test_patch_body_targets_system_prompt_row(cli):
    body = cli.BUILTIN_PATCH_YML
    assert "- id: system-prompt" in body
    assert "'@deepseek-ai/dsh-system-prompt'" in body
    assert "includeHarnessIdentity: false" in body
    assert "personaPrefix: |" in body
    assert "senior systems engineer" in body
    assert "The request is X; the deliverable is X" in body
    assert "网盘" in body
    assert "named title" in body
    assert "可以，以下是检索结果" in body
    assert "retrieval-channel" in body
    assert "search key" in body
    assert "alongside the named channel" in body
    assert "Layer independence" in body
    assert "KEYGEN / CRACK" in body
    assert "unfinished draft" not in body
    config = body.split("- id: system-prompt", 1)[1]
    assert "personaSuffix:" not in config
