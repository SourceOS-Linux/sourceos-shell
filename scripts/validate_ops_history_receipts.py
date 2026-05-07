#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "ops-history-receipt.schema.json"
EXAMPLE_DIR = ROOT / "examples" / "ops-history"


def validate_example(path: Path, schema: dict) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    jsonschema.validate(data, schema)
    if data.get("contentCaptureEnabled") is not False:
        raise ValueError(f"{path}: contentCaptureEnabled must default false")
    if data.get("payloadMode") == "redacted" and not data.get("redactionRefs"):
        raise ValueError(f"{path}: redacted receipts must include redactionRefs")
    return path.name


def main() -> int:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validators.validator_for(schema).check_schema(schema)
    examples = sorted(EXAMPLE_DIR.glob("receipt.*.example.json"))
    if not examples:
        raise SystemExit("No OpsHistory receipt examples found")
    checked = [validate_example(path, schema) for path in examples]
    print(json.dumps({"ok": True, "checked": checked}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
