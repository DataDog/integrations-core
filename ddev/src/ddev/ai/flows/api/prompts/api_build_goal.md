---
type: goal
name: api_build_goal
---
Evaluate the complete new integration, not only the configuration task's last edits. Read its
client/helpers, check, metadata.csv, spec, generated models/example, copied fixtures, and the READY
design contract.

Use the design handoff to locate relevant decisions and evidence, not as proof of API behavior.
Verify consequential request fields and metric semantics against the relevant portion of cited
vendor sources and current files. A supported correction to the design is valid; repeating its
mistake is not.

Review recorded command output before rerunning checks. Reuse results when the exact command,
scope, outcome, and tested file/environment state are established and still relevant. A summary
claim alone is insufficient. Rerun affected checks after relevant changes or when evidence is
missing or inconsistent; a new reviewer is not itself a reason to repeat a command. Keep recorded
environment failures explicit and retry only after a relevant change or evidence of a transient
failure. Reusing a failure never turns an unverified tier into a pass.

The goal is met only when:

- the implemented subset is explicitly traceable to validated PRD requirements and any omitted
  requirement is honestly reported;
- a focused custom client wraps self.http and owns exact request, response, pagination, polling,
  and download behavior without a second HTTP stack;
- check orchestration, joins, tags, values, failures, and metric submission semantics satisfy the
  requirements and verified API behavior, with justified departures from the design recorded;
- metadata names, units, and backend types match every emitted metric;
- both init_config/http and instances/http templates are present alongside default templates;
- each product option serves a connect, scope, or collection-cost need, declares its default and
  bounds once in spec.yaml (custom rules in validators.py), and agrees with generated configuration
  and ConfigMixin reads, with no duplicate defaults, fallbacks, or range checks in check code;
- fatal failures raise at the failing step and optional ones warn and continue, with no deferred
  raise and no custom exception the check does not handle differently;
- response-supplied URLs are rebuilt on, or validated against, the configured origin before
  credentials are sent;
- no integration service checks were added;
- direct API logs, when required, are guarded by logs_enabled, use an integration logs stanza,
  stable streams, get_log_cursor/send_log, compound next-resume cursors where needed, bounded work,
  and contiguous commit behavior that cannot skip a failed page/file;
- manual persistent cache does not duplicate or outrun the send_log delivery cursor;
- command results are reported truthfully, including failures and unrun work.

Return concrete fixable inconsistencies. Missing source information or an honestly reported tool/
environment gap is not permission to invent behavior or declare success. Do not demand live API or
Docker execution in this build phase.
