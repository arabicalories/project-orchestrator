# Project Orchestrator (Private Preview)

This repository is the private-preview packaging baseline for the Project Orchestrator prototype.

It is not a turnkey product yet. Think of it as a curated mirror of the prototype that is actively developed in a separate workspace, then trimmed and synced here for internal sharing, review, and gradual hardening.

## What this repo is

This repo is the clean publishing surface for the current prototype. It keeps the parts that are useful to review, discuss, and iterate on:

- core task/stage specs
- shared policy and workspace templates
- sample project instance (`pa-sample`)
- runtime-oriented prototype scripts
- packaging, implementation, and update workflow docs

## What this repo is not

This repo intentionally does **not** include local-private real project instances or runtime state. In particular, it excludes:

- real project configs and real registry entries
- local runtime state, logs, caches, tmp files
- review card outputs and workspace-private memory
- real environment configuration, secrets, and local machine paths
- local-private instance customizations used in day-to-day production work

## Repository layout

```text
.
├── README.md
├── docs/
│   ├── project-orchestrator-implementation-status-v0.1.md
│   ├── project-orchestrator-github-packaging-plan-v0.1.md
│   └── project-orchestrator-update-workflow-sop-v0.1.md
├── project-orchestrator/
│   ├── component-manifest.json
│   ├── projects/pa-sample/
│   ├── registry/projects.sample.json
│   ├── samples/
│   ├── shared-skills/
│   ├── specs/
│   ├── state-template/
│   └── workspace-template/
├── scripts/
└── tests/
```

## Current status

Current maturity: **private preview / internal beta**.

What is already here:

- a usable packaging skeleton
- sample config and sample instance shape
- stage transition specs and artifact rules
- prototype runtime scripts
- unit tests for the current prototype behavior

What is still intentionally unfinished:

- public installation experience
- stable external interfaces
- production-grade docs for third-party adopters
- fully generalized runtime adapters
- long-term compatibility guarantees

## How this repo is maintained

The current workflow is:

1. develop and validate in the workspace
2. curate changes in a staging directory
3. sync only the reviewed, trimmed result into this repository

In other words:

- **workspace** = real development source
- **staging** = packaging/filtering area
- **this repo** = reviewed mirror for sharing and iteration

This keeps local-private operational details out of the repository while still allowing the prototype to evolve quickly.

## Sample vs local-private instances

`pa-sample` is the example truth source in this repository.

Real local-private instances stay outside this repo. They may share the same structure, but they can contain:

- real message targets
- real runtime paths
- real environment bindings
- project-specific operational conventions

Those do not belong in the packaged preview repository.

## Working expectation

If you are reading this repo as a collaborator, the right expectation is:

- review the structure
- understand the current task/state model
- inspect the sample instance
- use the docs to follow packaging decisions
- do not assume this is a drop-in installable product yet

## Recommended reading order

If you want the fastest orientation path, read these first:

1. `docs/project-orchestrator-implementation-status-v0.1.md`
2. `docs/project-orchestrator-github-packaging-plan-v0.1.md`
3. `docs/project-orchestrator-update-workflow-sop-v0.1.md`
4. `docs/project-orchestrator-public-ready-gap-review-v0.1.md`
5. `docs/project-orchestrator-reviewer-quickstart-v0.1.md`
6. `project-orchestrator/component-manifest.json`
7. `project-orchestrator/projects/pa-sample/project.json`

## Quickstart for reviewers

If you are reviewing the repository for the first time, use this path:

1. Read `docs/project-orchestrator-reviewer-quickstart-v0.1.md`
2. Read `docs/project-orchestrator-implementation-status-v0.1.md`
3. Inspect `project-orchestrator/projects/pa-sample/project.json`
4. Run the read-only checks below if you want to verify the packaged state

## Pre-push release check

Before pushing updates from the staging repository, run:

```bash
cd <staging-repo>
python scripts/release_check.py
```

Author-local example:

```bash
# author-local example
cd /root/projects/staging/project-orchestrator-private
python scripts/release_check.py
```

What it checks:

- required sample/docs files still exist
- `.gitignore` and `.ignore` stay aligned
- `pa-sample` exists and local-private packaged files do not
- forbidden real-instance markers are not present
- phase1 structural check still passes
- core unit tests still pass

Useful shortcuts:

```bash
python scripts/release_check.py --skip-tests
python scripts/release_check.py --skip-phase1
```

## Notes for future packaging

This repository is expected to keep changing. The current goal is not “final public release”, but a clean enough private beta surface that can be updated repeatedly without dragging local-private coupling back in.

That means the packaging standard right now is:

- clean boundaries
- no real environment leakage
- sample-first examples
- docs that match actual behavior closely enough to avoid confusion

When the prototype stabilizes further, this repo can be tightened again toward a more public-facing distribution shape.
