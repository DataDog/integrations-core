---
type: prompt
name: api_scaffold_task
---
Prepare the scaffold for **${integration}**.

## Design handoff

${api_design_memory}

Read the handoff's status and identity first. If its status is BLOCKED, make no changes and
preserve the blockers. Use its directory and namespace rather than deriving new ones.

Inspect the target path. If it is absent, call ddev_create once with the display name
`${integration}`; the tool normalizes it to the directory and package name and generates the
shipped manifest. Confirm the created directory matches the designed directory. Reuse a scaffold
created earlier in this run; stop on an unrelated existing integration.

Inventory the generated manifest, package, check, spec, metadata, README, tests, and environment
assets.

This task ends after scaffolding. Report the exact identity, scaffold result, file inventory,
environment assets, and gaps.
