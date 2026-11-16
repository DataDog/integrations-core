# OpenMetrics integrations

The product serves metrics on one or more Prometheus or OpenMetrics endpoints, and the integration
scrapes them. Whoever builds it starts from what the endpoints expose and the product documents
(the type's section in `flows.md` describes the chosen flow's default build). So the PRD does not
list every metric: it states what users need from them, what they want to turn off, and how they
slice them. Turning that intent into changes to a default build is the builder's business, not the
PRD's.

## Decisions the PRD settles

- **Components**: which components are scraped (for example a server and its workers), and whether
  they run together.
- **Use cases in scope**: what users need to see and alert on, by area (for example traffic and
  errors per route, queue health, runtime), and the dimensions they slice by, including dimensions
  they need on every metric (for example the product version) and dimensions derived from a label
  (for example a status class from a status code).
- **Dimensions users do not want**: labels that add no value (the same value everywhere) or that
  split series without meaning (for example, names users rename), with the reason.
- **What users can turn off**: metric areas that are optional, and whether each is on or off by
  default.
- **Setup the customer provides**: the setting that turns each endpoint on, its default path and
  port, and the settings that make the families in scope appear.
- **Design choices**: the default check interval in seconds; installation sizes in the terms that
  drive series count (for example routes and backends, workflows, workers); whether the endpoints
  are protected by auth or TLS in production (product facts); whether unified service tagging comes
  from the product's labels; whether users need latency percentiles aggregated across hosts
  (Datadog distributions) or the Prometheus histograms as they are.
- **Compatibility**: names users depend on from a legacy integration or community check, and the
  namespace when an older integration owns one.
- **Logs**: wanted or not.
- **Versions, editions, deployment models**, and what is out of scope.

## Research

Besides the core research, look up and verify. Use what you find to ask better questions and to
state product facts; do not turn it into instructions for the builder.

- **The official metrics reference** and the **source** where metrics are defined or registered, at
  the version the PRD targets.
- **How the endpoint is enabled and configured**: the setting that turns it on, its default port and
  path, whether it supports auth or TLS, and the settings that gate metric groups (feature flags,
  optional labels, modes such as clustering or queues).
- **Families the endpoint only exposes under some conditions**: behind a feature flag, a connected
  backend, a newer version, or after traffic (for example, counters registered when an event first
  fires). The flags go into the customer setup; the conditions are lab needs.
- **The labels the product emits**: info metrics (such as `target_info` or `*_version_info`),
  constant labels, and labels with unbounded values (IDs, names users type, paths).
- **Histograms and summaries** the product exposes.
- **Existing integrations**: whether one already scrapes this product (a legacy integration, a
  community check) and owns a namespace or names users depend on.

When evidence (a running endpoint) is given, check it with the core evidence rules and compare its
families and labels with the docs. A family the docs describe but the endpoint lacks is a lab need,
not a requirement.

## Interview topics

Settle each topic by research when you can; ask the rest. Record each answer as a use case or a
decision in the caller's terms, not as an operation on metrics or labels.

- **Components**: which components to scrape, when the product has several.
- **Use cases**: which areas users need to see and alert on (multi-select, tailored to the families
  the product exposes), and any specific alert they have in mind.
- **Dimensions**: which labels users slice by, which they do not want and why, which product facts
  they need on every metric (such as the version), and any dimension derived from a label's value.
  Ask for specific tag names only when the caller wants them.
- **Turning things off**: which areas users must be able to turn off (typical candidates: runtime
  and process metrics such as Go, Node.js, or JVM; debug or internal families; high-cardinality
  families), and the default for each.
- **Design choices**: the check interval, installation sizes, whether production endpoints are
  protected, unified service tagging, and latency percentiles across hosts or not.
- **Compatibility**: whether a legacy integration or community check exists whose names, tags, or
  namespace users depend on. If so, collect the exact names to keep.
- **Logs**: wanted or not.
- **Versions**: the supported range.

## Lab needs (for the hand-off)

Not part of the PRD. From the research and the agreed scope, work out what a lab must run so every
in-scope family and dimension appears: the image tag, the customer setup from the PRD,
connected backends, the modes in scope (for example queue mode), and the workload or traffic that
makes counters, histograms, and event-driven families emit. Note each in-scope family no lab can
produce. The hand-off carries this list, with what the chosen flow needs from the lab (`flows.md`).

## Checklist

- Components are stated, and the customer setup gives the setting, path, and port of each endpoint.
- Each use case says what users need to see or alert on, and the dimensions they slice by.
- Dimensions users do not want carry their reason.
- Each area users can turn off states its default.
- Design choices give the check interval in seconds, installation sizes, endpoint protection, the
  unified service tagging decision, and the histogram decision.
- Compatibility is stated: the names to keep, or none.
- Logs are stated as in scope or out of scope.
- No change shapes for a default build (drop, rename, exclude, copy, force), and no option names
  unless the caller wants them, with the reason.
