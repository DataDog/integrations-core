# Dashboards

Read this when the PR changes `assets/dashboards/`. Scope tags are defined in the agent file.

## Context

- An out-of-the-box dashboard ships to every customer who installs the integration. A widget on a metric, tag or value the check doesn't send shows no data, and nothing tells the customer why.
- The repo's CI doesn't read dashboard JSON: `ddev validate all` hasn't run `validate dashboards` since #19835. The `validate-dashboards` check of the datadog-assets app (Publishing Platform) runs on every PR, but its rules aren't published: leave JSON shape and required fields to it.
- Nothing checks that a widget's metrics exist. Read the check code and `metadata.csv` for the metrics and the tags each one carries (the check's tag code, `sample_tags`, tests' `assert_metric(..., tags=...)`).
- The guidance customers' dashboards are held to is in `docs/developer/guidelines/dashboards.md` and Datadog's public "Create an integration dashboard" docs.

## Rules

- Every metric a widget queries is one the integration sends (in `metadata.csv`), or one that clearly comes from elsewhere (the Agent core, another integration) (**Request**, PR scope).
- Tag keys in `group_by`, template variable `prefix` and query filters are tags those metrics carry: a template variable on a missing tag empties every widget that uses it (**Request**, PR scope).
- Tag values in filters are values the check sends (`status:failed`, not a guessed `status:error`) (**Request**, PR scope).
- Formula variables match the names of the queries in the same request; otherwise the widget shows an error (**Request**, PR scope).
- Log widgets filter on the pipeline's log `source`, not the integration name, when the two differ; event streams use `sources:<name>` (**Request**, PR scope).
- Widgets that should follow the template variables use them in their scope (**Suggestion**, PR scope).
- The Overview shows at least one error or failure signal when the check sends one, and a monitor summary scoped to the integration when it ships monitors (**Suggestion**, new only).
- Conditional formatting agrees with the metric's direction: red at the bad end (high for errors and latency, low for success rates), no color on counts with no good or bad direction (**Suggestion**, PR scope).
- Two metrics with different units on one widget (**Suggestion**, PR scope).
- Structure: About and Overview groups first, About holding content, not data, and not full width; query values with a timeseries background; the title names the integration and has no hyphen (it builds the URL) (**Suggestion**, new only).
- Copy: Title Case group titles, sentence case widget titles, no units or integration name in titles, aliased formulas (**Nit**, PR scope).
