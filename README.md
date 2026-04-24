# sourceos-shell

Primary product/runtime repository for the SourceOS shell.

## Boundary

- `SourceOS-Linux/sourceos-shell` = product/runtime code
- `SourceOS-Linux/sourceos-spec` = shared machine-readable contracts
- `SociOS-Linux/source-os` = Linux realization surfaces
- `SociOS-Linux/albert` = temporary launcher bridge only

## Immediate sequencing

This repository is the runtime home for the broader shell stack, but the first implementation slice is **PDF-first**.

Initial runtime scope:
- `services/docd` — derive lane
- `services/pdf-secure` — sign / validate lane
- `apps/pdf-viewer-demo` — PDF viewer/demo surface
- `content/` — draft / derived / reports layout
- minimal workspace/bootstrap files

Explicitly deferred until after the PDF lane is real:
- notes / graph / gallery / playground surfaces
- broader shell UX expansion
- non-PDF publication features beyond what the PDF lane needs

## Intent

We keep the repo boundary correct without letting the first implementation slice sprawl beyond the PDF/document/runtime lane.
