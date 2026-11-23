# Writing the PRD

## Principles

- **Record decisions, not instructions to decide.** Each topic is either decided ("apply each
  limit per space") or explicitly left open to the builder ("no preference on tags"). Do not write
  "state whether…" or "decide if…": the checklists are for you, not text for the PRD.
- **Intent, not implementation.** Say what users need to see, alert on, or turn off, and why ("users
  alert on a deployment stuck in the queue", "users must be able to turn off Go runtime metrics").
  Avoid saying how to build it: which requests to make, what requests per run grow with, how to derive
  a tag, what to warn about, how to handle errors, or which changes to make to a default build.
- **Product facts are welcome.** A fact the builder could miss belongs in the PRD when it shapes a
  use case or a design choice: an auth scheme and header, a documented rate limit, a state name the
  product uses, a setting that turns a feature on, an edition that lacks an API.
- **Names are allowed, not required.** Include a metric, tag, or option name when the caller wants
  it, when users already know it (for example, the product's own setting names, or names to keep for
  compatibility), or when it makes a use case clearer. A PRD does not need to name metrics.
- **No assets outside the integration**: no monitors, dashboards, SLOs, or notebooks.
- **Requirements a flow forbids or cannot meet** (for example, a service check, or logs when the
  chosen flow cannot collect them) are still recorded when the caller requires them. The hand-off
  tells the caller which ones the flow cannot honor.
- **No secret values.** Name the setting or variable that holds a secret when it matters, never its
  value.
- **Each item once,** in one place.
- **Plain, direct sentences.** No marketing language, no filler, no references to the interview or
  to files the flow cannot read.
- **No fixed length.** There is no fixed length: a product with many signals and
  dimensions needs a longer PRD than a simple one.

## What a PRD covers

There is no fixed template. Each product is different: choose the headings, their order, and how
much each one says to fit the product, merging topics that have little to say and splitting the
ones that have a lot. The examples show a few shapes; use them for tone and level of detail, not as
a structure to copy.

Whatever the shape, a PRD covers these topics. The type's adapter adds its own.

- **What to build**: the display name in the title, then the product, its deployment model, how it
  is monitored, and the integration directory. A sentence such as "Build a Datadog Agent
  integration for self-hosted <Product> using its JSON REST API. Use `<directory>` as the
  integration directory." is enough. Name a metric namespace only when it differs from the
  directory, with the reason (for example, compatibility with an older integration).
- **Who uses the product and why they monitor it**, in a sentence or two.
- **Use cases and scope**: what users need to see and alert on (metrics, events, logs), with the
  dimensions they slice by.
- **Versions, editions, and deployment models** targeted.
- **Setup the customer provides**: the product configuration the integration needs and that the
  customer must change or enable (for example, enable a metrics endpoint, create a read-only API
  key, start a read-only server). The integration does not change it; the customer does.
- **Design choices**: the default check interval; typical and large installation sizes; which
  levels users can filter, and whether they can scope a level within a parent; whether limits apply
  per parent or globally; auth as product facts (the scheme, and the least-privileged setup to
  document); whether unified service tagging comes from product resources. Leave out the ones that
  do not apply to the product.
- **Compatibility**: names or options to keep from an older integration, script, or community
  check, or that there is none.
- **Out of scope**: editions, deployment models, features, and signals excluded on purpose.
- **Documentation links**: titles and exact URLs, with no instructions on how to use them.

When a topic has nothing to say (no setup, no compatibility constraint), one line is enough, inside
another section if that reads better.

## Core checklist

- The display name and directory are valid, and the directory exists neither in the
  working tree nor on the default branch, or the caller decided how to treat the existing one.
- Every answer is carried with its full meaning, and every item that did not come from the caller or
  the requirements source is in the assumptions list you give in the chat (check this when you write
  the draft and for each later change).
- Every topic in "What a PRD covers" and in the adapter is covered, explicitly out of scope, or
  does not apply to the product.
- No open decisions.
- Each use case is concrete enough to tell whether the built integration meets it. Requirements the
  flow cannot honor are kept if the caller keeps them, and flagged in the chat.
- No rules for agents, no generic engineering rules, and no implementation details.
- No monitors, dashboards, or other assets.
- Every link was opened, is exact, and is pinned to a version where it depends on one; the
  documentation links come with no instructions.
- No secret values anywhere.
- No item is stated twice.
