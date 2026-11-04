"""Profile selection: DSH Desktop boots only profiles/desktop (issue keysmith-switch#162)."""

from __future__ import annotations

import json

from conftest import desktop_profile, profile_dir, run_cli

MANIFEST = ".dsh-keysmith-manifest.json"


def _json(args):
    result = run_cli([*args, "--json", "--lang", "en"])
    assert result.stdout.strip().startswith("{"), result.stdout + result.stderr
    return result.returncode, json.loads(result.stdout)


def _installed(profile):
    pkg = json.loads((profile / "package.json").read_text(encoding="utf-8"))
    patch = (profile / "cordis.patch.yml").read_text(encoding="utf-8")
    return (
        (profile / "node_modules" / "dsh-keysmith" / "lib" / "index.js").is_file(),
        "dsh-keysmith" in pkg["dsh"]["profile"]["bundles"],
        "id: dsh-keysmith" in patch,
    )


def _manifest(home):
    return json.loads((home / MANIFEST).read_text(encoding="utf-8"))


def _old_web_manifest(home):
    """Rewrite the manifest as 0.4.0 wrote it: no profile_source, tool 0.4.0."""
    manifest = _manifest(home)
    manifest.pop("profile_source")
    manifest["tool_version"] = "0.4.0"
    (home / MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def test_no_desktop_profile_still_defaults_to_web(dsh_home):
    code, payload = _json(["--dsh-dir", str(dsh_home), "--yes"])
    assert code == 0
    assert payload["profile"] == "web"
    assert payload["profile_source"] == "auto"
    assert _installed(profile_dir(dsh_home, "web")) == (True, True, True)
    assert not profile_dir(dsh_home, "desktop").exists()


def test_desktop_profile_is_selected_automatically(dsh_home):
    desktop = desktop_profile(dsh_home)
    code, preview = _json(["--dsh-dir", str(dsh_home)])
    assert code == 0
    assert preview["profile"] == "desktop"
    assert preview["profile_source"] == "auto"
    assert all("/desktop/" in item["path"].replace("\\", "/") for item in preview["actions"])
    assert any("DSH Desktop" in note for note in preview["warnings"])
    assert not (desktop / "node_modules").exists()

    code, payload = _json(["--dsh-dir", str(dsh_home), "--yes"])
    assert code == 0
    assert payload["profile"] == "desktop"
    assert _installed(desktop) == (True, True, True)
    # Desktop's own template bundles are kept; the plugin is appended.
    pkg = json.loads((desktop / "package.json").read_text(encoding="utf-8"))
    assert pkg["dsh"]["profile"]["bundles"] == [
        "@deepseek-ai/dsh-base",
        "@deepseek-ai/dsh-web-app",
        "dsh-keysmith",
    ]
    assert (desktop / "pnpm-workspace.yaml").read_text(encoding="utf-8") == "packages:\n  - .\n"
    assert not profile_dir(dsh_home, "web").exists()
    assert _manifest(dsh_home)["profile"] == "desktop"
    assert _manifest(dsh_home)["profile_source"] == "auto"

    code, status = _json(["--dsh-dir", str(dsh_home), "--status"])
    assert status["state"] == "active"
    assert status["profile"] == "desktop"
    assert status["target_profile"] == "desktop"
    assert status["drift"] == []


def test_explicit_web_wins_over_desktop_and_sticks(dsh_home):
    desktop = desktop_profile(dsh_home)
    code, payload = _json(["--dsh-dir", str(dsh_home), "--profile", "web", "--yes"])
    assert code == 0
    assert payload["profile"] == "web"
    assert payload["profile_source"] == "explicit"
    assert _manifest(dsh_home)["profile_source"] == "explicit"
    # A later call without --profile (what Switch sends) keeps the choice.
    code, status = _json(["--dsh-dir", str(dsh_home), "--status"])
    assert status["state"] == "active"
    assert status["target_profile"] == "web"
    code, again = _json(["--dsh-dir", str(dsh_home), "--yes"])
    assert again["profile"] == "web"
    assert again["previous_profile"] is None
    assert not (desktop / "node_modules").exists()


def test_old_web_deploy_reports_drift_once_desktop_exists(dsh_home):
    assert _json(["--dsh-dir", str(dsh_home), "--yes"])[0] == 0
    _old_web_manifest(dsh_home)
    desktop_profile(dsh_home)
    code, status = _json(["--dsh-dir", str(dsh_home), "--status"])
    assert code == 0
    assert status["state"] == "drift"
    assert status["profile"] == "web"
    assert status["target_profile"] == "desktop"
    assert any(note.startswith("profile_target:") and "DSH Desktop" in note for note in status["drift"])


def test_redeploy_moves_old_web_deploy_into_desktop(dsh_home):
    web = profile_dir(dsh_home, "web")
    assert _json(["--dsh-dir", str(dsh_home), "--yes"])[0] == 0
    _old_web_manifest(dsh_home)
    # Something of the user's own in the web profile must survive the move.
    pkg = json.loads((web / "package.json").read_text(encoding="utf-8"))
    pkg["dsh"]["profile"]["bundles"].append("their-plugin")
    (web / "package.json").write_text(json.dumps(pkg, indent=2) + "\n", encoding="utf-8")
    with (web / "cordis.patch.yml").open("a", encoding="utf-8") as handle:
        handle.write("- id: their-row\n  config: {}\n")
    desktop = desktop_profile(dsh_home)

    code, preview = _json(["--dsh-dir", str(dsh_home)])
    assert preview["profile"] == "desktop"
    assert preview["previous_profile"] == "web"
    details = {item["detail"] for item in preview["actions"]}
    assert {"previous_profile_plugin", "previous_profile_bundles", "previous_profile_insert"} <= details
    assert _installed(web) == (True, True, True)

    code, payload = _json(["--dsh-dir", str(dsh_home), "--yes"])
    assert code == 0
    assert payload["profile"] == "desktop"
    assert payload["previous_profile"] == "web"
    assert _installed(desktop) == (True, True, True)
    assert _installed(web) == (False, False, False)
    web_pkg = json.loads((web / "package.json").read_text(encoding="utf-8"))
    assert "their-plugin" in web_pkg["dsh"]["profile"]["bundles"]
    assert "- id: their-row" in (web / "cordis.patch.yml").read_text(encoding="utf-8")
    code, status = _json(["--dsh-dir", str(dsh_home), "--status"])
    assert status["state"] == "active"
    assert status["profile"] == "desktop"


def test_workaround_desktop_deploy_from_0_4_0_is_kept(dsh_home):
    # The issue's workaround: `--profile desktop --yes` on 0.4.0.
    desktop = desktop_profile(dsh_home)
    assert _json(["--dsh-dir", str(dsh_home), "--profile", "desktop", "--yes"])[0] == 0
    _old_web_manifest(dsh_home)
    code, status = _json(["--dsh-dir", str(dsh_home), "--status"])
    assert status["state"] == "active"
    assert status["profile"] == "desktop"
    code, payload = _json(["--dsh-dir", str(dsh_home), "--yes"])
    assert payload["profile"] == "desktop"
    assert payload["previous_profile"] is None
    assert _installed(desktop) == (True, True, True)


def test_uninstall_follows_the_manifest(dsh_home):
    desktop = desktop_profile(dsh_home)
    assert _json(["--dsh-dir", str(dsh_home), "--yes"])[0] == 0
    code, payload = _json(["--dsh-dir", str(dsh_home), "--uninstall", "--yes", "--profile", "web"])
    assert code == 0
    assert payload["profile"] == "desktop"
    assert _installed(desktop) == (False, False, False)
    assert not (dsh_home / MANIFEST).exists()


def test_missing_desktop_dir_is_not_recreated(dsh_home):
    desktop_profile(dsh_home)
    assert _json(["--dsh-dir", str(dsh_home), "--yes"])[0] == 0
    # DSH Desktop removed along with its profile.
    import shutil

    shutil.rmtree(profile_dir(dsh_home, "desktop"))
    code, status = _json(["--dsh-dir", str(dsh_home), "--status"])
    assert status["state"] == "drift"
    assert status["target_profile"] == "web"
    code, payload = _json(["--dsh-dir", str(dsh_home), "--yes"])
    assert payload["profile"] == "web"
    assert payload["previous_profile"] == "desktop"
    assert not profile_dir(dsh_home, "desktop").exists()
    assert _installed(profile_dir(dsh_home, "web")) == (True, True, True)


def test_profile_auto_is_the_same_as_no_flag(dsh_home):
    desktop_profile(dsh_home)
    code, payload = _json(["--dsh-dir", str(dsh_home), "--profile", "auto"])
    assert payload["profile"] == "desktop"
    assert payload["profile_source"] == "auto"


def test_text_preview_names_the_desktop_choice(dsh_home):
    desktop_profile(dsh_home)
    result = run_cli(["--dsh-dir", str(dsh_home), "--lang", "en"])
    assert result.returncode == 0
    assert "Profile: desktop" in result.stdout
    assert "DSH Desktop" in result.stdout
