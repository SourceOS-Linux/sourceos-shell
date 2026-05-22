#!/usr/bin/env python3
"""Validate workspace-ops example JSON files against their JSON Schemas.

Mirrors the structure of scripts/validate_ops_history_receipts.py.
"""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = ROOT / "examples" / "workspace-ops"

SCHEMAS = {
    "workspace-operation-state": ROOT / "schemas" / "workspace-operation-state.schema.json",
    "operation-command": ROOT / "schemas" / "operation-command.schema.json",
    "diagnostics-export": ROOT / "schemas" / "diagnostics-export.schema.json",
}

# Map example filename prefix to schema key
PREFIX_TO_SCHEMA = {
    "workspace-operation-state": "workspace-operation-state",
    "operation-command": "operation-command",
    "diagnostics-export": "diagnostics-export",
}


def _schema_for(path: Path) -> dict:
    for prefix, key in PREFIX_TO_SCHEMA.items():
        if path.name.startswith(prefix):
            schema_path = SCHEMAS[key]
            return json.loads(schema_path.read_text(encoding="utf-8"))
    raise ValueError(f"No schema mapping found for example file: {path.name}")


def _check_workspace_operation_state(data: dict, path: Path) -> None:
    """Enforce invariants beyond what JSON Schema can express."""
    if not data.get("stateId", "").startswith("urn:srcos:workspace-op-state:"):
        raise ValueError(f"{path}: stateId must start with 'urn:srcos:workspace-op-state:'")
    if not data.get("policyDecisionRefs"):
        raise ValueError(f"{path}: policyDecisionRefs must be non-empty")


def _check_operation_command(data: dict, path: Path) -> None:
    if not data.get("commandId", "").startswith("urn:srcos:op-command:"):
        raise ValueError(f"{path}: commandId must start with 'urn:srcos:op-command:'")
    if not data.get("policyDecisionRefs"):
        raise ValueError(f"{path}: policyDecisionRefs must be non-empty")


def _check_diagnostics_export(data: dict, path: Path) -> None:
    if not data.get("redactionApplied"):
        raise ValueError(f"{path}: redactionApplied must be true")
    if data.get("contentCaptureEnabled") is not False:
        raise ValueError(f"{path}: contentCaptureEnabled must be false")
    if data.get("payloadMode") == "redacted" and not data.get("redactionRefs"):
        raise ValueError(f"{path}: redacted exports must include redactionRefs")
    if not data.get("policyDecisionRefs"):
        raise ValueError(f"{path}: policyDecisionRefs must be non-empty")


EXTRA_CHECKS = {
    "workspace-operation-state": _check_workspace_operation_state,
    "operation-command": _check_operation_command,
    "diagnostics-export": _check_diagnostics_export,
}


def validate_example(path: Path) -> str:
    schema = _schema_for(path)
    jsonschema.validators.validator_for(schema).check_schema(schema)
    data = json.loads(path.read_text(encoding="utf-8"))
    jsonschema.validate(data, schema)
    for prefix, key in PREFIX_TO_SCHEMA.items():
        if path.name.startswith(prefix):
            EXTRA_CHECKS[key](data, path)
            break
    return path.name


def main() -> int:
    examples = sorted(EXAMPLE_DIR.glob("*.example.json"))
    if not examples:
        raise SystemExit("No workspace-ops example files found")
    checked = [validate_example(path) for path in examples]
    print(json.dumps({"ok": True, "checked": checked}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
