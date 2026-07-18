# ADR-035 Compliance Examples for SourceOS Shell

ADR-035 (Engine Manifest + Boundary Transitions + Fault Envelopes) governs how all processing
engines in the SourceOS workstation report their identity, emit boundary-crossing events, and
surface faults. This document provides concrete fixture examples for shell-adjacent engines
(PDF viewer / docd, terminal, preview renderer).

---

## EngineManifest Examples

### PDF Viewer (docd engine)

```json
{
  "id": "urn:srcos:engine-manifest:docd:2026",
  "specVersion": "0.1.0",
  "engineKind": "document-renderer",
  "engineId": "docd",
  "version": "1.4.0",
  "declaredBoundaries": ["file-read", "render-emit"],
  "allowedInputKinds": ["application/pdf", "text/plain", "text/markdown"],
  "sideEffectPolicy": "suppressed",
  "networkEgressPolicy": "denied",
  "sandboxKind": "process-isolated",
  "capabilityContractRef": "urn:srcos:capability-contract:docd:2026",
  "orgPolicyRef": "urn:srcos:org-policy:default:2026"
}
```

### Terminal Engine

```json
{
  "id": "urn:srcos:engine-manifest:terminal:2026",
  "specVersion": "0.1.0",
  "engineKind": "terminal-helper",
  "engineId": "srcos-terminal",
  "version": "0.3.0",
  "declaredBoundaries": ["tty-read", "tty-write", "process-spawn", "env-read"],
  "allowedInputKinds": ["text/x-shellcommand"],
  "sideEffectPolicy": "allowed-with-receipt",
  "networkEgressPolicy": "policy-gated",
  "sandboxKind": "ambient-user-session",
  "capabilityContractRef": "urn:srcos:capability-contract:terminal:2026",
  "orgPolicyRef": "urn:srcos:org-policy:default:2026"
}
```

### Preview Renderer (browser-child engine)

```json
{
  "id": "urn:srcos:engine-manifest:preview-renderer:2026",
  "specVersion": "0.1.0",
  "engineKind": "browser-child",
  "engineId": "preview-renderer",
  "version": "0.9.1",
  "declaredBoundaries": ["file-read", "dom-emit", "network-fetch"],
  "allowedInputKinds": ["text/html", "text/css", "application/javascript"],
  "sideEffectPolicy": "allowed-with-receipt",
  "networkEgressPolicy": "allow-local-only",
  "sandboxKind": "browser-origin-sandbox",
  "capabilityContractRef": "urn:srcos:capability-contract:preview-renderer:2026",
  "orgPolicyRef": "urn:srcos:org-policy:default:2026"
}
```

---

## BoundaryTransition Fixtures

BoundaryTransitions are emitted whenever an engine crosses one of its `declaredBoundaries`.
Each transition is a typed event with before/after state refs and a policy decision record.

### Terminal: process-spawn boundary (admitted)

```json
{
  "id": "urn:srcos:boundary-transition:terminal:spawn-20260718T120000Z",
  "specVersion": "0.1.0",
  "engineRef": "urn:srcos:engine-manifest:terminal:2026",
  "boundaryKind": "process-spawn",
  "direction": "egress",
  "decision": "admitted",
  "policyDecisionRef": "urn:srcos:policy-decision:terminal-spawn-admit-20260718",
  "actorRef": "urn:srcos:identity:mdheller:2026",
  "commandToken": "git",
  "argsRedacted": true,
  "observedAt": "2026-07-18T12:00:00Z"
}
```

### Preview Renderer: network-fetch boundary (suppressed — external origin)

```json
{
  "id": "urn:srcos:boundary-transition:preview-renderer:net-fetch-20260718T120100Z",
  "specVersion": "0.1.0",
  "engineRef": "urn:srcos:engine-manifest:preview-renderer:2026",
  "boundaryKind": "network-fetch",
  "direction": "egress",
  "decision": "suppressed",
  "policyDecisionRef": "urn:srcos:policy-decision:preview-renderer-net-deny-20260718",
  "suppressionReason": "allow-local-only policy: external origin rejected",
  "targetOriginRedacted": true,
  "observedAt": "2026-07-18T12:01:00Z"
}
```

### docd: file-read boundary (admitted)

```json
{
  "id": "urn:srcos:boundary-transition:docd:file-read-20260718T120200Z",
  "specVersion": "0.1.0",
  "engineRef": "urn:srcos:engine-manifest:docd:2026",
  "boundaryKind": "file-read",
  "direction": "ingress",
  "decision": "admitted",
  "policyDecisionRef": "urn:srcos:policy-decision:docd-file-read-admit-20260718",
  "pathRedacted": true,
  "observedAt": "2026-07-18T12:02:00Z"
}
```

---

## FaultEnvelope Examples

FaultEnvelopes are emitted when an engine transition fails, a boundary is violated unexpectedly,
or a recovery branch is triggered.

### Preview Renderer: render failure (non-fatal)

```json
{
  "id": "urn:srcos:fault-envelope:preview-renderer:render-fail-20260718T120500Z",
  "specVersion": "0.1.0",
  "engineRef": "urn:srcos:engine-manifest:preview-renderer:2026",
  "faultClass": "render-failure",
  "severity": "non-fatal",
  "boundaryTransitionRef": "urn:srcos:boundary-transition:preview-renderer:dom-emit-fail-20260718T120500Z",
  "recoveryAction": "emit-empty-frame",
  "recoveryOutcome": "succeeded",
  "humanReviewRequired": false,
  "observedAt": "2026-07-18T12:05:00Z",
  "note": "Malformed HTML input caused render abort; engine emitted empty frame per degraded-mode policy."
}
```

### Terminal: policy-violation fault (fatal — process-spawn blocked by org policy)

```json
{
  "id": "urn:srcos:fault-envelope:terminal:policy-violation-20260718T130000Z",
  "specVersion": "0.1.0",
  "engineRef": "urn:srcos:engine-manifest:terminal:2026",
  "faultClass": "policy-violation",
  "severity": "fatal",
  "boundaryTransitionRef": "urn:srcos:boundary-transition:terminal:spawn-blocked-20260718T130000Z",
  "policyDecisionRef": "urn:srcos:policy-decision:terminal-spawn-deny-20260718",
  "recoveryAction": "refuse-start",
  "recoveryOutcome": "succeeded",
  "humanReviewRequired": true,
  "humanReviewRef": "urn:srcos:review-request:terminal-spawn-policy-20260718",
  "observedAt": "2026-07-18T13:00:00Z",
  "note": "Org policy denied process-spawn for disallowed command token. Engine terminated. Human review queued."
}
```

### docd: capability-revocation during render (fatal)

```json
{
  "id": "urn:srcos:fault-envelope:docd:capability-revoked-20260718T140000Z",
  "specVersion": "0.1.0",
  "engineRef": "urn:srcos:engine-manifest:docd:2026",
  "faultClass": "capability-revocation",
  "severity": "fatal",
  "capabilityRef": "urn:srcos:capability:file-read",
  "recoveryAction": "emit-receipt-and-exit",
  "recoveryOutcome": "succeeded",
  "humanReviewRequired": false,
  "hostLifecycleStateRef": "urn:srcos:lifecycle:docd:cleanup-running-20260718T140001Z",
  "observedAt": "2026-07-18T14:00:00Z",
  "note": "file-read capability revoked mid-render by policy update. Engine emitted ValidatorReceipt for partial render and exited cleanly."
}
```

---

## Lifecycle State Transition: SESSION_READY → RUNNING

This is the most common happy-path transition, confirmed by `sourceosctl lifecycle status`.

```json
{
  "id": "urn:srcos:lifecycle:host:running-20260718T090000Z",
  "specVersion": "0.1.0",
  "state": "RUNNING",
  "previousState": "SESSION_READY",
  "deviceRef": "urn:srcos:device:host:mdheller-mbp-2024",
  "identityRef": "urn:srcos:identity:mdheller:2026",
  "orgPolicyRef": "urn:srcos:org-policy:default:2026",
  "capabilityGraphRef": "urn:srcos:capability-graph:host:20260718",
  "sessionRef": "urn:srcos:session:mdheller:20260718T090000Z",
  "observedAt": "2026-07-18T09:00:00Z",
  "transitionedAt": "2026-07-18T09:00:02Z"
}
```

---

## Related Issues

- sourceos-shell #7 — State Integrity stub (`sourceosctl state-integrity status`)
- sourceos-shell #9 — explain surface stubs
- sourceos-shell #11 — HostRuntimeLifecycleState schema (`schemas/host-runtime-lifecycle.schema.json`)
- sourceos-shell #15 — mutation-evidence-accountability explain stubs
- sourceos-shell #18 — ADR-035 engine manifest / boundary transition / fault envelope (this document)
