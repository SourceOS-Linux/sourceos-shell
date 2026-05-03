# sourceos-shell

Primary product/runtime repository for the SourceOS shell.

## Repo boundary

| Repository | Responsibility |
|---|---|
| [`SourceOS-Linux/sourceos-shell`](https://github.com/SourceOS-Linux/sourceos-shell) | Product/runtime code (this repo) |
| [`SourceOS-Linux/sourceos-spec`](https://github.com/SourceOS-Linux/sourceos-spec) | Shared machine-readable contracts |
| [`SociOS-Linux/source-os`](https://github.com/SociOS-Linux/source-os) | Linux realization surfaces |
| `SociOS-Linux/albert` | Temporary launcher bridge only |

## PDF-first runtime scope

This repository is the runtime home for the broader shell stack. The **first implementation slice is PDF-first**.

### Services

| Service | Path | Role |
|---|---|---|
| `docd` | `services/docd` | Derive lane — draft → derived PDF |
| `pdf-secure` | `services/pdf-secure` | Sign / validate lane |

### Apps

| App | Path | Role |
|---|---|---|
| `pdf-viewer-demo` | `apps/pdf-viewer-demo` | PDF viewer / demo surface |

### Content layout

| Directory | Purpose |
|---|---|
| `content/draft` | Source draft documents |
| `content/derived` | Derived PDFs produced by `docd` |
| `content/reports` | Validation reports from `pdf-secure` |

## Commands

```bash
# Validate workspace layout (no external services needed)
make validate

# Run smoke tests for each runtime slice
make smoke

# Docker compose (requires Docker)
make up
make down
```

## Contracts

Machine-readable contracts for all inter-service boundaries live in
[`SourceOS-Linux/sourceos-spec`](https://github.com/SourceOS-Linux/sourceos-spec).
Do not define contracts in this repo; reference them from `sourceos-spec`.

## Linux realization

OS-level realization surfaces (packaging, init, system integration) live in
[`SociOS-Linux/source-os`](https://github.com/SociOS-Linux/source-os).

## Explicitly deferred

The following are out of scope until the PDF lane is real:

- Notes / graph / gallery / playground surfaces
- Broader shell UX expansion
- Non-PDF publication features beyond what the PDF lane needs

## Status

All runtime slices are **placeholder scaffolds** — smoke-tested, no external services required.
