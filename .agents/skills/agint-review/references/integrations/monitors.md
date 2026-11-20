# Recommended monitors

Read this when the PR changes `assets/monitors/`. Scope tags are defined in the agent file.

## Context

- A recommended monitor is a template every customer of the integration can enable as is, in any org. A monitor that never fires looks like a healthy integration: `notify_no_data` is off on recommended monitors, so nothing shows the silence.
- The repo's CI doesn't read monitor JSON. The datadog-assets app's `validate-monitors` and `validate-monitor-template-quality` checks run on every PR, but their rules aren't published: leave JSON shape, required fields and what the monitor API rejects to them.
- Nothing checks that a monitor's metrics exist. Read the check code and `metadata.csv` for the metrics, their tags and tag values, and `assets/configuration/spec.yaml` for options that gate them.

## Rules

- The query uses metrics the integration sends (in `metadata.csv`), or ones that clearly come from elsewhere (the Agent core, another integration) (**Request**, PR scope).
- Tag values in the scope are values the check sends (`status:failed`, not a guessed `status:error`); a wrong value never fires (**Request**, PR scope).
- The scope works in any org: no hardcoded host, cluster or environment, no `$var` template variables. A filter on a state value the monitor alerts on (`{!status:active}`) is fine (**Request**, PR scope).
- `{{<tag>.name}}` in the name or message only for tags the query groups `by`; otherwise it renders empty (**Request**, PR scope).
- No notification handles in the message (`@…`, placeholders like `@example.com` included): they notify, or show garbage, in every org that enables it (**Request**, PR scope).
- A `warning` threshold sits between `critical_recovery` and `critical`. The API accepts it on the wrong side, and then it fires after the alert it should precede (**Request**, PR scope).
- Log monitors query the pipeline's log `source`, not the integration name, when the two differ (**Request**, PR scope).
- A per-resource condition groups `by {<tag>}`, rather than one alert for the whole fleet (**Suggestion**, PR scope).
- The threshold has a defensible source: a boolean state, a ratio, `anomalies()` for unbounded counts and rates, or an absolute value cited from the product's docs or a sibling integration's monitor. A value tuned on one test environment is wrong for every customer (**Question** when the source isn't stated, PR scope).
- Not built on a metric behind a spec option that defaults to off: most customers get no data (**Suggestion**, PR scope).
- Counts and rates are evaluated over at least `last_15m`, unless the monitor reads a boolean state (**Suggestion**, PR scope).
- The display `title` is in the active voice, starts with the resource or metric and uses no template variables; `definition.name` starts with `[<Integration>]` (**Nit**, PR scope).
