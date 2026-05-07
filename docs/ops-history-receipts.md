# OpsHistory Operational Receipt Contract

Status: initial contract-capture slice.

`sourceos-shell` is the SourceOS shell runtime home. This document defines how shell/workbench activity is represented as bounded operational receipt metadata for the OpsHistory fabric without expanding the current PDF-first implementation slice.

## Boundary

This contract does not implement live shell integration. It does not add broad shell UX. It does not collect unrestricted session material.

The first slice is metadata-only and dry-run oriented.

## Receipt classes

Operational receipts may describe:

- session start metadata;
- session end metadata;
- request metadata;
- execution state metadata;
- artifact or evidence references;
- agent delegation metadata;
- policy decision references;
- cloud/fog attach or detach metadata;
- redaction/tombstone metadata.

## Safe defaults

- Content capture is disabled by default.
- Result material is represented as metadata, summary, or reference.
- Large outputs are referenced through artifact/evidence refs.
- Sensitive events route through redaction/tombstone policy.
- Non-human participants require Agent Registry authority.
- Policy Fabric decides export, context hydration, and memory writeback.

## OpsHistory relation

Operational receipt metadata may become an OpsHistory event only when policy and authority allow it. Memory Mesh should receive bounded context-pack refs rather than raw session material. AgentPlane should consume context-pack refs and emit evidence refs.

## Example command surface

Future dry-run surfaces should look like:

```bash
sourceos-shell receipts explain --session demo --dry-run
sourceos-shell receipts export-plan --session demo --dry-run
sourceos-shell receipts redactions --dry-run
```

Those commands are not implemented in this contract-only slice.

## Non-goals

- No unrestricted terminal recording.
- No live session capture.
- No memory writeback.
- No bridge/export without Policy Fabric decision refs.
- No agent visibility without Agent Registry refs.
- No expansion beyond the repo's current PDF-first sequencing.
