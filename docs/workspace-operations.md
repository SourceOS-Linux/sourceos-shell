# Workspace Operations Contract

Status: initial contract-capture slice.

`sourceos-shell` is the SourceOS shell and user-interface plane. This document
defines how the shell surfaces and controls local Workspace Operations — sync,
terminal, browser, local agent-machine, model carry, and workstation state —
without becoming a runtime or policy authority.

## Boundary

The shell is a **control surface and projection layer**. It must not create
hidden mutations or policy decisions outside the Operation Plane.

- The shell reads operation/task state from contracts supplied by the Operation
  Plane; it does not author that state.
- The shell routes actions through structured `OperationCommand` records; it
  does not execute integrations directly.
- The shell applies redaction policy before emitting diagnostics exports; it
  does not decide that policy.

## Required surfaces

| Surface | Description |
|---|---|
| Local Operation Tray projection | `operationTrayProjection` in `WorkspaceOperationState` |
| Local Operation Inspector projection | `operationInspectorProjection` in `WorkspaceOperationState` |
| File availability states | `fileAvailabilityState`: `local`, `remote`, `syncing`, `conflicted`, `quarantined` |
| Device identity / trust profile | `deviceIdentity` in `WorkspaceOperationState` |
| Sync status from `sourceos-syncd` | `syncStatus` in `WorkspaceOperationState` |
| TurtleTerm entry point | `integrationEntryPoints.turtleTerm` + `OperationCommand` class `turtleterm-open` / `turtleterm-close` |
| BearBrowser entry point | `integrationEntryPoints.bearBrowser` + `OperationCommand` class `bearbrowser-open` / `bearbrowser-close` |
| Agent-machine entry point | `integrationEntryPoints.agentMachine` + `OperationCommand` class `agentmachine-activate` / `agentmachine-deactivate` |
| Redacted diagnostics export | `DiagnosticsExport` schema with `redactionApplied: true` |

## Operation states

The shell must be able to distinguish all of the following `operationState`
values as reported by the Operation Plane:

| State | Meaning |
|---|---|
| `stored` | Operation received and stored; not yet admitted |
| `quarantined` | Operation held pending policy review |
| `admitted` | Operation admitted to the active workspace |
| `activated` | Operation is running |
| `syncing` | Operation is being synchronised with remote |
| `conflicted` | Operation has a merge or sync conflict |
| `failed` | Operation terminated with an error |

## File availability states

| State | Meaning |
|---|---|
| `local` | File is locally available |
| `remote` | File exists only on remote |
| `syncing` | File is being synchronised |
| `conflicted` | File has a sync or merge conflict |
| `quarantined` | File is held pending policy review |

## OperationCommand routing

Shell actions route through `OperationCommand` records
(`schemas/operation-command.schema.json`). The shell emits a command record
with a `commandClass` such as `turtleterm-open`, `sync-request`, or
`diagnostics-export`; the Operation Plane acts on it.

Supported command classes:

- `turtleterm-open` / `turtleterm-close`
- `bearbrowser-open` / `bearbrowser-close`
- `agentmachine-activate` / `agentmachine-deactivate`
- `sync-request` / `sync-cancel`
- `diagnostics-export`
- `model-carry-initiate`
- `workstation-state-query`

All commands support `isDryRun: true` for plan/preview without side effects.

## Diagnostics export

The `DiagnosticsExport` schema (`schemas/diagnostics-export.schema.json`)
enforces:

- `redactionApplied: true` — redaction is always applied before export.
- `contentCaptureEnabled: false` — inline content capture is always disabled.
- `payloadMode` — must be `metadata-only`, `summary`, `ref-only`, or
  `redacted`.
- `policyDecisionRefs` — non-empty; Policy Fabric decision refs are required.

## Required integrations

- `SourceOS-Linux/sourceos-spec#87`
- `SociOS-Linux/workstation-contracts#28`
- `SourceOS-Linux/sourceos-syncd#3`
- `SourceOS-Linux/sourceos-devtools#19`
- `SourceOS-Linux/BearBrowser#20`
- `SourceOS-Linux/agent-machine#18`
- `SocioProphet/prophet-core-contracts#1`
- `SocioProphet/sociosphere#259`

## Non-goals

- Shell does not own Policy Fabric or Operation Plane runtime logic.
- Shell does not create hidden mutations outside the Operation Plane.
- Shell does not enable content capture.
- Shell does not export diagnostics without Policy Fabric decision refs.
- Shell does not activate agent-machine integrations without Agent Registry
  authority.
