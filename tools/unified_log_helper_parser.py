#!/usr/bin/env python3
"""Unified-log-style helper receipt parser.

Converts macOS unified-log style text into conservative Helper Causal Receipt
candidate events. This tool is intentionally observational: it reconstructs
visible lifecycle/capability patterns from text and does not claim private OS
subsystem ground truth.
"""

from __future__ import annotations

from pathlib import Path
import argparse
import json
import re
import uuid
from typing import Optional

LINE_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)\s+"
    r"(?:\((?P<context>[^)]*)\)\s+)?"
    r"<(?P<severity>[^>]+)>:\s+"
    r"(?P<msg>.*)$"
)
PID_RE = re.compile(r"(?:pid/|\[)(?P<pid>\d+)")
SERVICE_NAME_RE = re.compile(r"name = (?P<name>[^,\s]+)")
REQUESTOR_RE = re.compile(r"requestor = (?P<requestor>[^,\s]+)")
XPCPROXY_RE = re.compile(r"xpcproxy spawned with pid (?P<pid>\d+)")
EXIT_DURATION_RE = re.compile(r"ran for (?P<ms>\d+)ms")
UUIDISH_RE = re.compile(r"([A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12})", re.I)

SERVICE_FAMILY_RULES = [
    ("mdworker", "spotlight_metadata_indexing", "indexer.metadata_local.v1", "metadata_index_worker"),
    ("CacheDelete", "cache_cleanup", "cache_cleanup.local_only.v1", "cache_cleanup"),
    ("CacheExtension", "cache_cleanup", "cache_cleanup.local_only.v1", "cache_cleanup"),
    ("WebKit", "web_thumbnail_or_webkit_helper", "preview.web_thumbnail.local_only.v1", "web_runtime_helper"),
    ("WebThumbnail", "web_thumbnail_or_webkit_helper", "preview.web_thumbnail.local_only.v1", "web_thumbnail_helper"),
    ("QuickLook", "quicklook_preview_rendering", "preview.local_only.v1", "preview_ui_or_thumbnail"),
    ("CGPDFService", "quicklook_preview_rendering", "preview.local_only.v1", "pdf_rendering_helper"),
    ("ImageIOXPCService", "quicklook_preview_rendering", "preview.local_only.v1", "image_decode_helper"),
    ("ThumbnailExtension", "quicklook_preview_rendering", "preview.local_only.v1", "thumbnail_helper"),
    ("screencapture", "screenshot_capture", "screenshot.capture_receipt.v1", "screenshot_capture_ui"),
    ("openAndSavePanelService", "native_file_picker", "file_picker.native_ui.v1", "native_file_picker"),
    ("AXVisualSupportAgent", "accessibility_ui_support", "accessibility.ui_support.v1", "accessibility_visual_support"),
    ("com.apple.accessibility", "accessibility_ui_support", "accessibility.ui_support.v1", "accessibility_service"),
    ("com.apple.filesystems.netfs", "filesystem_netfs_plugin", "filesystem.netfs_plugin.v1", "network_filesystem_plugin"),
    ("PlugInLibraryService", "filesystem_netfs_plugin", "filesystem.netfs_plugin.v1", "plugin_library_service"),
    ("iconservices", "iconservices_rendering", "iconservices.rendering_local.v1", "icon_rendering_service"),
    ("AudioComponentRegistrar", "audio_component_discovery", "audio.component_scan_local.v1", "audio_component_registry"),
    ("CarbonComponentScanner", "audio_component_discovery", "audio.component_scan_local.v1", "audio_component_scanner"),
    ("trustd", "trust_and_certificate_services", "trust.security_local.v1", "certificate_trust_service"),
    ("secinitd", "trust_and_certificate_services", "trust.security_local.v1", "security_initialization"),
    ("amfid", "security_integrity_sidecar", "security.scan_local.v1", "code_integrity"),
    ("XProtect", "security_integrity_sidecar", "security.scan_local.v1", "malware_protection"),
    ("CloudTelemetry", "telemetry_sidecar", "telemetry.local_metric.v1", "telemetry_service"),
    ("ecosystemanalytics", "telemetry_sidecar", "telemetry.local_metric.v1", "ecosystem_analytics"),
    ("geod", "location_services", "location.service_deny_by_default.v1", "location_service"),
    ("appleaccountd", "account_identity_services", "account.identity_deny_by_default.v1", "account_identity_service"),
    ("iCloudNotificationAgent", "cloud_notification_services", "cloud_notification_deny_by_default.v1", "icloud_notification_agent"),
    ("WorkflowKit", "workflow_background_shortcuts", "workflow.background_shortcut.v1", "background_shortcut_runner"),
    ("MTLCompilerService", "metal_shader_compilation", "gpu.shader_compile_local.v1", "metal_compiler_service"),
    ("swcd", "shared_web_credentials", "web_credentials_deny_by_default.v1", "shared_web_credentials_daemon"),
]

CAPABILITY_RULES = [
    ("pasteboard", "pasteboard.read", "high"),
    ("analyticsd", "analytics.emit", "high"),
    ("ecosystemanalyticsd", "analytics.emit", "high"),
    ("tccd", "privacy.tcc.lookup", "high"),
    ("distributed_notifications", "notifications.distributed.lookup", "medium"),
    ("webprivacyd", "privacy.web.lookup", "high"),
    ("PowerManagement", "power.management.lookup", "medium"),
    ("CARenderServer", "render.ca_server.lookup", "medium"),
    ("windowserver", "windowserver.lookup", "high"),
    ("dock", "dock.lookup", "low"),
    ("LaunchServices", "launchservices.lookup", "medium"),
    ("coreservices", "coreservices.lookup", "medium"),
    ("FileProvider", "fileprovider.lookup", "high"),
    ("CloudTelemetry", "telemetry.cloud.lookup", "high"),
    ("XProtect", "security.xprotect.lookup", "medium"),
    ("MobileFileIntegrity", "security.code_integrity.lookup", "medium"),
    ("Keychain", "credentials.keychain.lookup", "critical"),
    ("securityd", "security.service.lookup", "high"),
    ("apsd", "push_notifications.lookup", "medium"),
    ("geod", "location.service.lookup", "critical"),
]


def new_event_id() -> str:
    return "evt_" + uuid.uuid4().hex


def service_key(context: str) -> str:
    return re.sub(r"\s+\[\d+\]$", "", context or "global")


def family_for(text: str) -> tuple[str, str, str]:
    low = text.lower()
    for needle, phase, policy, role in SERVICE_FAMILY_RULES:
        if needle.lower() in low:
            return phase, policy, role
    return "unknown_or_general_launchd_churn", "unknown", "unknown"


def capability_for(service_name: str) -> tuple[str, str]:
    low = service_name.lower()
    for needle, cap, sensitivity in CAPABILITY_RULES:
        if needle.lower() in low:
            return cap, sensitivity
    return "mach_service.lookup", "unknown"


def base_event(ts: str, context: str, msg: str, severity: str, line_no: int) -> dict:
    pid_match = PID_RE.search(context or "") or PID_RE.search(msg)
    pid = int(pid_match.group("pid")) if pid_match else None
    uuid_match = UUIDISH_RE.search((context or "") + " " + msg)
    phase, policy_profile, role = family_for((context or "") + " " + msg)
    return {
        "schema": "sourceos.helper_causal_receipt.v0.1",
        "event_id": new_event_id(),
        "timestamp": ts,
        "root_intent_id": "intent.imported_log.analysis.synthetic",
        "raw_message": msg,
        "pid": pid,
        "line_no": line_no,
        "service_key": service_key(context or "global"),
        "service_uuid": uuid_match.group(1) if uuid_match else None,
        "phase": phase,
        "policy_profile": policy_profile,
        "service_family_role": role,
        "source_severity": severity,
    }


def classify(parsed: dict, line_no: int) -> Optional[dict]:
    context = parsed.get("context") or "global"
    msg = parsed["msg"]
    base = base_event(parsed["ts"], context, msg, parsed["severity"], line_no)
    child = base["service_key"].split("/")[-1].split(" [")[0]

    if "internal event: WILL_SPAWN" in msg:
        return {**base, "event_type": "helper.spawn", "lifecycle_state": "will_spawn", "parent_event_id": None, "parent_process": context, "child_process": child, "trigger": "ipc_or_launchd", "spawn_reason": "Demand-spawned helper candidate observed in unified log", "classification": "unknown", "inference_confidence": "medium", "severity": "trace"}

    xpc = XPCPROXY_RE.search(msg)
    if xpc:
        return {**base, "event_type": "helper.spawn", "lifecycle_state": "xpcproxy_spawned", "parent_event_id": None, "parent_process": context, "child_process": child, "pid": int(xpc.group("pid")), "trigger": "xpcproxy", "spawn_reason": "xpcproxy materialized helper process", "classification": "unknown", "inference_confidence": "high", "severity": "trace"}

    if "SOURCE_ATTACH" in msg:
        return {**base, "event_type": "helper.spawn", "lifecycle_state": "source_attach", "parent_event_id": None, "parent_process": context, "child_process": child, "trigger": "source_attach", "spawn_reason": "IPC/event source attached to helper", "classification": "unknown", "inference_confidence": "medium", "severity": "trace"}

    if "service state: running" in msg or "internal event: INIT" in msg or "job state = running" in msg:
        return {**base, "event_type": "helper.spawn", "lifecycle_state": "running_or_init", "parent_event_id": None, "parent_process": context, "child_process": child, "trigger": "init", "spawn_reason": "Helper entered running/initialized state", "classification": "unknown", "inference_confidence": "medium", "severity": "trace"}

    if "denied lookup" in msg or "failed lookup" in msg:
        service_match = SERVICE_NAME_RE.search(msg)
        requestor_match = REQUESTOR_RE.search(msg)
        service = service_match.group("name") if service_match else "unknown"
        capability, sensitivity = capability_for(service)
        denied = "denied lookup" in msg
        return {**base, "event_type": "capability.request", "requestor": requestor_match.group("requestor") if requestor_match else context, "capability": capability, "capability_sensitivity": sensitivity, "requested_service": service, "decision": "deny" if denied else "missing", "classification": "expected_denial" if denied else "missing_service", "policy_rule": f"{base['policy_profile']}.default_deny" if denied else None, "data_accessed": False, "inference_confidence": "high" if denied else "medium", "severity": "notice"}

    teardown_rules = [
        ("Operation already in progress", "duplicate_activation_coalesced", "Duplicate activation request while helper already active"),
        ("no client port found", "client_endpoint_missing_after_teardown", "Client disappeared before service reply completed"),
        ("invalid client reply port", "invalid_reply_endpoint_after_teardown", "Reply endpoint invalid during cleanup"),
        ("job not found", "service_removed_before_reply", "Service exited before late lookup/reply completed"),
        ("ENOSERVICE", "service_removed_before_reply", "Service exited before late lookup/reply completed"),
    ]
    for needle, normalized_class, meaning in teardown_rules:
        if needle in msg:
            classification = "teardown_race" if "reply" in normalized_class or "teardown" in normalized_class else "duplicate_activation_coalesced"
            return {**base, "event_type": "teardown.normalized", "normalized_class": normalized_class, "meaning": meaning, "receipt_complete": True, "policy_impact": "none", "classification": classification, "inference_confidence": "medium", "severity": "notice"}

    if "exited due to" in msg:
        duration_match = EXIT_DURATION_RE.search(msg)
        status = "clean" if "exit(0)" in msg else "supervisor_kill" if "SIGKILL" in msg else "unknown_exit"
        classification = "supervisor_worker_lifecycle_kill" if "SIGKILL" in msg and ("mds[" in msg or "launchd" in msg) else "unknown"
        return {**base, "event_type": "helper.exit", "lifecycle_state": "exited", "process": context, "exit_status": status, "duration_ms": int(duration_match.group("ms")) if duration_match else 0, "children_cleaned": None, "unexpected_denials": None, "network_used": None, "receipt_complete": True, "classification": classification, "inference_confidence": "high" if duration_match else "medium", "severity": "trace" if status == "clean" else "notice"}

    return None


def parse_text(text: str) -> list[dict]:
    events = []
    for line_no, line in enumerate(text.splitlines(), 1):
        match = LINE_RE.match(line)
        if not match:
            continue
        event = classify(match.groupdict(), line_no)
        if event:
            events.append(event)
    return events


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--jsonl", type=Path, required=True)
    args = parser.parse_args()

    events = parse_text(args.input.read_text(errors="replace"))
    with args.jsonl.open("w") as handle:
        for event in events:
            handle.write(json.dumps(event, sort_keys=True) + "\n")

    print(json.dumps({"events": len(events)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
