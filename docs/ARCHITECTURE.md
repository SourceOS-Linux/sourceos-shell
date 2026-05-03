# SourceOS Shell Architecture

SourceOS Shell is the product/runtime workspace shell for trusted documents, office workflows, search, provenance, and agent evidence.

It is not a GNOME Shell replacement in v0. GNOME remains the desktop shell, compositor, panel, and windowing environment for the first Linux realization. SourceOS Shell integrates with GNOME through desktop entries, launchers, file actions, reports, and adapters.

## Repository boundary

| Repository | Responsibility |
|---|---|
| `SourceOS-Linux/sourceos-shell` | Product/runtime shell code: document services, PDF runtime, office/workspace actions, UI packages, router/adapters. |
| `SourceOS-Linux/sourceos-spec` | Canonical contracts, schemas, examples, evidence object shapes. |
| `SociOS-Linux/source-os` | Linux realization: host profiles, GNOME defaults, installer, status/doctor, service wiring. |
| `SocioProphet/agentplane` and related repos | Agent execution evidence, policy/control integration, operator surfaces. |

## Staged model

### Stage 0: PDF-first runtime

The first executable slice is intentionally small:

- `services/docd` derives document artifacts.
- `services/pdf-secure` signs and validates artifact placeholders.
- `apps/pdf-viewer-demo` proves the viewer/demo entry point.
- `content/draft`, `content/derived`, and `content/reports` define the local artifact layout.
- `make validate` and `make smoke` prove the scaffold is callable without external services.

This does not claim a full PDF engine.

### Stage 1: Document shell

The document shell adds artifact manifests, validation reports, sidecars, annotation export, provenance ribbons, and publishing/report surfaces.

### Stage 2: Office shell

The office shell adds open/create/search/convert/export/template workflows, with LibreOffice/Collabora-compatible open implementation paths where appropriate.

### Stage 3: Workspace/action shell

The workspace shell adds action routing, shell-web surfaces, local report history, agent output inbox, status/doctor/fix report UI, and search-provider routing.

### Stage 4: GNOME adapter

The GNOME adapter integrates SourceOS Shell with Linux desktops through launchers, desktop entries, file-manager actions, notifications, portals, and the SourceOS workstation profile.

### Stage 5: Optional desktop shell path

A GNOME Shell replacement, compositor adapter, or full SourceOS desktop shell is deferred until the document/runtime shell proves value. This repository must not imply full desktop replacement before that decision gate.

## Non-goals for this scaffold

- No full PDF engine.
- No production signing.
- No proprietary dependency requirement.
- No GNOME Shell replacement.
- No host mutation or Linux profile wiring.
- No production readiness claim.

## Validation

The scaffold must remain smokeable with:

```bash
make validate
make smoke
```
