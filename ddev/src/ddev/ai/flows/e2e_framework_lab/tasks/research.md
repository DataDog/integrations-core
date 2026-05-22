Research the `$integration` technology for an integrations-core-owned E2E lab.

Integration path, when present: `$integration_path`
Lab output path: `$lab_path`

Read these local files when present:

- `README.md`
- `assets/configuration/spec.yaml`
- `datadog_checks/*/data/metrics.yaml`
- `datadog_checks/**`
- `tests/**`
- `hatch.toml`

Also use `http_get` to look up official upstream service documentation online when network access is available. Prefer vendor-maintained docs over blog posts or generated examples.

Produce a structured summary with:

1. official documentation URLs and what each source proves;
2. available integrations-core evidence, or a clear note that the integration does not exist yet;
3. service topology and deployment modes;
4. ports and protocols;
5. authentication or seed data requirements;
6. expected Agent configuration shape, even when the integration is unreleased;
7. documented metrics or upstream signals and the operation likely to generate each;
8. realistic load pattern for a long-running lab;
9. risky metrics or signals that may need manual validation.
