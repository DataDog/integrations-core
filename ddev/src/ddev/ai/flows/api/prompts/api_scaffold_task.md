---
type: prompt
name: api_scaffold_task
---
Prepare the scaffold for **${integration}**.

## PRD

${prd}

## Design handoff

${api_design_memory}

Read the entire handoff first. If its status is BLOCKED, make no edits and preserve the blockers.
Use its directory and namespace rather than deriving new ones.

Inspect the target path. If it is absent, call ddev_create once with only `integration`, using the
designed snake_case directory name. The tool owns scaffold defaults and generates the shipped
manifest. Reuse a scaffold created earlier in this run; stop on an unrelated existing integration.

Inventory the generated manifest, package, check, spec, metadata, README, tests, and environment
assets.

This task ends after scaffolding. Report the exact identity, scaffold result, file inventory,
environment assets, and gaps. The implementation task starts with fresh context and sees only the
design handoff and files, so record anything it needs in the integration files rather than in this
summary.