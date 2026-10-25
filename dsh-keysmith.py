#!/usr/bin/env python3
# ─── dsh-keysmith ─────────────────────────────────────────────────────────────
# Preview-first installer for the DeepSeek Harness Cordis plugin.
# Runtime effect lives in plugin/ (assemble guard, identity strip, contract
# pin, lookup, dock). This CLI installs that package into one DSH profile
# (default: web). It does not dump AGENTS.md or rewrite @deepseek-ai
# node_modules.
#
# Zero runtime dependencies: standard library only.
# License: MIT. See LICENSE.
# ─────────────────────────────────────────────────────────────────────────────
"""dsh-keysmith: install the DSH Keysmith Cordis plugin into a profile."""

from __future__ import annotations

import argparse
import hashlib
import json
import locale
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ─── Version ──────────────────────────────────────────────────────────────────
__version__ = "0.4.0"
VERSION = __version__

# ─── Names and constants ─────────────────────────────────────────────────────
TOOL_NAME = "dsh-keysmith"
PLUGIN_NAME = "dsh-keysmith"
PLUGIN_RELDIR = "plugin"
MANIFEST_FILENAME = ".dsh-keysmith-manifest.json"
MANIFEST_SCHEMA_VERSION = 1
DEFAULT_PROFILE = "web"
DSH_ENV_VAR = "DSH_HOME"
JSON_SCHEMA = "dsh-keysmith/v1"

OPERATION_DEPLOY = "deploy"
OPERATION_UNINSTALL = "uninstall"
OPERATION_STATUS = "status"
OPERATION_RECOVER = "recover"

RESOURCE_PLUGIN = "profile_plugin"
RESOURCE_BUNDLES = "profile_bundles"
RESOURCE_INSERT = "profile_insert"

_LAST_USAGE_ERROR: List[Optional[str]] = [None]
_OUTPUT_LANGUAGE = "zh-CN"

REPO_ROOT = Path(__file__).resolve().parent


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _plugin_src() -> Path:
    return REPO_ROOT / PLUGIN_RELDIR


DELIVERY_CONTRACT = _read_text(_plugin_src() / "lib" / "contract.md")
LOOKUP_PLUGIN_JS = _read_text(_plugin_src() / "lib" / "lookup.js")
BUILTIN_DSH_UNRESTRICTED_MD = _read_text(REPO_ROOT / "examples" / "dsh-unrestricted.md")


# ─── Language ─────────────────────────────────────────────────────────────────


class _SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _resolve_output_language(value: str) -> str:
    if value in ("zh-CN", "en"):
        return value
    for env in ("LC_ALL", "LC_MESSAGES", "LANG"):
        tag = os.environ.get(env)
        if tag:
            lowered = tag.lower()
            if "zh" in lowered:
                return "zh-CN"
            if "en" in lowered:
                return "en"
    try:
        current = locale.getlocale()[0]
    except ValueError:
        current = None
    if current and current.lower().startswith("zh"):
        return "zh-CN"
    return "zh-CN"


_STRINGS: Dict[str, Dict[str, str]] = {
    "banner": {
        "zh-CN": f"{TOOL_NAME} v{{version}} — DeepSeek Harness 插件安装器",
        "en": f"{TOOL_NAME} v{{version}} — DeepSeek Harness plugin installer",
    },
    "dsh_dir": {"zh-CN": "DSH 目录", "en": "DSH directory"},
    "profile": {"zh-CN": "Profile", "en": "Profile"},
    "plan": {"zh-CN": "写入计划", "en": "Write plan"},
    "create": {"zh-CN": "新建 {path}", "en": "create {path}"},
    "replace": {"zh-CN": "备份并替换 {path}", "en": "backup and replace {path}"},
    "update": {"zh-CN": "更新 {path}", "en": "update {path}"},
    "dry_run_no_write": {
        "zh-CN": "预览模式: 未写入任何文件。加 --yes 执行。",
        "en": "Dry-run: nothing written. Add --yes to apply.",
    },
    "deployed": {
        "zh-CN": "已装入 profile。完全退出并重新打开该宿主后生效。AGENTS.md 未改。",
        "en": "Installed into the profile. Fully quit and reopen that host. AGENTS.md was not changed.",
    },
    "confirm_gate": {
        "zh-CN": "该操作需要 --yes。",
        "en": "This operation requires --yes.",
    },
    "no_manifest": {
        "zh-CN": "未发现 {TOOL_NAME} manifest,没有可卸载的部署。",
        "en": "No {TOOL_NAME} manifest found; nothing to uninstall.",
    },
    "uninstalled": {"zh-CN": "卸载完成。", "en": "Uninstalled."},
    "residue_blocks": {
        "zh-CN": "发现未完成事务残留,先运行 --recover: {path}",
        "en": "unfinished transaction residue found, run --recover first: {path}",
    },
    "no_residue": {"zh-CN": "无事务残留。", "en": "No transaction residue."},
    "recovered": {"zh-CN": "恢复完成。", "en": "Recovered."},
    "not_ready": {"zh-CN": "就绪判定: 未就绪", "en": "Readiness: not ready"},
    "ready": {"zh-CN": "就绪判定: 就绪", "en": "Readiness: ready"},
    "status_layer": {"zh-CN": "部署层", "en": "deployment layer"},
    "status_none": {"zh-CN": "无部署", "en": "no deployment"},
    "status_prev": {"zh-CN": "上一层 manifest", "en": "previous manifest layer"},
    "error_dir_missing": {
        "zh-CN": "DSH 目录不存在: {path}",
        "en": "DSH directory does not exist: {path}",
    },
    "error_file_missing": {
        "zh-CN": "指令文件不存在: {path}",
        "en": "instruction file does not exist: {path}",
    },
    "error_profile_missing": {
        "zh-CN": "profile 不存在: {path}",
        "en": "profile does not exist: {path}",
    },
    "error_plugin_src": {
        "zh-CN": "插件源不存在: {path}",
        "en": "plugin source missing: {path}",
    },
    "note_no_host_patch": {
        "zh-CN": "不改 @deepseek-ai node_modules，不自动重启。",
        "en": "Does not patch @deepseek-ai node_modules and does not restart the host.",
    },
    "file_overlay": {
        "zh-CN": "用外部文件覆盖契约: {path}",
        "en": "overlay contract from file: {path}",
    },
}


def _tr(key: str, **kwargs: Any) -> str:
    table = _STRINGS.get(key)
    if table is None:
        return key
    text = table.get(_OUTPUT_LANGUAGE) or table.get("zh-CN", key)
    values = {TOOL_NAME: TOOL_NAME, "version": VERSION}
    values.update(kwargs)
    return text.format_map(_SafeDict(values))


def _localized(zh: str, en: str) -> str:
    return zh if _OUTPUT_LANGUAGE == "zh-CN" else en


# ─── Paths ────────────────────────────────────────────────────────────────────


def _default_dsh_home() -> Path:
    env = os.environ.get(DSH_ENV_VAR)
    if env:
        return Path(env).expanduser()
    return Path.home() / ".dsh"


def _profile_dir(home: Path, profile: str) -> Path:
    return home / "profiles" / profile


def _manifest_path(home: Path) -> Path:
    return home / MANIFEST_FILENAME


def _plugin_dest(profile_dir: Path) -> Path:
    return profile_dir / "node_modules" / PLUGIN_NAME


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    return _sha256_bytes(path.read_bytes())


def _fingerprint(payload: Dict[str, Any]) -> str:
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return _sha256_bytes(blob)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_deployment_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{os.getpid():x}"


# ─── Profile mutation ─────────────────────────────────────────────────────────

INSERT_BLOCK = "- insert:\n    - id: dsh-keysmith\n      name: dsh-keysmith\n"


def drop_empty_sequence_document(text: str) -> str:
    """A lone `[]` after comments is an empty YAML document; appending
    `- insert:` after it is a parse error. Drop that token."""
    lines = [line for line in text.splitlines() if line.strip() != "[]"]
    body = "\n".join(lines)
    if text.endswith("\n"):
        if body:
            body += "\n"
        elif not lines:
            body = ""
    return body


def profile_has_keysmith_insert(text: str) -> bool:
    lines = text.splitlines()
    insert_indent = -1
    for line in lines:
        if line.startswith("- insert:") or line.lstrip().startswith("- insert:"):
            if line.strip() == "- insert:":
                insert_indent = len(line) - len(line.lstrip())
                continue
        if insert_indent < 0:
            continue
        indent = len(line) - len(line.lstrip())
        trimmed = line.strip()
        if trimmed and indent <= insert_indent and trimmed.startswith("- "):
            insert_indent = -1
            if trimmed == "- insert:":
                insert_indent = indent
            continue
        if trimmed == "- id: dsh-keysmith":
            return True
    return False


def ensure_insert(text: str) -> str:
    cleaned = drop_empty_sequence_document(text)
    if profile_has_keysmith_insert(cleaned):
        return cleaned if cleaned.endswith("\n") else cleaned + "\n"
    body = cleaned if cleaned.endswith("\n") or not cleaned else cleaned + "\n"
    if body and not body.endswith("\n"):
        body += "\n"
    if body.strip() and not body.endswith("\n\n"):
        body += "\n"
    return body + INSERT_BLOCK


def strip_insert(text: str) -> str:
    lines = text.splitlines()
    out: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip() == "- insert:":
            block = [line]
            base = len(line) - len(line.lstrip())
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                indent = len(nxt) - len(nxt.lstrip())
                trimmed = nxt.strip()
                if trimmed and indent <= base and trimmed.startswith("- ") and not trimmed.startswith("- insert:"):
                    break
                block.append(nxt)
                j += 1
            ids = [ln.strip() for ln in block if ln.strip().startswith("- id:")]
            if any(ln == "- id: dsh-keysmith" for ln in ids) and len(ids) <= 1:
                i = j
                continue
            out.extend(block)
            i = j
            continue
        out.append(line)
        i += 1
    result = "\n".join(out)
    if text.endswith("\n"):
        result += "\n"
    return result


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _ensure_stub_profile(profile_dir: Path) -> None:
    """Tests (and a never-booted home) get a web-shaped stub profile."""
    pkg_path = profile_dir / "package.json"
    if not pkg_path.exists():
        profile_dir.mkdir(parents=True, exist_ok=True)
        _write_json(
            pkg_path,
            {
                "name": f"dsh-profile-{profile_dir.name}",
                "private": True,
                "dsh": {
                    "profile": {
                        "bundles": [
                            "@deepseek-ai/dsh-base",
                            "@deepseek-ai/dsh-web-app",
                        ]
                    }
                },
            },
        )
    patch = profile_dir / "cordis.patch.yml"
    if not patch.exists():
        patch.write_text(
            "# Your patch layer for this dsh profile, applied after every bundle layer.\n",
            encoding="utf-8",
        )
    yml = profile_dir / "cordis.yml"
    if not yml.exists():
        yml.write_text("[]\n", encoding="utf-8")


def _copy_plugin(src: Path, dest: Path, contract_overlay: Optional[bytes] = None) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    if contract_overlay is not None:
        (dest / "lib" / "contract.md").write_bytes(contract_overlay)


def _bundles_of(pkg: Dict[str, Any]) -> List[str]:
    profile = (pkg.get("dsh") or {}).get("profile") or {}
    bundles = profile.get("bundles")
    return list(bundles) if isinstance(bundles, list) else []


def _set_bundles(pkg: Dict[str, Any], bundles: List[str]) -> Dict[str, Any]:
    dsh = pkg.setdefault("dsh", {})
    if not isinstance(dsh, dict):
        pkg["dsh"] = {}
        dsh = pkg["dsh"]
    profile = dsh.setdefault("profile", {})
    if not isinstance(profile, dict):
        dsh["profile"] = {}
        profile = dsh["profile"]
    profile["bundles"] = bundles
    return pkg


# ─── Manifest ─────────────────────────────────────────────────────────────────


def _load_manifest(home: Path) -> Optional[Dict[str, Any]]:
    path = _manifest_path(home)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _write_manifest(home: Path, manifest: Dict[str, Any]) -> None:
    _manifest_path(home).write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _resource_entry(path: Path, before: Optional[str], after: Optional[str]) -> Dict[str, Any]:
    return {
        "path": str(path),
        "before": {"sha256": before} if before else None,
        "after": {"sha256": after} if after else None,
        "backup": None,
    }


# ─── JSON envelope ────────────────────────────────────────────────────────────


def _json_dump(payload: Dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _json_report(
    operation: str,
    mode: str,
    ok: bool,
    exit_status: int,
    *,
    actions: Optional[List[Dict[str, str]]] = None,
    warnings: Optional[List[str]] = None,
    blockers: Optional[List[str]] = None,
    error: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "schema": JSON_SCHEMA,
        "version": VERSION,
        "operation": operation,
        "mode": mode,
        "ok": ok,
        "actions": actions or [],
        "warnings": warnings or [],
        "blockers": blockers or [],
        "exit_status": exit_status,
        "error": error,
    }
    if extra:
        payload.update(extra)
    return payload


def _json_action(action: str, path: Any, detail: str = "") -> Dict[str, str]:
    return {"action": action, "path": str(path), "detail": detail}


def _adapter_status_payload() -> Dict[str, Any]:
    """0.4.0 does not patch the llm adapter. Field kept for Switch."""
    return {
        "state": "absent",
        "path": None,
        "managed": False,
        "already_patched": None,
    }


def _plugin_live_state(profile_dir: Path) -> Tuple[bool, bool, bool]:
    dest = _plugin_dest(profile_dir)
    pkg = _read_json(profile_dir / "package.json") or {}
    in_bundles = PLUGIN_NAME in _bundles_of(pkg)
    patch = profile_dir / "cordis.patch.yml"
    inserted = profile_has_keysmith_insert(patch.read_text(encoding="utf-8")) if patch.is_file() else False
    copied = dest.is_dir() and (dest / "lib" / "index.js").is_file()
    return copied, in_bundles, inserted


def _deployment_state(home: Path, profile: str, manifest: Optional[Dict[str, Any]]) -> Tuple[str, List[str]]:
    if manifest is None:
        profile_dir = _profile_dir(home, profile)
        copied, in_bundles, inserted = _plugin_live_state(profile_dir)
        if copied or in_bundles or inserted:
            notes = []
            if not copied:
                notes.append("profile_plugin: missing plugin copy")
            if not in_bundles:
                notes.append("profile_bundles: dsh-keysmith not in bundles")
            if not inserted:
                notes.append("profile_insert: insert missing")
            return ("drift" if notes else "active"), notes
        return "not-installed", []
    notes: List[str] = []
    profile_dir = _profile_dir(home, manifest.get("profile") or profile)
    copied, in_bundles, inserted = _plugin_live_state(profile_dir)
    if not copied:
        notes.append("profile_plugin: missing since deploy")
    if not in_bundles:
        notes.append("profile_bundles: changed since deploy")
    if not inserted:
        notes.append("profile_insert: changed since deploy")
    return ("drift" if notes else "active"), notes


def _manifest_public(manifest: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if manifest is None:
        return None
    resources = {}
    for key in (RESOURCE_PLUGIN, RESOURCE_BUNDLES, RESOURCE_INSERT):
        entry = manifest.get(key)
        if entry is None:
            continue
        resources[key] = {
            "path": entry.get("path"),
            "backup": entry.get("backup"),
            "after_sha256": ((entry.get("after") or {}).get("sha256")),
        }
    return {
        "deployment_id": manifest.get("deployment_id"),
        "tool_version": manifest.get("tool_version"),
        "created_at": manifest.get("created_at"),
        "profile": manifest.get("profile"),
        "resources": resources,
        "previous_manifest": bool((manifest.get("previous_manifest") or {}).get("fingerprint")),
    }


# ─── Commands ─────────────────────────────────────────────────────────────────


def _cmd_status(home: Path, json_mode: bool, profile: str) -> int:
    manifest = _load_manifest(home)
    state, drift = _deployment_state(home, profile, manifest)
    ready = True
    if json_mode:
        _json_dump(
            _json_report(
                OPERATION_STATUS,
                "preview",
                True,
                0,
                extra={
                    "dsh_dir": str(home),
                    "dsh_dir_exists": home.exists(),
                    "profile": (manifest or {}).get("profile") or profile,
                    "ready": ready,
                    "state": state,
                    "drift": drift,
                    "residue": [],
                    "manifest": _manifest_public(manifest),
                    "adapter_patch": _adapter_status_payload(),
                },
            )
        )
        return 0
    print(_tr("banner"))
    print(f"{_tr('dsh_dir')}: {home}")
    print(f"{_tr('profile')}: {(manifest or {}).get('profile') or profile}")
    print(_tr("no_residue"))
    if manifest is None:
        print(f"{_tr('status_layer')}: {_tr('status_none')}")
    else:
        print(f"{_tr('status_layer')}: {manifest.get('deployment_id', '?')}")
        print(f"{_tr('status_prev')}: {bool((manifest.get('previous_manifest') or {}).get('fingerprint'))}")
    copied, in_bundles, inserted = _plugin_live_state(_profile_dir(home, (manifest or {}).get("profile") or profile))
    print(f"  plugin: {'yes' if copied else 'no'}  bundles: {'yes' if in_bundles else 'no'}  insert: {'yes' if inserted else 'no'}")
    print(_tr("ready") if ready else _tr("not_ready"))
    return 0


def _plan_actions(profile_dir: Path) -> List[Dict[str, str]]:
    dest = _plugin_dest(profile_dir)
    pkg = profile_dir / "package.json"
    patch = profile_dir / "cordis.patch.yml"
    actions = [
        _json_action("create" if not dest.exists() else "replace", dest, RESOURCE_PLUGIN),
        _json_action("update", pkg, RESOURCE_BUNDLES),
        _json_action("update", patch, RESOURCE_INSERT),
    ]
    return actions


def _cmd_deploy(
    home: Path,
    file_arg: Optional[str],
    yes: bool,
    json_mode: bool,
    profile: str,
) -> int:
    mode = "execute" if yes else "preview"
    if not home.exists():
        message = _tr("error_dir_missing", path=home)
        if json_mode:
            _json_dump(
                _json_report(
                    OPERATION_DEPLOY,
                    mode,
                    False,
                    2,
                    error=message,
                    blockers=[message],
                    extra={"dsh_dir": str(home), "dsh_dir_exists": False, "state": "not-installed"},
                )
            )
        else:
            print(message)
        return 2

    src = _plugin_src()
    if not (src / "lib" / "index.js").is_file():
        message = _tr("error_plugin_src", path=src)
        if json_mode:
            _json_dump(_json_report(OPERATION_DEPLOY, mode, False, 2, error=message, blockers=[message]))
        else:
            print(message)
        return 2

    overlay: Optional[bytes] = None
    if file_arg is not None:
        source = Path(file_arg).expanduser()
        if not source.is_file():
            message = _tr("error_file_missing", path=source)
            if json_mode:
                _json_dump(_json_report(OPERATION_DEPLOY, mode, False, 2, error=message, extra={"dsh_dir": str(home)}))
            else:
                print(message)
            return 2
        overlay = source.read_bytes()

    profile_dir = _profile_dir(home, profile)
    dest = _plugin_dest(profile_dir)
    pkg_path = profile_dir / "package.json"
    patch_path = profile_dir / "cordis.patch.yml"
    actions = _plan_actions(profile_dir)
    warnings = [_tr("note_no_host_patch")]
    if overlay is not None:
        warnings.append(_tr("file_overlay", path=file_arg))

    if not yes:
        if json_mode:
            _json_dump(
                _json_report(
                    OPERATION_DEPLOY,
                    "preview",
                    True,
                    0,
                    actions=actions,
                    warnings=warnings,
                    extra={
                        "dsh_dir": str(home),
                        "dsh_dir_exists": True,
                        "profile": profile,
                        "state": "not-installed",
                        "ready": True,
                        "adapter_patch": _adapter_status_payload(),
                    },
                )
            )
        else:
            print(_tr("banner"))
            print(f"{_tr('dsh_dir')}: {home}")
            print(f"{_tr('profile')}: {profile}")
            print(_tr("plan"))
            for item in actions:
                print(f"  {item['action']} {item['path']}")
            print(_tr("note_no_host_patch"))
            print(_tr("dry_run_no_write"))
        return 0

    previous = _load_manifest(home)
    _ensure_stub_profile(profile_dir)
    before_pkg = _sha256_file(pkg_path)
    before_patch = _sha256_file(patch_path)
    _copy_plugin(src, dest, overlay)
    pkg = _read_json(pkg_path) or {}
    bundles = _bundles_of(pkg)
    if PLUGIN_NAME not in bundles:
        bundles.append(PLUGIN_NAME)
        _set_bundles(pkg, bundles)
        _write_json(pkg_path, pkg)
    patch_text = patch_path.read_text(encoding="utf-8") if patch_path.is_file() else ""
    patch_path.write_text(ensure_insert(patch_text), encoding="utf-8")

    deployment_id = _new_deployment_id()
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "tool_version": VERSION,
        "deployment_id": deployment_id,
        "created_at": _utc_now(),
        "profile": profile,
        RESOURCE_PLUGIN: _resource_entry(dest, None, _sha256_file(dest / "lib" / "index.js")),
        RESOURCE_BUNDLES: _resource_entry(pkg_path, before_pkg, _sha256_file(pkg_path)),
        RESOURCE_INSERT: _resource_entry(patch_path, before_patch, _sha256_file(patch_path)),
        "previous_manifest": {
            "fingerprint": _fingerprint(previous) if previous else None,
            "deployment_id": (previous or {}).get("deployment_id"),
        },
    }
    _write_manifest(home, manifest)
    if json_mode:
        _json_dump(
            _json_report(
                OPERATION_DEPLOY,
                "execute",
                True,
                0,
                actions=actions,
                warnings=warnings,
                extra={
                    "dsh_dir": str(home),
                    "dsh_dir_exists": True,
                    "profile": profile,
                    "deployment_id": deployment_id,
                    "state": "active",
                    "ready": True,
                    "manifest": _manifest_public(manifest),
                    "adapter_patch": _adapter_status_payload(),
                },
            )
        )
    else:
        print(_tr("banner"))
        print(f"{_tr('dsh_dir')}: {home}")
        print(f"{_tr('profile')}: {profile}")
        print(_tr("deployed"))
    return 0


def _cmd_uninstall(home: Path, yes: bool, json_mode: bool, profile: str) -> int:
    mode = "execute" if yes else "preview"
    manifest = _load_manifest(home)
    if manifest is None:
        message = _tr("no_manifest")
        if json_mode:
            _json_dump(
                _json_report(
                    OPERATION_UNINSTALL,
                    mode,
                    False,
                    1,
                    error=message,
                    blockers=[message],
                    extra={"dsh_dir": str(home), "state": "not-installed", "adapter_patch": _adapter_status_payload()},
                )
            )
        else:
            print(message)
        return 1
    used_profile = str(manifest.get("profile") or profile)
    profile_dir = _profile_dir(home, used_profile)
    dest = _plugin_dest(profile_dir)
    pkg_path = profile_dir / "package.json"
    patch_path = profile_dir / "cordis.patch.yml"
    actions = [
        _json_action("delete", dest, RESOURCE_PLUGIN),
        _json_action("update", pkg_path, RESOURCE_BUNDLES),
        _json_action("update", patch_path, RESOURCE_INSERT),
        _json_action("delete", _manifest_path(home), "manifest"),
    ]
    if not yes:
        if json_mode:
            _json_dump(
                _json_report(
                    OPERATION_UNINSTALL,
                    "preview",
                    True,
                    0,
                    actions=actions,
                    extra={
                        "dsh_dir": str(home),
                        "profile": used_profile,
                        "state": "active",
                        "adapter_patch": _adapter_status_payload(),
                    },
                )
            )
        else:
            print(_tr("banner"))
            print(_tr("plan"))
            for item in actions:
                print(f"  {item['action']} {item['path']}")
            print(_tr("dry_run_no_write"))
        return 0

    if dest.exists():
        shutil.rmtree(dest)
    pkg = _read_json(pkg_path)
    if pkg is not None:
        bundles = [item for item in _bundles_of(pkg) if item != PLUGIN_NAME]
        _set_bundles(pkg, bundles)
        _write_json(pkg_path, pkg)
    if patch_path.is_file():
        patch_path.write_text(strip_insert(patch_path.read_text(encoding="utf-8")), encoding="utf-8")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    archived = _manifest_path(home).with_name(f"{MANIFEST_FILENAME}.uninstalled_{stamp}")
    shutil.move(str(_manifest_path(home)), str(archived))
    if json_mode:
        _json_dump(
            _json_report(
                OPERATION_UNINSTALL,
                "execute",
                True,
                0,
                actions=actions,
                extra={
                    "dsh_dir": str(home),
                    "profile": used_profile,
                    "state": "not-installed",
                    "adapter_patch": _adapter_status_payload(),
                },
            )
        )
    else:
        print(_tr("uninstalled"))
    return 0


def _cmd_recover(home: Path, yes: bool, json_mode: bool) -> int:
    """0.4.0 has no transaction journals. Recover is a documented no-op."""
    if json_mode:
        _json_dump(
            _json_report(
                OPERATION_RECOVER,
                "execute" if yes else "preview",
                True,
                0,
                extra={
                    "dsh_dir": str(home),
                    "dsh_dir_exists": home.exists(),
                    "residue": [],
                    "adapter_patch": _adapter_status_payload(),
                },
            )
        )
        return 0
    print(_tr("no_residue"))
    print(_tr("recovered") if yes else _tr("dry_run_no_write"))
    return 0


# ─── Argument parsing ─────────────────────────────────────────────────────────


def _prescan_language(argv: List[str]) -> str:
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("--zh", "--zh-CN"):
            return "zh-CN"
        if arg == "--en":
            return "en"
        if arg.startswith("--lang="):
            return _resolve_output_language(arg.split("=", 1)[1])
        if arg == "--lang" and i + 1 < len(argv):
            return _resolve_output_language(argv[i + 1])
        i += 1
    return _resolve_output_language("auto")


class _ContractArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> "None":
        _LAST_USAGE_ERROR[0] = message
        super().error(message)


def _usage_error_mode(argv: List[str]) -> str:
    return "preview" if "--yes" not in argv else "execute"


def _operation_from_argv(argv: List[str]) -> str:
    if "--status" in argv:
        return OPERATION_STATUS
    if "--uninstall" in argv:
        return OPERATION_UNINSTALL
    if "--recover" in argv:
        return OPERATION_RECOVER
    return OPERATION_DEPLOY


def _emit_usage_error_as_contract(operation: str, message: str, mode: str) -> None:
    _json_dump(
        _json_report(
            operation,
            mode,
            False,
            2,
            error=message,
            blockers=[message],
        )
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = _ContractArgumentParser(
        prog=TOOL_NAME,
        description=_localized(
            "把 DSH Keysmith Cordis 插件装进一个 profile。不写 AGENTS.md，不打宿主补丁。",
            "Install the DSH Keysmith Cordis plugin into a profile. Does not write AGENTS.md or patch the host.",
        ),
        add_help=True,
    )
    parser.add_argument("--file", "-f", metavar="PATH", help=_localized(
        "外部契约 Markdown，覆盖 plugin/lib/contract.md。",
        "External contract Markdown overlaying plugin/lib/contract.md.",
    ))
    parser.add_argument("--name", "-n", metavar="NAME", default="dsh-unrestricted", help=_localized(
        "审计输出名（安装目标仍是 profile 插件）。",
        "Audit output name (the install target stays the profile plugin).",
    ))
    parser.add_argument("--dsh-dir", metavar="DIR", default=None, help=_localized(
        "显式选择 DSH 配置目录 (默认 ~/.dsh 或 $DSH_HOME)。",
        "Explicitly select one DSH config directory (default ~/.dsh or $DSH_HOME).",
    ))
    parser.add_argument("--profile", metavar="NAME", default=DEFAULT_PROFILE, help=_localized(
        "要安装的 profile，默认 web。",
        "Profile to install into, default web.",
    ))
    parser.add_argument("--lang", default="auto", choices=["auto", "zh-CN", "en"], help=_localized(
        "CLI 输出语言,默认 auto。",
        "CLI output language, default auto.",
    ))
    parser.add_argument("--yes", action="store_true", help=_localized(
        "确认执行写入操作。",
        "Confirm the write operation.",
    ))
    parser.add_argument("--json", action="store_true", help=_localized(
        "输出稳定 JSON（dsh-keysmith/v1）。",
        "Emit stable JSON (dsh-keysmith/v1).",
    ))
    parser.add_argument("--version", action="version", version=f"{TOOL_NAME} {VERSION}")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true", help=_localized(
        "预览安装,不写入任何文件 (无 --yes 时的默认行为)。",
        "Preview install without writing (the default when --yes is absent).",
    ))
    group.add_argument("--status", action="store_true", help=_localized(
        "只读状态。",
        "Read-only status.",
    ))
    group.add_argument("--uninstall", action="store_true", help=_localized(
        "预览或移除最新安装层。",
        "Preview or remove the newest install layer.",
    ))
    group.add_argument("--recover", action="store_true", help=_localized(
        "预览或恢复中断的事务（0.4.0 无 journal，为空操作）。",
        "Preview or restore an interrupted transaction (no-op in 0.4.0).",
    ))
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    global _OUTPUT_LANGUAGE
    args_list = list(sys.argv[1:] if argv is None else argv)
    _OUTPUT_LANGUAGE = _prescan_language(args_list)
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass
    parser = _build_parser()
    json_requested = "--json" in args_list
    if json_requested:
        operation = _operation_from_argv(args_list)
        try:
            args = parser.parse_args(args_list)
        except SystemExit as exit_request:
            status = exit_request.code if isinstance(exit_request.code, int) else 2
            if status == 0:
                raise
            _emit_usage_error_as_contract(
                operation,
                _LAST_USAGE_ERROR[0] or "argument validation failed",
                _usage_error_mode(args_list),
            )
            return status
    else:
        args = parser.parse_args(args_list)

    _OUTPUT_LANGUAGE = _resolve_output_language(args.lang)

    if args.dsh_dir is not None:
        home = Path(args.dsh_dir).expanduser()
    else:
        home = _default_dsh_home()

    json_mode = bool(getattr(args, "json", False))
    profile = str(args.profile or DEFAULT_PROFILE)
    if args.status and args.yes:
        if json_mode:
            message = "status does not accept --yes"
            _json_dump(
                _json_report(
                    OPERATION_STATUS,
                    "execute",
                    False,
                    2,
                    error=message,
                    blockers=[message],
                    extra={"dsh_dir": str(home)},
                )
            )
        else:
            print(_tr("confirm_gate"))
        return 2

    if args.status:
        return _cmd_status(home, json_mode, profile)
    if args.uninstall:
        return _cmd_uninstall(home, args.yes, json_mode, profile)
    if args.recover:
        return _cmd_recover(home, args.yes, json_mode)
    return _cmd_deploy(home, args.file, args.yes, json_mode, profile)


if __name__ == "__main__":
    raise SystemExit(main())
