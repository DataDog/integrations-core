# HTTP API integrations

The integration polls a product API over HTTP or HTTPS on each check run and turns what it reads
into metrics, and optionally events and logs. The API can be of any style or format: REST and JSON,
an XML API, GraphQL, JSON-RPC, or SOAP.

## Decisions the PRD settles

- **Use cases in scope**, by group, with the dimensions users slice each group by.
- **Optional signals**: wanted only if the API supports a reliable interpretation.
- **Events and logs**: whether they are wanted, which ones, and whether they are on by default.
- **Setup the customer provides**: what the customer must create or enable (a read-only account or
  key, a feature that is off by default, a read-only server).
- **Design choices**: the default check interval in seconds; typical and large installation sizes;
  which levels of the product's hierarchy users can filter, and whether a level can be scoped within
  a parent; whether limits apply per parent or globally; the auth scheme and the least-privileged
  setup to document; whether unified service tagging comes from product resources.
- **Compatibility**: names or options to keep from an older integration, script, or community check.
- **Versions, editions, deployment models**, and what is out of scope.

## Research

Besides the core research, look up and verify. Use what you find to ask better questions and to
state product facts; do not turn it into instructions for the builder.

- **API style and format**: REST and JSON, XML, GraphQL, JSON-RPC, SOAP, or another style over HTTP.
  It goes into the PRD's opening. If the product is not monitored over HTTP at all (for example
  gRPC, raw TCP, or SNMP), or only pushes data through webhooks, this type does not fit.
- **The API reference and any schema the product publishes**: an OpenAPI document, a WSDL, or a
  GraphQL schema, public or served by the product itself. Link the reference and the schema in the
  PRD.
- **Authentication**: the scheme (API key header, bearer token, basic auth, a session login, OAuth
  client credentials), and the least-privileged role or setup that can read what the integration
  needs. Flag early, before the interview, any auth that needs a client certificate (mTLS), a
  signature computed for each request (HMAC or SigV4 style), or an interactive browser login: it is
  hard to automate and to reproduce in a lab, so tell the caller and list it as a risk at hand-off.
- **Rate limits, quotas, and pagination**: they inform the check interval and the installation sizes
  you recommend. A documented rate limit is a product fact the PRD may state next to the check
  interval; pagination is the builder's business and stays out.
- **Where the product writes its logs**: a documented file path, or standard output only, and
  whether the API serves logs, per item or as a stream.
- **Deployment models and editions**, and whether they expose the same API.
- **Setup**: settings the customer must change for the integration to work (a feature off by
  default, a read-only mode, a role to create).
- **A documentation page for each concept behind an in-scope use case, event category, or log type**
  (for example jobs, health checks, audit events, queues). Do this after the interview, once the
  scope is known.

## Interview topics

Settle each topic by research when you can; ask the rest. Record each answer as a use case or a
decision in the caller's terms.

### Use cases and scope (the most important part)

Ask as a multi-select which use-case groups are in scope, with options tailored to the product. The
groups to consider:

- **Availability and health**: the API itself, and the product's nodes or components.
- **Inventory**: what exists (for example repositories, queues, clusters), and the settings or
  states users care about (a maintenance mode, a disabled flag, a configured capacity).
- **Capacity and limits**: license limits, concurrency caps, queue capacity, quota usage.
- **In-flight work**: what is queued, running, or waiting now, and **how long it has been there**.
  Users alert on stuck work, which durations measured after completion cannot show.
- **Outcomes of completed work**: success and failure counts, durations, and throughput.
- **Releases and versions**: which product version runs, and which release or version a unit of work
  carried, when the product has releases.
- **What users already alert on**: vendor-recommended health checks, common dashboards, or runbooks.
  They tell you which use cases matter; the PRD does not include monitors or dashboards.

Always consider in-flight work age, even if the caller leaves it out.

For each selected group, settle the **dimensions** users need to slice or filter it by (for example
environment, region, owner, or type), offering the ones the docs show the product has.

Then ask which additional signals are **optional**: wanted only if the API supports a reliable
interpretation. Never list as optional something the caller already selected.

### Events and logs

- **Datadog events**: wanted or not, which categories (for example state changes, audit,
  security-relevant), and whether they are off by default (the usual choice).
- **Logs fetched through the API**: wanted or not, and which ones.
- **Local logs**: whether users want to collect the product's log files, or its container logs when
  it logs to standard output, with the Agent.

### Design choices

- The default check interval, in seconds (for example 15 or 60).
- Typical and large installation sizes, in the product's terms (for example spaces, projects, and
  targets; runs per day).
- Which levels need include and exclude filters, and whether users must scope a level within a
  specific parent (for example, repositories within one organization), not only with patterns
  applied everywhere.
- Whether limits apply per parent or globally. Per parent stops one large parent from crowding out
  the others; global is simpler.
- Auth: confirm the scheme when research found several valid ones, and the least-privileged setup
  to document.
- Unified service tagging: whether `service`, `env`, and `version` should come from product
  resources (for example `version` from a release), or not at all.

### Compatibility

Whether an older integration, script, or community check exists whose metric names or options users
rely on. If so, collect the names to keep.

### Out of scope

Editions, deployment models, features, or signals to exclude explicitly (for example, the SaaS
edition when only self-hosted can be tested, or API log polling).

## Lab needs (for the hand-off)

Not part of the PRD. From the research and the agreed scope, work out what a lab must exercise so
every in-scope use case can be tested: the product version and edition, the customer setup from the
PRD, the workload (including failures and in-flight or stuck work), each state and dimension in
scope, more than one node or instance when users see them separately, more than one parent when
scoping or limits are per parent, a way to trigger each event category, log output the Agent can
read, the optional signals, and host secrets the product needs (for example a license), by variable
name. Note each in-scope signal no lab can produce (for example, a feature only the SaaS edition
has). The hand-off carries this list.

## Checklist

- The opening names the API style and format.
- In-flight work age is in scope or explicitly out of scope.
- Each in-scope use-case group lists the dimensions users slice it by, where the caller named any.
- Optional signals do not repeat anything required.
- Events state whether they are on by default; logs say which sources are wanted.
- The setup the customer provides is stated, or that none is needed.
- Design choices give the check interval in seconds, installation sizes, the levels with filters
  and any scoping within a parent, the limit decision (per parent or global), the auth scheme with
  the least-privileged setup, and the unified service tagging decision.
- Compatibility is stated: the names or options to keep, or none.
- The documentation links include the API reference, the auth docs, and a page for each in-scope
  concept that has one, with no instructions.
- No request budgets, limit warnings, error or pagination handling, or other build instructions.
