#!/usr/bin/env python3
"""Minimal CI policy gate for SourceOS Helper Causal Receipts.

This intentionally checks high-value invariants first:
- every event has a root intent
- helper spawns declare parent/process/trigger/reason/policy
- capability requests declare decision/classification/data_accessed
- local-only profiles do not allow network, DNS, analytics, pasteboard, or account lookup
"""

from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys
from typing import Iterable

LOCAL_ONLY_PROFILES = {
    "preview.local_only.v1",
    "preview.web_thumbnail.local_only.v1",
    "terminal.preview.local_only.v1",
    "cache_cleanup.local_only.v1",
    "file_picker.native_ui.v1",
}

DENY_IN_LOCAL_ONLY = {
    "network.egress",
    "dns.lookup",
    "analytics.emit",
    "pasteboard.read",
    "pasteboard.write",
    "account.lookup",
    "credentials.keychain.lookup",
}


def iter_events(path: Path) -> Iterable[dict]:
    if path.suffix == ".jsonl":
        for line in path.read_text(errors="replace").splitlines():
            if line.strip():
                yield json.loads(line)
    else:
        data = json.loads(path.read_text(errors="replace"))
        if isinstance(data, list):
            yield from data
        else:
            yield data


def check_event(ev: dict) -> list[str]:
    errors: list[str] = []

    if not str(ev.get("root_intent_id", "")).startswith("intent."):
        errors.append("root_intent_id must start with 'intent.'.")

    event_type = ev.get("event_type")

    if event_type == "helper.spawn":
        for field in ["parent_process", "child_process", "trigger", "spawn_reason", "policy_profile"]:
            if field not in ev or ev.get(field) in (None, ""):
                errors.append(f"helper.spawn missing {field}")

    if event_type == "capability.request":
        for field in ["requestor", "capability", "requested_service", "decision", "classification", "data_accessed"]:
            if field not in ev:
                errors.append(f"capability.request missing {field}")

        if ev.get("policy_profile") in LOCAL_ONLY_PROFILES:
            if ev.get("capability") in DENY_IN_LOCAL_ONLY and ev.get("decision") == "allow":
                errors.append(
                    f"local-only policy {ev.get('policy_profile')} allowed forbidden capability {ev.get('capability')}"
                )

    if event_type == "helper.exit":
        for field in ["process", "exit_status", "duration_ms", "receipt_complete"]:
            if field not in ev:
                errors.append(f"helper.exit missing {field}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    failures: list[dict] = []
    checked = 0

    for path in args.paths:
        for index, event in enumerate(iter_events(path)):
            checked += 1
            for error in check_event(event):
                failures.append({"path": str(path), "index": index, "error": error})

    print(json.dumps({"checked": checked, "errors": failures}, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
