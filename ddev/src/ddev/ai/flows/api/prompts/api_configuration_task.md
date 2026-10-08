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
and fixtures before editing. The design handoff is relevant context, not authority over
the implemented files or vendor contract; correct and report any material disagreement.

Make assets/configuration/spec.yaml accurately describe the implemented API, including the shared
default/HTTP templates and the correct logs stanza selected by the design. Reconcile every config
read with a product field or shared template and remove options the code does not use.
Check that every `self.config` read has one spec option whose default and bounds match the design
handoff unless code or vendor evidence corrects it, and put hard cross-field rules in
`check_instance` in `config_models/validators.py`. Remove check-code duplicates such as option
default constants, `value or default` fallbacks, and range-check `ConfigurationError`s. Turn
options that only tune internal pagination, timing, or per-run limits into constants.

Regenerate and verify artifacts with these tools:

1. ddev_validate config with sync=true;
2. ddev_validate models with sync=true;
3. ddev_validate metadata;
4. ddev_lint with fmt=true;
5. ddev_lint without formatting.

Fix scoped issues and regenerate after subsequent spec changes. Inspect final files and collect
any evidence needed by the tester while tools are available, including after reviewer repairs.
Finish with a concise reviewer summary: changed paths, exact command outcomes, design departures,
and incomplete requirements. Distinguish passing, failed, and unrun commands. Reserve the complete
build contract and tester handoff for the memory step.
