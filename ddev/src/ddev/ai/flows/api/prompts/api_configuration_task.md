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
deviations, and known limitations, but not as evidence of file contents. Re-read the final client,
check, metadata, spec, generated files, and manifest, and correct and report any material
disagreement with the design.

Complete the spec and generated artifacts under the standing configuration contract. Reconcile
all config reads with product fields or shared templates, remove unused options, and preserve the
design's defaults and bounds unless current code or vendor evidence justifies a correction.

Include init_config/default and init_config/http under init_config, and instances/default and
instances/http under instances. Reuse template overrides for authentication, headers, TLS, proxies,
timeouts, tags, and collection interval. Compare a couple of existing API specs for the applicable
conventions. Give each product option a non-secret example, description, and appropriate
fleet_configurable value.

Use spec value constraints supported by `OPENAPI_SCHEMA_PROPERTIES` in
`datadog_checks_dev/datadog_checks/dev/tooling/configuration/constants.py`. Constrain values only as
far as the vendor contract requires; a base URL may include a reverse-proxy path prefix. For custom
validators, inspect the generated hooks: `instance_<option>` sees explicitly supplied raw values,
`check_instance` sees the final model with defaults, and `initialize_instance` sees raw input without
defaults. Custom validation raises ValueError and returns the hook's input.

For direct send_log ingestion, add a logs template example with `type: integration`, source, and
any justified service/default-service setting. Local file/journald collection needs its separate
stanza. Order file entries to match prepared `DD_LOG_<N>` mounts, with concrete source and service.
Use the vendor-documented standard file path and describe it as install-dependent; inspect the lab
only to confirm file name and line format, since it may run as a non-standard user. The global
Agent `logs_enabled` flag is not a custom instance option.

Complete manifest.json: remove instructional placeholders, reconcile the display name, integration
identity, metric namespace, check metric, and declared telemetry with the implementation, and verify
referenced local assets exist. Use applicable manifest guidance for required fields and classifiers;
report unresolved identity or asset requirements rather than inventing values. Later phases do not
author the manifest. Repair production-code inconsistencies revealed by this reconciliation or the
build reviewer within the build phase's ownership.

Regenerate and verify artifacts with these tools:

1. ddev_validate config with sync=true;
2. ddev_validate models with sync=true;
3. ddev_validate metadata;
4. ddev_lint with fmt=true;
5. ddev_lint without formatting.

Fix scoped issues and regenerate after subsequent spec changes. Finish with a concise reviewer
summary: changed paths, exact command outcomes, design departures, and incomplete requirements.
Distinguish passing, failed, and unrun commands.
