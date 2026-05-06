#!/usr/bin/env python3
"""Helper Causal Receipt DAG correlator.

Reads JSONL emitted by `tools/unified_log_helper_parser.py` and builds a conservative
DAG. The graph is intentionally observational:

- phase containment edges group events by inferred subsystem family
- same-PID edges preserve chronological process-local continuity
- same-service edges preserve service-key continuity
- lifecycle edges connect spawn/init/exit progressions
- nearby capability edges connect service lookups to recent same-PID helper lifecycle events

The correlator does not claim private OS intent; it reconstructs visible evidence
for user-facing explanation and policy review.
"""

from __future__ import annotations

from pathlib import Path
import argparse
from collections import Counter, defaultdict
from datetime import datetime
import json
from typing import Any


def ts_float(timestamp: str) -> float:
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(timestamp, fmt).timestamp()
        except ValueError:
            continue
    return 0.0


def load_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in path.read_text(errors="replace").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events


def build_dag(events: list[dict[str, Any]]) -> dict[str, Any]:
    events = sorted(events, key=lambda ev: (ts_float(ev.get("timestamp", "")), ev.get("line_no", 0)))

    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []

    root_id = "root:intent.imported_log.analysis.synthetic"
    nodes[root_id] = {
        "id": root_id,
        "type": "root_intent",
        "label": "Imported unified-log helper receipt analysis",
    }

    for event in events:
        phase = event.get("phase", "unknown_or_general_launchd_churn")
        phase_id = f"phase:{phase}"
        if phase_id not in nodes:
            nodes[phase_id] = {
                "id": phase_id,
                "type": "phase",
                "label": phase.replace("_", " "),
                "phase": phase,
            }
            edges.append({"source": root_id, "target": phase_id, "type": "contains_phase"})

        event_id = event["event_id"]
        nodes[event_id] = {
            "id": event_id,
            "type": event.get("event_type"),
            "timestamp": event.get("timestamp"),
            "line_no": event.get("line_no"),
            "label": event.get("lifecycle_state") or event.get("capability") or event.get("normalized_class") or event.get("event_type"),
            "pid": event.get("pid"),
            "service_key": event.get("service_key"),
            "service_uuid": event.get("service_uuid"),
            "phase": phase,
            "policy_profile": event.get("policy_profile"),
            "service_family_role": event.get("service_family_role"),
            "capability": event.get("capability"),
            "requested_service": event.get("requested_service"),
            "decision": event.get("decision"),
            "classification": event.get("classification"),
            "lifecycle_state": event.get("lifecycle_state"),
            "exit_status": event.get("exit_status"),
            "duration_ms": event.get("duration_ms"),
            "severity": event.get("severity"),
            "inference_confidence": event.get("inference_confidence"),
        }
        edges.append({"source": phase_id, "target": event_id, "type": "contains_event"})

    by_pid: dict[int, list[dict[str, Any]]] = defaultdict(list)
    by_service: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for event in events:
        if event.get("pid") is not None:
            by_pid[int(event["pid"])].append(event)
        if event.get("service_key"):
            by_service[str(event["service_key"])].append(event)

    for pid, pid_events in by_pid.items():
        pid_events = sorted(pid_events, key=lambda ev: (ts_float(ev.get("timestamp", "")), ev.get("line_no", 0)))
        for previous, current in zip(pid_events, pid_events[1:]):
            edges.append({
                "source": previous["event_id"],
                "target": current["event_id"],
                "type": "same_pid_next_event",
                "pid": pid,
            })

    lifecycle_order = {
        "will_spawn": 1,
        "xpcproxy_spawned": 2,
        "source_attach": 3,
        "running_or_init": 4,
        "exited": 5,
    }

    for service_key, service_events in by_service.items():
        service_events = sorted(service_events, key=lambda ev: (ts_float(ev.get("timestamp", "")), ev.get("line_no", 0)))

        for previous, current in zip(service_events, service_events[1:]):
            edges.append({
                "source": previous["event_id"],
                "target": current["event_id"],
                "type": "same_service_next_event",
                "service_key": service_key,
            })

        lifecycle_events = [event for event in service_events if event.get("lifecycle_state")]
        for previous, current in zip(lifecycle_events, lifecycle_events[1:]):
            previous_order = lifecycle_order.get(previous.get("lifecycle_state"), 99)
            current_order = lifecycle_order.get(current.get("lifecycle_state"), 99)
            edge_type = "lifecycle_progression" if current_order >= previous_order else "lifecycle_loop_or_reactivation"
            edges.append({
                "source": previous["event_id"],
                "target": current["event_id"],
                "type": edge_type,
                "service_key": service_key,
            })

    prior_lifecycle_by_pid: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        if event.get("event_type") in {"helper.spawn", "helper.exit"} and event.get("pid") is not None:
            prior_lifecycle_by_pid[int(event["pid"])].append(event)

    for event in events:
        if event.get("event_type") != "capability.request" or event.get("pid") is None:
            continue
        candidates: list[tuple[float, dict[str, Any]]] = []
        for candidate in prior_lifecycle_by_pid.get(int(event["pid"]), []):
            delta = ts_float(event.get("timestamp", "")) - ts_float(candidate.get("timestamp", ""))
            if 0 <= delta <= 10:
                candidates.append((delta, candidate))
        if candidates:
            _, nearest = sorted(candidates, key=lambda item: item[0])[0]
            edges.append({
                "source": nearest["event_id"],
                "target": event["event_id"],
                "type": "nearby_pid_capability_request",
                "pid": event.get("pid"),
            })

    summary = {
        "event_count": len(events),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "event_type_counts": dict(Counter(event.get("event_type") for event in events)),
        "phase_counts": dict(Counter(event.get("phase", "unknown_or_general_launchd_churn") for event in events)),
        "policy_profile_counts": dict(Counter(event.get("policy_profile", "unknown") for event in events)),
        "service_family_role_counts": dict(Counter(event.get("service_family_role", "unknown") for event in events)),
        "capability_counts": dict(Counter(event.get("capability") for event in events if event.get("capability"))),
        "lifecycle_state_counts": dict(Counter(event.get("lifecycle_state") for event in events if event.get("lifecycle_state"))),
        "edge_type_counts": dict(Counter(edge["type"] for edge in edges)),
    }

    return {
        "schema": "sourceos.helper_causal_receipt_dag.v0.1",
        "root_intent_id": "intent.imported_log.analysis.synthetic",
        "summary": summary,
        "nodes": list(nodes.values()),
        "edges": edges,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    dag = build_dag(load_events(args.jsonl))
    args.out.write_text(json.dumps(dag, indent=2, sort_keys=True))
    print(json.dumps(dag["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
