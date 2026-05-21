Research the `{{integration}}` integration at `{{integration_path}}`.

Read these files when present:

- `README.md`
- `assets/configuration/spec.yaml`
- `datadog_checks/*/data/metrics.yaml`
- `datadog_checks/**`
- `tests/**`
- `hatch.toml`

Produce a structured summary with:

1. service topology and Docker dependencies;
2. ports and protocols;
3. authentication or seed data requirements;
4. integration configuration needed by the Agent;
5. every documented metric and the operation likely to generate it;
6. realistic load pattern for a long-running lab;
7. risky metrics that may need manual validation.
