---
type: prompt
name: api_configuration_task
---
Complete configuration for **${integration}** and reconcile the whole build.

## PRD

${prd}

## Design handoff

${api_design_memory}

This task starts from a compacted summary of the implementation task: use it for decisions,
deviations, and known limitations, but not as evidence of file contents. If design status is
BLOCKED, make no edits. Otherwise re-read the final client, check, metadata, spec, generated files,
and fixtures before editing, and correct and report any material disagreement with the design.

Make assets/configuration/spec.yaml accurately describe the implemented API, including the shared
default/HTTP templates and the correct logs stanza selected by the design. Reconcile every config
read with a product field or shared template per your configuration contract, keeping defaults and
bounds aligned with the design handoff unless code or vendor evidence corrects it, and remove
options the code does not use.

Regenerate and verify artifacts with these tools:

1. ddev_validate config with sync=true;
2. ddev_validate models with sync=true;
3. ddev_validate metadata;
4. ddev_lint with fmt=true;
5. ddev_lint without formatting.

Fix scoped issues and regenerate after subsequent spec changes. Finish with a concise reviewer
summary: changed paths, exact command outcomes, design departures, and incomplete requirements.
Distinguish passing, failed, and unrun commands.
