#!/usr/bin/env python3
"""Deterministic release builder for dsh-keysmith.

Builds from a clean, tagged tree:
    python3 scripts/build_release.py --tag v0.1.0 --out dist/

Produces:
    dsh-keysmith-vX.Y.Z.py        standalone single-file CLI
    dsh-keysmith-vX.Y.Z.zip       full source tree
    dsh-keysmith-vX.Y.Z.tar.gz    full source tree
    SHA256SUMS

Deterministic properties: fixed mtimes (epoch), sorted member order, no
absolute paths. Refuses: shallow clones, dirty trees, tags not pointing at
HEAD, malformed tag formats.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import os
import re
import subprocess
import tarfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
FIXED_TIME = datetime(1980, 1, 1, tzinfo=timezone.utc).timestamp()

INCLUDED_PATHS = [
    "dsh-keysmith.py",
    "VERSION",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "LICENSE",
    "README.md",
    "pyproject.toml",
    "requirements-quality.txt",
    ".gitignore",
    ".gitattributes",
    "examples/",
    "plugins/",
    "scripts/",
    "docs/",
    "tests/",
    ".github/",
]


def _git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _check_tree(tag: str) -> None:
    if not TAG_RE.match(tag):
        raise SystemExit(f"tag must match vX.Y.Z: {tag!r}")
    # Dirty tree: the builder may auto-commit on an explicit request only.
    status = _git(["status", "--porcelain"])
    if status:
        raise SystemExit("working tree is dirty; commit or stash first")
    if _git(["rev-parse", "--is-shallow-repository"]) == "true":
        raise SystemExit("shallow clone; fetch full history first")
    head = _git(["rev-parse", "HEAD"])
    try:
        tagged = _git(["rev-parse", tag + "^{commit}"])
    except SystemExit:
        raise SystemExit(f"tag {tag} does not exist") from None
    if head != tagged:
        raise SystemExit(f"tag {tag} does not point at HEAD ({head[:12]} != {tagged[:12]})")
    tag_line = _git(["tag", "-l", tag])
    if tag_line != tag:
        raise SystemExit(f"tag {tag} not found")


def _collect_files() -> list[Path]:
    files: list[Path] = []
    for pattern in INCLUDED_PATHS:
        path = REPO_ROOT / pattern
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file() and ".pytest_cache" not in child.parts:
                    files.append(child)
    return sorted(files, key=lambda p: str(p.relative_to(REPO_ROOT)).replace(os.sep, "/"))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_zip(out: Path, tag: str, files: list[tuple[str, bytes]]) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in files:
            info = zipfile.ZipInfo(name=f"dsh-keysmith-{tag}/{name}", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, data)
    out.write_bytes(buffer.getvalue())


def _write_tar(out: Path, tag: str, files: list[tuple[str, bytes]]) -> None:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tf:
        for name, data in files:
            info = tarfile.TarInfo(name=f"dsh-keysmith-{tag}/{name}")
            info.size = len(data)
            info.mtime = int(FIXED_TIME)
            info.mode = 0o644
            tf.addfile(info, io.BytesIO(data))
    out.write_bytes(buffer.getvalue())


def build(tag: str, out_dir: Path) -> int:
    _check_tree(tag)
    out_dir.mkdir(parents=True, exist_ok=True)
    version = tag[1:]
    paths = _collect_files()
    entries: list[tuple[str, bytes]] = []
    for path in paths:
        rel = str(path.relative_to(REPO_ROOT)).replace(os.sep, "/")
        data = path.read_bytes()
        if rel == "VERSION":
            data = (version + "\n").encode("utf-8")
        if rel == "dsh-keysmith.py":
            # Normalize the embedded version to the tag.
            text = data.decode("utf-8")
            import re as _re

            text = _re.sub(r'__version__ = "[^"]+"', f'__version__ = "{version}"', text, count=1)
            data = text.encode("utf-8")
        entries.append((rel, data))

    cli_data = (REPO_ROOT / "dsh-keysmith.py").read_bytes()
    standalone = out_dir / f"dsh-keysmith-{tag}.py"
    standalone.write_bytes(cli_data)
    os.chmod(standalone, 0o755)

    zip_path = out_dir / f"dsh-keysmith-{tag}.zip"
    _write_zip(zip_path, tag, entries)
    tar_path = out_dir / f"dsh-keysmith-{tag}.tar.gz"
    _write_tar(tar_path, tag, entries)

    sums = []
    for path in (standalone, zip_path, tar_path):
        sums.append(f"{_sha256(path.read_bytes())}  {path.name}")
    (out_dir / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
    print(f"built {len(entries)} entries for {tag} into {out_dir}/")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="dsh-keysmith release builder")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--out", default="dist")
    args = parser.parse_args()
    return build(args.tag, Path(args.out).resolve())


if __name__ == "__main__":
    raise SystemExit(main())
