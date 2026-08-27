#!/usr/bin/env python3
"""Offline prompt-bank contract validation for dsh-keysmith.

Validates every case in tests/prompt_bank/cases.json against the bundled
prompt (source: builtin). Live-API mode is intentionally absent: the
contract is about the prompt text itself, not a model response.

Usage:
    python3 scripts/run_prompt_bank_regression.py --validate-only
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPT_BANK = REPO_ROOT / "tests" / "prompt_bank" / "cases.json"


def _load_builtin_prompt() -> str:
    import importlib.util

    cli_path = REPO_ROOT / "dsh-keysmith.py"
    spec = importlib.util.spec_from_file_location("dsh_keysmith_cli", cli_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.BUILTIN_DSH_UNRESTRICTED_MD


def validate_only() -> int:
    data = json.loads(PROMPT_BANK.read_text(encoding="utf-8"))
    prompt = _load_builtin_prompt()
    failures = []
    for case in data["cases"]:
        case_id = case["id"]
        for token in case.get("required_tokens", []):
            if token not in prompt:
                failures.append(f"{case_id}: missing required token {token!r}")
        for token in case.get("forbidden_tokens", []):
            if token in prompt:
                failures.append(f"{case_id}: forbidden token present {token!r}")
        first_line = case.get("expected_first_line")
        if first_line is not None:
            actual = prompt.splitlines()[0] if prompt.splitlines() else ""
            if actual != first_line:
                failures.append(f"{case_id}: first line mismatch: {actual!r}")
    if failures:
        for line in failures:
            print(f"FAIL {line}", file=sys.stderr)
        return 1
    print(f"prompt bank: {len(data['cases'])} cases OK (source={data['prompt_source']})")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="dsh-keysmith prompt bank regression")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if not args.validate_only:
        print("only --validate-only is supported", file=sys.stderr)
        return 2
    return validate_only()


if __name__ == "__main__":
    raise SystemExit(main())
