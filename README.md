# Project Orchestrator (Private Preview)

This repository contains the private-preview packaging baseline for the Project Orchestrator prototype.

It is intended for iterative internal development, not for public release or turnkey installation yet.

## Current scope
- project orchestrator core specs, shared policy, templates, and samples
- runtime-oriented scripts used by the prototype
- `pa-sample` as the default example instance
- docs describing current implementation status, packaging plan, and update workflow

## Not included
- local-private real project instances
- local runtime state
- review card outputs, logs, caches, tmp files, or workspace-private memory
- real registry entries and real environment configuration

## Current status
This repository is a curated mirror of the actively developed workspace version.

Default workflow:
- develop and verify in the workspace
- curate in staging
- sync only the reviewed, trimmed result into this repository

See also:
- `docs/project-orchestrator-implementation-status-v0.1.md`
- `docs/project-orchestrator-github-packaging-plan-v0.1.md`
- `docs/project-orchestrator-update-workflow-sop-v0.1.md`
