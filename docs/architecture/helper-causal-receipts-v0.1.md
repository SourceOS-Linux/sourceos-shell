# Helper Causal Receipts v0.1

Status: Draft
Scope: SourceOS Shell, BearBrowser, TurtleTerm, Office/PDF runtime, preview/rendering helpers
Primary goal: preserve user-legible causal intent across helper-process boundaries.

## Problem

- Modern desktop actions are not single-process events.
- A visible action such as previewing a file, opening a native file picker, rendering a thumbnail, taking a screenshot, cleaning browser cache, or indexing metadata can spawn a hidden helper-process cascade.
- The macOS unified-log sample that motivated this spec shows repeated helper lifecycle patterns: demand spawn, `xpcproxy` materialization, source attachment, running/init transitions, sandbox-denied lookups, clean exits, supervisor kills, and teardown races.
- The useful primitive is not the raw process log. The useful primitive is a root-intent-bound receipt.
- SourceOS must not repeat the opaque pattern where users see helper churn but cannot answer: why did this run, what requested it, what data did it touch, what was denied, and did network/clipboard/account/analytics access occur?

## Design Principles

- Every helper process carries a `root_intent_id`.
- Every helper spawn has a declared purpose.
- Every sensitive capability request is recorded as a policy decision.
- Every denied capability records whether data was accessed. For a sandbox denial, the default is `data_accessed=false` unless an allow event proves otherwise.
- Every helper exit records completion, duration, and receipt completeness.
- Every teardown race is normalized before user presentation.
- Expected denials are evidence of containment, not automatic alerts.
- Unexpected denials are policy-regression candidates.
- Local preview helpers deny network, DNS, pasteboard, account lookup, analytics, camera, microphone, location, credential stores, and arbitrary file reads by default.
- Web thumbnailing is treated as hostile-content rendering, not as static image generation.
- Native file picker helpers must not inherit browser session authority.
- Terminal preview helpers must not inherit shell secrets.

## Event Types

| Event Type | Purpose | Required Fields |
|---|---|---|
| `root_intent.created` | Start a causal graph for a visible or scheduled action | `event_id`, `root_intent_id`, `timestamp`, `surface`, `actor`, `declared_purpose`, `data_scope`, `default_policy`, `receipt_required` |
| `helper.spawn` | Record subprocess/helper launch | `event_id`, `parent_event_id`, `root_intent_id`, `parent_process`, `child_process`, `trigger`, `spawn_reason`, `policy_profile` |
| `capability.request` | Record sensitive service/capability lookup | `event_id`, `root_intent_id`, `requestor`, `capability`, `requested_service`, `decision`, `classification`, `policy_rule`, `data_accessed` |
| `helper.exit` | Record termination and cleanup | `event_id`, `root_intent_id`, `process`, `exit_status`, `duration_ms`, `children_cleaned`, `unexpected_denials`, `network_used`, `receipt_complete` |
| `teardown.normalized` | Normalize noisy cleanup/race messages | `raw_message`, `normalized_class`, `severity`, `meaning`, `receipt_complete`, `policy_impact` |
| `policy.decision` | Record policy evaluation | `policy_profile`, `rule_id`, `capability`, `decision`, `reason`, `override_actor`, `override_expiry` |
| `data.touch` | Record data class touched | `object_type`, `object_hash`, `path_policy`, `access_mode`, `retention`, `derived_artifact` |

## Policy Profiles

### `preview.local_only.v1`

- Applies to local PDF, image, office, and generic file previews.
- Allows selected file snapshot reads, thumbnail cache writes, CPU rendering, mediated GPU rendering, allowlisted system font reads, and IPC to the preview broker.
- Denies network, DNS, pasteboard, analytics, account lookup, contacts, calendar, camera, microphone, location, arbitrary file reads, and unrestricted child processes.

### `preview.web_thumbnail.local_only.v1`

- Applies to HTML thumbnails, web archive previews, local browser export previews, and URL snapshot rendering.
- Risk model: hostile-content rendering.
- Allows parsing and rendering the selected local snapshot plus mediated GPU rendering and local thumbnail output.
- Denies network, DNS, cookies, credentials, local/session storage, extension APIs, service workers, remote fonts, pasteboard, account lookup, analytics, camera, microphone, and location.
- Non-negotiable invariant: web thumbnail helpers never inherit browser session authority.

### `cache_cleanup.local_only.v1`

- Applies to browser/app cache cleanup and local cache size accounting.
- Allows cache metadata read, cache entry delete, cache size compute, and local policy report.
- Denies network, DNS, analytics, account lookup, remote sync, and browser session reads.
- Special rule: if a network-shaped helper is spawned, its receipt must state whether network authority was actually granted or whether only local cache metadata was inspected.

### `file_picker.native_ui.v1`

- Applies to native open/save panels and file picker preview surfaces.
- Allows selected file grants, UI rendering, and preview-broker IPC.
- Denies account lookup, cloud sync triggers, pasteboard access, analytics, browser extension invocation, cookie reads, and browser session reads.
- Special rule: native file picker helpers must not inherit browser session authority.

### `terminal.preview.local_only.v1`

- Applies to TurtleTerm file previews, hyperlink previews, archive listings, and command-output renderers.
- Allows selected file/path preview, local rendering, and local temporary artifacts.
- Denies shell environment reads, shell history reads, SSH key reads, token reads, network fetches, clipboard reads, account lookup, and analytics.
- Special rule: terminal preview helpers must never inherit shell secrets.

## Denial Classification

| Classification | Meaning | Default Severity |
|---|---|---|
| `expected_denial` | Policy intentionally blocked a commonly probed service | notice |
| `unexpected_denial` | Helper requested capability outside declared profile | warning |
| `compatibility_probe` | Framework probed optional service and did not require it | notice |
| `policy_regression` | New build began requesting undeclared capability | error in CI |
| `malicious_probe_candidate` | Request unrelated to purpose and targeting sensitive data | critical |
| `missing_service` | Target service absent or not running | notice |
| `teardown_race` | Request/reply path raced with helper shutdown | trace/notice |

## Teardown Normalization

| Raw Pattern | Normalized Class | Meaning |
|---|---|---|
| `no client port found` | `client_endpoint_missing_after_teardown` | Client disappeared before service reply completed |
| `invalid client reply port -1` | `invalid_reply_endpoint_after_teardown` | Reply endpoint invalid during cleanup |
| `job not found` / `ENOSERVICE` | `service_removed_before_reply` | Service exited before late lookup/reply completed |
| `Operation already in progress` | `duplicate_activation_coalesced` | Duplicate demand while helper already running |
| supervisor `SIGKILL` | `supervisor_worker_lifecycle_kill` | Supervisor ended bounded worker |

## User Inspector Requirements

- Provide a local “Why did this run?” view.
- Group by `root_intent_id`, not raw PID.
- Show visible action, parent surface, helper chain, allowed capabilities, denied capabilities, data touched, network/DNS outcome, exit status, incomplete receipts, and policy regressions.
- Expected denials should be visible on expansion, but not noisy by default.
- Policy regressions and incomplete receipts should be surfaced immediately.

## Acceptance Tests

| Test | Given | Assert |
|---|---|---|
| Root intent propagation | Any helper spawn | `root_intent_id`, `parent_event_id`, `spawn_reason`, and `policy_profile` exist |
| Local preview no-network | Local PDF/image preview | network, DNS, analytics, and account lookup denied |
| Web thumbnail isolation | HTML/web thumbnail render | cookies, storage, extensions, network, and pasteboard denied |
| Cache cleanup transparency | Cache cleanup spawns network-shaped helper | receipt explains reason and egress decision |
| Native file picker isolation | Browser invokes native file panel | no browser session or extension authority inherited |
| Terminal preview isolation | TurtleTerm preview | shell secrets and environment denied |
| Receipt completeness | Completed action | all helper spawns have exit or active-state events |
| Denial classification | Denied capability request | denial classified and `data_accessed` recorded |
| Policy regression CI | New undeclared capability | CI fails unless policy is updated |
| Inspector rendering | Completed DAG | user-readable summary exists |

## Repo Integration

| Repo | Role |
|---|---|
| `SourceOS-Linux/sourceos-shell` | Runtime receipt store, helper wrapper, parser/correlator, local inspector |
| `SourceOS-Linux/BearBrowser` | Browser file picker, cache cleanup, preview and thumbnail helper enforcement |
| `SourceOS-Linux/TurtleTerm` | Terminal preview and command helper secret isolation |
| `SocioProphet/ontogenesis` | Ontology classes, properties, SHACL constraints |
| `SocioProphet/prophet-platform` | Evidence-envelope mapping, evidence-console view, CI trust gates |

## Non-Goals

- Do not alert for every expected denial.
- Do not ban short-lived helpers.
- Do not ban multiprocess rendering.
- Do not assume every denial is malicious.
- Do require causality, classification, policy, and receipts.

## Security Invariants

- Preview helpers are local-only by default.
- Web thumbnails do not inherit browser session state.
- Cache cleanup does not receive network authority by default.
- Native file picker helpers do not inherit browser extension authority.
- Terminal preview helpers do not inherit shell secrets.
- Every sensitive capability decision is recorded.
- Every helper exit is recorded.
- Incomplete receipts degrade trust state.
